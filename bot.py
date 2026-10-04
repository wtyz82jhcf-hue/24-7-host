# ============================================================
# RLP DISCORD BOT
# discord.py 2.x
# ============================================================

import os
import json
import random
import re
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks


# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

NUMBER_GAME_CHANNEL_ID = 1556308645942136872

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164
SUGGESTION_REVIEW_ROLE_ID = 1530188150456979526

NAMETAG = "RLP | "

DATA_FILE = "bot_data.json"

PREFIX = "?"

# ============================================================
# PANEL MARKER
# ============================================================

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
DEV_SHIFT_PANEL_MARKER = "RLP_DEV_SHIFT_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"
NUMBER_GAME_PANEL_MARKER = "RLP_NUMBER_GAME_PANEL"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# ============================================================
# DATEN
# ============================================================

DEFAULT_DATA = {
    "license_plates": {},
    "developer_tasks": {},
    "active_shifts": {},
    "shift_history": [],
    "suggestions": {},
    "feedback": {},
    "number_games": {},
    "settings": {
        "suggestion_channel": SUGGESTION_CHANNEL_ID,
        "feedback_channel": FEEDBACK_CHANNEL_ID,
        "developer_task_channel": DEVELOPER_TASK_CHANNEL_ID,
        "developer_shift_channel": DEVELOPER_SHIFT_CHANNEL_ID,
        "shift_log_channel": SHIFT_LOG_CHANNEL_ID,
        "license_channel": LICENSE_PLATE_CHANNEL_ID,
        "number_game_channel": NUMBER_GAME_CHANNEL_ID
    }
}


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = json.loads(json.dumps(DEFAULT_DATA))

    for key, value in DEFAULT_DATA.items():
        if key not in data:
            data[key] = value

    return data


def save_data():
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, DATA_FILE)
    except Exception as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


data = load_data()


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def timestamp():
    return int(now().timestamp())


def discord_time(ts):
    return f"<t:{int(ts)}:R>"


def get_guild():
    return bot.get_guild(GUILD_ID)


def get_member(guild, user_id):
    if guild is None:
        return None
    return guild.get_member(int(user_id))


def get_role(guild, role_id):
    if guild is None:
        return None
    return guild.get_role(int(role_id))


def is_owner(member):
    if not isinstance(member, discord.Member):
        return False

    return (
        member.guild_permissions.administrator
        or any(role.id == OWNER_ROLE_ID for role in member.roles)
    )


