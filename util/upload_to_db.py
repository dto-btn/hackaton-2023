import os
import sys
from random import randint
import json

import pymongo
from dotenv import load_dotenv

load_dotenv()
DB_CONN = os.environ.get("DB_CONN")
DB_NAME = "hackaton"
COLLECTION_NAME = "brs-sample"

client = pymongo.MongoClient(DB_CONN)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

for filename in os.listdir("output/"):
    with open(os.path.join("output/", filename), 'r') as f:
        print(f"inserting {filename}")
        data = json.load(f)  
        collection.insert_one(data) 