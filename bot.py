import os
import json
import time
import random
import asyncio
import re
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200

# Zahlenspiel
NUMBER_GAME_CHANNEL_ID = 1556308645942136872

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164
SUGGESTION_REVIEW_ROLE_ID = 1530188150456979526

NAMETAG = "RLP | "

DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
DEV_SHIFT_PANEL_MARKER = "RLP_DEV_SHIFT_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"
EMOJI_QUIZ_PANEL_MARKER = "RLP_EMOJI_QUIZ_PANEL"
NUMBER_GAME_PANEL_MARKER = "RLP_NUMBER_GAME_PANEL"

PREFIX = "?"

BOT_START_TIME = time.time()

STATUS_TEXTS = [
    "🚔 RLP | RP-System",
    "🌐 Für eine starke & aktive Community",
    "✨ Professionell • Innovativ • Einzigartig",
    "💻 Developed by RyZe 🚀"
]

# Emoji-Quiz-Limits
EMOJI_LIMIT = 3
EMOJI_RESET_SECONDS = 2 * 60 * 60

status_task = None
startup_done = False


# =========================================================
# INTENTS / BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "license_plates": {},
    "applications": {},
    "developer_tasks": {},
    "active_developer_shifts": {},
    "suggestions": {},
    "feedback": [],

    # Neues Emoji-Quiz
    "emoji_quiz": {},

    # Neues Zahlenspiel
    "number_game": {
        "current_number": 1,
        "last_user_id": None,
        "wrong_attempts": {},
        "message_id": None,
        "last_easter_egg": 0
    }
}


# =========================================================
# DATA SYSTEM
# =========================================================

def save_data(content):
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                content,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

    except Exception as error:
        print(
            f"Speicherfehler: {error}"
        )


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(
            DEFAULT_DATA
        )

        return json.loads(
            json.dumps(DEFAULT_DATA)
        )

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            loaded = json.load(file)

    except Exception:
        loaded = {}

    changed = False

    for key, value in DEFAULT_DATA.items():
        if key not in loaded:
            loaded[key] = json.loads(
                json.dumps(value)
            )

            changed = True

    # Alte Datenstrukturen absichern
    dictionary_keys = [
        "license_plates",
        "applications",
        "developer_tasks",
        "active_developer_shifts",
        "suggestions",
        "emoji_quiz"
    ]

    for key in dictionary_keys:
        if not isinstance(
            loaded.get(key),
            dict
        ):
            loaded[key] = {}
            changed = True

    if not isinstance(
        loaded.get("feedback"),
        list
    ):
        loaded["feedback"] = []
        changed = True

    if not isinstance(
        loaded.get("number_game"),
        dict
    ):
        loaded["number_game"] = json.loads(
            json.dumps(
                DEFAULT_DATA["number_game"]
            )
        )

        changed = True

    for key, value in DEFAULT_DATA[
        "number_game"
    ].items():

        if key not in loaded[
            "number_game"
        ]:
            loaded[
                "number_game"
            ][key] = json.loads(
                json.dumps(value)
            )

            changed = True

    if not isinstance(
        loaded["number_game"].get(
            "wrong_attempts"
        ),
        dict
    ):
        loaded["number_game"][
            "wrong_attempts"
        ] = {}

        changed = True

    if changed:
        save_data(
            loaded
        )

    return loaded


data = load_data()


# =========================================================
# BASIC HELPERS
# =========================================================

def get_guild():
    return bot.get_guild(
        GUILD_ID
    )


def get_channel(channel_id):
    channel = bot.get_channel(
        channel_id
    )

    if isinstance(
        channel,
        discord.TextChannel
    ):
        return channel

    return None


def member_has_role(
    member,
    role_id
):
    if not isinstance(
        member,
        discord.Member
    ):
        return False

    return any(
        role.id == role_id
        for role in member.roles
    )


def is_owner(member):
    return member_has_role(
        member,
        OWNER_ROLE_ID
    )


def is_shift_manager(member):
    return member_has_role(
        member,
        SHIFT_PERMISSION_ROLE_ID
    )


def current_time():
    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def make_embed(
    title,
    description="",
    color=None
):
    if color is None:
        color = discord.Color.blurple()

    result = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(
            timezone.utc
        )
    )

    result.set_footer(
        text="RLP • RP-System"
    )

    return result


async def error_response(
    interaction,
    message
):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except Exception:
        pass


async def find_panel(
    channel_id,
    marker
):
    channel = get_channel(
        channel_id
    )

    if channel is None:
        return None

    try:
        async for message in channel.history(
            limit=150
        ):
            if marker in message.content:
                return message

            for item in message.embeds:
                if marker in (
                    item.title or ""
                ):
                    return message

                if marker in (
                    item.description or ""
                ):
                    return message

    except Exception as error:
        print(
            f"Panel-Suche Fehler: {error}"
        )

    return None


async def update_panel(
    channel_id,
    marker,
    panel_embed,
    view
):
    channel = get_channel(
        channel_id
    )

    if channel is None:
        return None

    old_message = await find_panel(
        channel_id,
        marker
    )

    content = f"<!-- {marker} -->"

    try:
        if old_message:
            await old_message.edit(
                content=content,
                embed=panel_embed,
                view=view
            )

            return old_message

        return await channel.send(
            content=content,
            embed=panel_embed,
            view=view
        )

    except discord.Forbidden:
        print(
            f"Keine Rechte im Channel {channel_id}"
        )

    except Exception as error:
        print(
            f"Panel-Fehler: {error}"
        )

    return None


# =========================================================
# BOT STATUS
# =========================================================

async def rotate_bot_status():
    global status_task

    index = 0

    while True:
        try:
            await bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=STATUS_TEXTS[index]
                )
            )

            index = (
                index + 1
            ) % len(
                STATUS_TEXTS
            )

            await asyncio.sleep(
                15
            )

        except asyncio.CancelledError:
            break

        except Exception as error:
            print(
                f"Status-Fehler: {error}"
            )

            await asyncio.sleep(
                15
            )


# =========================================================
# NAMETAG
# =========================================================

def remove_nametag(name):
    if not name:
        return name

    if name.startswith(
        "RLP | "
    ):
        return name[6:]

    if name.startswith(
        "RLP |\u00a0"
    ):
        return name[6:]

    return name


def nametag_panel():
    return make_embed(
        "🏷️ RLP Nametag",
        (
            "Verwalte hier deinen Nametag.\n\n"
            "🏷️ **Nametag setzen**\n"
            "Setzt `RLP | ` vor deinen aktuellen Namen.\n\n"
            "♻️ **Nametag entfernen**\n"
            "Entfernt ausschließlich den RLP-Präfix.\n\n"
            "Deine Rollen werden dabei nicht verändert."
        ),
        discord.Color.blue()
    )


