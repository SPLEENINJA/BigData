from hdfs import InsecureClient
from io import BytesIO
import fitz
import pdfplumber
import pandas as pd

client = InsecureClient(
    "http://localhost:9870",
    user="root"
)

enterprise = "0400039084"

# Liste des fichiers de cette entreprise
files = client.list(f"/kbo/pdfs/{enterprise}")

# Lire le premier fichier
pdf_path = f"/kbo/pdfs/{enterprise}/{files[0]}"

with client.read(pdf_path) as reader:
    pdf_bytes = reader.read()

pdf_file = BytesIO(pdf_bytes)
doc = fitz.open(stream=pdf_bytes, filetype="pdf")


dfs = []

with pdfplumber.open(pdf_file) as pdf:

    for page_num in [2, 3, 4]:      # pages 3-4-5 (index commence à 0)

        page = pdf.pages[page_num]

        tables = page.extract_tables()

        print(f"Page {page_num+1} : {len(tables)} tableau(x)")

        for table in tables:

            df = pd.DataFrame(table)

            dfs.append(df)

            print(df.head())
print(doc[0].get_text())

hdfs_path = "/kbo/pdfs/0400039084/2024_2025-00299850.pdf"
local_path = r"C:\Users\capel\Downloads\2024_2025-00299850.pdf"

client.download(
    hdfs_path,
    local_path,
    overwrite=True
)

print("Téléchargement terminé.")

df = tables[1]      # deuxième tableau de la page

codes = df.iloc[1, 0].split("\n")
values = df.iloc[1, 1].split("\n")
previous = df.iloc[1, 2].split("\n")

mapping = {}

for code, value, prev in zip(codes, values, previous):
    mapping[code] = {
        "current": value,
        "previous": prev
    }

def to_float(x):

    if not x:
        return None

    return float(
        x.replace(".", "")
         .replace(",", ".")
    )

gold = {

    "70": "chiffre_affaires",

    "60": "achats",

    "71": "variation_stocks",

    "9901": "ebit",

    "9904": "resultat_net",

    "100": "capital_souscrit"

}

result = {}

for code, champ in gold.items():

    if code in mapping:

        result[champ] = to_float(
            mapping[code]["current"]
        )

result["dettes_financieres"] = (
    to_float(mapping["17"]["current"])
    +
    to_float(mapping["43"]["current"])
)

result["tresorerie"] = (
    to_float(mapping["54"]["current"])
    +
    to_float(mapping["55"]["current"])
)


result["tresorerie"] = (
    to_float(mapping["54"]["current"])
    +
    to_float(mapping["55"]["current"])
)


print(pd.DataFrame([result]))