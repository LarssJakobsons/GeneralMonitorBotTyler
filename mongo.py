import os
from dotenv import load_dotenv
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from beanie import init_beanie
from beanie.odm.documents import Document
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json


class Messages(Document):
    id: int
    channel_id: int
    attachments: list[str]
    content: str
    author_id: int
    long_date: datetime
    # short date will be in a format like this: yyyy-mm-dd
    short_date: str

class AutoUpdateChannel(Document):
    message_id: int

async def get_week(db, server):
    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=7)

    pipeline = [
        {"$match": {"long_date": {"$gte": start_date, "$lt": end_date}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$long_date"}},
                "count": {"$sum": 1},
            }
        },
    ]

    if server == "tyler":
        await init_beanie(database=db.data, document_models=[Messages])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[Messages])

    cursor = Messages.aggregate(pipeline)

    results = await cursor.to_list(None)

    if len(results) == 0:
        results_list = [{"date": start_date.strftime("%Y-%m-%d"), "count": 0}]
    else:
        results_list = [{"date": result["_id"], "count": result["count"]} for result in results]

    results = pd.DataFrame(results_list)
    results["date"] = pd.to_datetime(results["date"])
    results.set_index("date", inplace=True)
    results = results.reindex(pd.date_range(start=start_date, end=end_date)[:-1], fill_value=0)
    results = results.astype(int)
    return results


async def write_message(
    db, id, channel_id, content, attachments, author_id, long_date, short_date, server
):
    if server == "tyler":
        await init_beanie(database=db.data, document_models=[Messages])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[Messages])
    msg = Messages(
        id=id,
        channel_id=channel_id,
        attachments=attachments,
        content=content,
        author_id=author_id,
        long_date=long_date,
        short_date=short_date,
    )
    await msg.save()

async def get_day(db, server, date):
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    pipeline = [
        {"$match": {"long_date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {
            "_id": {"$hour": "$long_date"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    if server == "tyler":
        await init_beanie(database=db.data, document_models=[Messages])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[Messages])

    cursor = Messages.aggregate(pipeline)

    results = await cursor.to_list(None)

    if len(results) == 0:
        results_list = [{"hour": start_date.strftime("%H-%M"), "count": 0}]
    else:
        results_list = [
            {"hour": result["_id"], "count": result["count"]}
            for result in results
        ]

    results = pd.DataFrame(results_list)
    results["time"] = results["hour"].apply(lambda x: f"{x:02}:00")
    results.set_index("time", inplace=True)
    results = results.drop("hour", axis=1)
    results = results.reindex(pd.date_range(start=start_date, end=end_date, freq="H")[:-1].strftime("%H:%M"))
    results = results.fillna(0)
    results = results.astype(int)

    return results

async def get_month(db, server, date):
    start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = start_date.replace(day=28) + timedelta(days=4)  # Get the next month to determine the end date
    end_date = next_month - timedelta(days=next_month.day)

    pipeline = [
        {"$match": {"long_date": {"$gte": start_date, "$lt": end_date}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$long_date"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}}
    ]

    if server == "tyler":
        await init_beanie(database=db.data, document_models=[Messages])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[Messages])

    cursor = Messages.aggregate(pipeline)

    results = await cursor.to_list(None)

    if len(results) == 0:
        results_list = [{"date":start_date.strftime("%Y-%m-%d"), "count": 0}]
    else:
        results_list = [{"date": result["_id"], "count": result["count"]} for result in results]

    results = pd.DataFrame(results_list)
    results["date"] = pd.to_datetime(results["date"])
    results.set_index("date", inplace=True)
    results = results.reindex(pd.date_range(start=start_date, end=end_date, freq="D"), fill_value=0)
    results = results.astype(int)
    return results

async def update_auto_update_message(db, server, message_id):
    if server == "tyler":
        await init_beanie(database=db.data, document_models=[AutoUpdateChannel])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[AutoUpdateChannel])
    await AutoUpdateChannel.delete_all()
    channel = AutoUpdateChannel(message_id=message_id)
    await channel.save()

async def get_auto_update_message(db, server):
    if server == "tyler":
        await init_beanie(database=db.data, document_models=[AutoUpdateChannel])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[AutoUpdateChannel])

    cursor = AutoUpdateChannel.find({})
    results = await cursor.to_list(None)
    # get the message_id
    if len(results) == 0:
        return 0
    else:
        return results[0].message_id




async def export_db(server):

    load_dotenv()

    username = os.environ["MONGO_USERNAME"]
    password = os.environ["MONGO_PASSWORD"]
    host = os.environ["MONGO_HOST"]

    conn_str = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
    db = AsyncIOMotorClient(conn_str)

    if server == "tyler":
        await init_beanie(database=db.data, document_models=[Messages])
    elif server == "meloania":
        await init_beanie(database=db.meloania, document_models=[Messages])

    cursor = Messages.find({})

    results = await cursor.to_list()

    with open("export.json", "w") as f:
        json.dump(results, f, indent=4, default=str)
    
    return results

async def main():
    load_dotenv()

    username = os.environ["MONGO_USERNAME"]
    password = os.environ["MONGO_PASSWORD"]
    host = os.environ["MONGO_HOST"]

    conn_str = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
    db = AsyncIOMotorClient(conn_str)
    print(await get_auto_update_message(db, "meloania"))

if __name__ == "__main__":
    asyncio.run(main())