class NametagSet(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Nametag setzen",
            emoji="🏷️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_nametag_set"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not member_has_role(
            member,
            NAMETAG_ROLE_ID
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung für das Nametag-System."
            )

        current = (
            member.nick
            or member.name
        )

        if current.startswith(
            NAMETAG
        ):
            return await error_response(
                interaction,
                "❌ Du hast bereits einen RLP-Nametag."
            )

        new_name = NAMETAG + current

        if len(new_name) > 32:
            return await error_response(
                interaction,
                "❌ Dein Name wäre mit Nametag zu lang."
            )

        try:
            await member.edit(
                nick=new_name,
                reason="RLP Nametag gesetzt"
            )

            await interaction.response.send_message(
                f"✅ Nametag gesetzt: `{new_name}`",
                ephemeral=True
            )

        except discord.Forbidden:
            await error_response(
                interaction,
                "❌ Der Bot kann deinen Nickname nicht ändern."
            )

        except Exception as error:
            print(
                f"Nametag-Fehler: {error}"
            )

            await error_response(
                interaction,
                "❌ Der Nametag konnte nicht gesetzt werden."
            )


class NametagRemove(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            emoji="♻️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_remove"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not member.nick:
            return await error_response(
                interaction,
                "❌ Du hast keinen eigenen Nickname."
            )

        old_name = member.nick
        new_name = remove_nametag(
            old_name
        )

        if old_name == new_name:
            return await error_response(
                interaction,
                "❌ Bei dir ist kein RLP-Nametag vorhanden."
            )

        try:
            await member.edit(
                nick=new_name,
                reason="RLP Nametag entfernt"
            )

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await error_response(
                interaction,
                "❌ Der Bot kann deinen Nickname nicht ändern."
            )

        except Exception as error:
            print(
                f"Nametag-Fehler: {error}"
            )

            await error_response(
                interaction,
                "❌ Der Nametag konnte nicht entfernt werden."
            )


class NametagView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            NametagSet()
        )

        self.add_item(
            NametagRemove()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

def normalize_plate(value):
    return " ".join(
        str(value)
        .strip()
        .upper()
        .split()
    )


def get_plate_number(value):
    parts = normalize_plate(
        value
    ).split()

    if not parts:
        return None

    number = parts[-1]

    if not number.isdigit():
        return None

    return int(number)


def get_user_plate(user_id):
    value = data[
        "license_plates"
    ].get(
        str(user_id)
    )

    if isinstance(
        value,
        dict
    ):
        return value.get(
            "plate"
        )

    if isinstance(
        value,
        str
    ):
        return value

    return None


def plate_number_used(number):
    for value in data[
        "license_plates"
    ].values():

        if isinstance(
            value,
            dict
        ):
            plate = value.get(
                "plate",
                ""
            )
        else:
            plate = str(value)

        if get_plate_number(
            plate
        ) == number:
            return True

    return False


def license_panel():
    result = make_embed(
        "🚗 RLP Kennzeichen",
        (
            "Hier kannst du dein Kennzeichen registrieren.\n\n"
            "• Pro Benutzer ist ein Kennzeichen möglich.\n"
            "• Die Nummer am Ende muss serverweit einmalig sein.\n"
            "• Der Präfix darf mehrfach verwendet werden.\n\n"
            "Beispiele:\n"
            "`RLP 01`\n"
            "`RY ZE 01`"
        ),
        discord.Color.green()
    )

    entries = []

    guild = get_guild()

    for user_id, value in data[
        "license_plates"
    ].items():

        if isinstance(
            value,
            dict
        ):
            plate = value.get(
                "plate",
                "Unbekannt"
            )
        else:
            plate = str(value)

        member = None

        try:
            if guild:
                member = guild.get_member(
                    int(user_id)
                )
        except Exception:
            pass

        name = (
            member.display_name
            if member
            else f"User {user_id}"
        )

        entries.append(
            f"🚗 `{plate}` — **{name}**"
        )

    if entries:
        entries.sort(
            key=str.lower
        )

        text = "\n".join(
            entries
        )

        if len(text) > 3900:
            text = (
                text[:3850]
                + "\n…"
            )

        result.add_field(
            name=(
                "📋 Eingetragene Kennzeichen "
                f"({len(entries)})"
            ),
            value=text,
            inline=False
        )

    else:
        result.add_field(
            name="📋 Eingetragene Kennzeichen",
            value=(
                "Noch keine Kennzeichen eingetragen."
            ),
            inline=False
        )

    return result


class PlateModal(
    discord.ui.Modal,
    title="Kennzeichen eintragen"
):
    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        max_length=20,
        required=True
    )

    async def on_submit(
        self,
        interaction
    ):
        user_id = str(
            interaction.user.id
        )

        existing = get_user_plate(
            interaction.user.id
        )

        if existing:
            return await error_response(
                interaction,
                f"❌ Du hast bereits `{existing}`."
            )

        plate = normalize_plate(
            self.plate.value
        )

        number = get_plate_number(
            plate
        )

        if number is None:
            return await error_response(
                interaction,
                "❌ Das Kennzeichen muss mit einer Zahl enden."
            )

        if not any(
            char.isalpha()
            for char in plate
        ):
            return await error_response(
                interaction,
                "❌ Bitte gib einen Präfix und eine Nummer an."
            )

        if plate_number_used(
            number
        ):
            return await error_response(
                interaction,
                f"❌ Die Nummer `{number}` ist bereits vergeben."
            )

        data[
            "license_plates"
        ][user_id] = {
            "plate": plate,
            "created_at": current_time()
        }

        save_data(data)

        await interaction.response.send_message(
            f"✅ `{plate}` wurde erfolgreich gespeichert.",
            ephemeral=True
        )

        await refresh_license_panel()


class PlateButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Kennzeichen eintragen",
            emoji="🚗",
            style=discord.ButtonStyle.success,
            custom_id="rlp_plate_add"
        )

    async def callback(
        self,
        interaction
    ):
        await interaction.response.send_modal(
            PlateModal()
        )


class PlateView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            PlateButton()
        )


async def refresh_license_panel():
    await update_panel(
        LICENSE_PLATE_CHANNEL_ID,
        LICENSE_PANEL_MARKER,
        license_panel(),
        PlateView()
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(
    discord.ui.Modal,
    title="Bewerbung"
):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=50
    )

    age = discord.ui.TextInput(
        label="Alter",
        placeholder="z. B. 18",
        max_length=3
    )

    reason = discord.ui.TextInput(
        label="Warum möchtest du dich bewerben?",
        placeholder="Erzähle etwas über dich...",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(
        self,
        interaction
    ):
        channel = get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:
            return await error_response(
                interaction,
                "❌ Bewerbungskanal nicht gefunden."
            )

        result = make_embed(
            "📨 Neue Bewerbung",
            color=discord.Color.orange()
        )

        result.add_field(
            name="👤 Benutzer",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        result.add_field(
            name="📝 Name",
            value=self.name.value,
            inline=True
        )

        result.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=True
        )

        result.add_field(
            name="📋 Bewerbung",
            value=self.reason.value,
            inline=False
        )

        result.add_field(
            name="🕒 Eingegangen",
            value=current_time(),
            inline=False
        )

        try:
            await channel.send(
                embed=result
            )

            data[
                "applications"
            ][str(interaction.user.id)] = {
                "name": self.name.value,
                "age": self.age.value,
                "reason": self.reason.value,
                "created_at": current_time()
            }

            save_data(data)

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde eingereicht.",
                ephemeral=True
            )

        except Exception as error:
            print(
                f"Bewerbungsfehler: {error}"
            )

            await error_response(
                interaction,
                "❌ Bewerbung konnte nicht gesendet werden."
            )


class ApplicationButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_application"
        )

    async def callback(
        self,
        interaction
    ):
        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            ApplicationButton()
        )


def application_panel():
    return make_embed(
        "📨 Bewerbung",
        (
            "Du möchtest Teil des Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus.\n\n"
            "Bitte achte auf vollständige und ehrliche Angaben."
        ),
        discord.Color.orange()
    )


# =========================================================
# DEVELOPER AUFGABEN
# =========================================================

class DeveloperTaskModal(
    discord.ui.Modal,
    title="Developer-Aufgabe"
):
    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not is_shift_manager(
            member
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung."
            )

        channel = get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel is None:
            return await error_response(
                interaction,
                "❌ Developer-Kanal nicht gefunden."
            )

        task_id = str(
            int(time.time() * 1000)
        )

        data[
            "developer_tasks"
        ][task_id] = {
            "author_id": member.id,
            "task": self.task.value,
            "created_at": current_time(),
            "status": "offen"
        }

        save_data(data)

        result = make_embed(
            "🛠️ Neue Developer-Aufgabe",
            color=discord.Color.blue()
        )

        result.add_field(
            name="👤 Erstellt von",
            value=member.mention,
            inline=True
        )

        result.add_field(
            name="🆔 ID",
            value=f"`{task_id}`",
            inline=True
        )

        result.add_field(
            name="📋 Aufgabe",
            value=self.task.value,
            inline=False
        )

        result.add_field(
            name="📊 Status",
            value="🟡 Offen",
            inline=False
        )

        try:
            await channel.send(
                embed=result
            )

            await interaction.response.send_message(
                "✅ Developer-Aufgabe erstellt.",
                ephemeral=True
            )

        except Exception as error:
            print(
                f"Developer-Aufgabe: {error}"
            )

            await error_response(
                interaction,
                "❌ Aufgabe konnte nicht erstellt werden."
            )


class DeveloperTaskButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not is_shift_manager(
            member
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung."
            )

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            DeveloperTaskButton()
        )


def developer_task_panel():
    return make_embed(
        "🛠️ Developer-Aufgaben",
        (
            "Hier können berechtigte Entwickler neue Aufgaben erstellen.\n\n"
            "Klicke auf **Aufgabe erstellen**, "
            "um eine neue Aufgabe anzulegen."
        ),
        discord.Color.blue()
    )


# =========================================================
# DEVELOPER SCHICHT
# =========================================================

def shift_panel():
    result = make_embed(
        "🛠️ Developer-Schicht",
        (
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Startet deine Schicht und gibt dir die aktive Rolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Schicht und entfernt die aktive Rolle."
        ),
        discord.Color.blurple()
    )

    guild = get_guild()

    active = data[
        "active_developer_shifts"
    ]

    if not active:
        result.add_field(
            name="🟢 Aktive Entwickler",
            value=(
                "Aktuell ist niemand in einer Schicht."
            ),
            inline=False
        )

        return result

    lines = []

    for user_id, information in active.items():

        member = None

        try:
            if guild:
                member = guild.get_member(
                    int(user_id)
                )
        except Exception:
            pass

        name = (
            member.display_name
            if member
            else f"User {user_id}"
        )

        started = information.get(
            "started_at",
            "Unbekannt"
        )

        lines.append(
            f"🟢 **{name}**\n"
            f"└ Start: `{started}`"
        )

    result.add_field(
        name=(
            f"🟢 Aktive Entwickler "
            f"({len(lines)})"
        ),
        value="\n\n".join(
            lines
        )[:3900],
        inline=False
    )

    return result


