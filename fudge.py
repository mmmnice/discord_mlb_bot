import discord
import aiohttp
import asyncio
from datetime import date

import ssl
import certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())

# ---- CONFIG ----
DISCORD_TOKEN = 
CHANNEL_ID = 
CHECK_INTERVAL = 30  # seconds between polls
JUDGE_ID = 592450  # Aaron Judge's MLB player ID: 592450
# ----------------

intents = discord.Intents.default()
connector = aiohttp.TCPConnector(ssl=ssl_context)
client = discord.Client(intents=intents, connector=connector)

known_strikeout_count = None

async def get_todays_game_pks():
    today = date.today().strftime("%Y-%m-%d")
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

async def monitor():
    global known_strikeout_count
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while not client.is_closed():
        try:
            game_pks = await get_todays_game_pks()
            print(f"[{date.today()}] calling the api... " + str(game_pks))
            for pk in game_pks:
                strikeouts = await get_judge_strikeouts(pk)
                if strikeouts is None:
                    continue
                if known_strikeout_count is None:
                    known_strikeout_count = strikeouts
                elif strikeouts > known_strikeout_count:
                    new_ks = strikeouts - known_strikeout_count
                    for _ in range(new_ks):
                        await channel.send(
                            "⚾ **Aaron FUDGE JUST STRUCK OUT!** 🙈 "
                            f"That's strikeout #{strikeouts} today for Aaron Judge!"
                        )
                    known_strikeout_count = strikeouts
        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(monitor())

client.run(DISCORD_TOKEN)