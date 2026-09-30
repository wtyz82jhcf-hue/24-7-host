import discord
import asyncio
import random
from datetime import datetime, timedelta
from discord.ext import commands


# =========================================================
# TOKEN
# =========================================================

import os

TOKEN = os.getenv("DISCORD_TOKEN")


# =========================================================
# BOT SETUP
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="?",
    intents=intents
)

AUTHORIZED_ROLE_ID = 1530188150456979526

def has_control_role(ctx):
    return any(role.id == AUTHORIZED_ROLE_ID for role in getattr(ctx.author, "roles", []))

def has_permission(ctx, permission):
    return has_control_role(ctx) or getattr(ctx.author.guild_permissions, permission, False)


# =========================================================
# DATEN / EINSTELLUNGEN
# =========================================================

warnings_data = {}
history_data = {}

antispam_enabled = False
antilink_enabled = False
caps_enabled = False
antiraid_enabled = False
antimention_enabled = False

logging_enabled = False
log_channel_id = None

welcome_enabled = False
welcome_channel_id = None
welcome_message = "Willkommen {member} auf dem Server! 👋"

autorole_id = None

bot_start_time = datetime.now()


# =========================================================
# START
# =========================================================

@bot.event
async def on_ready():
    print(f"Online als {bot.user}")


# =========================================================
# MODERATION
# =========================================================

@bot.command()
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="Kein Grund angegeben"
):
    if not has_permission(ctx, "ban_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung zum Bannen."
        )
        return

    try:
        await member.ban(reason=reason)

        await ctx.send(
            f"🔨 {member.mention} wurde gebannt.\n"
            f"Grund: {reason}"
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann diesen Benutzer nicht bannen."
        )

    except discord.HTTPException as error:
        await ctx.send(
            f"❌ Discord-Fehler: `{error}`"
        )


@bot.command()
async def unban(ctx, user_id: int):
    if not has_permission(ctx, "ban_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung zum Entbannen."
        )
        return

    try:
        user = await bot.fetch_user(user_id)

        await ctx.guild.unban(user)

        await ctx.send(
            f"✅ {user} wurde entbannt."
        )

    except discord.NotFound:
        await ctx.send(
            "❌ Dieser Benutzer ist nicht gebannt."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich darf diesen Benutzer nicht entbannen."
        )


@bot.command()
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="Kein Grund angegeben"
):
    if not has_permission(ctx, "kick_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung zum Kicken."
        )
        return

    try:
        await member.kick(reason=reason)

        await ctx.send(
            f"👢 {member.mention} wurde gekickt.\n"
            f"Grund: {reason}"
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann diesen Benutzer nicht kicken."
        )

    except discord.HTTPException as error:
        await ctx.send(
            f"❌ Discord-Fehler: `{error}`"
        )


@bot.command()
async def mute(
    ctx,
    member: discord.Member,
    minutes: int = 10
):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung für Timeouts."
        )
        return

    if minutes < 1 or minutes > 1440:
        await ctx.send(
            "❌ Minuten müssen zwischen 1 und 1440 liegen."
        )
        return

    try:
        await member.timeout(
            discord.utils.utcnow()
            + timedelta(minutes=minutes),
            reason=f"Timeout von {ctx.author}"
        )

        await ctx.send(
            f"🔇 {member.mention} wurde für "
            f"{minutes} Minuten gemutet."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann diesen Benutzer nicht muten."
        )

    except discord.HTTPException as error:
        await ctx.send(
            f"❌ Discord-Fehler: `{error}`"
        )


@bot.command()
async def unmute(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung für Timeouts."
        )
        return

    try:
        await member.timeout(None)

        await ctx.send(
            f"🔊 Timeout von {member.mention} entfernt."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann den Timeout nicht entfernen."
        )


@bot.command()
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int = 10
):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung für Timeouts."
        )
        return

    if minutes < 1 or minutes > 1440:
        await ctx.send(
            "❌ Minuten müssen zwischen 1 und 1440 liegen."
        )
        return

    try:
        await member.timeout(
            discord.utils.utcnow()
            + timedelta(minutes=minutes),
            reason=f"Timeout von {ctx.author}"
        )

        await ctx.send(
            f"🔇 {member.mention} wurde für "
            f"{minutes} Minuten getimeoutet."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann diesen Benutzer nicht timeouten."
        )