async def shift_log(
    member,
    action,
    color,
    started=None
):
    channel = get_channel(
        SHIFT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    result = make_embed(
        f"🛠️ Developer-Schicht • {action}",
        color=color
    )

    result.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    result.add_field(
        name="👤 Entwickler",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=False
    )

    result.add_field(
        name="📌 Aktion",
        value=action,
        inline=True
    )

    result.add_field(
        name="🕒 Zeitpunkt",
        value=current_time(),
        inline=True
    )

    if started:
        result.add_field(
            name="⏱️ Schicht gestartet",
            value=started,
            inline=False
        )

    try:
        await channel.send(
            embed=result
        )

    except Exception as error:
        print(
            f"Shift-Log: {error}"
        )


class ShiftStart(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_shift_start"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not is_shift_manager(
            member
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung für Developer-Schichten."
            )

        key = str(
            member.id
        )

        if key in data[
            "active_developer_shifts"
        ]:
            return await error_response(
                interaction,
                "❌ Du bist bereits in einer Schicht."
            )

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:
            return await error_response(
                interaction,
                "❌ Schicht-Rolle nicht gefunden."
            )

        started = current_time()

        try:
            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

            data[
                "active_developer_shifts"
            ][key] = {
                "started_at": started
            }

            save_data(data)

            await shift_log(
                member,
                "🟢 Schicht gestartet",
                discord.Color.green(),
                started
            )

            await interaction.response.send_message(
                "🟢 Deine Developer-Schicht wurde gestartet.",
                ephemeral=True
            )

            await refresh_shift_panel()

        except discord.Forbidden:
            await error_response(
                interaction,
                "❌ Die Schicht-Rolle konnte nicht vergeben werden."
            )

        except Exception as error:
            print(
                f"Schichtstart: {error}"
            )

            await error_response(
                interaction,
                "❌ Die Schicht konnte nicht gestartet werden."
            )


class ShiftEnd(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_shift_end"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not is_shift_manager(
            member
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung für Developer-Schichten."
            )

        key = str(
            member.id
        )

        shift = data[
            "active_developer_shifts"
        ].get(key)

        if not shift:
            return await error_response(
                interaction,
                "❌ Du bist aktuell nicht in einer Schicht."
            )

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        try:
            if role and role in member.roles:
                await member.remove_roles(
                    role,
                    reason="Developer-Schicht beendet"
                )

            started = shift.get(
                "started_at",
                "Unbekannt"
            )

            data[
                "active_developer_shifts"
            ].pop(key)

            save_data(data)

            await shift_log(
                member,
                "🔴 Schicht beendet",
                discord.Color.red(),
                started
            )

            await interaction.response.send_message(
                "🔴 Deine Developer-Schicht wurde beendet.",
                ephemeral=True
            )

            await refresh_shift_panel()

        except discord.Forbidden:
            await error_response(
                interaction,
                "❌ Die Schicht-Rolle konnte nicht entfernt werden."
            )

        except Exception as error:
            print(
                f"Schichtende: {error}"
            )

            await error_response(
                interaction,
                "❌ Die Schicht konnte nicht beendet werden."
            )


class ShiftView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            ShiftStart()
        )

        self.add_item(
            ShiftEnd()
        )


async def refresh_shift_panel():
    await update_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        DEV_SHIFT_PANEL_MARKER,
        shift_panel(),
        ShiftView()
    )


# =========================================================
# COMMUNITY
# =========================================================

class SuggestionModal(
    discord.ui.Modal,
    title="Vorschlag"
):
    text = discord.ui.TextInput(
        label="Vorschlag",
        placeholder="Deine Idee...",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):
        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel is None:
            return await error_response(
                interaction,
                "❌ Vorschlagskanal nicht gefunden."
            )

        result = make_embed(
            "💡 Neuer Vorschlag",
            self.text.value,
            discord.Color.gold()
        )

        result.add_field(
            name="👤 Eingereicht von",
            value=interaction.user.mention,
            inline=True
        )

        result.add_field(
            name="📊 Status",
            value="🟡 Offen",
            inline=True
        )

        result.add_field(
            name="🟢 Für",
            value="0",
            inline=True
        )

        result.add_field(
            name="🔴 Gegen",
            value="0",
            inline=True
        )

        message = await channel.send(
            embed=result,
            view=SuggestionView()
        )

        data[
            "suggestions"
        ][str(message.id)] = {
            "author_id": interaction.user.id,
            "text": self.text.value,
            "status": "offen",
            "for_votes": [],
            "against_votes": []
        }

        save_data(data)

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde eingereicht.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="Feedback"
):
    text = discord.ui.TextInput(
        label="Feedback",
        placeholder="Dein Feedback...",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):
        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel is None:
            return await error_response(
                interaction,
                "❌ Feedback-Kanal nicht gefunden."
            )

        result = make_embed(
            "💬 Neues Feedback",
            self.text.value,
            discord.Color.blue()
        )

        result.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(
            embed=result
        )

        data[
            "feedback"
        ].append({
            "author_id": interaction.user.id,
            "text": self.text.value,
            "created_at": current_time()
        })

        save_data(data)

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


class CommunitySuggestion(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(
        self,
        interaction
    ):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class CommunityFeedback(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_community_feedback"
        )

    async def callback(
        self,
        interaction
    ):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class CommunityView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            CommunitySuggestion()
        )

        self.add_item(
            CommunityFeedback()
        )


def community_panel():
    return make_embed(
        "🌐 Community",
        (
            "🚔 **RLP | RP-System**\n"
            "🌐 **Für eine starke & aktive Community**\n"
            "✨ **Professionell • Innovativ • Einzigartig**\n"
            "💻 **Developed by RyZe 🚀**\n\n"
            "Über die Buttons kannst du mit dem Team "
            "in Kontakt treten."
        ),
        discord.Color.blurple()
    )


# =========================================================
# VORSCHLÄGE
# =========================================================

def suggestion_embed(
    message_id
):
    suggestion = data[
        "suggestions"
    ].get(
        str(message_id)
    )

    if not suggestion:
        return make_embed(
            "💡 Vorschlag",
            "Dieser Vorschlag ist nicht mehr verfügbar.",
            discord.Color.red()
        )

    status = suggestion.get(
        "status",
        "offen"
    )

    status_names = {
        "offen": "🟡 Offen",
        "angenommen": "🟢 Angenommen",
        "abgelehnt": "🔴 Abgelehnt"
    }

    result = make_embed(
        "💡 Vorschlag",
        suggestion.get(
            "text",
            ""
        ),
        discord.Color.gold()
    )

    guild = get_guild()

    author = None

    if guild:
        author = guild.get_member(
            suggestion.get(
                "author_id",
                0
            )
        )

    result.add_field(
        name="👤 Eingereicht von",
        value=(
            author.mention
            if author
            else "Unbekannt"
        ),
        inline=True
    )

    result.add_field(
        name="📊 Status",
        value=status_names.get(
            status,
            "🟡 Offen"
        ),
        inline=True
    )

    result.add_field(
        name="🟢 Für",
        value=str(
            len(
                suggestion.get(
                    "for_votes",
                    []
                )
            )
        ),
        inline=True
    )

    result.add_field(
        name="🔴 Gegen",
        value=str(
            len(
                suggestion.get(
                    "against_votes",
                    []
                )
            )
        ),
        inline=True
    )

    return result


async def update_suggestion(
    interaction
):
    message = interaction.message

    if not message:
        return

    try:
        await message.edit(
            embed=suggestion_embed(
                message.id
            ),
            view=SuggestionView()
        )

    except Exception as error:
        print(
            f"Vorschlag Update: {error}"
        )


