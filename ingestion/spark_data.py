from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.functions import regexp_replace
from pyspark.sql.functions import sum
from pyspark.sql.functions import (
    input_file_name,
    regexp_extract
)

from pyspark.sql.functions import when

spark = (
    SparkSession.builder
    .master("spark://spark-master:7077")
    .appName("KBO")
    .getOrCreate()
)



df = (
    spark.read
    .option("header", False)
    .csv("hdfs://namenode:9000/kbo/csv/*/*.csv")
    .toDF("code", "value")
    .withColumn("filename", input_file_name())
    .withColumn(
        "enterprise",
        regexp_extract("filename", r"/csv/([0-9]{10})/", 1)
    )
    .withColumn(
        "year",
        regexp_extract("filename", r"/([0-9]{4})_", 1).cast("int")
    )
)

codes = [
    "70",
    "60",
    "71",
    "9901",
    "9904",
    "54",
    "55",
    "17",
    "43",
    "100"
]

df_codes = df.filter(col("code").isin(codes))


df_treso = (
    df
    .filter(col("code").rlike("^54$|^55$"))
    )

df_fp = (
    df
    .filter(col("code").rlike("^1[0-5]$"))
)

df_dettes = (
    df.filter(col("code").rlike("^17$|^43$"))
)


df_codes = (
    df_codes
    .withColumn(
        "value",
        regexp_replace("value", ",", ".").cast("double")
    )
)
df_fp = (
    df_fp
    .withColumn(
        "value",
        regexp_replace("value", ",", ".").cast("double")
    )
)
df_treso = (
    df_treso
    .withColumn(
        "value",
        regexp_replace("value", ",", ".").cast("double")
    )
)
df_dettes = (
    df_dettes
    .withColumn(
        "value",
        regexp_replace("value", ",", ".").cast("double")
    )
)


fonds_propres = (
    df_fp
    .groupBy("enterprise","year")
    .agg(sum("value").alias("fonds_propres"))
)
tresorerie = (
    df_treso
    .groupBy("enterprise", "year")
    .agg(sum("value").alias("tresorerie"))
)
dettes = (
    df_dettes
    .groupBy("enterprise", "year")
    .agg(sum("value").alias("dettes_financieres"))
)


pivot = (
    df_codes
    .groupBy("enterprise","year")
    .pivot("code", codes)
    .sum("value")
)

pivot = (
    pivot
    .withColumnRenamed("70","chiffre_affaires")
    .withColumnRenamed("60","achats")
    .withColumnRenamed("71","variation_stocks")
    .withColumnRenamed("9901","ebit")
    .withColumnRenamed("9904","resultat_net")
    .withColumnRenamed("100","capital_souscrit")
    .fillna(0)
)

gold = (
    pivot
    .join(fonds_propres, ["enterprise", "year"], "left")
    .join(tresorerie, ["enterprise", "year"], "left")
    .join(dettes, ["enterprise", "year"], "left")
)
gold = (
    gold.fillna(
        0,
        subset=[
            "fonds_propres",
            "tresorerie",
            "dettes_financieres",
        ]
    )
)
gold = (
    gold
    .withColumn(
        "marge_brute",
        col("chiffre_affaires")
        - col("achats")
        + col("variation_stocks")
    )
    .withColumn(
        "marge_nette",
        when(
            col("chiffre_affaires") != 0,
            col("resultat_net") / col("chiffre_affaires") * 100
        )
    )
    .withColumn(
    "roe",
    when(
        col("fonds_propres") != 0,
        col("resultat_net") / col("fonds_propres") * 100
    )
    )
    .withColumn(
        "ratio_liquidite",
        when(
            col("dettes_financieres") != 0,
            col("tresorerie") / col("dettes_financieres")
        )
    )
    .withColumn(
        "taux_endettement",
        when(
            col("fonds_propres") != 0,
            col("dettes_financieres") / col("fonds_propres") * 100
        )
    )
)

import math

def clean_row(row):
    cleaned = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = 0
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = 0
        else:
            cleaned[k] = v
    return cleaned

def save_partition(rows):

    client = MongoClient(
        "mongodb://admin:admin123@mongodb:27017/?authSource=admin"
    )

    db = client["kbo"]
    collection = db["enterprise_gold"]

    for row in rows:

        row = clean_row(row.asDict())

        enterprise = row.get("enterprise")
        year = row.get("year")

        if not enterprise or not year:
            continue

        collection.update_one(
            {"enterprise_number": enterprise},
            {
                "$set": {
                    f"exercices.{year}": {
                        "chiffre_affaires": row.get("chiffre_affaires", 0),
                        "achats": row.get("achats", 0),
                        "variation_stocks": row.get("variation_stocks", 0),
                        "ebit": row.get("ebit", 0),
                        "resultat_net": row.get("resultat_net", 0),
                        "fonds_propres": row.get("fonds_propres", 0),
                        "capital_souscrit": row.get("capital_souscrit", 0),
                        "tresorerie": row.get("tresorerie", 0),
                        "dettes_financieres": row.get("dettes_financieres", 0),
                        "marge_brute": row.get("marge_brute", 0),
                        "marge_nette": row.get("marge_nette", 0),
                        "roe": row.get("roe", 0),
                        "ratio_liquidite": row.get("ratio_liquidite", 0),
                        "taux_endettement": row.get("taux_endettement", 0)
                    }
                }
            },
            upsert=True
        )

    client.close()

gold.show(truncate=False)

gold.foreachPartition(save_partition)