def is_shift_allowed(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    allowed_roles = {
        OWNER_ROLE_ID,
        SHIFT_PERMISSION_ROLE_ID,
        DEVELOPER_SHIFT_ROLE_ID
    }

    return any(role.id in allowed_roles for role in member.roles)


def is_developer(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    return any(
        role.id in {
            OWNER_ROLE_ID,
            SHIFT_PERMISSION_ROLE_ID,
            DEVELOPER_SHIFT_ROLE_ID
        }
        for role in member.roles
    )


async def send_ephemeral(interaction, content=None, embed=None, view=None):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=content,
                embed=embed,
                view=view,
                ephemeral=True
            )
    except Exception:
        pass


def get_channel(channel_id):
    channel = bot.get_channel(int(channel_id))

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


def get_setting(name, fallback):
    try:
        return int(data["settings"].get(name, fallback))
    except Exception:
        return fallback


async def edit_message_safe(message, *, embed=None, view=None, content=None):
    try:
        await message.edit(
            content=content,
            embed=embed,
            view=view
        )
        return True
    except discord.NotFound:
        return False
    except discord.Forbidden:
        return False
    except Exception as e:
        print(f"[EDIT] {e}")
        return False


# ============================================================
# EMBEDS
# ============================================================

def make_embed(title, description="", color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=now()
    )
    return embed


# ============================================================
# KENNZ EICHEN
# ============================================================

def normalize_plate(plate):
    plate = plate.upper().strip()
    plate = re.sub(r"\s+", " ", plate)
    return plate


def valid_plate(plate):
    # Beispiele:
    # GM AB 123
    # RY ZE 01
    # K XY 9999
    pattern = r"^[A-ZÄÖÜ]{1,3}\s[A-ZÄÖÜ]{1,3}\s\d{1,4}$"
    return bool(re.fullmatch(pattern, plate))


class LicensePlateModal(discord.ui.Modal, title="Kennzeichen setzen"):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RY ZE 01",
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        plate = normalize_plate(self.plate.value)

        if not valid_plate(plate):
            await send_ephemeral(
                interaction,
                "❌ Ungültiges Kennzeichen.\nBeispiel: `RY ZE 01`"
            )
            return

        # Prüfen, ob dieses Kennzeichen bereits jemand besitzt
        for user_id, saved_plate in data["license_plates"].items():
            if saved_plate.upper() == plate.upper() and int(user_id) != interaction.user.id:
                await send_ephemeral(
                    interaction,
                    "❌ Dieses Kennzeichen ist bereits vergeben."
                )
                return

        data["license_plates"][str(interaction.user.id)] = plate
        save_data()

        await send_ephemeral(
            interaction,
            f"✅ Dein Kennzeichen wurde auf **{plate}** gesetzt."
        )


class LicensePlateRemoveButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="license_remove"
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await send_ephemeral(
                interaction,
                "❌ Du hast kein Kennzeichen gespeichert."
            )
            return

        old_plate = data["license_plates"].pop(user_id)
        save_data()

        await send_ephemeral(
            interaction,
            f"✅ Dein Kennzeichen **{old_plate}** wurde entfernt."
        )


class LicensePlateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        set_button = discord.ui.Button(
            label="Kennzeichen setzen",
            emoji="🪪",
            style=discord.ButtonStyle.success,
            custom_id="license_set"
        )

        async def set_callback(interaction):
            await interaction.response.send_modal(LicensePlateModal())

        set_button.callback = set_callback

        self.add_item(set_button)
        self.add_item(LicensePlateRemoveButton())


def license_panel_embed():
    embed = make_embed(
        "🪪 Kennzeichen",
        "Hier kannst du dein persönliches Kennzeichen verwalten.",
        discord.Color.blue()
    )

    embed.add_field(
        name="Kennzeichen setzen",
        value="Klicke auf den Button und gib dein Kennzeichen ein.",
        inline=False
    )

    embed.add_field(
        name="Kennzeichen entfernen",
        value="Entfernt nur dein eigenes gespeichertes Kennzeichen.",
        inline=False
    )

    return embed


# ============================================================
# NAMETAG
# ============================================================

class NametagModal(discord.ui.Modal, title="Nametag ändern"):

    name = discord.ui.TextInput(
        label="Neuer Nametag",
        placeholder="z. B. Max",
        min_length=1,
        max_length=30
    )

    async def on_submit(self, interaction):
        if not isinstance(interaction.user, discord.Member):
            return

        role = get_role(interaction.guild, NAMETAG_ROLE_ID)

        if role is None:
            await send_ephemeral(
                interaction,
                "❌ Die Nametag-Rolle wurde nicht gefunden."
            )
            return

        new_name = self.name.value.strip()

        if not new_name:
            await send_ephemeral(
                interaction,
                "❌ Bitte einen Namen eingeben."
            )
            return

        try:
            await interaction.user.edit(
                nick=f"{NAMETAG}{new_name}"
            )
        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann deinen Nickname nicht ändern."
            )
            return
        except Exception as e:
            print(f"[NAMETAG] {e}")
            await send_ephemeral(
                interaction,
                "❌ Beim Ändern des Nametags ist ein Fehler aufgetreten."
            )
            return

        await send_ephemeral(
            interaction,
            f"✅ Dein Nametag wurde auf **{NAMETAG}{new_name}** gesetzt."
        )


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        button = discord.ui.Button(
            label="Nametag ändern",
            emoji="🏷️",
            style=discord.ButtonStyle.primary,
            custom_id="nametag_change"
        )

        async def callback(interaction):
            await interaction.response.send_modal(NametagModal())

        button.callback = callback
        self.add_item(button)


def nametag_panel_embed():
    return make_embed(
        "🏷️ Nametag",
        "Klicke auf den Button, um deinen Nametag zu ändern.",
        discord.Color.green()
    )


# ============================================================
# DEVELOPER AUFGABEN
# ============================================================

def task_embed(task_id, task):
    status = task.get("status", "Offen")
    assigned_id = task.get("assigned_to")

    if assigned_id:
        member = get_member(get_guild(), assigned_id)
        assigned_text = member.mention if member else f"<@{assigned_id}>"
    else:
        assigned_text = "Niemand"

    if status == "Offen":
        color = discord.Color.blue()
    elif status == "Übernommen":
        color = discord.Color.orange()
    elif status == "Erledigt":
        color = discord.Color.green()
    else:
        color = discord.Color.red()

    embed = make_embed(
        f"🛠️ Developer Aufgabe #{task_id}",
        task.get("description", "Keine Beschreibung."),
        color
    )

    embed.add_field(
        name="Status",
        value=f"**{status}**",
        inline=True
    )

    embed.add_field(
        name="Übernommen von",
        value=assigned_text,
        inline=True
    )

    embed.add_field(
        name="Erstellt von",
        value=f"<@{task.get('created_by')}>",
        inline=True
    )

    embed.set_footer(text=f"Developer Task ID: {task_id}")

    return embed


