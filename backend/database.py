from pymongo import MongoClient

client = MongoClient(
    "mongodb://admin:admin123@127.0.0.1:27018/?authSource=admin"
)

db = client["kbo"]

silver = db["enterprise_silver"]
gold = db["enterprise_gold"]

