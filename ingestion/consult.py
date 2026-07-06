import time
import requests
import pandas as pd
from io import StringIO
from pathlib import Path
from requests.exceptions import HTTPError

from ingestion import state_db

from hdfs import InsecureClient

client = InsecureClient(
    "http://localhost:9870",
    user="root"
)

class LocalClient:
    def __init__(self, root):
        self.root = Path(root)

    def makedirs(self, path):
        (self.root / path.lstrip("/")).mkdir(parents=True, exist_ok=True)

    def write(self, path, overwrite=True, encoding="utf-8"):
        file = self.root / path.lstrip("/")
        file.parent.mkdir(parents=True, exist_ok=True)
        return open(file, "w", encoding=encoding)
    
client = LocalClient(r"C:\Users\capel\Desktop\IPSSI\Semaine22 - Big Data")
import itertools

PROXIES = [
    "socks5h://127.0.0.1:9050",
    "socks5h://127.0.0.1:9052",
    "socks5h://127.0.0.1:9054",
]

proxy_cycle = itertools.cycle(PROXIES)

BASE = "https://consult.cbso.nbb.be/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


def make_session(enterprise_number: str) -> requests.Session:

    proxy = next(proxy_cycle)
    print(f"Proxy utilisé : {proxy}")

    session = requests.Session()

    session.proxies = {
        "http": proxy,
        "https": proxy,
    }

    session.headers.update(HEADERS)

    page_url = f"https://consult.cbso.nbb.be/consult-enterprise/{enterprise_number}"
    session.headers.update({"Referer": page_url})

    session.get(page_url)

    return session

def get_deposits(session: requests.Session, enterprise_number: str) -> list:
    url = (
        f"{BASE}/rs-consult/published-deposits"
        f"?page=0&size=10&enterpriseNumber={enterprise_number}"
        f"&sort=periodEndDate,desc&sort=depositDate,desc"
    )
    r = session.get(url)
    r.raise_for_status()
    data = r.json()
    print(f"Found {data['totalElements']} filings ({data['totalPages']} pages). Loading first {len(data['content'])}.")
    return data["content"]

def download_csv_to_hdfs(session, deposit):
    deposit_id = deposit["id"]
    year = deposit["periodEndDateYear"]
    enterprise = deposit["enterpriseNumber"]
    reference = deposit["reference"]
    hdfs_path = f"/kbo/csv/{enterprise}/{year}_{reference}.csv"
    url = f"{BASE}/external/broker/public/deposits/consult/csv/{deposit_id}"
    r = session.get(url)
    r.raise_for_status()
    client.makedirs(f"/kbo/csv/{enterprise}")
    with client.write(
        hdfs_path,
        overwrite=True,
        encoding="utf-8"
    ) as writer:
        writer.write(r.text)
    print(f"CSV uploadé : {hdfs_path}")
    return r.text

def download_pdf_to_hdfs(session: requests.Session, deposit: dict):
    deposit_id = deposit["id"]
    year       = deposit["periodEndDateYear"]
    enterprise = deposit["enterpriseNumber"]
    reference  = deposit["reference"]
    hdfs_path = f"/kbo/pdfs/{enterprise}/{year}_{reference}.pdf"
    url = f"{BASE}/external/broker/public/deposits/pdf/{deposit_id}"
    print(f"Téléchargement HDFS : {url} -> {hdfs_path}")
    r = session.get(url, stream=True)
    r.raise_for_status()
    
    with client.write(hdfs_path, overwrite=True) as writer:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                writer.write(chunk)

    print(f"PDF uploaded to HDFS: {hdfs_path}")
    return hdfs_path

def parse_csv(csv_text: str) -> dict:
    df = pd.read_csv(StringIO(csv_text), header=None, skiprows=1)
    codes = {}
    for _, row in df.iterrows():
        key = str(row[0]).strip()
        try:
            codes[key] = float(row[1])
        except (ValueError, TypeError):
            codes[key] = row[1]
    return codes