class DeveloperTaskCreateModal(discord.ui.Modal, title="Developer Aufgabe erstellen"):

    description = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction):
        if not is_developer(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung, Developer-Aufgaben zu erstellen."
            )
            return

        ids = [int(x) for x in data["developer_tasks"].keys() if str(x).isdigit()]
        task_id = max(ids, default=0) + 1

        data["developer_tasks"][str(task_id)] = {
            "description": self.description.value.strip(),
            "created_by": interaction.user.id,
            "assigned_to": None,
            "status": "Offen",
            "created_at": timestamp()
        }

        save_data()

        channel = get_channel(
            get_setting(
                "developer_task_channel",
                DEVELOPER_TASK_CHANNEL_ID
            )
        )

        if channel is None:
            await send_ephemeral(
                interaction,
                "❌ Der Developer-Aufgabenkanal wurde nicht gefunden."
            )
            return

        view = DeveloperTaskView(task_id)

        try:
            await channel.send(
                embed=task_embed(
                    task_id,
                    data["developer_tasks"][str(task_id)]
                ),
                view=view
            )
        except Exception as e:
            print(f"[TASK CREATE] {e}")

            await send_ephemeral(
                interaction,
                "❌ Die Aufgabe konnte nicht im Kanal erstellt werden."
            )
            return

        await send_ephemeral(
            interaction,
            f"✅ Aufgabe **#{task_id}** wurde erstellt."
        )


class DeveloperTaskView(discord.ui.View):

    def __init__(self, task_id):
        super().__init__(timeout=None)

        take = discord.ui.Button(
            label="Übernehmen",
            emoji="📌",
            style=discord.ButtonStyle.primary,
            custom_id=f"task_take_{task_id}"
        )

        done = discord.ui.Button(
            label="Erledigt",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"task_done_{task_id}"
        )

        delete = discord.ui.Button(
            label="Löschen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"task_delete_{task_id}"
        )

        async def take_callback(interaction):
            await task_take(interaction, task_id)

        async def done_callback(interaction):
            await task_done(interaction, task_id)

        async def delete_callback(interaction):
            await task_delete(interaction, task_id)

        take.callback = take_callback
        done.callback = done_callback
        delete.callback = delete_callback

        self.add_item(take)
        self.add_item(done)
        self.add_item(delete)


async def update_task_message(interaction, task_id):
    task = data["developer_tasks"].get(str(task_id))

    if task is None:
        return

    try:
        await interaction.message.edit(
            embed=task_embed(task_id, task),
            view=DeveloperTaskView(task_id)
        )
    except Exception as e:
        print(f"[TASK UPDATE] {e}")


async def task_take(interaction, task_id):
    if not is_developer(interaction.user):
        await send_ephemeral(
            interaction,
            "❌ Du hast keine Berechtigung für Developer-Aufgaben."
        )
        return

    task = data["developer_tasks"].get(str(task_id))

    if task is None:
        await send_ephemeral(
            interaction,
            "❌ Diese Aufgabe existiert nicht mehr."
        )
        return

    if task["status"] == "Erledigt":
        await send_ephemeral(
            interaction,
            "❌ Diese Aufgabe ist bereits erledigt."
        )
        return

    if task.get("assigned_to") is not None:
        await send_ephemeral(
            interaction,
            f"❌ Die Aufgabe wurde bereits von <@{task['assigned_to']}> übernommen."
        )
        return

    task["assigned_to"] = interaction.user.id
    task["status"] = "Übernommen"

    save_data()

    await update_task_message(interaction, task_id)

    await send_ephemeral(
        interaction,
        f"✅ Du hast Aufgabe **#{task_id}** übernommen."
    )


async def task_done(interaction, task_id):
    if not is_developer(interaction.user):
        await send_ephemeral(
            interaction,
            "❌ Du hast keine Berechtigung für Developer-Aufgaben."
        )
        return

    task = data["developer_tasks"].get(str(task_id))

    if task is None:
        await send_ephemeral(
            interaction,
            "❌ Diese Aufgabe existiert nicht mehr."
        )
        return

    assigned = task.get("assigned_to")

    if assigned is not None and int(assigned) != interaction.user.id:
        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Nur die Person, die die Aufgabe übernommen hat, kann sie erledigen."
            )
            return

    task["status"] = "Erledigt"

    save_data()

    await update_task_message(interaction, task_id)

    await send_ephemeral(
        interaction,
        f"✅ Aufgabe **#{task_id}** wurde als erledigt markiert."
    )


async def task_delete(interaction, task_id):
    if not is_owner(interaction.user):
        await send_ephemeral(
            interaction,
            "❌ Nur Owner/Admins können Aufgaben löschen."
        )
        return

    data["developer_tasks"].pop(str(task_id), None)
    save_data()

    try:
        await interaction.message.delete()
    except Exception:
        try:
            await interaction.message.edit(
                embed=make_embed(
                    "🗑️ Aufgabe gelöscht",
                    f"Die Developer-Aufgabe **#{task_id}** wurde gelöscht.",
                    discord.Color.red()
                ),
                view=None
            )
        except Exception:
            pass

    await send_ephemeral(
        interaction,
        f"🗑️ Aufgabe **#{task_id}** wurde gelöscht."
    )


class DeveloperTaskPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        button = discord.ui.Button(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="developer_task_create"
        )

        async def callback(interaction):
            if not is_developer(interaction.user):
                await send_ephemeral(
                    interaction,
                    "❌ Du hast keine Berechtigung."
                )
                return

            await interaction.response.send_modal(
                DeveloperTaskCreateModal()
            )

        button.callback = callback
        self.add_item(button)


def developer_task_panel_embed():
    return make_embed(
        "🛠️ Developer Aufgaben",
        "Erstelle hier eine neue Developer-Aufgabe.\n\n"
        "Aufgaben werden als Embeds im Aufgabenkanal erstellt.",
        discord.Color.blurple()
    )


# ============================================================
# SCHICHT
# ============================================================

def shift_embed():
    active = data["active_shifts"]

    embed = make_embed(
        "🕐 Developer-Schicht",
        "Hier kannst du deinen Developer-Dienst starten oder stoppen.",
        discord.Color.blurple()
    )

    if not active:
        embed.add_field(
            name="Aktueller Dienst",
            value="🟢 Niemand ist aktuell im Dienst.",
            inline=False
        )
    else:
        lines = []

        for user_id, shift in active.items():
            member = get_member(get_guild(), user_id)

            if member:
                name = member.mention
            else:
                name = f"<@{user_id}>"

            lines.append(
                f"🟢 {name}\n"
                f"Start: {discord_time(shift['started_at'])}"
            )

        embed.add_field(
            name="Aktueller Dienst",
            value="\n\n".join(lines),
            inline=False
        )

    embed.add_field(
        name="Status",
        value=(
            "🟢 **Im Dienst** wird direkt hier im Embed angezeigt.\n"
            "🔴 Beim Stoppen wird der Dienst ebenfalls direkt entfernt."
        ),
        inline=False
    )

    return embed


class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        start = discord.ui.Button(
            label="Dienst starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="shift_start"
        )

        stop = discord.ui.Button(
            label="Dienst stoppen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="shift_stop"
        )

        async def start_callback(interaction):
            await shift_start(interaction)

        async def stop_callback(interaction):
            await shift_stop(interaction)

        start.callback = start_callback
        stop.callback = stop_callback

        self.add_item(start)
        self.add_item(stop)


async def refresh_shift_embed():
    channel = get_channel(
        get_setting(
            "developer_shift_channel",
            DEVELOPER_SHIFT_CHANNEL_ID
        )
    )

    if channel is None:
        return

    found = None

    async for message in channel.history(limit=100):
        if (
            message.author.id == bot.user.id
            and message.embeds
            and message.embeds[0].footer
            and message.embeds[0].footer.text == DEV_SHIFT_PANEL_MARKER
        ):
            found = message
            break

    if found:
        try:
            await found.edit(
                embed=shift_embed(),
                view=DeveloperShiftView()
            )
        except Exception as e:
            print(f"[SHIFT EMBED] {e}")


async def shift_start(interaction):
    if not is_shift_allowed(interaction.user):
        await send_ephemeral(
            interaction,
            "❌ Du hast keine Berechtigung, eine Developer-Schicht zu starten."
        )
        return

    user_id = str(interaction.user.id)

    if user_id in data["active_shifts"]:
        await send_ephemeral(
            interaction,
            "❌ Du bist bereits im Dienst."
        )
        return

    role = get_role(interaction.guild, DEVELOPER_SHIFT_ROLE_ID)

    if role is None:
        await send_ephemeral(
            interaction,
            "❌ Die Developer-Schicht-Rolle wurde nicht gefunden."
        )
        return

    bot_member = interaction.guild.get_member(bot.user.id)

    if bot_member is None:
        await send_ephemeral(
            interaction,
            "❌ Der Bot konnte sich selbst auf dem Server nicht finden."
        )
        return

    if role >= bot_member.top_role:
        await send_ephemeral(
            interaction,
            "❌ Die Developer-Schicht-Rolle muss in der Rollenliste unter der höchsten Bot-Rolle stehen."
        )
        return

    try:
        await interaction.user.add_roles(
            role,
            reason="Developer-Schicht gestartet"
        )
    except discord.Forbidden:
        await send_ephemeral(
            interaction,
            "❌ Der Bot darf die Schicht-Rolle nicht vergeben. Prüfe die Rollen-Hierarchie und Manage-Roles."
        )
        return
    except Exception as e:
        print(f"[SHIFT START ROLE] {e}")
        await send_ephemeral(
            interaction,
            "❌ Beim Starten der Schicht ist ein Fehler aufgetreten."
        )
        return

    data["active_shifts"][user_id] = {
        "started_at": timestamp()
    }

    save_data()

    await refresh_shift_embed()

    log_channel = get_channel(
        get_setting(
            "shift_log_channel",
            SHIFT_LOG_CHANNEL_ID
        )
    )

    if log_channel:
        try:
            await log_channel.send(
                f"🟢 {interaction.user.mention} hat den Developer-Dienst gestartet."
            )
        except Exception:
            pass

    await send_ephemeral(
        interaction,
        "🟢 Du bist jetzt im Developer-Dienst."
    )


