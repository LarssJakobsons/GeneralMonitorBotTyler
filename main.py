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
from mongo import get_week, write_message, get_day, get_month, update_auto_update_message, get_auto_update_message
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pandas import DataFrame
import pandas as pd
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

@Task.create(TimeTrigger(hour=0, minute=0))
async def update_message():
    server = "meloania"
    if (server == "meloania"):
        force_update = Button(style=ButtonStyle.BLUE, custom_id="force_update", emoji="🔄")

        message = await get_auto_update_message(db, meloania_id)

        meloania_auto_update_channel = bot.get_channel(1128402590925865121)

        try:
            message = await meloania_auto_update_channel.fetch_message(message)
        except:
            message = await meloania_auto_update_channel.send("No message found, please run /force_update to create one")
            return

        await message.edit(content="Updating...")
        data = await get_week(db, "meloania")


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
        await message.edit(content="", embed=embed, components=[force_update])
        


@listen()
async def on_startup():
    print(f"{bot.user} has connected to Discord!")
    global startup
    startup = time.mktime(datetime.utcnow().timetuple())
    # update_message.start(db=db, server="meloania")



def gen_graph(data, title, x_label, y_label, color, marker, linestyle, line_width=1):
    data.plot(color=color, marker=marker, linestyle=linestyle, linewidth=line_width)
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


@slash_command(name="force_update", description="Force update the automatic stats message", dm_permission=False, scopes=[970525263211397171])
async def force_update(ctx):

    if ctx.author.has_permission(Permissions.ADMINISTRATOR) or ctx.author == bot.owner:

        force_update = Button(style=ButtonStyle.BLUE, custom_id="force_update", emoji="🔄")

        meloania_auto_update_channel = bot.get_channel(1128402590925865121)

        message = await get_auto_update_message(db, "meloania")
        print(message)

        if await meloania_auto_update_channel.fetch_message(message) == None:
            message = await meloania_auto_update_channel.send("No message found, creating a new one...")
            await update_auto_update_message(db, "meloania", message.id)
        else:
            message = await meloania_auto_update_channel.fetch_message(message)

        client_msg = await ctx.send(content="Updating...")
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
        await message.edit(content="", embed=embed, components=[force_update])
        await client_msg.edit(content="Succesfully updated the automatic stats message.")
    else:
        await ctx.send("Sorry, can't let you do that.", ephemeral=True)
        return

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
    data = await get_month(db, "meloania", month)

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


