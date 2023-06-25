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
from mongo import get_week, write_message, get_day, get_month
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

from keep_alive import start as keep_alive

keep_alive()

bot_intents: Intents = Intents.DEFAULT | Intents.GUILD_MEMBERS | Intents.MESSAGE_CONTENT

bot = interactions.Client(
    sync_interactions=True, intents=bot_intents, send_command_tracebacks=False
)

meloania_id = 970525263211397171
tyler_id = 966090001668534394


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


@slash_command(
    name="weekly", description="get the weekly acivity of the server", dm_permission=False
)
async def weekly(ctx):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")
    message = await ctx.send("Generating graph...", components=[btn1])
    if ctx.channel.guild.id == meloania_id:
        data = await get_week(db, "meloania")
    elif ctx.channel.guild.id == tyler_id:
        data = await get_week(db, "tyler")

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
    embed = Embed(
        title="Weekly Activity", description="Weekly activity on the server", color=0xFFFFFF
    )
    embed.set_image(url=url)
    await message.edit(content="", embed=embed, components=[btn1])


@slash_command(name="day", description="get the activity in a set date", dm_permission=False)
@slash_option(name="date", description="yyyy-mm-dd", required=True, opt_type=OptionType.STRING)
async def daily(ctx, date: str):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")
    try:
        date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        await ctx.send("Invalid date, please use the format `yyyy-mm-dd`", components=[btn1])
        return
    message = await ctx.send("Generating graph...", components=[btn1])
    if ctx.channel.guild.id == meloania_id:
        data = await get_day(db, "meloania", date)
    elif ctx.channel.guild.id == tyler_id:
        data = await get_day(db, "tyler", date)

    buf = gen_graph(
        data,
        "Daily Activity",
        "Time",
        "Messages",
        "red",
        "o",
        "-",
    )

    priv_message = await bot.owner.send(file=File(file=buf, file_name="figure.png"))
    url = priv_message.attachments[0].url
    embed = Embed(
        title=date.strftime("%Y-%m-%d"),
        description="Activity on the server on this date",
        color=0xFFFFFF,
    )
    embed.set_image(url=url)
    await message.edit(content="", embed=embed, components=[btn1])


@listen()
async def on_message(ctx: MessageCreate):
    message = ctx.message
    if message.author == bot.user:
        return
    elif message.author.bot:
        return
    elif message.channel.type == ChannelType.DM:
        return
    else:
        attachment_urls = []
        if message.channel.guild.id == meloania_id:
            server = "meloania"
        elif message.channel.guild.id == tyler_id:
            server = "tyler"
        if message.attachments != []:
            for attachment in message.attachments:
                attachment_urls.append(attachment.url)
        await write_message(
            db,
            message.id,
            message.channel.id,
            message.content,
            attachment_urls,
            message.author.id,
            message.timestamp,
            (message.timestamp).strftime("%Y-%m-%d"),
            server,
        )


@slash_command(name="month", description="get the activity in a month", dm_permission=False)
@slash_option(name="month", description="yyyy-mm", required=True, opt_type=OptionType.STRING)
async def monthly(ctx, month: str):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")
    try:
        month = datetime.strptime(month, "%Y-%m")
    except ValueError:
        await ctx.send("Invalid month, please use the format `yyyy-mm`", components=[btn1])
        return
    message = await ctx.send("Generating graph...", components=[btn1])
    if ctx.channel.guild.id == meloania_id:
        data = await get_month(db, "meloania", month)
    elif ctx.channel.guild.id == tyler_id:
        data = await get_month(db, "tyler", month)

    buf = gen_graph(
        data,
        "Monthly Activity",
        "Date",
        "Messages",
        "red",
        "o",
        "-",
    )

    priv_message = await bot.owner.send(file=File(file=buf, file_name="figure.png"))
    url = priv_message.attachments[0].url
    embed = Embed(
        title=month.strftime("%Y-%m"),
        description="Activity of the serveer on this month",
        color=0xFFFFFF,
    )
    embed.set_image(url=url)
    await message.edit(content="", embed=embed, components=[btn1])


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
