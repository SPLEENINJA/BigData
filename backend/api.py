from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from backend.database import gold,silver
from ingestion.dirigeants import scrape_directors as scrape_directors_kbo

router = APIRouter()

import re

def normalize_bce(number: str) -> str:
    return re.sub(r"\D", "", number)
import math

import math

def sanitize(value):

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    if isinstance(value, dict):
        return {
            k: sanitize(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize(v)
            for v in value
        ]

    return value

@router.get("/search")
def search(q: str):

    results = gold.find(
        {
            "$or": [
                {
                    "enterprise_number": {
                        "$regex": q,
                        "$options": "i"
                    }
                },
                {
                    "Name": {
                        "$regex": q,
                        "$options": "i"
                    }
                }
            ]
        },
        {
            "_id": 0
        }
    )

    return list(results)

@router.get("/enterprise/{enterprise_number}")
def enterprise(enterprise_number: str):

    enterprise_number = normalize_bce(enterprise_number)

    gold_doc = gold.find_one(
        {"enterprise_number": enterprise_number},
        {"_id": 0}
    )

    if not gold_doc:
        raise HTTPException(404, "Entreprise introuvable")

    # silver lookup safe
    silver_number = f"{enterprise_number[:4]}.{enterprise_number[4:7]}.{enterprise_number[7:]}"

    silver_doc = silver.find_one(
        {"EnterpriseNumber": silver_number},
        {"_id": 0}
    )

    name = ""

    if silver_doc:
        denominations = silver_doc.get("denominations", [])

        if isinstance(denominations, list) and len(denominations) > 0:
            name = denominations[0].get("Denomination", "")

        elif isinstance(denominations, dict):
            name = denominations.get("Denomination", "")

    gold_doc["name"] = name
    
    return {
            "gold": sanitize(jsonable_encoder(gold_doc))
    }

@router.get("/enterprise/{enterprise_number}/directors")
def directors(enterprise_number: str):
    enterprise_number = normalize_bce(enterprise_number)
    doc = gold.find_one(
        {"enterprise_number": enterprise_number},
        {
            "_id": 0,
            "Directors": 1
        }
    )

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Entreprise introuvable"
        )

    return doc


from fastapi import BackgroundTasks


@router.post("/enterprise/{enterprise_number}/directors/scrape")
def scrape_directors_endpoint(
    enterprise_number: str,
    background_tasks: BackgroundTasks
):
    enterprise_number = normalize_bce(enterprise_number)
    doc = gold.find_one(
        {"enterprise_number": enterprise_number},
        {"_id": 0}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    background_tasks.add_task(scrape_and_save_directors, enterprise_number)

    return {"status": "scraping_started"}

def scrape_and_save_directors(enterprise_number: str):
    try:
        directors = scrape_directors_kbo(enterprise_number)

        gold.update_one(
            {"enterprise_number": enterprise_number},
            {"$set": {"Directors": directors}},
            upsert=False
        )
    except Exception as e:
        print("SCRAPE ERROR:", e)