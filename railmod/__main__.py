import discord
import os
from discord.ext import commands
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("RAILMOD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

r = redis.Redis(host='localhost', port=6379, db=0)

shrug = "¯\\_(ツ)_/¯"

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

def human_readable_time_ago(date_str):
    dt = datetime.fromisoformat(date_str)
    now = datetime.now(timezone.utc)
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "less than a minute ago"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = diff.days
    if days < 7:
        leftover_hours = hours % 24
        if leftover_hours:
            return f"{days} day{'s' if days != 1 else ''}, {leftover_hours} hour{'s' if leftover_hours != 1 else ''} ago"
        else:
            return f"{days} day{'s' if days != 1 else ''} ago"
    weeks = days // 7
    leftover_days = days % 7
    if weeks < 4:
        if leftover_days:
            return f"{weeks} week{'s' if weeks != 1 else ''}, {leftover_days} day{'s' if leftover_days != 1 else ''} ago"
        else:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    rd = relativedelta(now, dt)
    months = rd.months + rd.years * 12
    leftover_weeks = (days % 30) // 7  # estimate
    if months < 12:
        if leftover_weeks:
            return f"{months} month{'s' if months != 1 else ''}, {leftover_weeks} week{'s' if leftover_weeks != 1 else ''} ago"
        else:
            return f"{months} month{'s' if months != 1 else ''} ago"
    years = rd.years
    leftover_months = rd.months
    if leftover_months:
        return f"{years} year{'s' if years != 1 else ''}, {leftover_months} month{'s' if leftover_months != 1 else ''} ago"
    else:
        return f"{years} year{'s' if years != 1 else ''} ago"


async def get_current_prefix():
    try:
        key = "prefix:default"
        prefix = await r.get(key)
        return prefix.decode() if prefix else "rm;"
    except redis.exceptions.ConnectionError:
        return "rm;"

async def get_prefix(bot, message):
    default = "rm;"
    key = f"prefix:{message.guild.id}"

    try:
        prefix = await r.get(key)
        return prefix.decode() if prefix else default
    except redis.exceptions.ConnectionError:
        return default

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f"[+] Railmod logged in as {bot.user}")

@bot.command(help="sets a new prefix for bot commands")
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix=""):
    if not new_prefix:
        key = f"prefix:{ctx.guild.id}"
        prefix = await r.get(key)
        prefix_str = prefix.decode() if prefix else "rm;"
        if prefix_str == "rm;":
            return_prefix = "!"
        else:
            return_prefix = "rm;"
        return await ctx.send(f"please provide a new prefix, for example `{prefix_str}setprefix {return_prefix}`")
    key = f"prefix:{ctx.guild.id}"
    await r.set(key, new_prefix)
    await ctx.send(f"prefix set to `{new_prefix}` for this server")
    
@bot.command(help="pings the bot, nothing else")
async def ping(ctx):
    await ctx.send("pong!")

@bot.command(help="get detailed info about a member")
async def memberinfo(ctx, *, member: discord.Member = None):
    if not member:
        prefix = await get_current_prefix()
        return await ctx.send(f"please provide a member to get info about, for example `{prefix}memberinfo @user`")
    await ctx.send(f"""
                   `{member}` | joined on `{member.joined_at}` ({human_readable_time_ago(member.joined_at.isoformat())})
                   """)

@bot.command(help="shows this help message")
async def help(ctx):
    help_str = ""
    for command in bot.commands:
        if command.hidden:
            continue
        help_str += f"`{command.name}` | {command.help or 'no description available'}\n"
    if not help_str:
        help_str = f"no commands found {shrug}"
    await ctx.send(help_str)


bot.run(token)