import os
import re
import json
import time
import random
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands


# ============================================================
# KONFIGURATION
# ============================================================

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


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

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
    "applications": {},
    "developer_tasks": {},
    "active_developer_shifts": {},
    "suggestions": {},
    "feedback": [],
    "emoji_quiz": {},
    "number_game": {
        "current_number": 1,
        "last_user_id": None,
        "wrong_attempts": {},
        "last_easter_egg": 0,
        "last_message_id": None
    }
}


def load_data():

    if not os.path.exists(DATA_FILE):
        return json.loads(
            json.dumps(DEFAULT_DATA)
        )

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

    except (
        json.JSONDecodeError,
        OSError
    ):

        loaded = {}

    data = json.loads(
        json.dumps(DEFAULT_DATA)
    )

    if isinstance(
        loaded,
        dict
    ):

        for key, value in loaded.items():

            if key in data:
                data[key] = value

    if not isinstance(
        data.get("license_plates"),
        dict
    ):
        data["license_plates"] = {}

    if not isinstance(
        data.get("applications"),
        dict
    ):
        data["applications"] = {}

    if not isinstance(
        data.get("developer_tasks"),
        dict
    ):
        data["developer_tasks"] = {}

    if not isinstance(
        data.get("active_developer_shifts"),
        dict
    ):
        data["active_developer_shifts"] = {}

    if not isinstance(
        data.get("suggestions"),
        dict
    ):
        data["suggestions"] = {}

    if not isinstance(
        data.get("feedback"),
        list
    ):
        data["feedback"] = []

    if not isinstance(
        data.get("emoji_quiz"),
        dict
    ):
        data["emoji_quiz"] = {}

    if not isinstance(
        data.get("number_game"),
        dict
    ):
        data["number_game"] = json.loads(
            json.dumps(
                DEFAULT_DATA["number_game"]
            )
        )

    number_game = data[
        "number_game"
    ]

    if not isinstance(
        number_game.get(
            "current_number"
        ),
        int
    ):
        number_game[
            "current_number"
        ] = 1

    if not isinstance(
        number_game.get(
            "wrong_attempts"
        ),
        dict
    ):
        number_game[
            "wrong_attempts"
        ] = {}

    if "last_user_id" not in number_game:
        number_game[
            "last_user_id"
        ] = None

    if "last_easter_egg" not in number_game:
        number_game[
            "last_easter_egg"
        ] = 0

    if "last_message_id" not in number_game:
        number_game[
            "last_message_id"
        ] = None

    return data


data = load_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

    except OSError as e:

        print(
            f"[DATA] Fehler beim Speichern: {e}"
        )


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def get_guild():

    return bot.get_guild(
        GUILD_ID
    )


def get_member_name(
    user_id
):

    guild = get_guild()

    if guild:

        member = guild.get_member(
            int(user_id)
        )

        if member:
            return member.display_name

    return f"User {user_id}"


def owner_check(
    member
):

    return (
        member.guild_permissions.administrator
        or any(
            role.id == OWNER_ROLE_ID
            for role in member.roles
        )
    )


async def delete_after_seconds(
    message,
    seconds=5
):

    try:

        await asyncio.sleep(
            seconds
        )

        await message.delete()

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):

        pass


async def find_panel(
    channel,
    marker
):

    if channel is None:
        return None

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            for embed in message.embeds:

                footer = (
                    embed.footer.text
                    or ""
                )

                if marker in footer:

                    return message

    except discord.HTTPException:
        pass

    return None


async def update_or_create_panel(
    channel,
    marker,
    embed,
    view=None
):

    if channel is None:
        return None

    existing = await find_panel(
        channel,
        marker
    )

    if existing:

        try:

            await existing.edit(
                embed=embed,
                view=view
            )

            return existing

        except discord.HTTPException:
            pass

    try:

        return await channel.send(
            embed=embed,
            view=view
        )

    except discord.HTTPException:

        return None


# ============================================================
# NAMETAG SYSTEM
# ============================================================

async def remove_nametag(
    member
):

    if (
        member.nick
        and member.nick.startswith(
            NAMETAG
        )
    ):

        new_nick = member.nick[
            len(NAMETAG):
        ].strip()

        try:

            await member.edit(
                nick=new_nick or None,
                reason="RLP Nametag entfernt"
            )

        except discord.HTTPException:
            pass


class NametagSet(
    discord.ui.Modal,
    title="Nametag setzen"
):

    name = discord.ui.TextInput(
        label="Dein Name",
        placeholder="z. B. Max",
        max_length=32
    )

    async def on_submit(
        self,
        interaction
    ):

        new_name = self.name.value.strip()

        if not new_name:

            await interaction.response.send_message(
                "❌ Bitte gib einen Namen ein.",
                ephemeral=True
            )

            return

        if new_name.startswith(
            NAMETAG
        ):

            new_name = new_name[
                len(NAMETAG):
            ].strip()

        final_name = (
            NAMETAG
            + new_name
        )

        try:

            await interaction.user.edit(
                nick=final_name,
                reason="RLP Nametag gesetzt"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf "
                f"`{final_name}` gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


class NametagSetButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Nametag setzen",
            emoji="✏️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_nametag_set"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            NametagSet()
        )


class NametagRemoveButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Nametag entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_remove"
        )

    async def callback(
        self,
        interaction
    ):

        await remove_nametag(
            interaction.user
        )

        await interaction.response.send_message(
            "✅ Dein Nametag wurde entfernt.",
            ephemeral=True
        )


class NametagViewButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Nametag anzeigen",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_nametag_view"
        )

    async def callback(
        self,
        interaction
    ):

        name = (
            interaction.user.nick
            or interaction.user.display_name
        )

        await interaction.response.send_message(
            f"👤 Dein aktueller Name: `{name}`",
            ephemeral=True
        )


class NametagPanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            NametagSetButton()
        )

        self.add_item(
            NametagRemoveButton()
        )

        self.add_item(
            NametagViewButton()
        )


