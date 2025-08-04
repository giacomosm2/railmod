import discord
import os
from discord.ext import commands
import redis.asyncio as redis
from redis.exceptions import ConnectionError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass
token = os.environ.get("RAILMOD_TOKEN")
redis_url = os.environ.get("REDIS_URL")

intents = discord.Intents.default()
intents.message_content = True

r = redis.from_url(redis_url)

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

async def send_dm(user: discord.User, message: str) -> bool:
    try:
        await user.send(message)
        return True
    except discord.Forbidden:
        return False
    
async def is_admin(ctx):
    key = f"adminroles:{ctx.guild.id}"
    admin_roles = await r.smembers(key)
    admin_roles = {int(r.decode()) for r in admin_roles}
    user_roles = {role.id for role in ctx.author.roles}
    return bool(admin_roles.intersection(user_roles))

async def get_current_prefix():
    try:
        key = "prefix:default"
        prefix = await r.get(key)
        return prefix.decode() if prefix else "rm;"
    except ConnectionError:
        return "rm;"

async def get_prefix(bot, message):
    default = "rm;"
    key = f"prefix:{message.guild.id}"

    try:
        prefix = await r.get(key)
        return prefix.decode() if prefix else default
    except ConnectionError:
        return default

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f"[+] Railmod logged in as {bot.user}")

@bot.command(help="sets a new prefix for bot commands | setprefix something")
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
        return await ctx.send(f"please provide a new prefix, for example `{prefix_str}setprefix {return_prefix}` to change the prefix from {prefix_str} to {return_prefix}")
    key = f"prefix:{ctx.guild.id}"
    await r.set(key, new_prefix)
    await ctx.send(f"prefix set to `{new_prefix}` for this server")
    
@bot.command(help="sets the servers point system name | setpointsname something")
async def setpn(ctx, name=""):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. if you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            # bot cant dm user, just ignore
            pass
        await ctx.message.delete()
        return
    if not name:
        key = f"pn:{ctx.guild.id}"
        pn_current = await r.get(key)
        pn = pn_current.decode() if pn_current else "points"
        if pn == "points":
            return_pn = "cookies"
        else:
            return_pn = "points"
        return await ctx.send(f"please provide a new prefix, for example `{pn}setpn {return_pn}` to change the points name from {pn} to {return_pn}")
    key = f"pn:{ctx.guild.id}"
    await r.set(key, name)
    await ctx.send(f"points name set to `{name}` for this server")
    
@bot.command(help="sets a user's points | setpoints @user amount")
async def setpoints(ctx, user: discord.Member = None, amount: int = None):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. If you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            pass
        await ctx.message.delete()
        return
    if not user or not amount:
        prefix = await get_current_prefix()
        return await ctx.send(f"please specify a user and amount, for example `{prefix}setpoints @someuser 100`")
    key = f"points:{ctx.guild.id}"
    await r.zadd(key, {str(user.id): amount})
    pn_key = f"pn:{ctx.guild.id}"
    pn_raw = await r.get(pn_key)
    pn = pn_raw.decode() if pn_raw else "points"
    await ctx.send(f"{user.mention}'s {pn} set to `{amount}` for this server")
    
@bot.command(help="shows the top users by points | leaderboard")
async def leaderboard(ctx, top: int = 10):
    key = f"points:{ctx.guild.id}"
    pn_key = f"pn:{ctx.guild.id}"
    pn_raw = await r.get(pn_key)
    pn = pn_raw.decode() if pn_raw else "points"
    top_users = await r.zrevrange(key, 0, top - 1, withscores=True)
    if not top_users:
        return await ctx.send(f"no {pn} data found for this server")
    parts = []
    for i, (user_id_bytes, score) in enumerate(top_users, start=1):
        user_id = int(user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes)
        user = ctx.guild.get_member(user_id)
        username = user.display_name if user else f"uid {user_id}"
        parts.append(f"{i}. {username} ({int(score)} {pn})")
    joined = "\n".join(parts)
    leaderboard_msg = f"top {top} {pn} leaderboard:\n{joined}"
    await ctx.send(leaderboard_msg)
    
