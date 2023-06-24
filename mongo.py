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
    content: str
    author_id: int
    long_date: datetime
    # short date will be in a format like this: yyyy-mm-dd
    short_date: str


async def get_week(db):
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

    await init_beanie(database=db.data, document_models=[Messages])

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


async def write_message(db, id, channel_id, content, author_id, long_date, short_date):
    await init_beanie(database=db.data, document_models=[Messages])
    msg = Messages(
        id=id,
        channel_id=channel_id,
        content=content,
        author_id=author_id,
        long_date=long_date,
        short_date=short_date,
    )
    await msg.save()


async def main():
    load_dotenv()

    username = os.environ["MONGO_USERNAME"]
    password = os.environ["MONGO_PASSWORD"]
    host = os.environ["MONGO_HOST"]

    conn_str = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
    db = AsyncIOMotorClient(conn_str)

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

    await init_beanie(database=db.data, document_models=[Messages])

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

    print(results_list)
    print(results)

    "Weekly Activity",
    "Date",
    "Messages",
    "red",
    "o",
    "-",

    results.plot(color="red", marker="o", linestyle="-")
    plt.grid(linewidth=0.3, color="black", axis="y")
    plt.title("Bruh")
    plt.xlabel("Date")
    plt.ylabel("Messages")
    # set the max y value to be +1 of the max value
    y_max = plt.ylim()[1]
    # plt.ylim(0, y_max + 1)
    # set the date values to not touch any of the margins
    plt.margins(x=50000000, y=0.01)
    # set the y ticks to be 1 apart
    t1 = np.arange(0, y_max + 1, y_max / 5)

    plt.yticks(t1)

        # make the right and left dates be not the margins
    plt.xlim(results.index[0], results.index[-1])


    plt.savefig("test.png")

if __name__ == "__main__":
    asyncio.run(main())
