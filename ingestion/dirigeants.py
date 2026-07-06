import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import pandas as pd

session = requests.Session()
client = MongoClient(
        "mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin"
    )

db = client["kbo"]
collection = db["enterprise_gold"]


BASE_URL = "https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html"

url = BASE_URL

def get_kbo_page(numero):
    try:
        response = session.get(
            "https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html",
            params={"lang": "fr", "nummer": numero},
            timeout=10
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    except Exception as e:
        print("KBO ERROR:", e)
        return BeautifulSoup("", "html.parser")


def table_to_dataframe(soup, numero_bce=None):


    results = []

    capture = False

    for tr in soup.find_all("tr"):

        h2 = tr.find("h2")

        if h2 and "Fonctions" in h2.get_text(strip=True):
            capture = True
            continue

        if capture and h2:
            break

        if capture:

            tds = tr.find_all("td")

            if len(tds) == 3:

                results.append({
                    "Fonction": tds[0].get_text(" ", strip=True),
                    "Nom": tds[1].get_text(" ", strip=True),
                    "Depuis": tds[2].get_text(" ", strip=True)
                })

    df = pd.DataFrame(results)

    if numero_bce:
        df.insert(0, "NumeroBCE", numero_bce)

    return df

# dfs = []

def scrape_directors(numero: str):

    soup = get_kbo_page(numero)

    df = table_to_dataframe(
        soup,
        numero_bce=numero
    )

    if df.empty:
        return []

    df[["Nom", "Prenom"]] = (
        df["Nom"]
        .str.split(",", n=1, expand=True)
    )

    ordre = [
        "NumeroBCE",
        "Nom",
        "Prenom",
        "Fonction",
        "Depuis"
    ]
    
    df = df[ordre]

    df = df.fillna("")
    
    records = df.to_dict("records")

    collection.update_one(
        {"enterprise_number": numero},
        {
            "$set": {
                "Directors": records
            }
        },
        upsert=False
    )
    
    return records