@bot.command(help="gets a user's points | getpoints @user")
async def getpoints(ctx, user: discord.Member = None):
    if not user:
        prefix = await get_current_prefix()
        pn_key = f"pn:{ctx.guild.id}"
        pn_raw = await r.get(pn_key)
        pn = pn_raw.decode() if pn_raw else "points"
        return await ctx.send(f"please specify a user, for example `{prefix}getpoints @someuser` to get someuser's {pn}")
    key = f"points:{ctx.guild.id}"
    score = await r.zscore(key, str(user.id))
    points_display = str(int(score)) if score else "0"
    pn_key = f"pn:{ctx.guild.id}"
    pn_raw = await r.get(pn_key)
    pn = pn_raw.decode() if pn_raw else "points"
    await ctx.send(f"{user.mention} has `{points_display}` {pn} in this server")

@bot.command(help="adds points to a user | addpoints @user amount")
async def addpoints(ctx, user: discord.Member = None, amount: int = None):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. If you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            pass
        await ctx.message.delete()
        return
    if not user:
        prefix = await get_current_prefix()
        return await ctx.send(f"please specify a user, for example `{prefix}addpoints @someuser 5` to add 5 points or `{prefix}addpoints @someuser` to add 1 point to someuser")
    if not amount:
        amount = 1
    key = f"points:{ctx.guild.id}"
    await r.zincrby(key, amount, str(user.id))
    pn_key = f"pn:{ctx.guild.id}"
    pn_raw = await r.get(pn_key)
    pn = pn_raw.decode() if pn_raw else "points"
    await ctx.send(f"{user.mention} got `{amount}` {pn}, yay! they now have `{int(await r.zscore(key, str(user.id)))}` {pn} in this server")

@bot.command(help="ban a user | ban @user [reason]")
async def ban(ctx, user: discord.Member = None, *, reason: str = "no reason provided"):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. if you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            pass
        await ctx.message.delete()
        return
    if not user:
        prefix = await get_current_prefix()
        return await ctx.send(f"please specify a user to ban, for example `{prefix}ban @someuser [reason]`")
    try:
        await user.ban(reason=reason)
        key = f"banned:{ctx.guild.id}:{user.id}"
        await r.set(key, "1")
        await ctx.send(f"{user.mention} has been banned for: *\"{reason}\"*")
    except discord.Forbidden:
        await ctx.send(f"failed to ban {user.mention} {shrug}")

@bot.command(help="unban a user | unban user_id")
async def unban(ctx, user_id: int = None):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. if you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            pass
        await ctx.message.delete()
        return
    if not user_id:
        prefix = await get_current_prefix()
        return await ctx.send(f"please specify a user ID to unban, for example `{prefix}unban 1234567890`")
    banned_users = await ctx.guild.bans()
    user = next((b.user for b in banned_users if b.user.id == user_id), None)
    if user is None:
        return await ctx.send("user is not banned or ID invalid")
    try:
        await ctx.guild.unban(user)
        key = f"banned:{ctx.guild.id}:{user.id}"
        await r.delete(key)
        await ctx.send(f"{user} has been unbanned")
    except discord.Forbidden:
        await ctx.send(f"failed to unban user {shrug}")

# @bot.command(help="list banned users in the server | bannedlist")
# async def bannedlist(ctx):
#     if not await is_admin(ctx):
#         try:
#             await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. if you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
#         except discord.Forbidden:
#             pass
#         await ctx.message.delete()
#         return
    
#     banned_users = await ctx.guild.bans()
#     if not banned_users:
#         return await ctx.send("no users are banned in this server, hooray!")
    
#     lines = []
#     for ban_entry in banned_users:
#         user = ban_entry.user
#         reason = ban_entry.reason or "[no reason provided]"
#         lines.append(f"- {user} (ID: {user.id}) — Reason: {reason}")
    
