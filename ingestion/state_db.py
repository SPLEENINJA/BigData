from pymongo import MongoClient

client = MongoClient("mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin")

# dbcible = client["strator"]
db = client["kbo"]
collection = db["enterprise"]

BATCH_SIZE = 10_000
batch = []


# state_db = dbcible["state_db"]
state_db = db["state_db"]
state_db.drop()
state_db.create_index("EnterpriseNumber", unique=True)


hotel_codes = {55100, 55201, 55202, 55203, 55204, 55209, 55300, 55400, 55900}


excluded_juridical_forms = {
    "110", "114", "116", "117",
    "301", "302", "303",
    "310", "320", "330", "340", "350",
    "400", "411", "412", "413", "414", "415", "416", "417", "418", "419", "420"
}


cursor = db["enterprise_silver"].find(
    {
        "Status": "AC",
        "TypeOfEnterprise": "2",
        "JuridicalForm": {"$nin": list(excluded_juridical_forms)},
        "activities.NaceCode": {"$in": list(map(str, hotel_codes))}
    },
    {
        "_id": 0,
        "EnterpriseNumber": 1,
        "Status": 1,
        "JuridicalForm": 1,
        "activities": 1
    }
)
   

batch = []

for doc in cursor:

    activities = [
        act
        for act in doc.get("activities", [])
        if (
            act.get("Classification") == "MAIN"
            and int(act.get("NaceCode")) in hotel_codes
        )
    ]

    if not activities:
        continue

    batch.append({
        "EnterpriseNumber": doc["EnterpriseNumber"],
        "Status": "pending"
    })

    if len(batch) == BATCH_SIZE:
        state_db.insert_many(batch)
        print(f"{len(batch)} documents insérés")
        batch.clear()

if batch:
    state_db.insert_many(batch)

print(f"Total : {state_db.count_documents({})}")