@slash_command(name="generategraph", description="Generate a graph")
@slash_option(
    name="title",
    description="Set the title of the graph",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(name="xvalue", description="Set the title of the X value", required=True, opt_type=OptionType.STRING)
@slash_option(name="yvalue", description="Set the title of the Y value", required=True, opt_type=OptionType.STRING)
@slash_option(
    name="color",
    description="Set the color of the graph",
    required=True,
    opt_type=OptionType.STRING,
    choices=[
        SlashCommandChoice(name="red", value="red"),
        SlashCommandChoice(name="green", value="green"),
        SlashCommandChoice(name="blue", value="blue"),
        SlashCommandChoice(name="yellow", value="yellow"),
        SlashCommandChoice(name="black", value="black"),
        SlashCommandChoice(name="white", value="white"),
        SlashCommandChoice(name="purple", value="purple"),
        SlashCommandChoice(name="orange", value="orange"),
        SlashCommandChoice(name="pink", value="pink"),
        SlashCommandChoice(name="brown", value="brown"),
        SlashCommandChoice(name="gray", value="gray"),
        SlashCommandChoice(name="cyan", value="cyan"),
    ],
)
@slash_option(
    name="marker",
    description="Set the marker of the graph",
    required=True,
    opt_type=OptionType.STRING,
    choices=[
        SlashCommandChoice(name="o", value="o"),
        SlashCommandChoice(name="*", value="*"),
        SlashCommandChoice(name=".", value="."),
        SlashCommandChoice(name="+", value="+"),
        SlashCommandChoice(name="x", value="x"),
        SlashCommandChoice(name="s", value="s"),
        SlashCommandChoice(name="d", value="d"),
    ],
)
@slash_option(name="line", description="Set the line of the graph", required=True, opt_type=OptionType.STRING, choices=[
        SlashCommandChoice(name="-", value="-"),
        SlashCommandChoice(name="--", value="--"),
        SlashCommandChoice(name="-.", value="-."),
        SlashCommandChoice(name=":", value=":"),
        SlashCommandChoice(name="steps", value="steps"),
        SlashCommandChoice(name="None", value="None"),
    ])
@slash_option(name="line_width", description="Set the line width of the graph", required=True, opt_type=OptionType.INTEGER)
# @slash_option(name="graph_type", description="Set the type of the graph", required=True, opt_type=OptionType.STRING, choices=[
#         SlashCommandChoice(name="line", value="line"),
#         SlashCommandChoice(name="bar", value="bar"),
#     ])
async def generate_plot(
    ctx, title: str, xvalue: str, yvalue: str, color: str, marker: str, line: str, line_width:str 
):
    btn1 = Button(style=ButtonStyle.RED, custom_id="delete", emoji="🗑️")

    # make data
    x = 0
    y = 0

    modal = Modal(
        ShortText(label="X values",required=True, placeholder="First opt, second opt, ...", custom_id="xvalues"),
        ShortText(label="Y values",required=True, placeholder="(must be integer) 0, 1, 2, ...", custom_id="yvalues"),
        title="Input graph data")
    await ctx.send_modal(modal=modal)
    modal_ctx: ModalContext = await ctx.bot.wait_for_modal(modal)

    xval = modal_ctx.responses["xvalues"]
    yval = modal_ctx.responses["yvalues"]


    # generate a pandas dataframe from the xval and yval
    xval = xval.split(",")
    yval = yval.split(",")

    if xval == "":
        xval = "xval"
    if yval == "":
        yval = "yval"

    # check if an xval has a yval
    if len(xval) != len(yval):
        await modal_ctx.send("Invalid X and Y values, there must be a Y value for each X value")
        return

    try:
        yval = [int(i) for i in yval]
    except ValueError:
        await modal_ctx.send("Invalid Y values, must be integers")
        return
    
    try:
        xval = [int(i) for i in xval]
    except ValueError:
        pass
    # generate a pandas dataframe from the xval and yval that will look like
    # xval : yval

    data = pd.DataFrame({"xval": xval, "yval": yval})
    data.set_index("xval", inplace=True)
    print(data)

    buf = gen_graph(
        data,
        title,
        xvalue,
        yvalue,
        color,
        marker,
        line,
        line_width,
    )
    priv_message = await bot.owner.send(file=File(file=buf, file_name="figure.png"))
    url = priv_message.attachments[0].url
    embed = Embed(title="Custom graph", description=f"Custom generated graph by {ctx.author.mention}", color=0xFFFFFF)
    embed.set_image(url=url)
    await modal_ctx.send(content=f"{ctx.author.mention}, heres your graph!",embed=embed, components=[btn1])


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
    if event.custom_id == "force_update":
        if not ctx.author.has_permission(Permissions.ADMINISTRATOR) or not ctx.author == bot.owner:
            await ctx.send("Sorry, can't let you do that.", ephemeral=True)
            return

        force_update = Button(style=ButtonStyle.BLUE, custom_id="force_update", emoji="🔄")

        message = await get_auto_update_message(db, ctx.guild.id)

        meloania_auto_update_channel = bot.get_channel(1128402590925865121)

        try:
            message = await meloania_auto_update_channel.fetch_message(message)
        except:
            message = await meloania_auto_update_channel.send("No message found, creating a new one...")
            await update_auto_update_message(db, ctx.guild.id, message.id)


        await message.edit(content="Updating...")
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
        await message.edit(content="", embed=embed, components=[force_update])



secret_token = os.environ["TOKEN"]
bot.start(secret_token)