#     # chunk if needed
#     chunk_size = 1900
#     message = "Banned users:\n" + "\n".join(lines)
#     if len(message) <= 2000:
#         await ctx.send(message)
#     else:
#         # make sure its not two long
#         for i in range(0, len(lines), 50):
#             chunk = lines[i:i+50]
#             await ctx.send("Banned users:\n" + "\n".join(chunk))

@bot.command(help="pings the bot, nothing else | ping")
async def ping(ctx):
    await ctx.send("pong!")

@bot.command(help="get detailed info about a member | memberinfo @user")
async def memberinfo(ctx, *, member: discord.Member = None):
    if not member:
        prefix = await get_current_prefix()
        return await ctx.send(f"please provide a member to get info about, for example `{prefix}memberinfo @user`")
    if member.joined_at is None:
        join_time = "unknown"
        join_date = "(deleted user?)"
    else:
        join_time = human_readable_time_ago(member.joined_at.isoformat())
        join_date = member.joined_at.strftime("%Y-%m-%d %H:%M:%S")
    key = f"warninglog:{ctx.guild.id}:{member.id}"
    warnings = await r.lrange(key, 0, -1)
    
    decoded = [w.decode() for w in warnings]
    warn_count = len(decoded)
    if warn_count == 0:
        color = discord.Color.green()
    elif warn_count < 3:
        color = discord.Color.orange()
    else:
        color = discord.Color.red()
    if not decoded:
        warning_str = "no warnings, yay!"
    else:
        warning_str = "\n".join(f"- {w}" for w in decoded[-10:])
    
    embed = discord.Embed( # nice embed output
        title=f"member info | {member.display_name}",
        description=f"full username: `{member}`",
        color=color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="joined server", value=f"`{join_date}`\n({join_time})", inline=False)
    embed.add_field(name="warnings", value=warning_str, inline=False)
    embed.set_footer(text=f"user ID: {member.id}")

    await ctx.send(embed=embed)

@bot.command(help="shows this help message | help")
async def help(ctx):
    help_str = ""
    for command in bot.commands:
        if command.hidden:
            continue
        help_str += f"`{command.name}` | {command.help or 'no description available'}\n"
    if not help_str:
        help_str = f"no commands found {shrug}"
    await ctx.send(help_str)

@bot.command(help="add a role to admin group | mkroleadmin @role")
@commands.has_permissions(administrator=True)
async def mkroleadmin(ctx, role: discord.Role):
    key = f"adminroles:{ctx.guild.id}"
    await r.sadd(key, str(role.id))
    await ctx.send(f"role {role.name} added to admin group")

@bot.command(help="remove a role from admin group | rmvroleadmin @role")
@commands.has_permissions(administrator=True)
async def rmvroleadmin(ctx, role: discord.Role):
    key = f"adminroles:{ctx.guild.id}"
    await r.srem(key, str(role.id))
    await ctx.send(f"role {role.name} removed from admin group")


@bot.command(help="warn a user with reason | warn @user reason")
async def warn(ctx, user: discord.Member, *, reason: str):
    if not await is_admin(ctx):
        try:
            await ctx.author.send(f"railmod here! you tried to use an admin-level command in **\"{ctx.guild.name}\"**, but you are not an admin there. if you think this is a mistake contact the server owners :)\n`{ctx.message.content}`")
        except discord.Forbidden:
            # bot cant dm user, just ignore
            pass
        await ctx.message.delete()
        return
    key = f"warninglog:{ctx.guild.id}:{user.id}"
    await r.rpush(key, reason)
    dm_success = await send_dm(user, f"**warning!** you have been warned in **{ctx.guild.name}** for: *\"{reason}\"*")
    if dm_success:
        await ctx.send(f"{user.mention} has been warned for: *\"{reason}\"*")
    else:
        await ctx.send(f"{user.mention} has been warned for *\"{reason}\"*, but warning could not be sent via DMs, they might have blocked me")

bot.run(token)
