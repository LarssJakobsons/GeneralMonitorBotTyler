import os
from dotenv import load_dotenv
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import datetime
from beanie import init_beanie
from beanie.odm.documents import Document
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class Messages(Document):
    id: int
    channel_id: int
    attachments: list
    content: str
    author_id: int
    long_date: datetime
    # short date will be in a format like this: yyyy-mm-dd
    short_date: str


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


async def write_message(db, id, channel_id, content, attachments, author_id, long_date, short_date, server):
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