class SuggestionFor(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Für den Vorschlag",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_for"
        )

    async def callback(
        self,
        interaction
    ):
        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:
            return await error_response(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        uid = interaction.user.id

        if uid in suggestion[
            "for_votes"
        ]:
            suggestion[
                "for_votes"
            ].remove(uid)

            message = (
                "↩️ Deine Stimme wurde entfernt."
            )

        else:
            if uid in suggestion[
                "against_votes"
            ]:
                suggestion[
                    "against_votes"
                ].remove(uid)

            suggestion[
                "for_votes"
            ].append(uid)

            message = (
                "🟢 Deine Stimme wurde geändert."
            )

        save_data(data)

        await update_suggestion(
            interaction
        )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


class SuggestionAgainst(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Gegen den Vorschlag",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_against"
        )

    async def callback(
        self,
        interaction
    ):
        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:
            return await error_response(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        uid = interaction.user.id

        if uid in suggestion[
            "against_votes"
        ]:
            suggestion[
                "against_votes"
            ].remove(uid)

            message = (
                "↩️ Deine Stimme wurde entfernt."
            )

        else:
            if uid in suggestion[
                "for_votes"
            ]:
                suggestion[
                    "for_votes"
                ].remove(uid)

            suggestion[
                "against_votes"
            ].append(uid)

            message = (
                "🔴 Deine Stimme wurde geändert."
            )

        save_data(data)

        await update_suggestion(
            interaction
        )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


class SuggestionAccept(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Annehmen",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_accept"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not member_has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung."
            )

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:
            return await error_response(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        suggestion[
            "status"
        ] = "angenommen"

        save_data(data)

        await update_suggestion(
            interaction
        )

        await interaction.response.send_message(
            "🟢 Vorschlag angenommen.",
            ephemeral=True
        )


class SuggestionReject(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Ablehnen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_reject"
        )

    async def callback(
        self,
        interaction
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            return await error_response(
                interaction,
                "❌ Mitglied nicht gefunden."
            )

        if not member_has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            return await error_response(
                interaction,
                "❌ Du hast keine Berechtigung."
            )

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:
            return await error_response(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        suggestion[
            "status"
        ] = "abgelehnt"

        save_data(data)

        await update_suggestion(
            interaction
        )

        await interaction.response.send_message(
            "🔴 Vorschlag abgelehnt.",
            ephemeral=True
        )


class SuggestionView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            SuggestionFor()
        )

        self.add_item(
            SuggestionAgainst()
        )

        self.add_item(
            SuggestionAccept()
        )

        self.add_item(
            SuggestionReject()
        )


# =========================================================
# EMOJI QUIZ
# =========================================================

EMOJI_QUESTIONS = [
    {
        "emoji": "🍎📱",
        "answer": "apple",
        "aliases": [
            "apple",
            "iphone"
        ],
        "category": "Technik / Marke",
        "hints": [
            "Es geht um eine bekannte Technikmarke.",
            "Die Marke ist besonders für Smartphones und Computer bekannt.",
            "Der Name ist gleichzeitig eine englische Frucht."
        ]
    },
    {
        "emoji": "🕷️🦸",
        "answer": "spiderman",
        "aliases": [
            "spiderman",
            "spider man",
            "spider-man"
        ],
        "category": "Film / Comic",
        "hints": [
            "Es geht um eine bekannte Figur.",
            "Die Figur hat mit einer Spinne zu tun.",
            "Der Name beginnt mit Spider."
        ]
    },
    {
        "emoji": "❄️👸",
        "answer": "eiskoenigin",
        "aliases": [
            "eiskoenigin",
            "eiskönigin",
            "frozen"
        ],
        "category": "Film",
        "hints": [
            "Es geht um einen bekannten Animationsfilm.",
            "Schnee und Eis spielen eine wichtige Rolle.",
            "Der englische Titel lautet Frozen."
        ]
    },
    {
        "emoji": "🌧️☂️",
        "answer": "regen",
        "aliases": [
            "regen"
        ],
        "category": "Wetter",
        "hints": [
            "Es geht um Wetter.",
            "Ein Regenschirm kann dabei sehr hilfreich sein.",
            "Wasser fällt vom Himmel."
        ]
    },
    {
        "emoji": "🌙⭐",
        "answer": "nacht",
        "aliases": [
            "nacht"
        ],
        "category": "Zeit",
        "hints": [
            "Es geht um eine Tageszeit.",
            "Man sieht dabei häufig Sterne.",
            "Sie kommt nach dem Abend."
        ]
    },
    {
        "emoji": "🚒🔥",
        "answer": "feuerwehr",
        "aliases": [
            "feuerwehr"
        ],
        "category": "Einsatzdienst",
        "hints": [
            "Es geht um einen Einsatzdienst.",
            "Die Einheit hilft unter anderem bei Bränden.",
            "Die Fahrzeuge sind häufig rot."
        ]
    },
    {
        "emoji": "⚽🥅",
        "answer": "fussball",
        "aliases": [
            "fussball",
            "fußball"
        ],
        "category": "Sport",
        "hints": [
            "Es geht um eine Sportart.",
            "Ein Ball und ein Tor spielen eine wichtige Rolle.",
            "Die Sportart wird weltweit gespielt."
        ]
    },
    {
        "emoji": "🎄🎁",
        "answer": "weihnachten",
        "aliases": [
            "weihnachten"
        ],
        "category": "Feiertag",
        "hints": [
            "Es geht um einen bekannten Feiertag.",
            "Geschenke spielen dabei häufig eine Rolle.",
            "Der Feiertag ist im Dezember."
        ]
    },
    {
        "emoji": "🍕🇮🇹",
        "answer": "pizza",
        "aliases": [
            "pizza"
        ],
        "category": "Essen",
        "hints": [
            "Es geht um ein bekanntes Gericht.",
            "Das Gericht wird stark mit Italien verbunden.",
            "Es wird meistens in Stücke geschnitten."
        ]
    },
    {
        "emoji": "🐝🍯",
        "answer": "honig",
        "aliases": [
            "honig"
        ],
        "category": "Natur / Essen",
        "hints": [
            "Es geht um ein Naturprodukt.",
            "Bienen haben damit zu tun.",
            "Es ist süß."
        ]
    },
    {
        "emoji": "🚗⛽",
        "answer": "auto",
        "aliases": [
            "auto"
        ],
        "category": "Verkehr",
        "hints": [
            "Es geht um ein Fahrzeug.",
            "Es wird normalerweise auf Straßen benutzt.",
            "Viele Fahrzeuge benötigen Kraftstoff."
        ]
    },
    {
        "emoji": "🐶🏠",
        "answer": "hund",
        "aliases": [
            "hund"
        ],
        "category": "Tier",
        "hints": [
            "Es geht um ein Haustier.",
            "Viele Menschen halten dieses Tier zu Hause.",
            "Es bellt häufig."
        ]
    },
    {
        "emoji": "🐱🐟",
        "answer": "katze",
        "aliases": [
            "katze"
        ],
        "category": "Tier",
        "hints": [
            "Es geht um ein Haustier.",
            "Das Tier miaut.",
            "Es wird häufig mit Fischen in Verbindung gebracht."
        ]
    },
    {
        "emoji": "🌊🏖️☀️",
        "answer": "urlaub",
        "aliases": [
            "urlaub"
        ],
        "category": "Freizeit",
        "hints": [
            "Es geht um freie Zeit.",
            "Viele Menschen fahren dafür ans Meer.",
            "Strand und Sonne passen dazu."
        ]
    },
    {
        "emoji": "🎮🕹️",
        "answer": "gaming",
        "aliases": [
            "gaming",
            "videospiel",
            "videospiele"
        ],
        "category": "Freizeit",
        "hints": [
            "Es geht um eine beliebte Freizeitbeschäftigung.",
            "Controller können dazugehören.",
            "Man spielt dabei digitale Spiele."
        ]
    }
]


def normalize_quiz_answer(
    value
):
    value = str(
        value
    ).lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss"
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new
        )

    value = re.sub(
        r"[^a-z0-9 ]",
        "",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def get_quiz_state(
    user_id
):
    key = str(
        user_id
    )

    if key not in data[
        "emoji_quiz"
    ]:
        data[
            "emoji_quiz"
        ][key] = {
            "active": False,
            "question_index": None,
            "tips_used": 0,
            "letters_used": 0,
            "skips_used": 0,
            "usage_reset_at": (
                time.time()
                + EMOJI_RESET_SECONDS
            ),
            "score": 0,
            "solved": 0,
            "skipped": 0,
            "total": 0,
            "last_action": 0
        }

    state = data[
        "emoji_quiz"
    ][key]

    defaults = {
        "active": False,
        "question_index": None,
        "tips_used": 0,
        "letters_used": 0,
        "skips_used": 0,
        "usage_reset_at": (
            time.time()
            + EMOJI_RESET_SECONDS
        ),
        "score": 0,
        "solved": 0,
        "skipped": 0,
        "total": 0,
        "last_action": 0
    }

    for key2, value in defaults.items():
        if key2 not in state:
            state[key2] = value

    # =====================================================
    # 2-STUNDEN-RESET
    # =====================================================

    if time.time() >= state[
        "usage_reset_at"
    ]:

        state[
            "tips_used"
        ] = 0

        state[
            "letters_used"
        ] = 0

        state[
            "skips_used"
        ] = 0

        state[
            "usage_reset_at"
        ] = (
            time.time()
            + EMOJI_RESET_SECONDS
        )

        save_data(
            data
        )

    return state


def quiz_reset_text(
    state
):
    seconds = max(
        0,
        int(
            state["usage_reset_at"]
            - time.time()
        )
    )

    hours = seconds // 3600
    minutes = (
        seconds % 3600
    ) // 60

    return (
        f"🔄 Alle Nutzungen werden automatisch "
        f"in **{hours} Std. {minutes} Min.** zurückgesetzt."
    )


def quiz_limit_message(
    category,
    used
):
    return (
        f"⛔ **{category}-Limit erreicht**\n\n"
        f"Du hast bereits **{used}/3** Nutzungen "
        f"für **{category}** verwendet.\n\n"
        f"🔒 Weitere Nutzungen dieser Kategorie "
        f"sind momentan nicht verfügbar.\n"
        f"🔄 Das Limit wird automatisch alle **2 Stunden** zurückgesetzt."
    )


def quiz_remaining_text(
    state
):
    return (
        f"💡 Tipps: **{state['tips_used']}/3**\n"
        f"🔤 Anfangsbuchstaben: **{state['letters_used']}/3**\n"
        f"⏭️ Überspringen: **{state['skips_used']}/3**"
    )


def current_quiz_question(
    state
):
    index = state.get(
        "question_index"
    )

    if index is None:
        return None

    if not (
        0 <= index < len(
            EMOJI_QUESTIONS
        )
    ):
        return None

    return EMOJI_QUESTIONS[
        index
    ]


def quiz_embed(
    state
):
    question = current_quiz_question(
        state
    )

    if question is None:
        return make_embed(
            "🎭 Emoji-Quiz",
            (
                "Klicke auf **▶️ Neues Quiz**, "
                "um eine Aufgabe zu starten."
            ),
            discord.Color.blurple()
        )

    return make_embed(
        "🎭 Emoji-Quiz",
        (
            f"## {question['emoji']}\n\n"
            f"🏷️ Kategorie: **{question['category']}**\n\n"
            "✍️ Schreibe deine Antwort einfach in den Chat.\n\n"
            f"{quiz_remaining_text(state)}\n"
            f"{quiz_reset_text(state)}"
        ),
        discord.Color.blurple()
    )


def quiz_pick_question(
    state
):
    old_index = state.get(
        "question_index"
    )

    available = list(
        range(
            len(EMOJI_QUESTIONS)
        )
    )

    if (
        old_index is not None
        and len(available) > 1
    ):
        available.remove(
            old_index
        )

    state[
        "question_index"
    ] = random.choice(
        available
    )

    state[
        "active"
    ] = True


class EmojiQuizNew(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Neues Quiz",
            emoji="▶️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_emoji_new"
        )

    async def callback(
        self,
        interaction
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        # Neues Quiz setzt NICHT die drei Nutzungslimits zurück.
        quiz_pick_question(
            state
        )

        state[
            "total"
        ] += 1

        save_data(
            data
        )

        await interaction.response.send_message(
            embed=quiz_embed(
                state
            ),
            ephemeral=True
        )


class EmojiQuizHint(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Tipp anfordern",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_emoji_hint"
        )

    async def callback(
        self,
        interaction
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if not state["active"]:
            return await error_response(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )

        if state[
            "tips_used"
        ] >= EMOJI_LIMIT:

            return await error_response(
                interaction,
                quiz_limit_message(
                    "💡 Tipp anfordern",
                    state["tips_used"]
                )
                + "\n\n"
                + quiz_reset_text(state)
            )

        question = current_quiz_question(
            state
        )

        number = state[
            "tips_used"
        ]

        state[
            "tips_used"
        ] += 1

        save_data(
            data
        )

        await interaction.response.send_message(
            (
                f"💡 **Tipp {number + 1}/3**\n\n"
                f"{question['hints'][number]}\n\n"
                f"{quiz_remaining_text(state)}\n"
                f"{quiz_reset_text(state)}"
            ),
            ephemeral=True
        )


class EmojiQuizLetters(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Anfangsbuchstaben",
            emoji="🔤",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_emoji_letters"
        )

    async def callback(
        self,
        interaction
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if not state["active"]:
            return await error_response(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )

        if state[
            "letters_used"
        ] >= EMOJI_LIMIT:

            return await error_response(
                interaction,
                quiz_limit_message(
                    "🔤 Anfangsbuchstaben",
                    state["letters_used"]
                )
                + "\n\n"
                + quiz_reset_text(state)
            )

        question = current_quiz_question(
            state
        )

        answer = question[
            "answer"
        ]

        use_number = (
            state["letters_used"]
            + 1
        )

        # Bei jeder Nutzung wird ein weiterer Anfangsbuchstabe
        # des gesuchten Wortes angezeigt.
        shown = answer[
            :use_number
        ]

        state[
            "letters_used"
        ] += 1

        save_data(
            data
        )

        await interaction.response.send_message(
            (
                f"🔤 **Anfangsbuchstaben {use_number}/3**\n\n"
                f"Gesucht beginnt mit: **{shown}...**\n\n"
                f"{quiz_remaining_text(state)}\n"
                f"{quiz_reset_text(state)}"
            ),
            ephemeral=True
        )


class EmojiQuizSkip(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Aufgabe überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_skip"
        )

    async def callback(
        self,
        interaction
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if not state["active"]:
            return await error_response(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )

        if state[
            "skips_used"
        ] >= EMOJI_LIMIT:

            return await error_response(
                interaction,
                quiz_limit_message(
                    "⏭️ Überspringen",
                    state["skips_used"]
                )
                + "\n\n"
                + quiz_reset_text(state)
            )

        old_question = current_quiz_question(
            state
        )

        state[
            "skips_used"
        ] += 1

        state[
            "skipped"
        ] += 1

        quiz_pick_question(
            state
        )

        save_data(
            data
        )

        new_question = current_quiz_question(
            state
        )

        await interaction.response.send_message(
            (
                "⏭️ **Aufgabe übersprungen.**\n\n"
                f"Vorher: {old_question['emoji']}\n"
                f"Neue Aufgabe: **{new_question['emoji']}**\n\n"
                f"{quiz_remaining_text(state)}\n"
                f"{quiz_reset_text(state)}"
            ),
            ephemeral=True
        )


class EmojiQuizLeaderboard(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Bestenliste anzeigen",
            emoji="🏆",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_leaderboard"
        )

    async def callback(
        self,
        interaction
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        result = make_embed(
            "🏆 Deine Emoji-Quiz-Statistik",
            (
                "Diese Statistik ist **nur für dich sichtbar**."
            ),
            discord.Color.gold()
        )

        result.add_field(
            name="⭐ Punkte",
            value=str(
                state["score"]
            ),
            inline=True
        )

        result.add_field(
            name="✅ Gelöst",
            value=str(
                state["solved"]
            ),
            inline=True
        )

        result.add_field(
            name="⏭️ Übersprungen",
            value=str(
                state["skipped"]
            ),
            inline=True
        )

        result.add_field(
            name="📊 Gestartete Aufgaben",
            value=str(
                state["total"]
            ),
            inline=True
        )

        result.add_field(
            name="💡 Tipps",
            value=f"{state['tips_used']}/3",
            inline=True
        )

        result.add_field(
            name="🔤 Buchstaben",
            value=f"{state['letters_used']}/3",
            inline=True
        )

        result.add_field(
            name="⏭️ Überspringen",
            value=f"{state['skips_used']}/3",
            inline=True
        )

        result.add_field(
            name="🔄 Reset",
            value=quiz_reset_text(state),
            inline=False
        )

        await interaction.response.send_message(
            embed=result,
            ephemeral=True
        )


class EmojiQuizView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            EmojiQuizNew()
        )

        self.add_item(
            EmojiQuizHint()
        )

        self.add_item(
            EmojiQuizLetters()
        )

        self.add_item(
            EmojiQuizSkip()
        )

        self.add_item(
            EmojiQuizLeaderboard()
        )


def emoji_quiz_panel():
    return make_embed(
        "🎭 Emoji-Quiz",
        (
            "Errate den Begriff anhand der Emojis.\n\n"
            "▶️ **Neues Quiz** — startet eine neue Aufgabe.\n"
            "💡 **Tipp anfordern** — maximal 3 Nutzungen.\n"
            "🔤 **Anfangsbuchstaben** — maximal 3 Nutzungen.\n"
            "⏭️ **Aufgabe überspringen** — maximal 3 Nutzungen.\n"
            "🏆 **Bestenliste** — deine persönliche Statistik.\n\n"
            "⚠️ Die drei Limits gelten **über mehrere Quiz-Aufgaben hinweg**.\n"
            "🔄 Alle drei Limits werden automatisch **alle 2 Stunden** zurückgesetzt.\n\n"
            "✍️ Deine Antwort schreibst du einfach in den Chat."
        ),
        discord.Color.purple()
    )


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
async def emojiquizpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await update_panel(
        ctx.channel.id,
        EMOJI_QUIZ_PANEL_MARKER,
        emoji_quiz_panel(),
        EmojiQuizView()
    )

    await ctx.send(
        "✅ Emoji-Quiz-Panel aktualisiert.",
        delete_after=5
    )


# =========================================================
# ZAHLENSPIEL
# =========================================================

def number_game_state():
    return data[
        "number_game"
    ]


def number_game_panel():
    state = number_game_state()

    current = int(
        state.get(
            "current_number",
            1
        )
    )

    return make_embed(
        "🔢 RLP Zahlenspiel",
        (
            "## 🔢 Hier die Zahlen von 1 – ∞\n\n"
            f"🎯 **Als Nächstes:** `{current}`\n\n"
            "📌 **Regeln**\n"
            "• Schreibe immer die nächste Zahl.\n"
            "• Die gleiche Person darf nicht zweimal "
            "hintereinander richtig zählen.\n"
            "• Eine falsche Zahl setzt das Spiel wieder auf **1**.\n"
            "• Jede richtige Zahl wird mit ✅ bestätigt.\n"
            "• Falsche Zahlen werden mit ❌ markiert.\n"
            "• Bei 100, 200, 300 usw. gibt es ein Easter Egg. 🎉\n\n"
            "⚠️ Mehrfach falsche Eingaben können automatisch "
            "zu einem Timeout führen."
        ),
        discord.Color.blurple()
    )


class NumberGameView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            NumberGameInfo()
        )


class NumberGameInfo(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Spielregeln",
            emoji="📖",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_number_rules"
        )

    async def callback(
        self,
        interaction
    ):
        await interaction.response.send_message(
            (
                "📖 **Zahlenspiel-Regeln**\n\n"
                "1️⃣ Immer die nächste erwartete Zahl schreiben.\n"
                "2️⃣ Zwei richtige Zahlen hintereinander "
                "vom selben User sind nicht erlaubt.\n"
                "3️⃣ Eine falsche Zahl setzt auf **1** zurück.\n"
                "4️⃣ Bei jeder richtigen Zahl gibt es ✅.\n"
                "5️⃣ Bei jeder falschen Zahl gibt es ❌.\n"
                "6️⃣ Bei 100/200/300/... gibt es ein Easter Egg.\n"
                "7️⃣ Wiederholte Fehlversuche können einen Timeout auslösen."
            ),
            ephemeral=True
        )


async def refresh_number_game_panel():
    await update_panel(
        NUMBER_GAME_CHANNEL_ID,
        NUMBER_GAME_PANEL_MARKER,
        number_game_panel(),
        NumberGameView()
    )


def number_timeout_minutes(
    wrong_count
):
    """
    4 Fehler  -> 5 Minuten
    14 Fehler -> 10 Minuten
    24 Fehler -> 15 Minuten
    34 Fehler -> 20 Minuten
    usw.

    Damit wird nach dem ersten 4er-Block nicht jeder Fehler
    einzeln bestraft, sondern die Strafe steigt blockweise.
    """

    if wrong_count < 4:
        return 0

    if wrong_count == 4:
        return 5

    additional = (
        wrong_count - 4
    ) // 10

    return 5 + (
        additional * 5
    )


def number_easter_egg(
    number
):
    eggs = {
        100: "💯 **100!** Stark! Die erste dreistellige Marke ist erreicht! 🔥",
        200: "🎉 **200!** Ihr seid weiter unterwegs. RLP zählt weiter!",
        300: "🚀 **300!** Das Zahlenspiel nimmt Fahrt auf!",
        400: "🔥 **400!** Schon wieder eine Hunderter-Marke!",
        500: "👑 **500!** Halbtausend geschafft!",
        1000: "🏆 **1000!** VIERSTELLIG! Was für eine Zahl!",
    }

    return eggs.get(
        number,
        f"🎉 **{number}!** Eine weitere Hunderter-Marke wurde erreicht!"
    )


async def handle_number_game(
    message
):
    if message.channel.id != NUMBER_GAME_CHANNEL_ID:
        return False

    # Keine Bot-Nachrichten
    if message.author.bot:
        return True

    content = message.content.strip()

    # Nur reine Ganzzahlen behandeln.
    # Normale Chatnachrichten bleiben normal.
    if not re.fullmatch(
        r"\d+",
        content
    ):
        return False

    try:
        number = int(
            content
        )
    except ValueError:
        return True

    state = number_game_state()

    expected = int(
        state.get(
            "current_number",
            1
        )
    )

    last_user_id = state.get(
        "last_user_id"
    )

    # =====================================================
    # GLEICHER USER ZWEIMAL HINTEREINANDER
    # =====================================================

    if (
        number == expected
        and last_user_id == message.author.id
    ):
        try:
            await message.add_reaction(
                "⚠️"
            )
        except Exception:
            pass

        await message.channel.send(
            (
                f"⚠️ {message.author.mention} "
                "Du darfst nicht zweimal hintereinander "
                "eine richtige Zahl schreiben.\n"
                f"🎯 Weiter geht es mit **{expected}**."
            ),
            delete_after=7
        )

        return True

    # =====================================================
    # RICHTIGE ZAHL
    # =====================================================

    if number == expected:

        try:
            await message.add_reaction(
                "✅"
            )
        except Exception:
            pass

        state[
            "current_number"
        ] = expected + 1

        state[
            "last_user_id"
        ] = message.author.id

        save_data(
            data
        )

        await refresh_number_game_panel()

        # Easter Egg genau bei 100 / 200 / 300 usw.
        if number % 100 == 0:
            egg = number_easter_egg(
                number
            )

            await message.channel.send(
                embed=make_embed(
                    "🎉 EASTER EGG",
                    egg,
                    discord.Color.gold()
                ),
                delete_after=12
            )

        return True

    # =====================================================
    # FALSCHE ZAHL
    # =====================================================

    try:
        await message.add_reaction(
            "❌"
        )
    except Exception:
        pass

    user_key = str(
        message.author.id
    )

    wrong_attempts = state[
        "wrong_attempts"
    ]

    wrong_attempts[
        user_key
    ] = int(
        wrong_attempts.get(
            user_key,
            0
        )
    ) + 1

    count = wrong_attempts[
        user_key
    ]

    # Spiel IMMER auf 1 zurücksetzen
    state[
        "current_number"
    ] = 1

    state[
        "last_user_id"
    ] = None

    save_data(
        data
    )

    timeout_minutes = number_timeout_minutes(
        count
    )

    member = message.author

    if (
        timeout_minutes > 0
        and isinstance(
            member,
            discord.Member
        )
    ):
        try:
            until = (
                discord.utils.utcnow()
                + timedelta(
                    minutes=timeout_minutes
                )
            )

            await member.timeout(
                until,
                reason=(
                    "RLP Zahlenspiel: "
                    f"{count} falsche Eingaben"
                )
            )

            await message.channel.send(
                (
                    f"❌ {member.mention} hat die falsche Zahl "
                    f"geschrieben.\n"
                    f"🔄 Das Zahlenspiel beginnt wieder bei **1**.\n\n"
                    f"⚠️ Fehlversuche: **{count}**\n"
                    f"⏱️ Timeout: **{timeout_minutes} Minuten**"
                ),
                delete_after=10
            )

        except discord.Forbidden:
            await message.channel.send(
                (
                    f"❌ {member.mention} hat die falsche Zahl "
                    f"geschrieben.\n"
                    f"🔄 Das Zahlenspiel beginnt wieder bei **1**.\n\n"
                    f"⚠️ Fehlversuche: **{count}**\n"
                    f"❗ Der Timeout konnte wegen fehlender "
                    f"Bot-Berechtigungen nicht gesetzt werden."
                ),
                delete_after=10
            )

        except Exception as error:
            print(
                f"Zahlenspiel Timeout: {error}"
            )

    else:
        await message.channel.send(
            (
                f"❌ {member.mention} hat die falsche Zahl "
                f"geschrieben.\n"
                f"🔄 Das Zahlenspiel beginnt wieder bei **1**.\n"
                f"⚠️ Fehlversuche dieser Person: **{count}**"
            ),
            delete_after=8
        )

    await refresh_number_game_panel()

    return True


@bot.command(
    name="zahlenspiel",
    aliases=["numbergame"]
)
async def numbergame_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await refresh_number_game_panel()

    await ctx.send(
        f"✅ Zahlenspiel-Panel wurde in "
        f"<#{NUMBER_GAME_CHANNEL_ID}> aktualisiert.",
        delete_after=6
    )


@bot.command(
    name="zahlenspielreset"
)
async def numbergame_reset_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    data[
        "number_game"
    ] = {
        "current_number": 1,
        "last_user_id": None,
        "wrong_attempts": {},
        "message_id": None,
        "last_easter_egg": 0
    }

    save_data(
        data
    )

    await refresh_number_game_panel()

    await ctx.send(
        "🔄 Zahlenspiel wurde vollständig auf **1** zurückgesetzt.",
        delete_after=6
    )


# =========================================================
# OWNER SYSTEM
# =========================================================

async def owner_check(
    interaction
):
    member = interaction.user

    if not isinstance(
        member,
        discord.Member
    ):
        await error_response(
            interaction,
            "❌ Mitglied nicht gefunden."
        )

        return False

    if not is_owner(
        member
    ):
        await error_response(
            interaction,
            "❌ Du hast nicht genügend Berechtigungen. "
            "Diese Funktion ist nur für Owner verfügbar."
        )

        return False

    return True


class OwnerChannelSelect(
    discord.ui.View
):
    def __init__(
        self,
        callback
    ):
        super().__init__(
            timeout=60
        )

        self.callback_function = callback

        self.select = discord.ui.ChannelSelect(
            placeholder="Kanal auswählen...",
            channel_types=[
                discord.ChannelType.text
            ],
            min_values=1,
            max_values=1
        )

        self.select.callback = (
            self.select_channel
        )

        self.add_item(
            self.select
        )

    async def select_channel(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        selected = self.select.values[0]

        channel = (
            interaction.guild.get_channel(
                selected.id
            )
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return await error_response(
                interaction,
                "❌ Bitte einen Textkanal auswählen."
            )

        await self.callback_function(
            interaction,
            channel
        )


class AnnouncementModal(
    discord.ui.Modal,
    title="Ankündigung"
):
    title_input = discord.ui.TextInput(
        label="Titel",
        max_length=256
    )

    message_input = discord.ui.TextInput(
        label="Nachricht",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(
        self,
        channel
    ):
        super().__init__()
        self.channel = channel

    async def on_submit(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        result = make_embed(
            self.title_input.value,
            self.message_input.value,
            discord.Color.blurple()
        )

        result.set_author(
            name=(
                "Ankündigung von "
                f"{interaction.user.display_name}"
            ),
            icon_url=interaction.user.display_avatar.url
        )

        await self.channel.send(
            embed=result
        )

        await interaction.response.send_message(
            f"✅ Ankündigung in {self.channel.mention} gesendet.",
            ephemeral=True
        )


class BotSayModal(
    discord.ui.Modal,
    title="Bot Say"
):
    message = discord.ui.TextInput(
        label="Nachricht",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(
        self,
        channel
    ):
        super().__init__()
        self.channel = channel

    async def on_submit(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await self.channel.send(
            self.message.value
        )

        await interaction.response.send_message(
            f"✅ Nachricht in {self.channel.mention} gesendet.",
            ephemeral=True
        )


async def announcement_channel(
    interaction,
    channel
):
    await interaction.response.send_modal(
        AnnouncementModal(channel)
    )


async def say_channel(
    interaction,
    channel
):
    await interaction.response.send_modal(
        BotSayModal(channel)
    )


async def lock_channel(
    interaction,
    channel
):
    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=False,
            reason=(
                f"Owner Lock durch "
                f"{interaction.user}"
            )
        )

        await interaction.response.send_message(
            f"🔒 {channel.mention} wurde gesperrt.",
            ephemeral=True
        )

    except Exception as error:
        print(error)

        await error_response(
            interaction,
            "❌ Channel konnte nicht gesperrt werden."
        )


async def unlock_channel(
    interaction,
    channel
):
    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            send_messages=None,
            reason=(
                f"Owner Unlock durch "
                f"{interaction.user}"
            )
        )

        await interaction.response.send_message(
            f"🔓 {channel.mention} wurde entsperrt.",
            ephemeral=True
        )

    except Exception as error:
        print(error)

        await error_response(
            interaction,
            "❌ Channel konnte nicht entsperrt werden."
        )


class AnnouncementButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "📢 Wähle den Kanal:",
            view=OwnerChannelSelect(
                announcement_channel
            ),
            ephemeral=True
        )


class SayButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_say"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "💬 Wähle den Kanal:",
            view=OwnerChannelSelect(
                say_channel
            ),
            ephemeral=True
        )


class LockButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Channel Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "🔒 Wähle den Kanal:",
            view=OwnerChannelSelect(
                lock_channel
            ),
            ephemeral=True
        )


class UnlockButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Channel Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "🔓 Wähle den Kanal:",
            view=OwnerChannelSelect(
                unlock_channel
            ),
            ephemeral=True
        )


class StatusButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        uptime = int(
            time.time()
            - BOT_START_TIME
        )

        days, rest = divmod(
            uptime,
            86400
        )

        hours, rest = divmod(
            rest,
            3600
        )

        minutes, seconds = divmod(
            rest,
            60
        )

        result = make_embed(
            "📊 Bot Status",
            color=discord.Color.green()
        )

        result.add_field(
            name="🟢 Status",
            value="Online",
            inline=True
        )

        result.add_field(
            name="🏓 Ping",
            value=(
                f"{round(bot.latency * 1000)} ms"
            ),
            inline=True
        )

        result.add_field(
            name="⏱️ Uptime",
            value=(
                f"{days}T "
                f"{hours}H "
                f"{minutes}M "
                f"{seconds}S"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=result,
            ephemeral=True
        )


class ServerInfoButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_server"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        guild = interaction.guild

        result = make_embed(
            "🖥️ Server Info",
            color=discord.Color.blurple()
        )

        result.add_field(
            name="👥 Mitglieder",
            value=str(
                guild.member_count
            ),
            inline=True
        )

        result.add_field(
            name="💬 Channels",
            value=str(
                len(guild.channels)
            ),
            inline=True
        )

        result.add_field(
            name="🎭 Rollen",
            value=str(
                len(guild.roles)
            ),
            inline=True
        )

        result.add_field(
            name="🆔 Server ID",
            value=str(
                guild.id
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=result,
            ephemeral=True
        )


class UserInfoButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_user"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        member = interaction.user

        result = make_embed(
            "👤 User Info",
            color=discord.Color.blurple()
        )

        result.set_thumbnail(
            url=member.display_avatar.url
        )

        result.add_field(
            name="Name",
            value=member.display_name,
            inline=True
        )

        result.add_field(
            name="ID",
            value=str(
                member.id
            ),
            inline=True
        )

        result.add_field(
            name="Account erstellt",
            value=discord.utils.format_dt(
                member.created_at,
                style="F"
            ),
            inline=False
        )

        result.add_field(
            name="Server beigetreten",
            value=(
                discord.utils.format_dt(
                    member.joined_at,
                    style="F"
                )
                if member.joined_at
                else "Unbekannt"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=result,
            ephemeral=True
        )


class RolesInfoButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Rollen Info",
            emoji="🎭",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_roles"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        roles = [
            role
            for role in interaction.guild.roles
            if role.name != "@everyone"
        ]

        roles.sort(
            key=lambda role: role.position,
            reverse=True
        )

        text = "\n".join(
            f"• {role.mention} — `{role.id}`"
            for role in roles
        )

        if len(text) > 3900:
            text = (
                text[:3850]
                + "\n…"
            )

        result = make_embed(
            "🎭 Rollen",
            text or "Keine Rollen vorhanden.",
            discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=result,
            ephemeral=True
        )


class ClearMessagesModal(
    discord.ui.Modal,
    title="Nachrichten löschen"
):
    amount = discord.ui.TextInput(
        label="Anzahl",
        placeholder="1 - 100",
        max_length=3
    )

    def __init__(
        self,
        channel
    ):
        super().__init__()
        self.channel = channel

    async def on_submit(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        try:
            amount = int(
                self.amount.value
            )

        except ValueError:
            return await error_response(
                interaction,
                "❌ Bitte eine gültige Zahl eingeben."
            )

        if amount < 1 or amount > 100:
            return await error_response(
                interaction,
                "❌ Erlaubt sind 1 bis 100 Nachrichten."
            )

        try:
            deleted = await self.channel.purge(
                limit=amount
            )

            await interaction.response.send_message(
                f"🧹 {len(deleted)} Nachrichten gelöscht.",
                ephemeral=True
            )

        except Exception as error:
            print(error)

            await error_response(
                interaction,
                "❌ Nachrichten konnten nicht gelöscht werden."
            )


async def clear_channel(
    interaction,
    channel
):
    await interaction.response.send_modal(
        ClearMessagesModal(channel)
    )


class ClearButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Nachrichten löschen",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_clear"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "🧹 Wähle den Kanal:",
            view=OwnerChannelSelect(
                clear_channel
            ),
            ephemeral=True
        )


class GiveawayModal(
    discord.ui.Modal,
    title="Giveaway"
):
    prize = discord.ui.TextInput(
        label="Gewinn",
        placeholder="z. B. 10€ Gutschein",
        max_length=200
    )

    duration = discord.ui.TextInput(
        label="Dauer in Minuten",
        placeholder="z. B. 60",
        max_length=6
    )

    winners = discord.ui.TextInput(
        label="Anzahl Gewinner",
        placeholder="z. B. 1",
        max_length=3
    )

    def __init__(
        self,
        channel
    ):
        super().__init__()
        self.channel = channel

    async def on_submit(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        try:
            duration = int(
                self.duration.value
            )

            winner_count = int(
                self.winners.value
            )

        except ValueError:
            return await error_response(
                interaction,
                "❌ Dauer und Gewinner müssen Zahlen sein."
            )

        if (
            duration <= 0
            or winner_count <= 0
        ):
            return await error_response(
                interaction,
                "❌ Werte müssen größer als 0 sein."
            )

        if duration > 10080:
            return await error_response(
                interaction,
                "❌ Maximale Dauer sind 10080 Minuten."
            )

        end_time = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                minutes=duration
            )
        )

        result = make_embed(
            "🎁 GIVEAWAY",
            (
                f"## 🎉 {self.prize.value}\n\n"
                "Reagiere mit 🎉, um teilzunehmen.\n\n"
                f"🏆 Gewinner: **{winner_count}**\n"
                f"⏱️ Ende: "
                f"{discord.utils.format_dt(end_time, style='R')}"
            ),
            discord.Color.gold()
        )

        result.add_field(
            name="👑 Veranstalter",
            value=interaction.user.mention,
            inline=False
        )

        try:
            message = await self.channel.send(
                embed=result
            )

            await message.add_reaction(
                "🎉"
            )

            await interaction.response.send_message(
                f"🎁 Giveaway in {self.channel.mention} gestartet.",
                ephemeral=True
            )

            asyncio.create_task(
                finish_giveaway(
                    message,
                    duration,
                    winner_count,
                    self.prize.value
                )
            )

        except Exception as error:
            print(
                f"Giveaway: {error}"
            )

            await error_response(
                interaction,
                "❌ Giveaway konnte nicht gestartet werden."
            )


async def finish_giveaway(
    message,
    duration,
    winner_count,
    prize
):
    await asyncio.sleep(
        duration * 60
    )

    try:
        message = await message.channel.fetch_message(
            message.id
        )

        reaction = discord.utils.get(
            message.reactions,
            emoji="🎉"
        )

        users = []

        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(
                        user
                    )

        unique = {}

        for user in users:
            unique[
                user.id
            ] = user

        users = list(
            unique.values()
        )

        result = make_embed(
            "🎁 Giveaway beendet",
            f"## 🎉 {prize}",
            discord.Color.gold()
        )

        if not users:
            result.add_field(
                name="🏆 Gewinner",
                value="Es gab keine Teilnehmer.",
                inline=False
            )

            await message.channel.send(
                embed=result
            )

            return

        winners = random.sample(
            users,
            min(
                winner_count,
                len(users)
            )
        )

        mentions = ", ".join(
            user.mention
            for user in winners
        )

        result.add_field(
            name="🏆 Gewinner",
            value=mentions,
            inline=False
        )

        await message.channel.send(
            content=mentions,
            embed=result
        )

    except Exception as error:
        print(
            f"Giveaway Ende: {error}"
        )


class GiveawayStartButton(
    discord.ui.Button
):
    def __init__(self):
        super().__init__(
            label="Giveaway starten",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_giveaway"
        )

    async def callback(
        self,
        interaction
    ):
        if not await owner_check(
            interaction
        ):
            return

        await interaction.response.send_message(
            "🎁 Wähle den Kanal:",
            view=OwnerChannelSelect(
                self.open_modal
            ),
            ephemeral=True
        )

    async def open_modal(
        self,
        interaction,
        channel
    ):
        await interaction.response.send_modal(
            GiveawayModal(channel)
        )


class OwnerView(
    discord.ui.View
):
    def __init__(self):
        super().__init__(
            timeout=None
        )

        self.add_item(
            AnnouncementButton()
        )

        self.add_item(
            SayButton()
        )

        self.add_item(
            LockButton()
        )

        self.add_item(
            UnlockButton()
        )

        self.add_item(
            StatusButton()
        )

        self.add_item(
            ServerInfoButton()
        )

        self.add_item(
            GiveawayStartButton()
        )

        self.add_item(
            ClearButton()
        )

        self.add_item(
            UserInfoButton()
        )

        self.add_item(
            RolesInfoButton()
        )


def owner_panel():
    return make_embed(
        "👑 Owner Panel",
        (
            "Zentrale Verwaltung für den RLP-Server.\n\n"
            "📢 Ankündigungen\n"
            "💬 Bot-Nachrichten\n"
            "🔒 Channel sperren\n"
            "🔓 Channel entsperren\n"
            "📊 Bot-Status\n"
            "🖥️ Server-Informationen\n"
            "🎁 Giveaways\n"
            "🧹 Nachrichten löschen\n"
            "👤 User-Informationen\n"
            "🎭 Rollen-Informationen\n\n"
            "🔐 Die Berechtigung wird bei jedem Button-Klick "
            "über die Owner-Rolle geprüft."
        ),
        discord.Color.dark_gold()
    )


# =========================================================
# PANEL COMMANDS
# =========================================================

@bot.command(
    name="nametagpanel"
)
async def nametagpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await update_panel(
        NAMETAG_CHANNEL_ID,
        NAMETAG_PANEL_MARKER,
        nametag_panel(),
        NametagView()
    )

    await ctx.send(
        "✅ Nametag-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="licensepanel"
)
async def licensepanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await refresh_license_panel()

    await ctx.send(
        "✅ Kennzeichen-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="bewerbungpanel"
)
async def applicationpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await update_panel(
        APPLICATION_CHANNEL_ID,
        APPLICATION_PANEL_MARKER,
        application_panel(),
        ApplicationView()
    )

    await ctx.send(
        "✅ Bewerbungs-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="devtaskpanel"
)
async def devtaskpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await update_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        DEV_TASK_PANEL_MARKER,
        developer_task_panel(),
        DeveloperTaskView()
    )

    await ctx.send(
        "✅ Developer-Aufgaben-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="devshiftpanel"
)
async def devshiftpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    await refresh_shift_panel()

    await ctx.send(
        "✅ Developer-Schicht-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="communitypanel"
)
async def communitypanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    # =====================================================
    # COMMUNITY PANEL ABSICHTLICH IM AKTUELLEN CHANNEL
    # =====================================================

    await update_panel(
        ctx.channel.id,
        COMMUNITY_PANEL_MARKER,
        community_panel(),
        CommunityView()
    )

    await ctx.send(
        "✅ Community-Panel wurde in diesem Channel aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="ownerpanel"
)
async def ownerpanel_command(
    ctx
):
    if not is_owner(
        ctx.author
    ):
        return

    # =====================================================
    # OWNER PANEL ABSICHTLICH IM AKTUELLEN CHANNEL
    # =====================================================

    await update_panel(
        ctx.channel.id,
        OWNER_PANEL_MARKER,
        owner_panel(),
        OwnerView()
    )

    await ctx.send(
        "✅ Owner-Panel erstellt.",
        delete_after=5
    )


@bot.command(
    name="owner"
)
async def owner_command(
    ctx
):
    await ownerpanel_command(
        ctx
    )


# =========================================================
# HELP
# =========================================================

@bot.command(
    name="help"
)
async def help_command(
    ctx
):
    result = make_embed(
        "📚 RLP Bot",
        "Verfügbare Befehle:",
        discord.Color.blurple()
    )

    result.add_field(
        name="🎭 Emoji-Quiz",
        value=(
            "`?emojiquizpanel`"
        ),
        inline=False
    )

    result.add_field(
        name="🔢 Zahlenspiel",
        value=(
            "`?zahlenspiel`\n"
            "`?zahlenspielreset`"
        ),
        inline=False
    )

    if is_owner(
        ctx.author
    ):
        result.add_field(
            name="👑 Owner",
            value=(
                "`?nametagpanel`\n"
                "`?licensepanel`\n"
                "`?bewerbungpanel`\n"
                "`?devtaskpanel`\n"
                "`?devshiftpanel`\n"
                "`?communitypanel`\n"
                "`?ownerpanel`\n"
                "`?owner`"
            ),
            inline=False
        )

    await ctx.send(
        embed=result
    )


# =========================================================
# COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):
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
            f"❌ Es fehlt ein Argument. "
            f"Nutze `{PREFIX}help`."
        )

        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):
        await ctx.send(
            "❌ Dieser Benutzer wurde nicht gefunden."
        )

        return

    if isinstance(
        error,
        commands.RoleNotFound
    ):
        await ctx.send(
            "❌ Diese Rolle wurde nicht gefunden."
        )

        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du hast nicht genügend Berechtigungen."
        )

        return

    if isinstance(
        error,
        commands.CheckFailure
    ):
        return

    print(
        f"COMMAND ERROR | "
        f"{ctx.command} | "
        f"{type(error).__name__}: {error}"
    )


# =========================================================
# ON READY
# =========================================================

@bot.event
async def on_ready():
    global startup_done
    global status_task

    print(
        f"Online als {bot.user} "
        f"(ID: {bot.user.id})"
    )

    if (
        status_task is None
        or status_task.done()
    ):
        status_task = asyncio.create_task(
            rotate_bot_status()
        )

    if startup_done:
        return

    startup_done = True

    print(
        "Registriere Views..."
    )

    try:
        bot.add_view(
            NametagView()
        )

        bot.add_view(
            PlateView()
        )

        bot.add_view(
            ApplicationView()
        )

        bot.add_view(
            DeveloperTaskView()
        )

        bot.add_view(
            ShiftView()
        )

        bot.add_view(
            CommunityView()
        )

        bot.add_view(
            SuggestionView()
        )

        bot.add_view(
            OwnerView()
        )

        bot.add_view(
            EmojiQuizView()
        )

        bot.add_view(
            NumberGameView()
        )

    except Exception as error:
        print(
            f"View-Registrierung: {error}"
        )

    print(
        "Aktualisiere Panels..."
    )

    try:
        # Alte Panels: ihre bisherigen festen Channels
        await update_panel(
            NAMETAG_CHANNEL_ID,
            NAMETAG_PANEL_MARKER,
            nametag_panel(),
            NametagView()
        )

        await refresh_license_panel()

        await update_panel(
            APPLICATION_CHANNEL_ID,
            APPLICATION_PANEL_MARKER,
            application_panel(),
            ApplicationView()
        )

        await update_panel(
            DEVELOPER_TASK_CHANNEL_ID,
            DEV_TASK_PANEL_MARKER,
            developer_task_panel(),
            DeveloperTaskView()
        )

        await refresh_shift_panel()

        # Community: NICHT automatisch in den festen
        # Suggestions-Channel verschieben.
        # Es wird nur über ?communitypanel im aktuellen
        # Channel erstellt/aktualisiert.

        # Owner: ebenfalls nur über ?ownerpanel / ?owner
        # im aktuellen Channel.

        # Neues Zahlenspiel: fester Channel
        await refresh_number_game_panel()

        print(
            "Panels aktualisiert."
        )

    except Exception as error:
        print(
            f"Panel-Update Fehler: {error}"
        )


# =========================================================
# ON MESSAGE
# =========================================================

@bot.event
async def on_message(
    message
):
    if message.author.bot:
        return

    # Zahlenspiel zuerst behandeln.
    # Nur reine Zahlen im Zahlenspiel-Channel werden
    # vom Zahlenspiel verarbeitet.
    if message.channel.id == NUMBER_GAME_CHANNEL_ID:

        handled = await handle_number_game(
            message
        )

        if handled:
            return

    # =====================================================
    # EMOJI QUIZ ANTWORTEN
    # =====================================================

    if message.guild and not message.content.startswith(
        PREFIX
    ):
        state = get_quiz_state(
            message.author.id
        )

        if state.get(
            "active",
            False
        ):
            question = current_quiz_question(
                state
            )

            if question:
                given = normalize_quiz_answer(
                    message.content
                )

                aliases = [
                    normalize_quiz_answer(
                        value
                    )
                    for value in question.get(
                        "aliases",
                        []
                    )
                ]

                correct = (
                    given in aliases
                    or given == normalize_quiz_answer(
                        question["answer"]
                    )
                )

                if correct:
                    state[
                        "active"
                    ] = False

                    state[
                        "score"
                    ] += 1

                    state[
                        "solved"
                    ] += 1

                    save_data(
                        data
                    )

                    await message.channel.send(
                        embed=make_embed(
                            "✅ Richtig!",
                            (
                                f"{message.author.mention} hat "
                                f"**{question['answer']}** richtig erraten! 🎉\n\n"
                                f"⭐ Punkt: **+1**\n"
                                f"🏆 Gesamtpunkte: **{state['score']}**\n\n"
                                "Starte über das Panel eine neue Aufgabe."
                            ),
                            discord.Color.green()
                        ),
                        delete_after=10
                    )

                    return

    await bot.process_commands(
        message
    )


# =========================================================
# START
# =========================================================

def start_bot():
    if not TOKEN:
        print(
            "❌ DISCORD_TOKEN wurde nicht gefunden."
        )

        return

    print(
        "🚔 RLP Bot wird gestartet..."
    )

    while True:
        try:
            bot.run(
                TOKEN,
                reconnect=True
            )

            print(
                "⚠️ Bot wurde beendet."
            )

            break

        except KeyboardInterrupt:
            print(
                "🛑 Bot manuell beendet."
            )

            break

        except Exception as error:
            print(
                f"❌ Bot-Fehler: {error}"
            )

            print(
                "🔄 Neustart in 5 Sekunden..."
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    start_bot()