@bot.command()
async def untimeout(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung für Timeouts."
        )
        return

    try:
        await member.timeout(None)

        await ctx.send(
            f"🔊 Timeout von {member.mention} entfernt."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Ich kann den Timeout nicht entfernen."
        )


@bot.command()
async def softban(
    ctx,
    member: discord.Member,
    *,
    reason="Kein Grund angegeben"
):
    if not has_permission(ctx, "ban_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung zum Bannen."
        )
        return

    user_id = member.id

    try:
        await member.ban(
            reason=reason,
            delete_message_seconds=86400
        )

        user = await bot.fetch_user(user_id)

        await ctx.guild.unban(user)

        await ctx.send(
            f"🔨 {member.mention} wurde softgebanned."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Softban konnte nicht ausgeführt werden."
        )


# =========================================================
# WARN SYSTEM
# =========================================================

@bot.command()
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="Kein Grund angegeben"
):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Du hast keine Berechtigung zum Verwarnen."
        )
        return

    warnings_data.setdefault(
        member.id,
        []
    ).append(reason)

    history_data.setdefault(
        member.id,
        []
    ).append(
        f"Warnung von {ctx.author}: {reason}"
    )

    await ctx.send(
        f"⚠️ {member.mention} wurde verwarnt.\n"
        f"Grund: {reason}"
    )