async def shift_stop(interaction):
    if not is_shift_allowed(interaction.user):
        await send_ephemeral(
            interaction,
            "❌ Du hast keine Berechtigung, eine Developer-Schicht zu stoppen."
        )
        return

    user_id = str(interaction.user.id)

    shift = data["active_shifts"].get(user_id)

    if shift is None:
        await send_ephemeral(
            interaction,
            "❌ Du bist aktuell nicht im Dienst."
        )
        return

    started = shift["started_at"]
    ended = timestamp()
    duration = max(0, ended - started)

    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60

    role = get_role(interaction.guild, DEVELOPER_SHIFT_ROLE_ID)

    if role:
        try:
            await interaction.user.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )
        except Exception as e:
            print(f"[SHIFT STOP ROLE] {e}")

    data["shift_history"].append({
        "user_id": interaction.user.id,
        "started_at": started,
        "ended_at": ended,
        "duration": duration
    })

    data["active_shifts"].pop(user_id, None)

    save_data()

    await refresh_shift_embed()

    log_channel = get_channel(
        get_setting(
            "shift_log_channel",
            SHIFT_LOG_CHANNEL_ID
        )
    )

    if log_channel:
        try:
            await log_channel.send(
                f"🔴 {interaction.user.mention} hat den Developer-Dienst beendet.\n"
                f"⏱️ Dauer: **{hours}h {minutes}m {seconds}s**"
            )
        except Exception:
            pass

    await send_ephemeral(
        interaction,
        f"🔴 Dein Dienst wurde beendet.\n"
        f"⏱️ Dauer: **{hours}h {minutes}m {seconds}s**"
    )


def developer_shift_panel_embed():
    embed = shift_embed()
    embed.set_footer(text=DEV_SHIFT_PANEL_MARKER)
    return embed


# ============================================================
# COMMUNITY
# ============================================================

class FeedbackModal(discord.ui.Modal, title="Feedback"):

    text = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Schreibe dein Feedback...",
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction):
        feedback_id = str(timestamp()) + str(random.randint(100, 999))

        data["feedback"][feedback_id] = {
            "user_id": interaction.user.id,
            "text": self.text.value,
            "created_at": timestamp()
        }

        save_data()

        channel = get_channel(
            get_setting(
                "feedback_channel",
                FEEDBACK_CHANNEL_ID
            )
        )

        if channel:
            embed = make_embed(
                "💬 Neues Feedback",
                self.text.value,
                discord.Color.blue()
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention,
                inline=True
            )

            await channel.send(embed=embed)

        await send_ephemeral(
            interaction,
            "✅ Dein Feedback wurde gesendet."
        )


class SuggestionModal(discord.ui.Modal, title="Vorschlag"):

    text = discord.ui.TextInput(
        label="Vorschlag",
        style=discord.TextStyle.paragraph,
        placeholder="Was möchtest du vorschlagen?",
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction):
        suggestion_id = str(timestamp()) + str(random.randint(100, 999))

        data["suggestions"][suggestion_id] = {
            "user_id": interaction.user.id,
            "text": self.text.value,
            "status": "Offen",
            "created_at": timestamp()
        }

        save_data()

        channel = get_channel(
            get_setting(
                "suggestion_channel",
                SUGGESTION_CHANNEL_ID
            )
        )

        if channel:
            embed = make_embed(
                "💡 Neuer Vorschlag",
                self.text.value,
                discord.Color.orange()
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention,
                inline=True
            )

            embed.add_field(
                name="Status",
                value="🟡 Offen",
                inline=True
            )

            await channel.send(embed=embed)

        await send_ephemeral(
            interaction,
            "✅ Dein Vorschlag wurde gesendet."
        )


class CommunityView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        feedback = discord.ui.Button(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="community_feedback"
        )

        suggestion = discord.ui.Button(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.success,
            custom_id="community_suggestion"
        )

        async def feedback_callback(interaction):
            await interaction.response.send_modal(FeedbackModal())

        async def suggestion_callback(interaction):
            await interaction.response.send_modal(SuggestionModal())

        feedback.callback = feedback_callback
        suggestion.callback = suggestion_callback

        self.add_item(feedback)
        self.add_item(suggestion)