def compute_kpis(codes: dict) -> dict:
    def get(code):
        return codes.get(code, 0.0)

    omzet        = get("70")
    cogs         = get("60")
    depreciation = get("630")
    ebit         = get("9901")
    net_profit   = get("9904")
    cash         = get("54/58")
    equity       = get("10/15")
    total_assets = get("20/58")
    fin_debt     = get("17") + get("43")
    gross_profit = omzet - cogs
    ebitda       = ebit + depreciation

    def pct(num, denom):
        return round(num / denom * 100, 2) if denom else None

    return {
        "entity":           codes.get("Entity name"),
        "period_end":       codes.get("Accounting period end date"),
        "chiffre_affaires": omzet,
        "marge_brute":      gross_profit,
        "ebitda":           ebitda,
        "ebit":             ebit,
        "resultat_net":     net_profit,
        "taux_marge_brute": pct(gross_profit, omzet),
        "taux_ebitda":      pct(ebitda, omzet),
        "marge_nette":      pct(net_profit, omzet),
        "tresorerie":       cash,
        "dettes_fin":       fin_debt,
        "dette_nette":      fin_debt - cash,
        "fonds_propres":    equity,
        "total_actif":      total_assets,
        "autonomie_fin":    pct(equity, total_assets),
    }

def get_all_kpis(enterprise_number: str) -> list[dict]:

    print(f"\nRecherche des dépôts pour {enterprise_number}")

    session = make_session(enterprise_number)

    deposits = get_deposits(session, enterprise_number)

    print(f"{len(deposits)} dépôts trouvés")

    results = []

    for deposit in deposits:
        year = deposit["periodEndDateYear"]
        if year < 2021:
            break
        deposit_id = deposit["id"]
    
        print(f"  Processing {year} (id={deposit_id})...")

        # ---------------- PDF ----------------   

        try:
            download_pdf_to_hdfs(session, deposit)

        except HTTPError:
            # on laisse la boucle principale gérer le 400/429
            raise

        except Exception as e:
            print(f"    ✗ PDF failed for {year}: {e}")

        time.sleep(0.3)

        # ---------------- CSV ----------------

        if deposit.get("migration"):
            print(f"    Skipping CSV for {year} (legacy/migrated filing)")
            continue

        try:
            csv_text = download_csv_to_hdfs(session, deposit)

            codes = parse_csv(csv_text)

            kpis = compute_kpis(codes)
            kpis["year"] = year
            kpis["reference"] = deposit["reference"]

            results.append(kpis)

        except HTTPError:
            raise

        except Exception as e:
            print(f"    ✗ CSV failed for {year}: {e}")

        time.sleep(0.3)

    return results

def worker(worker_id: int):
    while True:

        enterprise_number = "0400039084"


        try:

            kpis = get_all_kpis(enterprise_number.replace(".", ""))

            if kpis:

                df = (
                    pd.DataFrame(kpis)
                    .set_index("year")
                    .sort_index(ascending=False)
                )

                print(df[[
                    "entity",
                    "period_end",
                    "chiffre_affaires",
                    "ebitda",
                    "resultat_net",
                    "marge_nette",
                    "autonomie_fin"
                ]])

                state_db.update_one(
                    {"EnterpriseNumber": enterprise_number},
                    {"$set": {"Status": "done"}}
                )

            else:

                print(f"{enterprise_number} -> Aucun KPI trouvé.")

                state_db.update_one(
                    {"EnterpriseNumber": enterprise_number},
                    {"$set": {"Status": "no_data"}}
                )

        except HTTPError as e:

            status = e.response.status_code

            if status == 400:
                print(f"{enterprise_number} -> Erreur 400 (entreprise sans dépôt ou requête invalide)")

                state_db.update_one(
                    {"EnterpriseNumber": enterprise_number},
                    {"$set": {"Status": "no_data"}}
                )

            elif status == 429:
                print("429 -> changement de proxy Tor")

                state_db.update_one(
                    {"EnterpriseNumber": enterprise_number},
                    {"$set": {"Status": "pending"}}
                )

                time.sleep(3)
                continue

            else:
                print(f"{enterprise_number} -> HTTP {status}")



        except Exception as e:

            print(f"{enterprise_number} -> {e}")




from concurrent.futures import ThreadPoolExecutor

NB_WORKERS = 3

with ThreadPoolExecutor(max_workers=NB_WORKERS) as executor:
    for i in range(NB_WORKERS):
        executor.submit(worker, i)