@bot.command()
async def warnings(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    warns = warnings_data.get(
        member.id,
        []
    )

    if not warns:
        await ctx.send(
            f"✅ {member.mention} hat keine Verwarnungen."
        )
        return

    text = "\n".join(
        f"{i + 1}. {reason}"
        for i, reason in enumerate(warns)
    )

    await ctx.send(
        f"⚠️ **Verwarnungen von "
        f"{member.mention}**\n{text}"
    )


@bot.command()
async def warnlist(ctx):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if not warnings_data:
        await ctx.send(
            "✅ Keine Verwarnungen vorhanden."
        )
        return

    text = []

    for user_id, warns in warnings_data.items():
        member = ctx.guild.get_member(user_id)

        if member:
            name = member.mention
        else:
            name = str(user_id)

        text.append(
            f"{name}: {len(warns)} Warnung(en)"
        )

    await ctx.send(
        "⚠️ **Warnliste**\n"
        + "\n".join(text)
    )


@bot.command()
async def unwarn(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    warns = warnings_data.get(
        member.id,
        []
    )

    if not warns:
        await ctx.send(
            "❌ Dieser Benutzer hat keine Verwarnungen."
        )
        return

    warns.pop()

    if not warns:
        warnings_data.pop(
            member.id,
            None
        )

    history_data.setdefault(
        member.id,
        []
    ).append(
        f"Letzte Warnung entfernt von {ctx.author}"
    )

    await ctx.send(
        f"✅ Letzte Warnung von "
        f"{member.mention} entfernt."
    )


@bot.command()
async def history(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    history_entries = history_data.get(
        member.id,
        []
    )

    if not history_entries:
        await ctx.send(
            "📋 Keine Moderations-Historie vorhanden."
        )
        return

    text = "\n".join(
        f"• {entry}"
        for entry in history_entries[-20:]
    )

    await ctx.send(
        f"📋 **Moderations-Historie von "
        f"{member}**\n{text}"
    )


@bot.command()
async def reason(
    ctx,
    member: discord.Member,
    *,
    text
):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    history_data.setdefault(
        member.id,
        []
    ).append(
        f"Grund von {ctx.author}: {text}"
    )

    await ctx.send(
        f"📝 Grund für {member.mention} gespeichert."
    )


@bot.command()
async def modlog(ctx, member: discord.Member):
    if not has_permission(ctx, "moderate_members"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    history_entries = history_data.get(
        member.id,
        []
    )

    if not history_entries:
        await ctx.send(
            "📋 Keine Moderations-Historie vorhanden."
        )
        return

    text = "\n".join(
        f"• {entry}"
        for entry in history_entries[-20:]
    )

    await ctx.send(
        f"📋 **Moderations-Historie von "
        f"{member}**\n{text}"
    )


# =========================================================
# NACHRICHTEN
# =========================================================

@bot.command()
async def clear(ctx, amount: int):
    if not has_permission(ctx, "manage_messages"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if amount < 1 or amount > 100:
        await ctx.send(
            "❌ Anzahl muss zwischen 1 und 100 liegen."
        )
        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 {len(deleted) - 1} Nachrichten gelöscht."
    )

    await msg.delete(delay=3)


@bot.command()
async def purge(
    ctx,
    member: discord.Member,
    amount: int
):
    if not has_permission(ctx, "manage_messages"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if amount < 1 or amount > 100:
        await ctx.send(
            "❌ Anzahl muss zwischen 1 und 100 liegen."
        )
        return

    deleted = await ctx.channel.purge(
        limit=amount,
        check=lambda message:
            message.author.id == member.id
    )

    await ctx.send(
        f"🧹 {len(deleted)} Nachrichten von "
        f"{member.mention} gelöscht.",
        delete_after=3
    )


# =========================================================
# KANAL
# =========================================================

@bot.command()
async def slowmode(ctx, seconds: int):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if seconds < 0 or seconds > 21600:
        await ctx.send(
            "❌ Sekunden müssen zwischen "
            "0 und 21600 liegen."
        )
        return

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    await ctx.send(
        f"🐌 Slowmode: {seconds} Sekunden."
    )


@bot.command()
async def lock(ctx):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔒 Kanal gesperrt."
    )


@bot.command()
async def unlock(ctx):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = True

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔓 Kanal entsperrt."
    )


@bot.command()
async def renamechannel(ctx, *, name):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    old_name = ctx.channel.name

    await ctx.channel.edit(
        name=name
    )

    await ctx.send(
        f"✏️ **{old_name}** wurde zu "
        f"**{name}** umbenannt."
    )


@bot.command()
async def createchannel(ctx, *, name):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    channel = await ctx.guild.create_text_channel(
        name
    )

    await ctx.send(
        f"✅ Kanal {channel.mention} erstellt."
    )


@bot.command()
async def deletechannel(ctx):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.send(
        "🗑️ Dieser Kanal wird gelöscht.",
        delete_after=1
    )

    await asyncio.sleep(1)

    await ctx.channel.delete()


# =========================================================
# BENUTZER
# =========================================================

@bot.command()
async def nick(
    ctx,
    member: discord.Member,
    *,
    name
):
    if not has_permission(ctx, "manage_nicknames"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await member.edit(
        nick=name
    )

    await ctx.send(
        f"✏️ Nickname von "
        f"{member.mention} geändert."
    )


@bot.command()
async def nickname(
    ctx,
    member: discord.Member,
    *,
    name
):
    if not has_permission(ctx, "manage_nicknames"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await member.edit(
        nick=name
    )

    await ctx.send(
        f"✏️ Nickname von "
        f"{member.mention} geändert."
    )


@bot.command()
async def userinfo(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    await ctx.send(
        f"👤 **{member}**\n"
        f"ID: `{member.id}`\n"
        f"Bot: {'Ja' if member.bot else 'Nein'}"
    )


@bot.command()
async def avatar(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    embed = discord.Embed(
        title=f"🖼️ Avatar von {member}"
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def roles(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    role_names = [
        role.name
        for role in member.roles
        if role.name != "@everyone"
    ]

    await ctx.send(
        "🎭 **Rollen:**\n"
        + (
            "\n".join(role_names)
            if role_names
            else "Keine"
        )
    )


@bot.command()
async def checkrole(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    role_names = [
        role.name
        for role in member.roles
        if role.name != "@everyone"
    ]

    await ctx.send(
        "🎭 **Rollen:**\n"
        + (
            "\n".join(role_names)
            if role_names
            else "Keine"
        )
    )


@bot.command()
async def permissions(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    p = member.guild_permissions

    text = (
        f"Administrator: "
        f"{'✅' if p.administrator else '❌'}\n"
        f"Ban: {'✅' if p.ban_members else '❌'}\n"
        f"Kick: {'✅' if p.kick_members else '❌'}\n"
        f"Moderate: "
        f"{'✅' if p.moderate_members else '❌'}\n"
        f"Manage Messages: "
        f"{'✅' if p.manage_messages else '❌'}\n"
        f"Manage Channels: "
        f"{'✅' if p.manage_channels else '❌'}\n"
        f"Manage Roles: "
        f"{'✅' if p.manage_roles else '❌'}"
    )

    await ctx.send(
        f"🔐 **Berechtigungen von "
        f"{member}**\n{text}"
    )


@bot.command()
async def joined(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    if member.joined_at is None:
        await ctx.send(
            "❌ Keine Beitrittszeit verfügbar."
        )
        return

    await ctx.send(
        f"📅 {member.mention} ist seit "
        f"{discord.utils.format_dt(member.joined_at, 'F')} "
        f"auf dem Server."
    )


@bot.command()
async def created(
    ctx,
    member: discord.Member = None
):
    member = member or ctx.author

    await ctx.send(
        f"📅 Account erstellt: "
        f"{discord.utils.format_dt(member.created_at, 'F')}"
    )


# =========================================================
# ROLLEN
# =========================================================

@bot.command()
async def role(
    ctx,
    member: discord.Member,
    *,
    role_name
):
    if not has_permission(ctx, "manage_roles"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    role_obj = discord.utils.get(
        ctx.guild.roles,
        name=role_name
    )

    if role_obj is None:
        await ctx.send(
            "❌ Rolle nicht gefunden."
        )
        return

    if role_obj >= ctx.guild.me.top_role:
        await ctx.send(
            "❌ Diese Rolle ist zu hoch."
        )
        return

    await member.add_roles(
        role_obj
    )

    await ctx.send(
        f"✅ {role_obj.mention} an "
        f"{member.mention} gegeben."
    )


@bot.command()
async def unrole(
    ctx,
    member: discord.Member,
    *,
    role_name
):
    if not has_permission(ctx, "manage_roles"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    role_obj = discord.utils.get(
        ctx.guild.roles,
        name=role_name
    )

    if role_obj is None:
        await ctx.send(
            "❌ Rolle nicht gefunden."
        )
        return

    if role_obj >= ctx.guild.me.top_role:
        await ctx.send(
            "❌ Diese Rolle ist zu hoch."
        )
        return

    await member.remove_roles(
        role_obj
    )

    await ctx.send(
        f"✅ Rolle von "
        f"{member.mention} entfernt."
    )


@bot.command()
async def roleinfo(ctx, *, role_name):
    role_obj = discord.utils.get(
        ctx.guild.roles,
        name=role_name
    )

    if role_obj is None:
        await ctx.send(
            "❌ Rolle nicht gefunden."
        )
        return

    await ctx.send(
        f"🎭 **{role_obj.name}**\n"
        f"ID: `{role_obj.id}`\n"
        f"Mitglieder: `{len(role_obj.members)}`"
    )


@bot.command()
async def rolelist(ctx):
    role_names = [
        role.name
        for role in ctx.guild.roles
        if role.name != "@everyone"
    ]

    await ctx.send(
        "🎭 **Rollen:**\n"
        + (
            "\n".join(role_names)
            if role_names
            else "Keine"
        )
    )


@bot.command()
async def createrole(ctx, *, name):
    if not has_permission(ctx, "manage_roles"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    role_obj = await ctx.guild.create_role(
        name=name
    )

    await ctx.send(
        f"✅ Rolle **{role_obj.name}** erstellt."
    )


@bot.command()
async def deleterole(ctx, *, name):
    if not has_permission(ctx, "manage_roles"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    role_obj = discord.utils.get(
        ctx.guild.roles,
        name=name
    )

    if role_obj is None:
        await ctx.send(
            "❌ Rolle nicht gefunden."
        )
        return

    if role_obj >= ctx.guild.me.top_role:
        await ctx.send(
            "❌ Diese Rolle ist zu hoch für meinen Bot."
        )
        return

    await role_obj.delete()

    await ctx.send(
        f"🗑️ Rolle **{name}** gelöscht."
    )


@bot.command()
async def autorole(ctx, *, role_name):
    global autorole_id

    if not has_permission(ctx, "manage_roles"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    role_obj = discord.utils.get(
        ctx.guild.roles,
        name=role_name
    )

    if role_obj is None:
        await ctx.send(
            "❌ Rolle nicht gefunden."
        )
        return

    if role_obj >= ctx.guild.me.top_role:
        await ctx.send(
            "❌ Diese Rolle ist zu hoch für meinen Bot."
        )
        return

    autorole_id = role_obj.id

    await ctx.send(
        f"🎭 Autorole gesetzt: "
        f"**{role_obj.name}**"
    )


# =========================================================
# SERVER
# =========================================================

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

    await ctx.send(
        f"📊 **{guild.name}**\n"
        f"👥 Mitglieder: `{guild.member_count}`\n"
        f"💬 Kanäle: `{len(guild.channels)}`\n"
        f"🎭 Rollen: `{len(guild.roles)}`"
    )


@bot.command()
async def channelinfo(ctx):
    await ctx.send(
        f"💬 **{ctx.channel.name}**\n"
        f"ID: `{ctx.channel.id}`\n"
        f"Typ: `{ctx.channel.type}`"
    )


@bot.command()
async def membercount(ctx):
    await ctx.send(
        f"👥 Mitglieder: "
        f"**{ctx.guild.member_count}**"
    )


@bot.command()
async def members(ctx):
    await ctx.send(
        f"👥 Mitglieder: "
        f"**{ctx.guild.member_count}**"
    )


@bot.command()
async def bots(ctx):
    count = sum(
        1
        for member in ctx.guild.members
        if member.bot
    )

    await ctx.send(
        f"🤖 Bots: **{count}**"
    )


@bot.command()
async def channels(ctx):
    await ctx.send(
        f"💬 Kanäle: "
        f"**{len(ctx.guild.channels)}**"
    )


@bot.command()
async def servericon(ctx):
    if ctx.guild.icon:
        await ctx.send(
            ctx.guild.icon.url
        )
    else:
        await ctx.send(
            "❌ Kein Server-Icon."
        )


@bot.command()
async def serverbanner(ctx):
    if ctx.guild.banner:
        await ctx.send(
            ctx.guild.banner.url
        )
    else:
        await ctx.send(
            "❌ Kein Server-Banner."
        )


@bot.command()
async def botinfo(ctx):
    await ctx.send(
        f"🤖 **{bot.user}**\n"
        f"ID: `{bot.user.id}`\n"
        f"Server: `{len(bot.guilds)}`"
    )


# =========================================================
# BOT STATUS
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! "
        f"`{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def botstatus(ctx):
    await ctx.send(
        f"🤖 **Bot-Status**\n"
        f"Online: ✅\n"
        f"Ping: `{round(bot.latency * 1000)}ms`\n"
        f"Server: `{len(bot.guilds)}`"
    )


@bot.command()
async def status(ctx):
    await ctx.send(
        f"🤖 **Bot-Status**\n"
        f"Online: ✅\n"
        f"Ping: `{round(bot.latency * 1000)}ms`\n"
        f"Server: `{len(bot.guilds)}`"
    )


@bot.command()
async def uptime(ctx):
    elapsed = datetime.now() - bot_start_time

    total_seconds = int(
        elapsed.total_seconds()
    )

    days, remainder = divmod(
        total_seconds,
        86400
    )

    hours, remainder = divmod(
        remainder,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    await ctx.send(
        f"⏱️ **Uptime:** "
        f"{days}T {hours}Std "
        f"{minutes}Min {seconds}Sek"
    )


# =========================================================
# FUN
# =========================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question):
    answers = [
        "Ja.",
        "Nein.",
        "Vielleicht.",
        "Sehr wahrscheinlich.",
        "Eher nicht.",
        "Keine Ahnung."
    ]

    await ctx.send(
        f"🎱 **Frage:** {question}\n"
        f"**Antwort:** "
        f"{random.choice(answers)}"
    )


@bot.command()
async def coinflip(ctx):
    await ctx.send(
        f"🪙 **{random.choice(['Kopf', 'Zahl'])}**"
    )


@bot.command()
async def dice(ctx):
    await ctx.send(
        f"🎲 **{random.randint(1, 6)}**"
    )


@bot.command()
async def choose(ctx, *, options):
    choices = [
        option.strip()
        for option in options.split("|")
        if option.strip()
    ]

    if len(choices) < 2:
        await ctx.send(
            "❌ Beispiel: "
            "`?choose Pizza | Burger`"
        )
        return

    await ctx.send(
        f"🎯 Ich wähle: "
        f"**{random.choice(choices)}**"
    )


@bot.command()
async def say(ctx, *, text):
    if not has_permission(ctx, "manage_messages"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.message.delete()
    await ctx.send(text)


# =========================================================
# COMMUNITY
# =========================================================

@bot.command()
async def poll(ctx, *, question):
    message = await ctx.send(
        f"📊 **Umfrage**\n\n"
        f"{question}\n\n"
        f"👍 Ja\n"
        f"👎 Nein"
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.command()
async def announce(ctx, *, text):
    if not has_permission(ctx, "manage_messages"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    embed = discord.Embed(
        title="📢 Ankündigung",
        description=text,
        timestamp=discord.utils.utcnow()
    )

    embed.set_footer(
        text=f"Von {ctx.author}"
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def suggest(ctx, *, text):
    embed = discord.Embed(
        title="💡 Vorschlag",
        description=text
    )

    message = await ctx.send(
        embed=embed
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.command()
async def feedback(ctx, *, text):
    await ctx.send(
        f"💬 **Feedback von "
        f"{ctx.author.mention}:**\n{text}"
    )


@bot.command()
async def report(
    ctx,
    member: discord.Member,
    *,
    reason
):
    await ctx.send(
        f"🚨 Meldung über "
        f"{member.mention} wurde aufgenommen.\n"
        f"Grund: {reason}"
    )


# =========================================================
# TICKETS
# =========================================================

@bot.command()
async def ticket(ctx):
    channel_name = (
        f"ticket-{ctx.author.id}"
    )

    existing = discord.utils.get(
        ctx.guild.text_channels,
        name=channel_name
    )

    if existing:
        await ctx.send(
            f"❌ Dein Ticket existiert bereits: "
            f"{existing.mention}"
        )
        return

    overwrites = {
        ctx.guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        ctx.author:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            ),

        ctx.guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
    }

    channel = await ctx.guild.create_text_channel(
        channel_name,
        overwrites=overwrites
    )

    await channel.send(
        f"🎫 Willkommen {ctx.author.mention}!\n"
        f"Beschreibe hier dein Anliegen.\n"
        f"Nutze `?close` zum Schließen."
    )

    await ctx.send(
        f"🎫 Ticket erstellt: "
        f"{channel.mention}"
    )


@bot.command()
async def close(ctx):
    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ Das ist kein Ticket-Kanal."
        )
        return

    await ctx.send(
        "🔒 Ticket wird geschlossen..."
    )

    await asyncio.sleep(2)

    await ctx.channel.delete()


@bot.command()
async def add(
    ctx,
    member: discord.Member
):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ Das ist kein Ticket-Kanal."
        )
        return

    await ctx.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True
    )

    await ctx.send(
        f"✅ {member.mention} wurde "
        f"zum Ticket hinzugefügt."
    )


@bot.command()
async def remove(
    ctx,
    member: discord.Member
):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ Das ist kein Ticket-Kanal."
        )
        return

    await ctx.channel.set_permissions(
        member,
        view_channel=False,
        send_messages=False
    )

    await ctx.send(
        f"✅ {member.mention} wurde "
        f"aus dem Ticket entfernt."
    )


@bot.command()
async def claim(ctx):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ Das ist kein Ticket-Kanal."
        )
        return

    await ctx.send(
        f"🎫 Ticket übernommen von "
        f"{ctx.author.mention}."
    )


@bot.command()
async def rename(ctx, *, name):
    if not has_permission(ctx, "manage_channels"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    if not ctx.channel.name.startswith(
        "ticket-"
    ):
        await ctx.send(
            "❌ Das ist kein Ticket-Kanal."
        )
        return

    await ctx.channel.edit(
        name=name
    )

    await ctx.send(
        "✏️ Ticket umbenannt."
    )


# =========================================================
# REMINDER
# =========================================================

@bot.command()
async def remind(
    ctx,
    seconds: int,
    *,
    text
):
    if seconds < 1 or seconds > 86400:
        await ctx.send(
            "❌ Zeit muss zwischen "
            "1 und 86400 Sekunden liegen."
        )
        return

    await ctx.send(
        f"⏰ Erinnerung in "
        f"{seconds} Sekunden gesetzt."
    )

    await asyncio.sleep(seconds)

    await ctx.send(
        f"⏰ {ctx.author.mention}: "
        f"**{text}**"
    )


# =========================================================
# WELCOME + AUTOROLE
# =========================================================

@bot.command()
async def welcome(ctx, state):
    global welcome_enabled

    if not has_permission(ctx, "manage_guild"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    state = state.lower()

    if state not in ("on", "off"):
        await ctx.send(
            "❌ Benutze "
            "`?welcome on` oder `?welcome off`."
        )
        return

    welcome_enabled = (
        state == "on"
    )

    await ctx.send(
        f"👋 Welcome-System: "
        f"{'AN' if welcome_enabled else 'AUS'}"
    )


@bot.command()
async def setwelcome(ctx, *, message):
    global welcome_message
    global welcome_channel_id
    global welcome_enabled

    if not has_permission(ctx, "manage_guild"):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    welcome_message = message
    welcome_channel_id = ctx.channel.id
    welcome_enabled = True

    await ctx.send(
        "✅ Welcome-Nachricht gespeichert.\n"
        f"📢 Kanal: {ctx.channel.mention}\n"
        f"💬 Nachricht: {message}"
    )


# =========================================================
# WEITERE COMMANDS
# =========================================================


@bot.command()
async def raid(ctx):
    if not has_permission(ctx, "administrator"):
        await ctx.send(
            "❌ Nur Administratoren können "
            "den Raid-Alarm auslösen."
        )
        return

    role = ctx.guild.get_role(
        1551240024098340916
    )

    if role is None:
        await ctx.send(
            "❌ Raid-Rolle nicht gefunden."
        )
        return

    await ctx.send(
        f"{role.mention} ⚠️ **RAID-ALARM!**\n"
        "Bitte sofort den Server überprüfen.",
        allowed_mentions=discord.AllowedMentions(
            roles=True
        )
    )


@bot.command(name="commands")
async def commands_list(ctx):
    await ctx.send(
        "📋 **Meine Commands**\n\n"

        "**Moderation:**\n"
        "`?ban` `?unban` `?kick` `?mute` `?unmute`\n"
        "`?timeout` `?untimeout` `?softban`\n"
        "`?warn` `?warnings` `?warnlist` `?unwarn`\n"
        "`?history` `?reason` `?modlog`\n"
        "`?clear` `?purge`\n\n"

        "**Server:**\n"
        "`?serverinfo` `?channelinfo` "
        "`?membercount` `?members` `?bots`\n"
        "`?channels` `?servericon` "
        "`?serverbanner` `?botinfo`\n\n"

        "**Bot:**\n"
         "`?ping` `?botstatus` `?status` `?uptime`\n\n"
        "**Fun:**\n"
        "`?8ball` `?coinflip` `?dice` `?choose`\n\n"

        "**Community:**\n"
        "`?poll` `?announce` `?suggest` `?feedback` `?report`\n\n"

        "**Sonstiges:**\n"
                "`?welcome` `?setwelcome` `?remind`"
    )


# =========================================================
# WELCOME + AUTOROLE EVENT
# =========================================================

@bot.event
async def on_member_join(member):
    if autorole_id:
        role = member.guild.get_role(autorole_id)
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

    if welcome_enabled and welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            text = welcome_message.replace("{member}", member.mention)
            try:
                await channel.send(text)
            except discord.Forbidden:
                pass


# =========================================================
# NACHRICHTEN / ANTI-LINK / CAPS
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if antilink_enabled:
        content = message.content.lower()

        if (
            "http://" in content
            or "https://" in content
        ):
            if not message.author.guild_permissions.manage_messages:
                try:
                    await message.delete()

                    await message.channel.send(
                        f"🔗 {message.author.mention} "
                        "Links sind hier nicht erlaubt.",
                        delete_after=3
                    )

                    return

                except discord.Forbidden:
                    pass

    if caps_enabled:
        letters = [
            char
            for char in message.content
            if char.isalpha()
        ]

        if len(letters) >= 8:
            uppercase = sum(
                1
                for char in letters
                if char.isupper()
            )

            if (
                uppercase / len(letters)
                >= 0.8
            ):
                if not message.author.guild_permissions.manage_messages:
                    try:
                        await message.delete()

                        await message.channel.send(
                            f"🔠 {message.author.mention} "
                            "Bitte weniger Großbuchstaben.",
                            delete_after=3
                        )

                        return

                    except discord.Forbidden:
                        pass

    await bot.process_commands(message)


# =========================================================
# FEHLERBEHANDLUNG
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Fehlender Parameter. "
            "Benutze `?commands` für Beispiele."
        )
        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):
        await ctx.send(
            "❌ Benutzer nicht gefunden. "
            "Bitte benutze eine Erwähnung."
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Ungültiger Parameter."
        )
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du hast nicht die nötigen "
            "Berechtigungen."
        )
        return

    print(
        f"Command-Fehler bei "
        f"{ctx.command}: {error}"
    )


# =========================================================
# ENDE
# =========================================================

bot.run(TOKEN)