def nametag_embed():

    embed = discord.Embed(
        title="🏷️ RLP Nametag-System",
        description=(
            "Hier kannst du deinen persönlichen "
            "RLP-Nametag verwalten.\n\n"
            "✏️ **Nametag setzen**\n"
            "🗑️ **Nametag entfernen**\n"
            "👤 **Nametag anzeigen**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=NAMETAG_PANEL_MARKER
    )

    return embed


@bot.command(
    name="nametagpanel"
)
@commands.has_permissions(
    administrator=True
)
async def nametag_panel(
    ctx
):

    channel = bot.get_channel(
        NAMETAG_CHANNEL_ID
    )

    await update_or_create_panel(
        channel,
        NAMETAG_PANEL_MARKER,
        nametag_embed(),
        NametagPanelView()
    )

    await ctx.send(
        "✅ Nametag-Panel aktualisiert."
    )


# ============================================================
# KENNZEICHEN-SYSTEM
# ============================================================

def normalize_plate_number(
    value
):

    value = str(
        value
    ).strip()

    if not value.isdigit():
        return None

    number = int(value)

    if number < 1:
        return None

    return number


def normalize_plate_text(
    value
):

    value = str(
        value
    ).strip().upper()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def parse_plate(
    value
):

    value = normalize_plate_text(
        value
    )

    # Erlaubt z. B.:
    # RY ZE 01
    # RY-ZE-01
    # RY ZE 001
    # RYZ E01 wird NICHT automatisch erraten.

    match = re.fullmatch(
        r"([A-ZÄÖÜ]{1,4})\s+([A-ZÄÖÜ]{1,4})\s+(\d+)",
        value
    )

    if not match:
        return None

    district = match.group(1)
    letters = match.group(2)
    number_text = match.group(3)

    number = normalize_plate_number(
        number_text
    )

    if number is None:
        return None

    return {
        "district": district,
        "letters": letters,
        "number": number,
        "plate": (
            f"{district} "
            f"{letters} "
            f"{number:02d}"
        )
    }


def plate_number_is_taken(
    plate,
    ignore_user_id=None
):

    if not plate:
        return True

    number = normalize_plate_number(
        plate["number"]
    )

    for user_id, stored in data[
        "license_plates"
    ].items():

        if (
            ignore_user_id is not None
            and str(user_id)
            == str(ignore_user_id)
        ):
            continue

        if not isinstance(
            stored,
            dict
        ):
            continue

        stored_number = normalize_plate_number(
            stored.get(
                "number"
            )
        )

        if stored_number == number:
            return True

    return False


def get_all_plates():

    result = []

    for user_id, stored in data[
        "license_plates"
    ].items():

        if not isinstance(
            stored,
            dict
        ):
            continue

        plate = stored.get(
            "plate"
        )

        number = normalize_plate_number(
            stored.get(
                "number"
            )
        )

        if (
            plate
            and number is not None
        ):

            result.append(
                (
                    number,
                    plate,
                    user_id,
                    stored.get(
                        "username",
                        get_member_name(
                            user_id
                        )
                    )
                )
            )

    result.sort(
        key=lambda item: item[0]
    )

    return result


def get_all_plates_text():

    plates = get_all_plates()

    if not plates:

        return (
            "🚘 **Noch keine Kennzeichen vergeben.**"
        )

    lines = []

    for (
        number,
        plate,
        user_id,
        username
    ) in plates:

        lines.append(
            f"🚘 `{plate}` — "
            f"**{username}** "
            f"(<@{user_id}>)"
        )

    text = "\n".join(
        lines
    )

    if len(text) > 3900:

        text = (
            text[:3850]
            + "\n\n… weitere Kennzeichen vorhanden."
        )

    return text


class PlateModal(
    discord.ui.Modal,
    title="Kennzeichen beantragen"
):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RY ZE 01",
        min_length=5,
        max_length=20
    )

    async def on_submit(
        self,
        interaction
    ):

        parsed = parse_plate(
            self.plate.value
        )

        if parsed is None:

            await interaction.response.send_message(
                "❌ Ungültiges Kennzeichen.\n"
                "Nutze zum Beispiel: `RY ZE 01`",
                ephemeral=True
            )

            return

        if plate_number_is_taken(
            parsed
        ):

            await interaction.response.send_message(
                f"❌ Die Nummer "
                f"`{parsed['number']}` ist bereits vergeben.\n\n"
                f"Beispiel: `RY ZE 01` und "
                f"`RLP XX 001` können nicht dieselbe "
                f"Nummer verwenden.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        data[
            "license_plates"
        ][user_id] = {
            "district": parsed[
                "district"
            ],
            "letters": parsed[
                "letters"
            ],
            "number": parsed[
                "number"
            ],
            "plate": parsed[
                "plate"
            ],
            "user_id": interaction.user.id,
            "username": interaction.user.display_name,
            "created_at": int(
                time.time()
            )
        }

        save_data()

        # Panel SOFORT aktualisieren
        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen "
            f"`{parsed['plate']}` wurde erfolgreich "
            f"eingetragen.\n\n"
            f"Es ist jetzt im Kennzeichen-Panel "
            f"für alle sichtbar.",
            ephemeral=True
        )


class PlateRequestButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Kennzeichen beantragen",
            emoji="🚘",
            style=discord.ButtonStyle.success,
            custom_id="rlp_plate_request"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            PlateModal()
        )


class PlateRemoveButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Kennzeichen entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_plate_remove"
        )

    async def callback(
        self,
        interaction
    ):

        user_id = str(
            interaction.user.id
        )

        old = data[
            "license_plates"
        ].get(
            user_id
        )

        if not old:

            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )

            return

        old_plate = old.get(
            "plate",
            "unbekannt"
        )

        del data[
            "license_plates"
        ][user_id]

        save_data()

        # Panel SOFORT aktualisieren
        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen "
            f"`{old_plate}` wurde entfernt.",
            ephemeral=True
        )


class PlateView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            PlateRequestButton()
        )

        self.add_item(
            PlateRemoveButton()
        )


def license_embed():

    plates = get_all_plates()

    embed = discord.Embed(
        title="🚘 RLP Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen beantragen.\n\n"
            "📌 **Beispiel:** `RY ZE 01`\n\n"
            "⚠️ Die **Nummer** darf nur einmal "
            "vergeben werden.\n"
            "Dabei sind führende Nullen egal:\n"
            "`RY ZE 01` und `ABC XY 001` "
            "haben beide die Nummer **1**.\n\n"
            "👇 Nutze die Buttons unten."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name=(
            f"🚘 Alle vergebenen Kennzeichen "
            f"({len(plates)})"
        ),
        value=get_all_plates_text(),
        inline=False
    )

    embed.set_footer(
        text=LICENSE_PANEL_MARKER
    )

    return embed


async def refresh_license_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:

        print(
            "[LICENSE] Kanal nicht gefunden."
        )

        return

    await update_or_create_panel(
        channel,
        LICENSE_PANEL_MARKER,
        license_embed(),
        PlateView()
    )


@bot.command(
    name="licensepanel"
)
@commands.has_permissions(
    administrator=True
)
async def license_panel(
    ctx
):

    await refresh_license_panel()

    await ctx.send(
        "✅ Kennzeichen-Panel aktualisiert."
    )


# ============================================================
# BEWERBUNGEN
# ============================================================