def community_panel_embed():
    return make_embed(
        "💬 Community",
        "Hier kannst du Feedback senden oder einen Vorschlag einreichen.",
        discord.Color.blurple()
    )


# ============================================================
# OWNER PANEL
# ============================================================

class ChannelIdModal(discord.ui.Modal):

    def __init__(self, setting_name, title, description):
        self.setting_name = setting_name
        self.description_text = description

        super().__init__(title=title)

        self.channel_id = discord.ui.TextInput(
            label="Textkanal-ID",
            placeholder="z. B. 123456789012345678",
            min_length=10,
            max_length=25,
            required=True
        )

        self.add_item(self.channel_id)

    async def on_submit(self, interaction):
        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Nur der Owner/Admin kann Einstellungen ändern."
            )
            return

        raw = self.channel_id.value.strip()

        if not raw.isdigit():
            await send_ephemeral(
                interaction,
                "❌ Bitte eine gültige Kanal-ID eingeben."
            )
            return

        channel = interaction.guild.get_channel(int(raw))

        if not isinstance(channel, discord.TextChannel):
            await send_ephemeral(
                interaction,
                "❌ Die angegebene ID gehört nicht zu einem Textkanal auf diesem Server."
            )
            return

        data["settings"][self.setting_name] = channel.id
        save_data()

        await send_ephemeral(
            interaction,
            f"✅ {self.description_text}: {channel.mention}"
        )


class OwnerPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        task_channel = discord.ui.Button(
            label="Aufgaben-Kanal",
            emoji="🛠️",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_tasks"
        )

        shift_channel = discord.ui.Button(
            label="Schicht-Kanal",
            emoji="🕐",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_shift"
        )

        log_channel = discord.ui.Button(
            label="Schicht-Log",
            emoji="📜",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_shiftlog"
        )

        suggestion_channel = discord.ui.Button(
            label="Vorschlags-Kanal",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_suggestions"
        )

        feedback_channel = discord.ui.Button(
            label="Feedback-Kanal",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_feedback"
        )

        number_channel = discord.ui.Button(
            label="Zahlenspiel-Kanal",
            emoji="🔢",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_channel_number"
        )

        async def task_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "developer_task_channel",
                    "Aufgaben-Kanal",
                    "Aufgaben-Kanal gesetzt"
                )
            )

        async def shift_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "developer_shift_channel",
                    "Schicht-Kanal",
                    "Schicht-Kanal gesetzt"
                )
            )

        async def log_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "shift_log_channel",
                    "Schicht-Log",
                    "Schicht-Log gesetzt"
                )
            )

        async def suggestion_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "suggestion_channel",
                    "Vorschlags-Kanal",
                    "Vorschlags-Kanal gesetzt"
                )
            )

        async def feedback_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "feedback_channel",
                    "Feedback-Kanal",
                    "Feedback-Kanal gesetzt"
                )
            )

        async def number_callback(interaction):
            await interaction.response.send_modal(
                ChannelIdModal(
                    "number_game_channel",
                    "Zahlenspiel-Kanal",
                    "Zahlenspiel-Kanal gesetzt"
                )
            )

        task_channel.callback = task_callback
        shift_channel.callback = shift_callback
        log_channel.callback = log_callback
        suggestion_channel.callback = suggestion_callback
        feedback_channel.callback = feedback_callback
        number_channel.callback = number_callback

        self.add_item(task_channel)
        self.add_item(shift_channel)
        self.add_item(log_channel)
        self.add_item(suggestion_channel)
        self.add_item(feedback_channel)
        self.add_item(number_channel)


def owner_panel_embed():
    return make_embed(
        "👑 Owner Panel",
        "Hier kannst du die wichtigsten Bot-Kanäle konfigurieren.\n\n"
        "Die Kanal-Auswahl erfolgt über die **Kanal-ID**, damit keine "
        "fehlerhaften Channel-Selects mehr auftreten.",
        discord.Color.gold()
    )


# ============================================================
# ZAHLENSPIEL
# ============================================================

class NumberGameView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        button = discord.ui.Button(
            label="Spiel starten",
            emoji="🔢",
            style=discord.ButtonStyle.success,
            custom_id="number_game_start"
        )

        async def callback(interaction):
            await start_number_game(interaction)

        button.callback = callback
        self.add_item(button)


