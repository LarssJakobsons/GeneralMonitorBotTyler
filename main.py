import interactions
from interactions import *
from interactions.models import *
from interactions.api.events.discord import MessageCreate
import os
import datetime
import time
from dotenv import load_dotenv

import matplotlib.pyplot as plt
from io import BytesIO
from mongo import get_week, write_message
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pandas import DataFrame
import numpy as np


load_dotenv()

username = os.environ["MONGO_USERNAME"]
password = os.environ["MONGO_PASSWORD"]
host = os.environ["MONGO_HOST"]

conn_str = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
db = AsyncIOMotorClient(conn_str)

# from keep_alive import start as thugshaker

# thugshaker()

bot_intents: Intents = Intents.DEFAULT | Intents.GUILD_MEMBERS | Intents.MESSAGE_CONTENT

bot = interactions.Client(
    sync_interactions=True, intents=bot_intents, send_command_tracebacks=False
)


@listen()
async def on_startup():
    print(f"{bot.user} has connected to Discord!")
    global startup
    startup = time.mktime(datetime.utcnow().timetuple())


def gen_graph(data, title, x_label, y_label, color, marker, linestyle):
    data.plot(color=color, marker=marker, linestyle=linestyle)
    plt.grid(linewidth=0.5, color="black", axis="y")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    # set the max y value to be +1 of the max value
    y_max = plt.ylim()[1]
    plt.ylim(0, y_max + 1, y_max / 5)
    # set the points to not touch any of the edges
    plt.margins(x=0.1, y=0.1)

    buf = BytesIO()
    plt.savefig(buf)
    buf.seek(0)
    return buf


@slash_command(name="ping", description="check the bots status")
async def ping(ctx):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")
    message = await ctx.send(
        f"""
pong! 🏓
latency: `{round(bot.latency * 1000)}ms`
startup: <t:{round(startup)}:R>
""",
        components=[btn1],
    )


@slash_command(name="weekly", description="get the weekly acivity of the server")
async def weekly(ctx):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")
    message = await ctx.send("Generating graph...", components=[btn1])

    data = await get_week(db)

    buf = gen_graph(
        data,
        "Weekly Activity",
        "Date",
        "Messages",
        "red",
        "o",
        "-",
    )

    priv_message = await bot.owner.send(file=File(file=buf, file_name="figure.png"))
    url = priv_message.attachments[0].url
    embed = Embed(title="Weekly Activity", description="Weekly activity on the server", color=0xFFFFFF)
    embed.set_image(url=url)
    await message.edit(content="" ,embed=embed, components=[btn1])


@listen()
async def on_message(ctx: MessageCreate):
    message = ctx.message
    if message.author == bot.user:
        return
    if message.channel.type == ChannelType.DM:
        return
    else:
        await write_message(
            db,
            message.id,
            message.channel.id,
            message.content,
            message.author.id,
            message.timestamp,
            (message.timestamp).strftime("%Y-%m-%d"),
        )


@listen()
async def on_component(ctx: ComponentContext):
    event = ctx.ctx
    if event.custom_id == "delete":
        if (
            event.message.interaction._user_id == event.author.id
            or event.author.has_permission(Permissions.MANAGE_MESSAGES) == True
        ):
            await event.message.delete()
        else:
            await event.send("Not your interaction.", ephemeral=True)


secret_token = os.environ["TOKEN"]
bot.start(secret_token)