class ApplicationModal(
    discord.ui.Modal,
    title="Bewerbung"
):

    name = discord.ui.TextInput(
        label="Name",
        max_length=50
    )

    age = discord.ui.TextInput(
        label="Alter",
        max_length=3
    )

    experience = discord.ui.TextInput(
        label="RP-Erfahrung",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    motivation = discord.ui.TextInput(
        label="Warum möchtest du beitreten?",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(
        self,
        interaction
    ):

        channel = bot.get_channel(
            REVIEW_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="Name",
            value=self.name.value,
            inline=True
        )

        embed.add_field(
            name="Alter",
            value=self.age.value,
            inline=True
        )

        embed.add_field(
            name="RP-Erfahrung",
            value=self.experience.value,
            inline=False
        )

        embed.add_field(
            name="Motivation",
            value=self.motivation.value,
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Bewerbung wurde eingereicht.",
            ephemeral=True
        )


class ApplicationButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.success,
            custom_id="rlp_application_button"
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


def application_embed():

    embed = discord.Embed(
        title="📨 RLP Bewerbung",
        description=(
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle "
            "die Bewerbung aus."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text=APPLICATION_PANEL_MARKER
    )

    return embed


async def refresh_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel:

        await update_or_create_panel(
            channel,
            APPLICATION_PANEL_MARKER,
            application_embed(),
            ApplicationView()
        )


@bot.command(
    name="bewerbungpanel"
)
@commands.has_permissions(
    administrator=True
)
async def application_panel(
    ctx
):

    await refresh_application_panel()

    await ctx.send(
        "✅ Bewerbungs-Panel aktualisiert."
    )


# ============================================================
# DEVELOPER TASKS
# ============================================================

class DeveloperTaskModal(
    discord.ui.Modal,
    title="Developer-Aufgabe"
):

    task = discord.ui.TextInput(
        label="Aufgabe",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        task_id = str(
            int(time.time() * 1000)
        )

        data[
            "developer_tasks"
        ][task_id] = {
            "task": self.task.value,
            "author_id": interaction.user.id,
            "created_at": int(
                time.time()
            ),
            "completed": False
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💻 Neue Developer-Aufgabe",
                description=self.task.value,
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Developer-Aufgabe erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Aufgabe erstellen",
            emoji="💻",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_button"
        )

    async def callback(
        self,
        interaction
    ):

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


def developer_task_embed():

    embed = discord.Embed(
        title="💻 Developer-System",
        description=(
            "Hier können neue Developer-Aufgaben "
            "erstellt werden."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    return embed


async def refresh_developer_task_panel():

    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel:

        await update_or_create_panel(
            channel,
            DEV_TASK_PANEL_MARKER,
            developer_task_embed(),
            DeveloperTaskView()
        )


@bot.command(
    name="devtaskpanel"
)
@commands.has_permissions(
    administrator=True
)
async def developer_task_panel(
    ctx
):

    await refresh_developer_task_panel()

    await ctx.send(
        "✅ Developer-Task-Panel aktualisiert."
    )


# ============================================================
# DEVELOPER SCHICHT
# ============================================================

def has_shift_permission(
    member
):

    return (
        member.guild_permissions.administrator
        or any(
            role.id == SHIFT_PERMISSION_ROLE_ID
            for role in member.roles
        )
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

        if not has_shift_permission(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        if user_id in data[
            "active_developer_shifts"
        ]:

            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )

            return

        data[
            "active_developer_shifts"
        ][user_id] = {
            "started": time.time()
        }

        save_data()

        await shift_log(
            interaction.user,
            "🟢 Schicht gestartet"
        )

        await interaction.response.send_message(
            "🟢 Schicht gestartet.",
            ephemeral=True
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

        if not has_shift_permission(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        shift = data[
            "active_developer_shifts"
        ].get(
            user_id
        )

        if not shift:

            await interaction.response.send_message(
                "⚠️ Du hast keine aktive Schicht.",
                ephemeral=True
            )

            return

        duration = int(
            time.time()
            - shift["started"]
        )

        del data[
            "active_developer_shifts"
        ][user_id]

        save_data()

        minutes = duration // 60
        seconds = duration % 60

        await shift_log(
            interaction.user,
            f"🔴 Schicht beendet — "
            f"{minutes}m {seconds}s"
        )

        await interaction.response.send_message(
            f"🔴 Schicht beendet.\n"
            f"⏱️ Dauer: `{minutes}m {seconds}s`",
            ephemeral=True
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


async def shift_log(
    member,
    text
):

    channel = bot.get_channel(
        SHIFT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Developer-Schicht",
        description=text,
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )

    embed.add_field(
        name="Developer",
        value=member.mention
    )

    await channel.send(
        embed=embed
    )


def shift_embed():

    active = data[
        "active_developer_shifts"
    ]

    lines = []

    for user_id, shift in active.items():

        duration = int(
            time.time()
            - shift["started"]
        )

        minutes = duration // 60
        seconds = duration % 60

        lines.append(
            f"🟢 **{get_member_name(user_id)}** "
            f"— `{minutes}m {seconds}s`"
        )

    active_text = (
        "\n".join(lines)
        if lines
        else
        "Aktuell ist niemand im Developer-Dienst."
    )

    embed = discord.Embed(
        title="🛠️ Developer-Schichtsystem",
        description=active_text,
        color=discord.Color.green()
    )

    embed.set_footer(
        text=DEV_SHIFT_PANEL_MARKER
    )

    return embed


async def refresh_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel:

        await update_or_create_panel(
            channel,
            DEV_SHIFT_PANEL_MARKER,
            shift_embed(),
            ShiftView()
        )


@bot.command(
    name="devshiftpanel"
)
@commands.has_permissions(
    administrator=True
)
async def developer_shift_panel(
    ctx
):

    await refresh_shift_panel()

    await ctx.send(
        "✅ Developer-Schicht-Panel aktualisiert."
    )


# ============================================================
# COMMUNITY
# ============================================================

class SuggestionModal(
    discord.ui.Modal,
    title="Vorschlag einreichen"
):

    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        suggestion_id = str(
            int(time.time() * 1000)
        )

        data[
            "suggestions"
        ][suggestion_id] = {
            "author_id": interaction.user.id,
            "text": self.suggestion.value,
            "for": [],
            "against": [],
            "accepted": False,
            "rejected": False,
            "created_at": int(
                time.time()
            )
        }

        save_data()

        channel = bot.get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:

            await channel.send(
                embed=suggestion_embed(
                    suggestion_id
                ),
                view=SuggestionView(
                    suggestion_id
                )
            )

        await interaction.response.send_message(
            "✅ Vorschlag eingereicht.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="Feedback geben"
):

    feedback = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction
    ):

        data[
            "feedback"
        ].append({
            "user_id": interaction.user.id,
            "text": self.feedback.value,
            "created_at": int(
                time.time()
            )
        })

        save_data()

        channel = bot.get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💬 Neues Feedback",
                description=self.feedback.value,
                color=discord.Color.gold()
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Vielen Dank für dein Feedback!",
            ephemeral=True
        )


class CommunitySuggestionButton(
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


class CommunityFeedbackButton(
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
            CommunitySuggestionButton()
        )

        self.add_item(
            CommunityFeedbackButton()
        )


def community_embed():

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "💡 **Vorschlag**\n"
            "Reiche einen neuen Vorschlag ein.\n\n"
            "💬 **Feedback**\n"
            "Sende uns dein Feedback."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=COMMUNITY_PANEL_MARKER
    )

    return embed


@bot.command(
    name="communitypanel"
)
async def community_panel(
    ctx
):

    await update_or_create_panel(
        ctx.channel,
        COMMUNITY_PANEL_MARKER,
        community_embed(),
        CommunityView()
    )

    await ctx.send(
        "✅ Community-Panel aktualisiert."
    )


def suggestion_embed(
    suggestion_id
):

    suggestion = data[
        "suggestions"
    ].get(
        suggestion_id
    )

    if not suggestion:

        return discord.Embed(
            title="❌ Vorschlag nicht gefunden."
        )

    if suggestion.get(
        "accepted"
    ):

        status = "🟢 Angenommen"

    elif suggestion.get(
        "rejected"
    ):

        status = "🔴 Abgelehnt"

    else:

        status = "🟡 Offen"

    embed = discord.Embed(
        title="💡 Community-Vorschlag",
        description=suggestion["text"],
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👤 Autor",
        value=f"<@{suggestion['author_id']}>"
    )

    embed.add_field(
        name="📊 Status",
        value=status
    )

    embed.add_field(
        name="👍 Dafür",
        value=str(
            len(
                suggestion.get(
                    "for",
                    []
                )
            )
        )
    )

    embed.add_field(
        name="👎 Dagegen",
        value=str(
            len(
                suggestion.get(
                    "against",
                    []
                )
            )
        )
    )

    return embed


class SuggestionFor(
    discord.ui.Button
):

    def __init__(
        self,
        suggestion_id
    ):

        super().__init__(
            label="Dafür",
            emoji="👍",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_for_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(
        self,
        interaction
    ):

        suggestion = data[
            "suggestions"
        ].get(
            self.suggestion_id
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )

            return

        user_id = interaction.user.id

        if user_id in suggestion[
            "against"
        ]:

            suggestion[
                "against"
            ].remove(
                user_id
            )

        if user_id not in suggestion[
            "for"
        ]:

            suggestion[
                "for"
            ].append(
                user_id
            )

        save_data()

        await interaction.message.edit(
            embed=suggestion_embed(
                self.suggestion_id
            ),
            view=SuggestionView(
                self.suggestion_id
            )
        )

        await interaction.response.send_message(
            "👍 Stimme gespeichert.",
            ephemeral=True
        )


class SuggestionAgainst(
    discord.ui.Button
):

    def __init__(
        self,
        suggestion_id
    ):

        super().__init__(
            label="Dagegen",
            emoji="👎",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_against_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(
        self,
        interaction
    ):

        suggestion = data[
            "suggestions"
        ].get(
            self.suggestion_id
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )

            return

        user_id = interaction.user.id

        if user_id in suggestion[
            "for"
        ]:

            suggestion[
                "for"
            ].remove(
                user_id
            )

        if user_id not in suggestion[
            "against"
        ]:

            suggestion[
                "against"
            ].append(
                user_id
            )

        save_data()

        await interaction.message.edit(
            embed=suggestion_embed(
                self.suggestion_id
            ),
            view=SuggestionView(
                self.suggestion_id
            )
        )

        await interaction.response.send_message(
            "👎 Stimme gespeichert.",
            ephemeral=True
        )


class SuggestionAccept(
    discord.ui.Button
):

    def __init__(
        self,
        suggestion_id
    ):

        super().__init__(
            label="Annehmen",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_accept_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(
        self,
        interaction
    ):

        if not (
            interaction.user.guild_permissions.administrator
            or any(
                role.id == SUGGESTION_REVIEW_ROLE_ID
                for role in interaction.user.roles
            )
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        suggestion = data[
            "suggestions"
        ].get(
            self.suggestion_id
        )

        if not suggestion:
            return

        suggestion[
            "accepted"
        ] = True

        suggestion[
            "rejected"
        ] = False

        save_data()

        await interaction.message.edit(
            embed=suggestion_embed(
                self.suggestion_id
            ),
            view=SuggestionView(
                self.suggestion_id
            )
        )

        await interaction.response.send_message(
            "✅ Vorschlag angenommen.",
            ephemeral=True
        )


class SuggestionReject(
    discord.ui.Button
):

    def __init__(
        self,
        suggestion_id
    ):

        super().__init__(
            label="Ablehnen",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_reject_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(
        self,
        interaction
    ):

        if not (
            interaction.user.guild_permissions.administrator
            or any(
                role.id == SUGGESTION_REVIEW_ROLE_ID
                for role in interaction.user.roles
            )
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        suggestion = data[
            "suggestions"
        ].get(
            self.suggestion_id
        )

        if not suggestion:
            return

        suggestion[
            "rejected"
        ] = True

        suggestion[
            "accepted"
        ] = False

        save_data()

        await interaction.message.edit(
            embed=suggestion_embed(
                self.suggestion_id
            ),
            view=SuggestionView(
                self.suggestion_id
            )
        )

        await interaction.response.send_message(
            "❌ Vorschlag abgelehnt.",
            ephemeral=True
        )


class SuggestionView(
    discord.ui.View
):

    def __init__(
        self,
        suggestion_id
    ):

        super().__init__(
            timeout=None
        )

        self.add_item(
            SuggestionFor(
                suggestion_id
            )
        )

        self.add_item(
            SuggestionAgainst(
                suggestion_id
            )
        )

        self.add_item(
            SuggestionAccept(
                suggestion_id
            )
        )

        self.add_item(
            SuggestionReject(
                suggestion_id
            )
        )


# ============================================================
# EMOJI QUIZ
# ============================================================

EMOJI_QUESTIONS = [
    {
        "emojis": "🍕",
        "answer": "pizza",
        "hint": "Ein beliebtes italienisches Essen."
    },
    {
        "emojis": "🐶",
        "answer": "hund",
        "hint": "Ein beliebtes Haustier."
    },
    {
        "emojis": "🐱",
        "answer": "katze",
        "hint": "Ein beliebtes Haustier."
    },
    {
        "emojis": "🌈",
        "answer": "regenbogen",
        "hint": "Sieht man oft nach Regen und Sonne."
    },
    {
        "emojis": "⚽",
        "answer": "fußball",
        "hint": "Ein beliebter Mannschaftssport."
    },
    {
        "emojis": "🚗",
        "answer": "auto",
        "hint": "Damit kann man fahren."
    },
    {
        "emojis": "🍎",
        "answer": "apfel",
        "hint": "Eine Frucht."
    },
    {
        "emojis": "☀️",
        "answer": "sonne",
        "hint": "Sie scheint am Himmel."
    },
    {
        "emojis": "🌙",
        "answer": "mond",
        "hint": "Man sieht ihn nachts."
    },
    {
        "emojis": "🚔",
        "answer": "polizei",
        "hint": "Sie sorgt für Sicherheit."
    }
]


def ensure_emoji_user(
    user_id
):

    user_id = str(
        user_id
    )

    now = time.time()

    state = data[
        "emoji_quiz"
    ].get(
        user_id
    )

    if not isinstance(
        state,
        dict
    ):

        state = {
            "active": False,
            "question": None,
            "question_index": None,
            "answer": "",
            "hints": [],
            "tips_used": 0,
            "letters_used": 0,
            "skips_used": 0,
            "usage_reset_at": now + 7200,
            "score": 0,
            "solved": 0,
            "skipped": 0,
            "total": 0,
            "last_action": 0,
            "quiz_channel_id": None
        }

        data[
            "emoji_quiz"
        ][user_id] = state

    if now >= state.get(
        "usage_reset_at",
        0
    ):

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
        ] = now + 7200

    return state


def emoji_new_question(
    state
):

    index = random.randrange(
        len(EMOJI_QUESTIONS)
    )

    question = EMOJI_QUESTIONS[
        index
    ]

    state[
        "active"
    ] = True

    state[
        "question"
    ] = question[
        "emojis"
    ]

    state[
        "question_index"
    ] = index

    state[
        "answer"
    ] = question[
        "answer"
    ]

    state[
        "hints"
    ] = []

    state[
        "last_action"
    ] = time.time()

    state[
        "total"
    ] += 1

    return question


class EmojiNewQuiz(
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

        state = ensure_emoji_user(
            interaction.user.id
        )

        question = emoji_new_question(
            state
        )

        state[
            "quiz_channel_id"
        ] = interaction.channel.id

        save_data()

        await interaction.response.send_message(
            f"🎯 **Emoji-Quiz**\n\n"
            f"{question['emojis']}\n\n"
            f"Schreibe deine Antwort hier in den Chat.",
            ephemeral=True
        )


class EmojiHint(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Tipp anfordern",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_hint"
        )

    async def callback(
        self,
        interaction
    ):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state[
            "tips_used"
        ] >= 3:

            await interaction.response.send_message(
                "❌ Tipp-Limit erreicht: **3/3**.\n"
                "🔄 Reset erfolgt automatisch alle 2 Stunden.",
                ephemeral=True
            )

            return

        if not state[
            "active"
        ]:

            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )

            return

        question = EMOJI_QUESTIONS[
            state[
                "question_index"
            ]
        ]

        state[
            "tips_used"
        ] += 1

        save_data()

        await interaction.response.send_message(
            f"💡 Tipp: {question['hint']}\n\n"
            f"Nutzung: `{state['tips_used']}/3`",
            ephemeral=True
        )


class EmojiLetters(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Anfangsbuchstaben",
            emoji="🔤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_letters"
        )

    async def callback(
        self,
        interaction
    ):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state[
            "letters_used"
        ] >= 3:

            await interaction.response.send_message(
                "❌ Anfangsbuchstaben-Limit erreicht: **3/3**.\n"
                "🔄 Reset erfolgt automatisch alle 2 Stunden.",
                ephemeral=True
            )

            return

        if not state[
            "active"
        ]:

            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )

            return

        letters = " ".join(
            word[0].upper()
            for word in state[
                "answer"
            ].split()
            if word
        )

        state[
            "letters_used"
        ] += 1

        save_data()

        await interaction.response.send_message(
            f"🔤 Anfangsbuchstaben: `{letters}`\n\n"
            f"Nutzung: `{state['letters_used']}/3`",
            ephemeral=True
        )


class EmojiSkip(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Aufgabe überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_emoji_skip"
        )

    async def callback(
        self,
        interaction
    ):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state[
            "skips_used"
        ] >= 3:

            await interaction.response.send_message(
                "❌ Überspringen-Limit erreicht: **3/3**.\n"
                "🔄 Reset erfolgt automatisch alle 2 Stunden.",
                ephemeral=True
            )

            return

        if not state[
            "active"
        ]:

            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )

            return

        state[
            "skips_used"
        ] += 1

        state[
            "skipped"
        ] += 1

        question = emoji_new_question(
            state
        )

        state[
            "quiz_channel_id"
        ] = interaction.channel.id

        save_data()

        await interaction.response.send_message(
            f"⏭️ Neue Aufgabe:\n\n"
            f"{question['emojis']}",
            ephemeral=True
        )


class EmojiLeaderboard(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Bestenliste",
            emoji="🏆",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_emoji_leaderboard"
        )

    async def callback(
        self,
        interaction
    ):

        entries = []

        for user_id, state in data[
            "emoji_quiz"
        ].items():

            if not isinstance(
                state,
                dict
            ):
                continue

            entries.append(
                (
                    int(
                        state.get(
                            "score",
                            0
                        )
                    ),
                    int(
                        state.get(
                            "solved",
                            0
                        )
                    ),
                    user_id
                )
            )

        entries.sort(
            key=lambda x: (
                x[0],
                x[1]
            ),
            reverse=True
        )

        lines = []

        for position, (
            score,
            solved,
            user_id
        ) in enumerate(
            entries[:10],
            start=1
        ):

            lines.append(
                f"**{position}.** "
                f"{get_member_name(user_id)} — "
                f"🏆 `{score}` | "
                f"✅ `{solved}`"
            )

        if not lines:
            lines.append(
                "Noch keine Ergebnisse."
            )

        state = ensure_emoji_user(
            interaction.user.id
        )

        await interaction.response.send_message(
            "🏆 **Emoji-Quiz Bestenliste**\n\n"
            + "\n".join(lines)
            + "\n\n"
            f"Dein Score: `{state['score']}`\n"
            f"Gelöst: `{state['solved']}`",
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
            EmojiNewQuiz()
        )

        self.add_item(
            EmojiHint()
        )

        self.add_item(
            EmojiLetters()
        )

        self.add_item(
            EmojiSkip()
        )

        self.add_item(
            EmojiLeaderboard()
        )


def emoji_quiz_embed():

    embed = discord.Embed(
        title="🎯 Emoji-Quiz",
        description=(
            "▶️ **Neues Quiz**\n"
            "💡 **Tipp anfordern** — 3 / 2 Stunden\n"
            "🔤 **Anfangsbuchstaben** — 3 / 2 Stunden\n"
            "⏭️ **Aufgabe überspringen** — 3 / 2 Stunden\n"
            "🏆 **Bestenliste**"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=EMOJI_QUIZ_PANEL_MARKER
    )

    return embed


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
async def emojiquiz_panel(
    ctx
):

    await update_or_create_panel(
        ctx.channel,
        EMOJI_QUIZ_PANEL_MARKER,
        emoji_quiz_embed(),
        EmojiQuizView()
    )

    await ctx.send(
        "✅ Emoji-Quiz-Panel aktualisiert."
    )


# ============================================================
# ZAHLENSPIEL
# ============================================================

def wrong_timeout_minutes(
    wrong_count
):

    if wrong_count < 4:
        return 0

    level = 1 + (
        (wrong_count - 4) // 10
    )

    minutes = 5 * level

    return min(
        minutes,
        24 * 60
    )


async def handle_number_game(
    message
):

    if message.channel.id != NUMBER_GAME_CHANNEL_ID:
        return False

    if message.author.bot:
        return False

    content = message.content.strip()

    if not re.fullmatch(
        r"\d+",
        content
    ):
        return False

    number = int(content)

    number_game = data[
        "number_game"
    ]

    expected = int(
        number_game.get(
            "current_number",
            1
        )
    )

    last_user_id = number_game.get(
        "last_user_id"
    )

    user_id = str(
        message.author.id
    )

    # --------------------------------------------------------
    # RICHTIG
    # --------------------------------------------------------

    if number == expected:

        if last_user_id == message.author.id:

            warning = await message.channel.send(
                f"⚠️ **Nicht möglich!**\n"
                f"Die Zahl `{expected}` muss von "
                f"einer anderen Person geschrieben werden."
            )

            asyncio.create_task(
                delete_after_seconds(
                    warning,
                    5
                )
            )

            return True

        number_game[
            "current_number"
        ] = expected + 1

        number_game[
            "last_user_id"
        ] = message.author.id

        number_game[
            "last_message_id"
        ] = message.id

        save_data()

        try:

            await message.add_reaction(
                "✅"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        if number % 100 == 0:

            if number_game.get(
                "last_easter_egg",
                0
            ) != number:

                number_game[
                    "last_easter_egg"
                ] = number

                save_data()

                egg = await message.channel.send(
                    f"🎉 **{number} erreicht!**\n"
                    f"Weiter geht's mit `{number + 1}`!"
                )

                asyncio.create_task(
                    delete_after_seconds(
                        egg,
                        5
                    )
                )

        return True

    # --------------------------------------------------------
    # FALSCH
    # --------------------------------------------------------

    wrong_attempts = number_game.setdefault(
        "wrong_attempts",
        {}
    )

    wrong_attempts[
        user_id
    ] = int(
        wrong_attempts.get(
            user_id,
            0
        )
    ) + 1

    wrong_count = wrong_attempts[
        user_id
    ]

    # IMMER WIEDER AUF 1
    number_game[
        "current_number"
    ] = 1

    number_game[
        "last_user_id"
    ] = None

    number_game[
        "last_message_id"
    ] = message.id

    save_data()

    timeout_minutes = wrong_timeout_minutes(
        wrong_count
    )

    wrong_message = await message.channel.send(
        f"❌ **Falsch ({message.author.display_name})!**\n"
        f"🔄 Das Zahlenspiel startet wieder bei **1**."
    )

    asyncio.create_task(
        delete_after_seconds(
            wrong_message,
            5
        )
    )

    asyncio.create_task(
        delete_after_seconds(
            message,
            5
        )
    )

    if timeout_minutes > 0:

        try:

            await message.author.timeout(
                discord.utils.utcnow()
                + timedelta(
                    minutes=timeout_minutes
                ),
                reason=(
                    "RLP Zahlenspiel – "
                    "zu viele Fehlversuche"
                )
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    return True


def number_game_embed():

    current = data[
        "number_game"
    ].get(
        "current_number",
        1
    )

    embed = discord.Embed(
        title="🔢 RLP Zahlenspiel",
        description=(
            "Zählt gemeinsam hoch!\n\n"
            "📌 **Regeln:**\n"
            "• Start ist bei **1**.\n"
            "• Die nächste Zahl muss geschrieben werden.\n"
            "• Derselbe User darf nicht zweimal "
            "direkt hintereinander zählen.\n"
            "• Eine falsche Zahl setzt alles wieder auf **1**.\n"
            "• Richtig → Bot reagiert mit **✅**.\n"
            "• Falsch → **Falsch (User)!**.\n"
            "• Falsche Nachrichten werden nach "
            "**5 Sekunden** gelöscht.\n\n"
            f"🎯 Aktuell erwartet: `{current}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=NUMBER_GAME_PANEL_MARKER
    )

    return embed


async def refresh_number_game_panel():

    channel = bot.get_channel(
        NUMBER_GAME_CHANNEL_ID
    )

    if channel:

        await update_or_create_panel(
            channel,
            NUMBER_GAME_PANEL_MARKER,
            number_game_embed(),
            None
        )


@bot.command(
    name="zahlenspiel",
    aliases=["numbergame"]
)
async def number_game_panel(
    ctx
):

    if not owner_check(
        ctx.author
    ):

        await ctx.send(
            "❌ Keine Berechtigung."
        )

        return

    await refresh_number_game_panel()

    await ctx.send(
        "✅ Zahlenspiel-Panel aktualisiert."
    )


# ============================================================
# OWNER PANEL - KANAL AUSWAHL
# ============================================================

class OwnerActionChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(
        self,
        action
    ):

        self.action = action

        super().__init__(
            placeholder="📌 Zuerst einen Kanal auswählen",
            custom_id=(
                f"rlp_owner_channel_{action}"
            ),
            channel_types=[
                discord.ChannelType.text
            ],
            min_values=1,
            max_values=1
        )

    async def callback(
        self,
        interaction
    ):

        if not owner_check(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        channel = self.values[0]

        if self.action == "announcement":

            await interaction.response.send_modal(
                OwnerAnnouncementModal(
                    channel.id
                )
            )

            return

        if self.action == "botsay":

            await interaction.response.send_modal(
                OwnerBotSayModal(
                    channel.id
                )
            )

            return

        if self.action == "giveaway":

            await interaction.response.send_modal(
                OwnerGiveawayModal(
                    channel.id
                )
            )

            return

        if self.action == "lock":

            overwrite = channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = False

            try:

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite
                )

            except discord.HTTPException:

                await interaction.response.send_message(
                    "❌ Der Kanal konnte nicht gesperrt werden.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                f"🔒 {channel.mention} wurde gesperrt.",
                ephemeral=True
            )

            return

        if self.action == "unlock":

            overwrite = channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = None

            try:

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite
                )

            except discord.HTTPException:

                await interaction.response.send_message(
                    "❌ Der Kanal konnte nicht entsperrt werden.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                f"🔓 {channel.mention} wurde entsperrt.",
                ephemeral=True
            )

            return

        if self.action == "status":

            await send_owner_status(
                channel,
                interaction
            )

            return

        if self.action == "serverinfo":

            await send_owner_server_info(
                channel,
                interaction
            )

            return

        if self.action == "userinfo":

            await send_owner_user_info(
                channel,
                interaction
            )

            return

        if self.action == "roles":

            await send_owner_roles_info(
                channel,
                interaction
            )

            return

        if self.action == "clear":

            await interaction.response.send_modal(
                OwnerClearModal(
                    channel.id
                )
            )

            return

        await interaction.response.send_message(
            "❌ Unbekannte Owner-Aktion.",
            ephemeral=True
        )


class OwnerChannelSelectView(
    discord.ui.View
):

    def __init__(
        self,
        action
    ):

        super().__init__(
            timeout=60
        )

        self.add_item(
            OwnerActionChannelSelect(
                action
            )
        )


async def open_owner_channel_select(
    interaction,
    action,
    title
):

    if not owner_check(
        interaction.user
    ):

        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung "
            "für das Owner Panel.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title=title,
        description=(
            "Bitte wähle zuerst den **Textkanal** aus, "
            "in dem die Aktion ausgeführt werden soll."
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        view=OwnerChannelSelectView(
            action
        ),
        ephemeral=True
    )


# ============================================================
# OWNER MODALS
# ============================================================

class OwnerAnnouncementModal(
    discord.ui.Modal,
    title="📢 Ankündigung"
):

    text = discord.ui.TextInput(
        label="Ankündigung",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(
        self,
        channel_id
    ):

        super().__init__()

        self.channel_id = channel_id

    async def on_submit(
        self,
        interaction
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.text.value,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )

        embed.set_footer(
            text=f"Von {interaction.user.display_name}"
        )

        try:

            await channel.send(
                embed=embed
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Nachricht konnte nicht gesendet werden.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"✅ Ankündigung wurde in "
            f"{channel.mention} gesendet.",
            ephemeral=True
        )


class OwnerBotSayModal(
    discord.ui.Modal,
    title="💬 Bot Say"
):

    text = discord.ui.TextInput(
        label="Nachricht",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(
        self,
        channel_id
    ):

        super().__init__()

        self.channel_id = channel_id

    async def on_submit(
        self,
        interaction
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        try:

            await channel.send(
                self.text.value
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Nachricht konnte nicht gesendet werden.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"✅ Bot-Nachricht wurde in "
            f"{channel.mention} gesendet.",
            ephemeral=True
        )


class OwnerGiveawayModal(
    discord.ui.Modal,
    title="🎁 Giveaway"
):

    prize = discord.ui.TextInput(
        label="Preis",
        placeholder="z. B. 10€ Gutschein",
        max_length=200
    )

    duration = discord.ui.TextInput(
        label="Dauer in Sekunden",
        placeholder="z. B. 60",
        max_length=6
    )

    def __init__(
        self,
        channel_id
    ):

        super().__init__()

        self.channel_id = channel_id

    async def on_submit(
        self,
        interaction
    ):

        try:

            duration = int(
                self.duration.value
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Die Dauer muss eine Zahl sein.",
                ephemeral=True
            )

            return

        duration = max(
            5,
            min(
                duration,
                86400
            )
        )

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🎁 GIVEAWAY",
            description=(
                f"🎁 Preis: **{self.prize.value}**\n\n"
                "Klicke auf 🎉, um teilzunehmen!\n\n"
                f"⏱️ Dauer: **{duration} Sekunden**"
            ),
            color=discord.Color.gold()
        )

        try:

            giveaway_message = await channel.send(
                embed=embed
            )

            await giveaway_message.add_reaction(
                "🎉"
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Giveaway konnte nicht gestartet werden.",
                ephemeral=True
            )

            return

        asyncio.create_task(
            finish_giveaway(
                channel,
                giveaway_message.id,
                self.prize.value,
                duration
            )
        )

        await interaction.response.send_message(
            f"✅ Giveaway wurde in "
            f"{channel.mention} gestartet.",
            ephemeral=True
        )


class OwnerClearModal(
    discord.ui.Modal,
    title="🧹 Nachrichten löschen"
):

    amount = discord.ui.TextInput(
        label="Anzahl",
        placeholder="1 bis 100",
        max_length=3
    )

    def __init__(
        self,
        channel_id
    ):

        super().__init__()

        self.channel_id = channel_id

    async def on_submit(
        self,
        interaction
    ):

        try:

            amount = int(
                self.amount.value
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Bitte eine Zahl eingeben.",
                ephemeral=True
            )

            return

        amount = max(
            1,
            min(
                amount,
                100
            )
        )

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        try:

            deleted = await channel.purge(
                limit=amount
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Nachrichten konnten nicht gelöscht werden.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"🧹 In {channel.mention} wurden "
            f"`{len(deleted)}` Nachrichten gelöscht.",
            ephemeral=True
        )


# ============================================================
# OWNER INFOS
# ============================================================

async def send_owner_status(
    channel,
    interaction
):

    uptime = int(
        time.time()
        - BOT_START_TIME
    )

    hours = uptime // 3600
    minutes = (
        uptime % 3600
    ) // 60
    seconds = uptime % 60

    embed = discord.Embed(
        title="📊 Bot Status",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Status",
        value="🟢 Online"
    )

    embed.add_field(
        name="Ping",
        value=f"`{round(bot.latency * 1000)} ms`"
    )

    embed.add_field(
        name="Uptime",
        value=(
            f"`{hours}h "
            f"{minutes}m "
            f"{seconds}s`"
        )
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"📊 Status wurde in "
        f"{channel.mention} gesendet.",
        ephemeral=True
    )


async def send_owner_server_info(
    channel,
    interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title="🖥️ Server Information",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🏠 Server",
        value=guild.name,
        inline=False
    )

    embed.add_field(
        name="🆔 Server ID",
        value=str(guild.id),
        inline=False
    )

    embed.add_field(
        name="👥 Mitglieder",
        value=str(
            guild.member_count
        ),
        inline=True
    )

    embed.add_field(
        name="💬 Kanäle",
        value=str(
            len(guild.channels)
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 Rollen",
        value=str(
            len(guild.roles)
        ),
        inline=True
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"🖥️ Server-Info wurde in "
        f"{channel.mention} gesendet.",
        ephemeral=True
    )


async def send_owner_user_info(
    channel,
    interaction
):

    member = interaction.user

    roles = [
        role.mention
        for role in member.roles
        if not role.is_default()
    ]

    embed = discord.Embed(
        title="👤 User Information",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Name",
        value=member.display_name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Erstellt am",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    embed.add_field(
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

    embed.add_field(
        name="🎭 Rollen",
        value=", ".join(
            roles
        ) or "Keine",
        inline=False
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"👤 User-Info wurde in "
        f"{channel.mention} gesendet.",
        ephemeral=True
    )


async def send_owner_roles_info(
    channel,
    interaction
):

    roles = []

    for role in reversed(
        interaction.guild.roles
    ):

        if role.is_default():
            continue

        roles.append(
            f"{role.mention} — `{role.id}`"
        )

    text = "\n".join(
        roles
    )

    if not text:
        text = "Keine Rollen."

    if len(text) > 3900:

        text = (
            text[:3850]
            + "\n… weitere Rollen vorhanden."
        )

    embed = discord.Embed(
        title="🎭 Server Rollen",
        description=text,
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"🎭 Rollen-Info wurde in "
        f"{channel.mention} gesendet.",
        ephemeral=True
    )


# ============================================================
# GIVEAWAY
# ============================================================

async def finish_giveaway(
    channel,
    message_id,
    prize,
    duration
):

    await asyncio.sleep(
        duration
    )

    try:

        message = await channel.fetch_message(
            message_id
        )

    except discord.HTTPException:

        return

    reaction = None

    for r in message.reactions:

        if str(r.emoji) == "🎉":

            reaction = r
            break

    if reaction is None:

        await channel.send(
            "🎁 Giveaway beendet — keine Teilnehmer."
        )

        return

    users = []

    try:

        async for user in reaction.users():

            if not user.bot:
                users.append(user)

    except discord.HTTPException:

        return

    if not users:

        await channel.send(
            "🎁 Giveaway beendet — keine Teilnehmer."
        )

        return

    winner = random.choice(
        users
    )

    await channel.send(
        f"🎉 **Giveaway beendet!**\n"
        f"🏆 Gewinner: {winner.mention}\n"
        f"🎁 Preis: **{prize}**"
    )


# ============================================================
# OWNER BUTTONS
# ============================================================

class OwnerAnnouncementButton(
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

        await open_owner_channel_select(
            interaction,
            "announcement",
            "📢 Ankündigung — Kanal auswählen"
        )


class OwnerBotSayButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_botsay"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "botsay",
            "💬 Bot Say — Kanal auswählen"
        )


class OwnerLockButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "lock",
            "🔒 Kanal zum Sperren auswählen"
        )


class OwnerUnlockButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "unlock",
            "🔓 Kanal zum Entsperren auswählen"
        )


class OwnerStatusButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "status",
            "📊 Status — Kanal auswählen"
        )


class OwnerServerInfoButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_serverinfo"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "serverinfo",
            "🖥️ Server Info — Kanal auswählen"
        )


class OwnerUserInfoButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_userinfo"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "userinfo",
            "👤 User Info — Kanal auswählen"
        )


class OwnerRolesInfoButton(
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

        await open_owner_channel_select(
            interaction,
            "roles",
            "🎭 Rollen Info — Kanal auswählen"
        )


class OwnerClearButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Clear",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_clear"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "clear",
            "🧹 Clear — Kanal auswählen"
        )


class OwnerGiveawayButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Giveaway",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_giveaway"
        )

    async def callback(
        self,
        interaction
    ):

        await open_owner_channel_select(
            interaction,
            "giveaway",
            "🎁 Giveaway — Kanal auswählen"
        )


class OwnerView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            OwnerAnnouncementButton()
        )

        self.add_item(
            OwnerBotSayButton()
        )

        self.add_item(
            OwnerLockButton()
        )

        self.add_item(
            OwnerUnlockButton()
        )

        self.add_item(
            OwnerStatusButton()
        )

        self.add_item(
            OwnerServerInfoButton()
        )

        self.add_item(
            OwnerUserInfoButton()
        )

        self.add_item(
            OwnerRolesInfoButton()
        )

        self.add_item(
            OwnerClearButton()
        )

        self.add_item(
            OwnerGiveawayButton()
        )


def owner_embed():

    embed = discord.Embed(
        title="👑 RLP Owner Panel",
        description=(
            "Willkommen im Owner Panel.\n\n"
            "📢 **Ankündigung**\n"
            "Sendet eine Ankündigung in einen ausgewählten Kanal.\n\n"
            "💬 **Bot Say**\n"
            "Sendet eine Nachricht als Bot.\n\n"
            "🔒 **Lock**\n"
            "Sperrt einen ausgewählten Kanal.\n\n"
            "🔓 **Unlock**\n"
            "Entsperrt einen ausgewählten Kanal.\n\n"
            "📊 **Status**\n"
            "Zeigt den Bot-Status in einem ausgewählten Kanal.\n\n"
            "🖥️ **Server Info**\n"
            "Zeigt Serverinformationen.\n\n"
            "👤 **User Info**\n"
            "Zeigt deine Userinformationen.\n\n"
            "🎭 **Rollen Info**\n"
            "Zeigt die Serverrollen.\n\n"
            "🧹 **Clear**\n"
            "Löscht Nachrichten in einem ausgewählten Kanal.\n\n"
            "🎁 **Giveaway**\n"
            "Startet ein Giveaway in einem ausgewählten Kanal.\n\n"
            "📌 **Wichtig:**\n"
            "Bei jeder Aktion musst du zuerst einen "
            "Textkanal auswählen."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=OWNER_PANEL_MARKER
    )

    return embed


@bot.command(
    name="ownerpanel",
    aliases=["owner"]
)
async def owner_panel(
    ctx
):

    if not owner_check(
        ctx.author
    ):

        await ctx.send(
            "❌ Du hast keine Berechtigung "
            "für das Owner Panel.",
            delete_after=5
        )

        return

    await update_or_create_panel(
        ctx.channel,
        OWNER_PANEL_MARKER,
        owner_embed(),
        OwnerView()
    )

    await ctx.send(
        "✅ Owner Panel wurde hier erstellt.",
        delete_after=5
    )


# ============================================================
# HELP
# ============================================================

@bot.command(
    name="help"
)
async def help_command(
    ctx
):

    embed = discord.Embed(
        title="📚 RLP Bot Hilfe",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔧 Panels",
        value=(
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
            "`?bewerbungpanel`\n"
            "`?devtaskpanel`\n"
            "`?devshiftpanel`\n"
            "`?zahlenspiel`\n"
            "`?communitypanel`\n"
            "`?emojiquizpanel`\n"
            "`?ownerpanel`"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
# COMMAND ERROR
# ============================================================

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
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ Du hast dafür keine Berechtigung.",
            delete_after=5
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ Es fehlt ein benötigtes Argument.",
            delete_after=5
        )

        return

    print(
        f"[COMMAND ERROR] {repr(error)}"
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ Eingeloggt als "
        f"{bot.user} "
        f"(ID: {bot.user.id})"
    )

    # Persistent Views
    bot.add_view(
        NametagPanelView()
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
        EmojiQuizView()
    )

    bot.add_view(
        OwnerView()
    )

    # Panels aktualisieren
    await refresh_license_panel()

    await refresh_application_panel()

    await refresh_developer_task_panel()

    await refresh_shift_panel()

    await refresh_number_game_panel()

    try:

        await bot.change_presence(
            activity=discord.Game(
                name=STATUS_TEXTS[0]
            )
        )

    except discord.HTTPException:
        pass


# ============================================================
# MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    # --------------------------------------------------------
    # ZAHLENSPIEL
    # --------------------------------------------------------

    handled = await handle_number_game(
        message
    )

    if handled:
        return

    # --------------------------------------------------------
    # EMOJI QUIZ
    # --------------------------------------------------------

    user_id = str(
        message.author.id
    )

    quiz_state = data[
        "emoji_quiz"
    ].get(
        user_id
    )

    if isinstance(
        quiz_state,
        dict
    ):

        if (
            quiz_state.get(
                "active"
            )
            and quiz_state.get(
                "quiz_channel_id"
            ) == message.channel.id
        ):

            answer = (
                message.content
                .strip()
                .lower()
            )

            expected = (
                quiz_state.get(
                    "answer",
                    ""
                )
                .strip()
                .lower()
            )

            if answer == expected:

                quiz_state[
                    "active"
                ] = False

                quiz_state[
                    "solved"
                ] += 1

                quiz_state[
                    "score"
                ] += 1

                save_data()

                await message.channel.send(
                    f"✅ **Richtig, "
                    f"{message.author.display_name}!** "
                    f"+1 Punkt.",
                    delete_after=5
                )

                return

    await bot.process_commands(
        message
    )


# ============================================================
# START
# ============================================================

def start_bot():

    if not TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gesetzt."
        )

    bot.run(
        TOKEN
    )


if __name__ == "__main__":
    start_bot()