class NumberGameModal(discord.ui.Modal, title="Zahlenspiel"):

    guess = discord.ui.TextInput(
        label="Deine Zahl",
        placeholder="Gib eine Zahl ein",
        min_length=1,
        max_length=5,
        required=True
    )

    def __init__(self, game_id):
        super().__init__()
        self.game_id = game_id

    async def on_submit(self, interaction):
        game = data["number_games"].get(str(self.game_id))

        if game is None:
            await send_ephemeral(
                interaction,
                "❌ Dieses Spiel existiert nicht mehr."
            )
            return

        if int(game["user_id"]) != interaction.user.id:
            await send_ephemeral(
                interaction,
                "❌ Dieses Spiel gehört jemand anderem."
            )
            return

        try:
            guess = int(self.guess.value)
        except ValueError:
            await send_ephemeral(
                interaction,
                "❌ Bitte gib eine Zahl ein."
            )
            return

        target = int(game["target"])

        if guess == target:
            attempts = int(game["attempts"]) + 1

            data["number_games"].pop(str(self.game_id), None)
            save_data()

            await send_ephemeral(
                interaction,
                f"🎉 Richtig!\n\n"
                f"Du hast die Zahl **{target}** nach **{attempts}** Versuch(en) erraten."
            )
            return

        game["attempts"] += 1
        save_data()

        if guess < target:
            hint = "📈 Die gesuchte Zahl ist **höher**."
        else:
            hint = "📉 Die gesuchte Zahl ist **niedriger**."

        await send_ephemeral(
            interaction,
            f"❌ Falsch!\n{hint}\n"
            f"Versuche: **{game['attempts']}**"
        )


async def start_number_game(interaction):
    user_id = str(interaction.user.id)

    # Nur ein Spiel pro Person
    for game in data["number_games"].values():
        if str(game.get("user_id")) == user_id:
            await send_ephemeral(
                interaction,
                "❌ Du hast bereits ein Zahlenspiel laufen."
            )
            return

    game_id = str(timestamp()) + str(random.randint(100, 999))

    data["number_games"][game_id] = {
        "user_id": interaction.user.id,
        "target": random.randint(1, 100),
        "attempts": 0,
        "created_at": timestamp()
    }

    save_data()

    await interaction.response.send_modal(
        NumberGameModal(game_id)
    )


def number_game_panel_embed():
    return make_embed(
        "🔢 Zahlenspiel",
        "Klicke auf **Spiel starten**.\n\n"
        "Der Bot denkt sich eine Zahl zwischen **1 und 100** aus. "
        "Du musst sie erraten.",
        discord.Color.purple()
    )


# ============================================================
# PANELS SENDEN / AKTUALISIEREN
# ============================================================

async def ensure_panel(
    channel,
    marker,
    embed,
    view,
    limit=100
):
    if channel is None:
        return None

    try:
        async for message in channel.history(limit=limit):
            if (
                message.author.id == bot.user.id
                and message.embeds
                and message.embeds[0].footer
                and message.embeds[0].footer.text == marker
            ):
                await message.edit(
                    embed=embed,
                    view=view
                )
                return message

        new_message = await channel.send(
            embed=embed,
            view=view
        )

        try:
            await new_message.edit(
                embed=embed,
                view=view
            )
        except Exception:
            pass

        return new_message

    except discord.Forbidden:
        print(
            f"[PANEL] Keine Berechtigung für #{channel.name}"
        )
    except Exception as e:
        print(f"[PANEL] {marker}: {e}")

    return None


def add_marker(embed, marker):
    embed.set_footer(text=marker)
    return embed


async def ensure_fixed_panels():
    guild = get_guild()

    if guild is None:
        print("[READY] Server nicht gefunden.")
        return

    # Nametag
    channel = bot.get_channel(NAMETAG_CHANNEL_ID)

    if isinstance(channel, discord.TextChannel):
        await ensure_panel(
            channel,
            NAMETAG_PANEL_MARKER,
            add_marker(
                nametag_panel_embed(),
                NAMETAG_PANEL_MARKER
            ),
            NametagView()
        )

    # Kennzeichen
    channel = bot.get_channel(LICENSE_PLATE_CHANNEL_ID)

    if isinstance(channel, discord.TextChannel):
        await ensure_panel(
            channel,
            LICENSE_PANEL_MARKER,
            add_marker(
                license_panel_embed(),
                LICENSE_PANEL_MARKER
            ),
            LicensePlateView()
        )

    # Aufgaben
    channel = get_channel(
        get_setting(
            "developer_task_channel",
            DEVELOPER_TASK_CHANNEL_ID
        )
    )

    if channel:
        await ensure_panel(
            channel,
            DEV_TASK_PANEL_MARKER,
            add_marker(
                developer_task_panel_embed(),
                DEV_TASK_PANEL_MARKER
            ),
            DeveloperTaskPanelView()
        )

        # Vorhandene Aufgaben wiederherstellen
        for task_id, task in list(
            data["developer_tasks"].items()
        ):
            # Nur bereits vorhandene Discord-Nachrichten können
            # nicht sicher automatisch zugeordnet werden.
            # Der normale Aufgaben-Panel funktioniert aber weiter.
            pass

    # Schicht
    channel = get_channel(
        get_setting(
            "developer_shift_channel",
            DEVELOPER_SHIFT_CHANNEL_ID
        )
    )

    if channel:
        await ensure_panel(
            channel,
            DEV_SHIFT_PANEL_MARKER,
            developer_shift_panel_embed(),
            DeveloperShiftView()
        )

    # Community
    # Hier werden die fest eingestellten Community-Kanäle genutzt.
    suggestion_channel = get_channel(
        get_setting(
            "suggestion_channel",
            SUGGESTION_CHANNEL_ID
        )
    )

    if suggestion_channel:
        await ensure_panel(
            suggestion_channel,
            COMMUNITY_PANEL_MARKER,
            add_marker(
                community_panel_embed(),
                COMMUNITY_PANEL_MARKER
            ),
            CommunityView()
        )

    # Owner Panel wird bewusst im Vorschlagskanal nur erzeugt,
    # wenn dort noch kein Owner Panel vorhanden ist.
    # Besser ist der separate ?ownerpanel Befehl.


