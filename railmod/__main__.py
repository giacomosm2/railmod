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

@bot.command()
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