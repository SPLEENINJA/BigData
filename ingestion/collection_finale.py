from pymongo import MongoClient

client = MongoClient("mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin")

db = client["kbo"]

collection = db["enterprise_finale"]

cursor = db.enterprise.find({"EnterpriseNumber": {"$exists": True}}, {"_id": 0, "EnterpriseNumber": 1})

pipeline = [
    {
        "$lookup": {
            "from": "denomination",
            "localField": "EnterpriseNumber",
            "foreignField": "EntityNumber",
            "as": "denominations"
        }
    },
    {
        "$lookup": {
            "from": "address",
            "localField": "EnterpriseNumber",
            "foreignField": "EntityNumber",
            "as": "addresses"
        }
    },
    {
        "$lookup": {
            "from": "activity",
            "localField": "EnterpriseNumber",
            "foreignField": "EntityNumber",
            "as": "activities"
        }
    },
    {
        "$lookup": {
            "from": "contact",
            "localField": "EnterpriseNumber",
            "foreignField": "EntityNumber",
            "as": "contacts"
        }
    },
    {
        "$lookup": {
            "from": "establishment",
            "localField": "EnterpriseNumber",
            "foreignField": "EnterpriseNumber",
            "as": "establishments"
        }
    },
    {
        "$merge": {
            "into": "enterprise_finale2",
            "whenMatched": "replace",
            "whenNotMatched": "insert"
        }
    }
]

db.enterprise.aggregate(pipeline)