# ============================================================
# COMMANDS
# ============================================================

@bot.command()
@commands.guild_only()
async def help(ctx):
    embed = make_embed(
        "📚 Bot Hilfe",
        "Verfügbare Befehle:",
        discord.Color.blurple()
    )

    embed.add_field(
        name="Panels",
        value=(
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
            "`?devtaskpanel`\n"
            "`?devshiftpanel`\n"
            "`?communitypanel`\n"
            "`?ownerpanel`\n"
            "`?numbergamepanel`"
        ),
        inline=False
    )

    embed.add_field(
        name="Hinweis",
        value="Das Bewerbungssystem ist vollständig entfernt.",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
@commands.guild_only()
async def nametagpanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        nametag_panel_embed(),
        NAMETAG_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=NametagView()
    )


@bot.command()
@commands.guild_only()
async def licensepanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        license_panel_embed(),
        LICENSE_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=LicensePlateView()
    )


@bot.command()
@commands.guild_only()
async def devtaskpanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        developer_task_panel_embed(),
        DEV_TASK_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=DeveloperTaskPanelView()
    )


@bot.command()
@commands.guild_only()
async def devshiftpanel(ctx):
    if not is_owner(ctx.author):
        return

    await ctx.send(
        embed=developer_shift_panel_embed(),
        view=DeveloperShiftView()
    )


@bot.command()
@commands.guild_only()
async def communitypanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        community_panel_embed(),
        COMMUNITY_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=CommunityView()
    )


@bot.command()
@commands.guild_only()
async def ownerpanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        owner_panel_embed(),
        OWNER_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=OwnerPanelView()
    )


@bot.command()
@commands.guild_only()
async def numbergamepanel(ctx):
    if not is_owner(ctx.author):
        return

    embed = add_marker(
        number_game_panel_embed(),
        NUMBER_GAME_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=NumberGameView()
    )


# ============================================================
# STATUS
# ============================================================

status_messages = [
    "RLP | Community",
    "RLP | Developer",
    "RLP | Support",
    "RLP | Deutschland"
]


@tasks.loop(seconds=30)
async def status_loop():
    try:
        text = random.choice(status_messages)

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=text
            )
        )
    except Exception as e:
        print(f"[STATUS] {e}")


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Bot online: {bot.user}")
    print(f"Guild ID: {GUILD_ID}")
    print("=" * 50)

    # Persistente Views
    try:
        bot.add_view(NametagView())
        bot.add_view(LicensePlateView())
        bot.add_view(DeveloperTaskPanelView())
        bot.add_view(DeveloperShiftView())
        bot.add_view(CommunityView())
        bot.add_view(OwnerPanelView())
        bot.add_view(NumberGameView())
    except Exception as e:
        print(f"[VIEWS] {e}")

    # Dynamische Task Views
    for task_id in data["developer_tasks"].keys():
        try:
            bot.add_view(
                DeveloperTaskView(int(task_id))
            )
        except Exception as e:
            print(f"[TASK VIEW] {task_id}: {e}")

    try:
        await ensure_fixed_panels()
    except Exception as e:
        print(f"[PANELS] {e}")

    if not status_loop.is_running():
        status_loop.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Du hast keine Berechtigung für diesen Befehl."
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        return

    print(f"[COMMAND ERROR] {error}")


# ============================================================
# TOKEN PRÜFUNG
# ============================================================

if not TOKEN:
    print(
        "============================================================"
    )
    print(
        "FEHLER: DISCORD_TOKEN wurde nicht gefunden."
    )
    print(
        "Setze die Umgebungsvariable DISCORD_TOKEN mit deinem Bot-Token."
    )
    print(
        "============================================================"
    )
else:
    bot.run(TOKEN)
