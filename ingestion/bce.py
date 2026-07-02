from duckdb import df
from pymongo.errors import BulkWriteError
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from time import sleep
import pandas as pd


client = MongoClient("mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin")
db = client["kbo"]
collection = db["enterprise"]

cursor = collection.find(
    {},
    {"_id": 0, "EnterpriseNumber": 1}
)

NUMEROS = [
    str(doc["EnterpriseNumber"]).replace(".", "")
    for doc in cursor
    if doc.get("EnterpriseNumber")
]

a = len(NUMEROS)
print(f"Found {a} enterprise numbers in MongoDB collection.")

PROXIES = [
    "socks5h://127.0.0.1:9050",
    "socks5h://127.0.0.1:9052",
    "socks5h://127.0.0.1:9054",
]

import itertools

proxy_cycle = itertools.cycle(PROXIES)

BASE_URL = "https://kbopub.economie.fgov.be/kbopub/toonondernemingps.html"

FIELD_MAP = {
    "Numéro d'entreprise:": "EnterpriseNumber",
    "Statut:": "Status",
    "Situation juridique:": "LegalSituation",
    "Date de début:": "StartDate",
    "Dénomination:": "Name",
    "Adresse du siège:": "Address",
    "Numéro de téléphone:": "Phone",
    "Numéro de fax:": "Fax",
    "E-mail:": "Email",
    "Adresse web:": "Website",
    "Type d'entité:": "EntityType",
    "Forme légale:": "LegalForm",
    "Nombre d'unités d'établissement (UE):": "EstablishmentCount",
}

def get_kbo_page(numero: str) -> BeautifulSoup:
    """Télécharge et parse la fiche KBO d'une entreprise."""
    url = f"{BASE_URL}?lang=fr&ondernemingsnummer={numero}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-BE,fr;q=0.9"}
    proxy = next(proxy_cycle)

    resp = requests.get(
        url,
        headers=headers,
        proxies={"http": proxy, "https": proxy},
        timeout=15
    )
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def fiche_to_dataframe(soup, numero_bce):
    data = {v: None for v in FIELD_MAP.values()}
    data["NumeroBCE"] = numero_bce

    for tr in soup.find_all("tr"):
        if tr.find("h2"):
            continue
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        cle = tds[0].get_text(" ", strip=True)
        valeur = tds[-1].get_text(" ", strip=True)
        if not cle or "Pas de données" in valeur:
            continue
        if cle not in FIELD_MAP:
            continue
        data[FIELD_MAP[cle]] = valeur
        if cle.startswith("Nombre d'unités d'établissement"):
            break
    return pd.DataFrame([data])

# def insert_df_to_mongo(df, collection):
#     if df.empty:
#         return 0

#     records = df.where(pd.notna(df), None).to_dict("records")

#     try:
#         res = collection.insert_many(records, ordered=False)
#         return len(res.inserted_ids)

#     except BulkWriteError as e:
#         return e.details["nInserted"]

BATCH_SIZE = 100
collection_bce = db["bce"]

dfs = []
for numero in NUMEROS[:100]:
    
    soup = get_kbo_page(numero)
    dfs.append(
        fiche_to_dataframe(
            soup,
            numero_bce=numero
        )
    )

    # if len(dfs) == BATCH_SIZE:
    #     df_batch = pd.concat(dfs, ignore_index=True)
    #     nb = insert_df_to_mongo(df_batch, collection_bce)
    #     print(f"{nb} documents insérés.")

    #     dfs.clear()

    sleep(0.5)  

# if dfs:
#     df_batch = pd.concat(dfs, ignore_index=True)
#     nb = insert_df_to_mongo(df_batch, collection_bce)
#     print(f"{nb} documents insérés.")

print("Import terminé.")

data = pd.concat(dfs, ignore_index=True)
print(data)

