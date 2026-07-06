from pymongo import MongoClient

client = MongoClient("mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin")

db = client["kbo"]

collection = db["enterprise_silver"]
code_collection = db["code"]

source = db["enterprise_finale"]
silver = db["enterprise_silver"]

BATCH_SIZE = 10000
batch = []

status_lookup = {}
juridical_lookup = {}
nace_lookup = {}

for c in code_collection.find({}, {"_id": 0}):

    category = c.get("Category")
    code = c.get("Code")
    label = c.get("Description")

    if not code or not label:
        continue

    if category == "Status":
        status_lookup[code] = label

    elif category == "JuridicalForm":
        juridical_lookup[code] = label

    elif category.startswith("Nace"):
        nace_lookup.setdefault(code, label)


for ent in source.find({}, {"_id": 0}):

    if ent.get("StartDate"):
        j, m, a = ent["StartDate"].split("-")
        ent["StartDate"] = f"{a}-{m}-{j}"

    for est in ent.get("establishments", []):
        if est.get("StartDate"):
            j, m, a = est["StartDate"].split("-")
            est["StartDate"] = f"{a}-{m}-{j}"

    seen = set()
    activities = []

    for act in ent.get("activities", []):

        key = (
            act.get("NaceCode")
        )

        if key in seen:
            continue

        seen.add(key)
        activities.append(act)

    ent["activities"] = activities
      
    ent["StatusLabel"] = status_lookup.get(ent.get("Status"))

    ent["JuridicalFormLabel"] = juridical_lookup.get(
        ent.get("JuridicalForm")
    )

    # Labels activités
    for act in ent.get("activities", []):
        act["NaceLabel"] = nace_lookup.get(
            act.get("NaceCode")
        )
    
    ent["addresses"] = [
        adr
        for adr in ent.get("addresses", [])
        if adr.get("TypeOfAddress") == "REGO"
    ]

    ent["denominations"] = [
        den
        for den in ent.get("denominations", [])
        if den.get("TypeOfDenomination") == "001"
    ]

    batch.append(ent)

    if len(batch) == BATCH_SIZE:
        silver.insert_many(batch)
        batch.clear()

if batch:
    silver.insert_many(batch)