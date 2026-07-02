from pathlib import Path
import pandas as pd
import numpy as np
from pymongo import MongoClient
import csv

DATA_DIR = Path(r"C:\Users\capel\Desktop\IPSSI\Semaine22 - Big Data\notebook solo\KboOpenData_0404_2026_06_28_Full")


client = MongoClient("mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin")
db = client["kbo"]

FILES = {
    "enterprise": "enterprise.csv",
    "denomination": "denomination.csv",
    "address": "address.csv",
    "activity": "activity.csv",
    "contact": "contact.csv",
    "establishment": "establishment.csv",
    "branch": "branch.csv",
    "code": "code.csv",
    "meta": "meta.csv",
}

def load_csv(path):
    return pd.read_csv(path, dtype=str)

def insert_csv_to_mongo(df, collection):
    if df.empty:
        return 0

    records = df.to_dict("records")

    # clean NaN
    for r in records:
        for k in r:
            if pd.isna(r[k]):
                r[k] = None

    res = collection.insert_many(records, ordered=False)
    return len(res.inserted_ids)


def main():
    
    total = 0

    for name, file in FILES.items():

        print(f"Ingestion {name}...")

        df = load_csv(DATA_DIR / file)

        col = db[name]

        inserted = insert_csv_to_mongo(df, col)

        print(f"{name} -> {inserted} lignes insérées")

        total += inserted

    print(f"\nTOTAL INSÉRÉ : {total}")


if __name__ == "__main__":
    main()
