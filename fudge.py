import discord
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz


import ssl
import certifi

load_dotenv()
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ---- CONFIG ----
DISCORD_TOKEN = os.getenv("discord_token")
CHANNEL_ID = int(os.getenv("channel_id"))
CHECK_INTERVAL = 30  # seconds between polls
JUDGE_ID = 592450  # Aaron Judge's MLB player ID: 592450
# ----------------

intents = discord.Intents.default()
connector = aiohttp.TCPConnector(ssl=ssl_context)
client = discord.Client(intents=intents, connector=connector)

known_strikeout_count = None
currentpk = None
airout = None
groundout = None

async def get_todays_game_pks():
    est = pytz.timezone("America/New_York")
    today = datetime.now(est).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&teamId=147"
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.get(url) as r:
            data = await r.json()
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append(g["gamePk"])
    return games

async def get_judge_strikeouts(game_pk):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.get(url) as r:
            data = await r.json()

    for side in ["away", "home"]:
        players = data.get("teams", {}).get(side, {}).get("players", {})
        key = f"ID{JUDGE_ID}"
        if key in players:
            stats = players[key].get("stats", {}).get("batting", {})
            return stats.get("strikeOuts", 0)
    return None
#combine get_judge_strikeouts and outty into one function to reduce redundant API calls
async def outty(game_pk):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.get(url) as r:
            data = await r.json()

    for side in ["away", "home"]:
        players = data.get("teams", {}).get(side, {}).get("players", {})
        key = f"ID{JUDGE_ID}"
        if key in players:
            stats = players[key].get("stats", {}).get("batting", {})
            return [stats.get("airOuts", 0), stats.get("groundOuts", 0)]
    return None

async def monitor():
    global known_strikeout_count
    global airout
    global groundout
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while not client.is_closed():
        try:
            game_pks = await get_todays_game_pks()
            if current_pk is None:
                current_pk = game_pks[0]
            elif currrent_pk != game_pks[0]:
                current_pk = game_pks[0]
                known_strikeout_count = None
                airout = None
                groundout = None
                print("reset count for new game")

            print(f"[{datetime.today()}] calling the api... Game id:" + str(game_pks))
            for pk in game_pks:
                strikeouts = await get_judge_strikeouts(pk)
                outs = await outty(pk)
                print("Players Stats: " + "pop: "+str(outs[0]) + " ground: " + str(outs[1]) + " strikeouts: " + str(strikeouts))
                if strikeouts is None:
                    continue
                if known_strikeout_count is None:
                    known_strikeout_count = strikeouts
                elif strikeouts > known_strikeout_count:
                    new_ks = strikeouts - known_strikeout_count
                    for _ in range(new_ks):
                        await channel.send(
                            "⚾ **Aaron FUDGE JUST STRUCK OUT!** 🙈💩 "
                            f"That's strikeout #{strikeouts} today for Aaron Fudge!"
                        )
                    known_strikeout_count = strikeouts
                if airout is None:
                    airout = outs[0]
                elif outs[0] > airout:
                    await channel.send(
                            "⚾ **Aaron FUDGE JUST pop OUT!** 🙈 "
                            f"That's popout #{outs[0]} today for Aaron Fudge!"
                        )
                    airout = outs[0]

                if groundout is None:
                    groundout = outs[1]
                elif outs[1] > groundout:
                    await channel.send(
                            "⚾ **Aaron FUDGE JUST ground OUT!** 💩 "
                            f"That's groundout #{outs[1]} today for Aaron Fudge!"
                        )
                    groundout = outs[1]

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    asyncio.ensure_future(monitor())

client.run(DISCORD_TOKEN)