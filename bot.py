import os
import json
import random
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.environ.get("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NICKNAME_CHANNEL_ID = 1555684071911202836

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348
QUIZ_COMMAND_ROLE_ID = 1530188150456979526
DEVELOPER_SHIFT_ROLE_ID = 1540817417222094968

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"


# ============================================================
# EMOJIS
# ============================================================

E_CHECK = "<:circlecheck:1492540257575506113>"
E_CASE = "<:memopadfingerprint:1492541033580597249>"
E_CLOCK = "<:clock:1492541036881248497>"
E_USER = "<:user:1360768014756352010>"
E_SUPPORTER = "<:supporter:1360767995596640340>"
E_DURATION = "<:duration:1360767960838574232>"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# DATEN
# ============================================================

DEFAULT_DATA = {
    "nametag_opt_out": [],
    "quiz_scores": {},
    "developer_shifts": {},
    "developer_tasks": {},
    "developer_task_counter": 0,
    "license_plates": {},
    "license_plate_counter": 0,
    "support_case_counter": 0
}

data = {}

startup_finished = False

current_quiz = None
current_quiz_message = None
quiz_bag = []

active_support_cases = {}
active_applications = {}

quiz_lock = asyncio.Lock()
support_lock = asyncio.Lock()


# ============================================================
# ALLGEMEINE HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def timestamp():
    return now().strftime("%d.%m.%Y %H:%M:%S UTC")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )
    except Exception as error:
        print(f"[DATA] Speichern fehlgeschlagen: {error}")


def load_data():
    global data

    data = json.loads(json.dumps(DEFAULT_DATA))

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)

        for key in DEFAULT_DATA:
            if key in saved:
                data[key] = saved[key]

    except Exception as error:
        print(f"[DATA] Laden fehlgeschlagen: {error}")
        save_data()


def get_channel(channel_id):
    return bot.get_channel(channel_id)


def base_embed(title, description=None):
    return discord.Embed(
        title=title,
        description=description,
        timestamp=now()
    )


def format_duration(seconds):
    seconds = max(0, int(seconds))

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def clean_bot_messages(channel):
    if channel is None:
        return

    try:
        async for message in channel.history(limit=None):
            if bot.user and message.author.id == bot.user.id:
                await safe_delete(message)

    except Exception as error:
        print(
            f"[CLEAN] Fehler in "
            f"{getattr(channel, 'name', 'unknown')}: {error}"
        )


# ============================================================
# NAMETAG
# ============================================================

def has_nametag_role(member):
    return any(
        role.id == NAMETAG_ROLE_ID
        for role in member.roles
    )


def clean_nametag(name):
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def apply_nametag(member, force=False):

    if member.bot:
        return

    if not has_nametag_role(member):
        return

    user_id = str(member.id)

    if (
        user_id in data["nametag_opt_out"]
        and not force
    ):
        return

    if force and user_id in data["nametag_opt_out"]:
        data["nametag_opt_out"].remove(user_id)
        save_data()

    clean_name = clean_nametag(member.display_name)

    new_name = f"{NAMETAG}{clean_name}"[:32]

    if member.display_name == new_name:
        return

    try:
        await member.edit(
            nick=new_name,
            reason="RLP Nametag"
        )
    except discord.Forbidden:
        print(f"[NAMETAG] Keine Berechtigung für {member}")
    except Exception as error:
        print(f"[NAMETAG] Fehler: {error}")


async def remove_nametag(member):

    if member.bot:
        return

    user_id = str(member.id)

    if user_id not in data["nametag_opt_out"]:
        data["nametag_opt_out"].append(user_id)

    save_data()

    clean_name = clean_nametag(member.display_name)

    try:
        await member.edit(
            nick=clean_name[:32],
            reason="RLP Nametag entfernt"
        )

    except discord.Forbidden:
        print(f"[NAMETAG] Keine Berechtigung für {member}")

    except Exception as error:
        print(f"[NAMETAG] Fehler: {error}")


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🏷️",
        style=discord.ButtonStyle.danger,
        custom_id="nametag_remove"
    )
    async def remove(
        self,
        interaction,
        button
    ):
        await remove_nametag(interaction.user)

        await interaction.response.send_message(
            "✅ Dein RLP-Nametag wurde entfernt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Nametag aktivieren",
        emoji="🔄",
        style=discord.ButtonStyle.success,
        custom_id="nametag_enable"
    )
    async def enable(
        self,
        interaction,
        button
    ):
        user_id = str(interaction.user.id)

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(user_id)

        save_data()

        await apply_nametag(
            interaction.user,
            force=True
        )

        await interaction.response.send_message(
            "✅ Dein RLP-Nametag wurde wieder aktiviert.",
            ephemeral=True
        )


async def send_nametag_panel():

    channel = get_channel(NICKNAME_CHANNEL_ID)

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "🏷️ RLP | Nametag",
        "Verwalte hier deinen persönlichen RLP-Nametag."
    )

    embed.add_field(
        name="Automatisch",
        value=(
            "Wenn du die RLP-Nametag-Rolle besitzt, "
            "wird automatisch `RLP ` vor deinen Namen gesetzt."
        ),
        inline=False
    )

    embed.add_field(
        name="Entfernen",
        value=(
            "Mit dem roten Button kannst du den Nametag entfernen. "
            "Diese Einstellung bleibt über Neustarts erhalten."
        ),
        inline=False
    )

    embed.add_field(
        name="Aktivieren",
        value=(
            "Mit dem grünen Button kannst du den Nametag "
            "jederzeit wieder aktivieren."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# ============================================================
# DEVELOPER SCHICHTEN
# ============================================================

def has_shift(member):
    return str(member.id) in data["developer_shifts"]


async def give_shift_role(member):

    role = member.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:
        return False

    try:
        if role not in member.roles:
            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

        return True

    except discord.Forbidden:
        return False


async def remove_shift_role(member):

    role = member.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:
        return False

    try:
        if role in member.roles:
            await member.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )

        return True

    except discord.Forbidden:
        return False


class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        emoji="▶️",
        style=discord.ButtonStyle.success,
        custom_id="developer_shift_start"
    )
    async def start(
        self,
        interaction,
        button
    ):

        user_id = str(interaction.user.id)

        if user_id in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Schicht.",
                ephemeral=True
            )
            return

        role_added = await give_shift_role(
            interaction.user
        )

        if not role_added:
            await interaction.response.send_message(
                "❌ Die Schichtrolle konnte nicht vergeben werden. "
                "Prüfe die Rollen-Hierarchie und Bot-Berechtigungen.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
            "started_at": now().isoformat(),
            "name": interaction.user.display_name
        }

        save_data()

        await interaction.response.send_message(
            "✅ **Developer-Schicht gestartet.**\n"
            "Dir wurde die Schichtrolle gegeben.",
            ephemeral=True
        )

        await send_shift_log(
            interaction.user,
            "start",
            0
        )

    @discord.ui.button(
        label="Schicht beenden",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        custom_id="developer_shift_end"
    )
    async def end(
        self,
        interaction,
        button
    ):

        user_id = str(interaction.user.id)

        shift = data["developer_shifts"].pop(
            user_id,
            None
        )

        if shift is None:
            await interaction.response.send_message(
                "⚠️ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        started = datetime.fromisoformat(
            shift["started_at"]
        )

        duration = (
            now() - started
        ).total_seconds()

        await remove_shift_role(
            interaction.user
        )

        save_data()

        await interaction.response.send_message(
            f"✅ **Developer-Schicht beendet.**\n"
            f"⏱️ Dauer: **{format_duration(duration)}**",
            ephemeral=True
        )

        await send_shift_log(
            interaction.user,
            "end",
            duration
        )


async def send_shift_log(
    member,
    action,
    duration
):

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    # Kein zusätzliches Panel löschen:
    # die Schicht-Historie bleibt erhalten.

    embed = base_embed(
        "⏱️ Developer-Schicht",
        f"{member.mention}"
    )

    if action == "start":
        embed.description = (
            f"▶️ {member.mention} hat eine "
            f"Developer-Schicht gestartet."
        )

        embed.add_field(
            name="Status",
            value="🟢 Aktiv",
            inline=True
        )

        embed.add_field(
            name="Gestartet",
            value=timestamp(),
            inline=True
        )

    else:
        embed.description = (
            f"⏹️ {member.mention} hat seine "
            f"Developer-Schicht beendet."
        )

        embed.add_field(
            name="Status",
            value="🔴 Beendet",
            inline=True
        )

        embed.add_field(
            name="Dauer",
            value=format_duration(duration),
            inline=True
        )

        embed.add_field(
            name="Beendet",
            value=timestamp(),
            inline=True
        )

    await channel.send(embed=embed)


async def send_shift_panel():

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "⏱️ | Developer-Schichten",
        "Verwalte deine Developer-Schicht direkt über die Buttons."
    )

    embed.add_field(
        name="▶️ Schicht starten",
        value=(
            "Startet deine Schicht und gibt dir automatisch "
            f"die Rolle <@&{DEVELOPER_SHIFT_ROLE_ID}>."
        ),
        inline=False
    )

    embed.add_field(
        name="⏹️ Schicht beenden",
        value=(
            "Beendet deine Schicht, entfernt die Rolle "
            "und berechnet die Dauer."
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Wichtig",
        value=(
            "Du kannst keine zweite Schicht starten, "
            "solange bereits eine aktiv ist."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# ============================================================
# SUPPORT
# ============================================================

def is_support_staff(member):

    if member.bot:
        return False

    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_guild:
        return True

    if has_shift(member):
        return True

    return False


def create_case_id():

    data["support_case_counter"] += 1

    save_data()

    return f"RLP-{data['support_case_counter']:05d}"


def get_support_voice():

    return get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )


async def assign_supporter(case):

    voice = get_support_voice()

    if voice is None:
        return

    if case["supporter_id"] is not None:
        return

    user = voice.guild.get_member(
        case["user_id"]
    )

    if user is None:
        return

    for member in voice.members:

        if member.id == user.id:
            continue

        if is_support_staff(member):

            case["supporter_id"] = member.id
            case["supporter_name"] = member.display_name

            return


async def create_support_case(member):

    async with support_lock:

        if str(member.id) in active_support_cases:
            return

        case = {
            "case_id": create_case_id(),
            "user_id": member.id,
            "user_name": str(member),
            "supporter_id": None,
            "supporter_name": None,
            "created_at": now().isoformat(),
            "comment": "",
            "status": "offen"
        }

        active_support_cases[
            str(member.id)
        ] = case

        await assign_supporter(case)

        await send_support_case_message(
            case,
            "start"
        )


async def send_support_case_message(
    case,
    action="update"
):

    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = base_embed(
        f"{E_CHECK} Support Fall Gestartet"
        if action == "start"
        else f"{E_CHECK} Support Fall",
        "Ein Support-Fall wird aktuell bearbeitet."
    )

    embed.add_field(
        name=f"{E_CASE} CaseID",
        value=f"`{case['case_id']}`",
        inline=True
    )

    created = datetime.fromisoformat(
        case["created_at"]
    )

    embed.add_field(
        name=f"{E_CLOCK} Erstellt am",
        value=created.strftime(
            "%d.%m.%Y %H:%M:%S UTC"
        ),
        inline=True
    )

    user = channel.guild.get_member(
        case["user_id"]
    )

    embed.add_field(
        name=f"{E_USER} Nutzer",
        value=(
            user.mention
            if user
            else case["user_name"]
        ),
        inline=True
    )

    supporter_text = "Nicht angenommen"

    if case["supporter_id"]:
        supporter = channel.guild.get_member(
            case["supporter_id"]
        )

        supporter_text = (
            supporter.mention
            if supporter
            else case["supporter_name"]
        )

    embed.add_field(
        name=f"{E_SUPPORTER} Supporter",
        value=supporter_text,
        inline=True
    )

    duration = (
        now() - created
    ).total_seconds()

    embed.add_field(
        name=f"{E_DURATION} Dauer",
        value=format_duration(duration),
        inline=True
    )

    if case.get("comment"):
        embed.add_field(
            name="💬 Kommentar",
            value=case["comment"][:1024],
            inline=False
        )

    if case["status"] == "offen":

        await channel.send(
            embed=embed,
            view=SupportCaseView(
                case["user_id"]
            )
        )

    else:

        embed.add_field(
            name="Status",
            value="🔒 Geschlossen",
            inline=False
        )

        await channel.send(
            embed=embed
        )


class SupportCommentModal(discord.ui.Modal):

    def __init__(self, user_id):
        super().__init__(
            title="Support-Kommentar"
        )

        self.user_id = user_id

        self.comment = discord.ui.TextInput(
            label="Kommentar",
            placeholder="Kommentar zum Support-Fall...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )

        self.add_item(self.comment)

    async def on_submit(self, interaction):

        case = active_support_cases.get(
            str(self.user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Der Support-Fall existiert nicht mehr.",
                ephemeral=True
            )
            return

        if not is_support_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Du bist kein Supporter.",
                ephemeral=True
            )
            return

        case["comment"] = self.comment.value

        await interaction.response.send_message(
            "✅ Kommentar wurde hinzugefügt.",
            ephemeral=True
        )

        await send_support_case_message(
            case,
            "update"
        )


class SupportTransferView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=120)

        self.user_id = user_id

        self.select = discord.ui.UserSelect(
            placeholder="Supporter auswählen...",
            min_values=1,
            max_values=1
        )

        self.select.callback = self.selected

        self.add_item(self.select)

    async def selected(self, interaction):

        case = active_support_cases.get(
            str(self.user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Support-Fall nicht gefunden.",
                ephemeral=True
            )
            return

        if not is_support_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Du bist kein Supporter.",
                ephemeral=True
            )
            return

        target = self.select.values[0]

        if not is_support_staff(target):
            await interaction.response.send_message(
                "❌ Diese Person besitzt keine aktive Support-/Developer-Schicht.",
                ephemeral=True
            )
            return

        case["supporter_id"] = target.id
        case["supporter_name"] = target.display_name

        await interaction.response.send_message(
            f"✅ Support-Fall wurde an {target.mention} übertragen.",
            ephemeral=True
        )

        await send_support_case_message(
            case,
            "update"
        )


class SupportCaseView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)

        self.user_id = user_id

    @discord.ui.button(
        label="Annehmen",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="support_accept"
    )
    async def accept(
        self,
        interaction,
        button
    ):

        case = active_support_cases.get(
            str(self.user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Dieser Support-Fall ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if not is_support_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Du bist kein Supporter.",
                ephemeral=True
            )
            return

        if case["supporter_id"] is not None:
            await interaction.response.send_message(
                "⚠️ Dieser Fall wurde bereits angenommen.",
                ephemeral=True
            )
            return

        case["supporter_id"] = interaction.user.id
        case["supporter_name"] = interaction.user.display_name

        await interaction.response.send_message(
            "✅ Du hast den Support-Fall angenommen.",
            ephemeral=True
        )

        await send_support_case_message(
            case,
            "update"
        )

    @discord.ui.button(
        label="Übertragen",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        custom_id="support_transfer"
    )
    async def transfer(
        self,
        interaction,
        button
    ):

        case = active_support_cases.get(
            str(self.user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Support-Fall nicht gefunden.",
                ephemeral=True
            )
            return

        if not is_support_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Du bist kein Supporter.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔄 Wähle den Supporter aus:",
            view=SupportTransferView(
                self.user_id
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Kommentar",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
        custom_id="support_comment"
    )
    async def comment(
        self,
        interaction,
        button
    ):

        if not is_support_staff(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Du bist kein Supporter.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SupportCommentModal(
                self.user_id
            )
        )


class SupportPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Support öffnen",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="support_open"
    )
    async def open_support(
        self,
        interaction,
        button
    ):

        await interaction.response.send_message(
            f"🎫 Betrete den Support-Sprachkanal:\n"
            f"<#{SUPPORT_VOICE_CHANNEL_ID}>",
            ephemeral=True
        )


async def close_support_case(member):

    case = active_support_cases.pop(
        str(member.id),
        None
    )

    if case is None:
        return

    created = datetime.fromisoformat(
        case["created_at"]
    )

    duration = (
        now() - created
    ).total_seconds()

    case["status"] = "geschlossen"
    case["closed_at"] = now().isoformat()

    case["duration"] = duration

    await send_support_case_message(
        case,
        "close"
    )


async def send_support_panel():

    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "🎫 | Support",
        "Willkommen im Support-System."
    )

    embed.add_field(
        name="📞 Support öffnen",
        value=(
            f"Betrete den Sprachkanal "
            f"<#{SUPPORT_VOICE_CHANNEL_ID}>."
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Automatisches System",
        value=(
            "Beim Betreten wird automatisch ein Case erstellt. "
            "Developer mit aktiver Schicht können den Fall annehmen."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Support-Funktionen",
        value=(
            "Supporter können Fälle annehmen, "
            "übertragen und Kommentare hinzufügen."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=SupportPanelView()
    )


# ============================================================
# KENNZEICHEN
# ============================================================

def normalize_plate(plate):

    plate = plate.upper().strip()

    plate = " ".join(
        plate.split()
    )

    return plate


class LicensePlateModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Kennzeichen eintragen"
        )

        self.plate = discord.ui.TextInput(
            label="Kennzeichen",
            placeholder="z. B. RY ZE 66",
            max_length=20,
            required=True
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction):

        plate = normalize_plate(
            self.plate.value
        )

        if len(plate) < 3:
            await interaction.response.send_message(
                "❌ Das Kennzeichen ist zu kurz.",
                ephemeral=True
            )
            return

        # Doppelte Kennzeichen verhindern
        for existing in data["license_plates"].values():

            if (
                existing["plate"].lower()
                == plate.lower()
            ):
                await interaction.response.send_message(
                    "❌ Dieses Kennzeichen ist bereits eingetragen.",
                    ephemeral=True
                )
                return

        data["license_plate_counter"] += 1

        entry_id = str(
            data["license_plate_counter"]
        )

        data["license_plates"][entry_id] = {
            "plate": plate,
            "user_id": interaction.user.id,
            "name": interaction.user.display_name,
            "created_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Kennzeichen **{plate}** wurde eingetragen.",
            ephemeral=True
        )

        await send_license_plate_panel()


class LicensePlateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen eintragen",
        emoji="🚘",
        style=discord.ButtonStyle.success,
        custom_id="license_plate_add"
    )
    async def add(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            LicensePlateModal()
        )


async def send_license_plate_panel():

    channel = get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "🚘 | Kennzeichen",
        "Hier tragt ihr euer Kennzeichen ein."
    )

    embed.add_field(
        name="📝 Eintragen",
        value=(
            "Klicke auf **Kennzeichen eintragen** "
            "und gib dein Kennzeichen ein, z. B. `RY ZE 66`."
        ),
        inline=False
    )

    if not data["license_plates"]:

        embed.add_field(
            name="📋 Eingetragene Kennzeichen",
            value="Noch keine Kennzeichen eingetragen.",
            inline=False
        )

    else:

        entries = []

        sorted_entries = sorted(
            data["license_plates"].items(),
            key=lambda item: item[1]["plate"].lower()
        )

        for entry_id, entry in sorted_entries:

            entries.append(
                f"🚘 **{entry['plate']}** — "
                f"{entry['name']}"
            )

        text = "\n".join(entries)

        if len(text) > 4000:
            text = text[:3990] + "\n..."

        embed.add_field(
            name="📋 Eingetragene Kennzeichen",
            value=text,
            inline=False
        )

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# ============================================================
# DEVELOPER AUFGABEN
# ============================================================

class DeveloperTaskModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Neue Developer-Aufgabe"
        )

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="z. B. Support-System verbessern",
            max_length=100
        )

        self.description_input = discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Beschreibe die Aufgabe...",
            style=discord.TextStyle.paragraph,
            max_length=1500,
            required=False
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Du brauchst `Server verwalten`.",
                ephemeral=True
            )
            return

        data["developer_task_counter"] += 1

        task_id = str(
            data["developer_task_counter"]
        )

        data["developer_tasks"][task_id] = {
            "title": self.title_input.value,
            "description": self.description_input.value,
            "creator": interaction.user.display_name,
            "claimed_by": None,
            "status": "Offen",
            "created_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )

        await send_developer_tasks()


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.success,
        custom_id="developer_task_create"
    )
    async def create(
        self,
        interaction,
        button
    ):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Du brauchst `Server verwalten`.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )

    @discord.ui.button(
        label="Aufgaben aktualisieren",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="developer_task_refresh"
    )
    async def refresh(
        self,
        interaction,
        button
    ):

        await interaction.response.send_message(
            "🔄 Aufgaben werden aktualisiert.",
            ephemeral=True
        )

        await send_developer_tasks()


@bot.command(name="devclaim")
@commands.guild_only()
async def devclaim(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devclaim <ID>`"
        )
        return

    task = data["developer_tasks"].get(
        str(task_id)
    )

    if task is None:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden."
        )
        return

    task["claimed_by"] = ctx.author.display_name
    task["status"] = "In Bearbeitung"

    save_data()

    await ctx.reply(
        f"✅ Aufgabe **#{task_id}** übernommen."
    )

    await send_developer_tasks()


@bot.command(name="devdone")
@commands.guild_only()
async def devdone(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdone <ID>`"
        )
        return

    task = data["developer_tasks"].get(
        str(task_id)
    )

    if task is None:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden."
        )
        return

    task["status"] = "Erledigt"

    save_data()

    await ctx.reply(
        f"✅ Aufgabe **#{task_id}** erledigt."
    )

    await send_developer_tasks()


@bot.command(name="devdelete")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def devdelete(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdelete <ID>`"
        )
        return

    if str(task_id) not in data["developer_tasks"]:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden."
        )
        return

    del data["developer_tasks"][
        str(task_id)
    ]

    save_data()

    await ctx.reply(
        f"🗑️ Aufgabe **#{task_id}** gelöscht."
    )

    await send_developer_tasks()


async def send_developer_tasks():

    channel = get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "🛠️ | Developer-Aufgaben",
        "Zentrale Verwaltung aller offenen und erledigten Developer-Aufgaben."
    )

    embed.add_field(
        name="➕ Neue Aufgabe",
        value=(
            "Über den Button kann die berechtigte Teamleitung "
            "eine neue Aufgabe erstellen."
        ),
        inline=False
    )

    if not data["developer_tasks"]:

        embed.add_field(
            name="📋 Aufgabenliste",
            value="Aktuell sind keine Aufgaben vorhanden.",
            inline=False
        )

    else:

        for task_id, task in list(
            data["developer_tasks"].items()
        )[:15]:

            description = (
                task.get("description")
                or "Keine Beschreibung."
            )

            claimed = (
                task.get("claimed_by")
                or "Niemand"
            )

            value = (
                f"**Beschreibung:** {description[:500]}\n"
                f"**Status:** {task.get('status', 'Offen')}\n"
                f"**Bearbeiter:** {claimed}\n"
                f"**Erstellt von:** {task.get('creator', 'Unbekannt')}"
            )

            embed.add_field(
                name=f"#{task_id} — {task['title']}",
                value=value,
                inline=False
            )

    embed.set_footer(
        text="Developer Task Management"
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# ============================================================
# DEVELOPER BEWERBUNG
# ============================================================

APPLICATION_QUESTIONS = [
    "Wie heißt du und wie alt bist du?",
    "Warum möchtest du Developer werden?",
    "Welche Programmiersprachen kannst du?",
    "Welche Erfahrungen mit Discord-Bots hast du?",
    "Welche Projekte hast du bereits umgesetzt?",
    "Warum sollten wir dich ins Developer-Team aufnehmen?"
]


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        emoji="📝",
        style=discord.ButtonStyle.success,
        custom_id="developer_application"
    )
    async def apply(
        self,
        interaction,
        button
    ):

        if interaction.user.id in active_applications:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine laufende Bewerbung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📩 Ich habe dir eine DM für die Bewerbung geschickt.",
            ephemeral=True
        )

        asyncio.create_task(
            run_application(
                interaction.user
            )
        )


async def run_application(user):

    active_applications[user.id] = True

    try:

        dm = await user.create_dm()

        await dm.send(
            "📝 **Developer-Bewerbung**\n\n"
            "Beantworte die folgenden Fragen nacheinander.\n"
            "Schreibe `abbrechen`, wenn du die Bewerbung beenden möchtest."
        )

        answers = []

        for index, question in enumerate(
            APPLICATION_QUESTIONS,
            start=1
        ):

            await dm.send(
                f"**Frage {index}/{len(APPLICATION_QUESTIONS)}**\n"
                f"{question}"
            )

            def check(message):
                return (
                    message.author.id == user.id
                    and message.channel.id == dm.id
                )

            try:

                message = await bot.wait_for(
                    "message",
                    timeout=900,
                    check=check
                )

            except asyncio.TimeoutError:

                await dm.send(
                    "⌛ Deine Bewerbung wurde wegen Inaktivität beendet."
                )

                return

            if message.content.lower().strip() == "abbrechen":

                await dm.send(
                    "❌ Bewerbung abgebrochen."
                )

                return

            answers.append(
                message.content
            )

        review_channel = get_channel(
            REVIEW_CHANNEL_ID
        )

        if review_channel is None:

            await dm.send(
                "❌ Der Bewerbungs-Kanal wurde nicht gefunden."
            )

            return

        embed = base_embed(
            "🧑‍💻 | Neue Developer-Bewerbung",
            f"Bewerber: {user.mention}\n"
            f"ID: `{user.id}`"
        )

        for index, answer in enumerate(
            answers,
            start=1
        ):

            embed.add_field(
                name=f"Frage {index}",
                value=answer[:1024],
                inline=False
            )

        await review_channel.send(
            embed=embed
        )

        await dm.send(
            "✅ Deine Bewerbung wurde erfolgreich weitergeleitet."
        )

    except discord.Forbidden:

        try:
            await user.send(
                "❌ Ich konnte deine DMs nicht öffnen. "
                "Bitte aktiviere Direktnachrichten für diesen Server."
            )
        except Exception:
            pass

    except Exception as error:

        print(
            f"[APPLICATION] Fehler: {error}"
        )

    finally:

        active_applications.pop(
            user.id,
            None
        )


async def send_application_panel():

    channel = get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_bot_messages(channel)

    embed = base_embed(
        "🧑‍💻 | Developer-Bewerbung",
        "Du möchtest Teil des Developer-Teams werden?"
    )

    embed.add_field(
        name="📝 Bewerbung",
        value=(
            "Klicke auf den Button. "
            "Die komplette Bewerbung findet anschließend "
            "über deine Discord-DMs statt."
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Wichtig",
        value=(
            "Beantworte alle Fragen ehrlich und ausführlich."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
# QUIZ
# ============================================================

QUIZ_CATEGORIES = {
    "Länder": [
        ("🇩🇪", "Deutschland"),
        ("🇫🇷", "Frankreich"),
        ("🇮🇹", "Italien"),
        ("🇪🇸", "Spanien"),
        ("🇵🇹", "Portugal"),
        ("🇬🇧", "Vereinigtes Königreich"),
        ("🇳🇱", "Niederlande"),
        ("🇧🇪", "Belgien"),
        ("🇨🇭", "Schweiz"),
        ("🇦🇹", "Österreich"),
        ("🇵🇱", "Polen"),
        ("🇨🇿", "Tschechien"),
        ("🇩🇰", "Dänemark"),
        ("🇸🇪", "Schweden"),
        ("🇳🇴", "Norwegen"),
        ("🇫🇮", "Finnland"),
        ("🇬🇷", "Griechenland"),
        ("🇹🇷", "Türkei"),
        ("🇺🇸", "USA"),
        ("🇨🇦", "Kanada"),
        ("🇲🇽", "Mexiko"),
        ("🇧🇷", "Brasilien"),
        ("🇦🇷", "Argentinien"),
        ("🇯🇵", "Japan"),
        ("🇨🇳", "China"),
        ("🇰🇷", "Südkorea"),
        ("🇮🇳", "Indien"),
        ("🇦🇺", "Australien"),
        ("🇳🇿", "Neuseeland"),
        ("🇿🇦", "Südafrika"),
        ("🇪🇬", "Ägypten"),
        ("🇲🇦", "Marokko")
    ],

    "Farben": [
        ("🔴", "Rot"),
        ("🟠", "Orange"),
        ("🟡", "Gelb"),
        ("🟢", "Grün"),
        ("🔵", "Blau"),
        ("🟣", "Lila"),
        ("🟤", "Braun"),
        ("⚫", "Schwarz"),
        ("⚪", "Weiß"),
        ("🩷", "Rosa"),
        ("🩵", "Hellblau"),
        ("🩶", "Grau")
    ],

    "Tiere": [
        ("🐶", "Hund"),
        ("🐱", "Katze"),
        ("🐭", "Maus"),
        ("🐹", "Hamster"),
        ("🐰", "Hase"),
        ("🦊", "Fuchs"),
        ("🐻", "Bär"),
        ("🐼", "Panda"),
        ("🐨", "Koala"),
        ("🐯", "Tiger"),
        ("🦁", "Löwe"),
        ("🐮", "Kuh"),
        ("🐷", "Schwein"),
        ("🐸", "Frosch"),
        ("🐵", "Affe"),
        ("🐔", "Huhn"),
        ("🐧", "Pinguin"),
        ("🦋", "Schmetterling"),
        ("🐢", "Schildkröte"),
        ("🐍", "Schlange"),
        ("🐘", "Elefant"),
        ("🦒", "Giraffe")
    ],

    "Essen": [
        ("🍕", "Pizza"),
        ("🍔", "Burger"),
        ("🍟", "Pommes"),
        ("🌮", "Taco"),
        ("🌯", "Burrito"),
        ("🍝", "Pasta"),
        ("🍜", "Ramen"),
        ("🍣", "Sushi"),
        ("🍛", "Curry"),
        ("🥨", "Brezel"),
        ("🥪", "Sandwich"),
        ("🥩", "Steak"),
        ("🧀", "Käse"),
        ("🍞", "Brot"),
        ("🥞", "Pfannkuchen"),
        ("🧇", "Waffel"),
        ("🍎", "Apfel"),
        ("🍌", "Banane"),
        ("🍓", "Erdbeere"),
        ("🍉", "Wassermelone")
    ],

    "Aufgaben": [
        ("📚", "Lernen"),
        ("✍️", "Schreiben"),
        ("📖", "Lesen"),
        ("🧹", "Putzen"),
        ("🍳", "Kochen"),
        ("🛒", "Einkaufen"),
        ("🏃", "Laufen"),
        ("🚿", "Duschen"),
        ("😴", "Schlafen"),
        ("🍽️", "Essen"),
        ("💧", "Trinken"),
        ("💻", "Programmieren"),
        ("📞", "Telefonieren"),
        ("📦", "Packen"),
        ("🧩", "Rätseln"),
        ("🎮", "Spielen"),
        ("🎨", "Malen"),
        ("🎵", "Musik hören")
    ],

    "Fahrzeuge": [
        ("🚗", "Auto"),
        ("🚕", "Taxi"),
        ("🚌", "Bus"),
        ("🚓", "Polizeiauto"),
        ("🚑", "Rettungswagen"),
        ("🚒", "Feuerwehr"),
        ("🚚", "LKW"),
        ("🏎️", "Rennwagen"),
        ("🚜", "Traktor"),
        ("🏍️", "Motorrad"),
        ("🚲", "Fahrrad"),
        ("✈️", "Flugzeug"),
        ("🚁", "Helikopter"),
        ("🚀", "Rakete"),
        ("🚂", "Zug"),
        ("🚢", "Schiff")
    ],

    "Sport": [
        ("⚽", "Fußball"),
        ("🏀", "Basketball"),
        ("🏈", "Football"),
        ("⚾", "Baseball"),
        ("🎾", "Tennis"),
        ("🏐", "Volleyball"),
        ("🏓", "Tischtennis"),
        ("🏸", "Badminton"),
        ("🥊", "Boxen"),
        ("🥋", "Kampfsport"),
        ("🏊", "Schwimmen"),
        ("🚴", "Radfahren"),
        ("🏃", "Laufen"),
        ("⛷️", "Skifahren")
    ],

    "Natur": [
        ("🌳", "Baum"),
        ("🌲", "Tanne"),
        ("🌴", "Palme"),
        ("🌵", "Kaktus"),
        ("🌻", "Sonnenblume"),
        ("🌹", "Rose"),
        ("🌷", "Tulpe"),
        ("🍀", "Klee"),
        ("🌊", "Welle"),
        ("🏔️", "Berg"),
        ("🌋", "Vulkan"),
        ("🏜️", "Wüste"),
        ("🌈", "Regenbogen"),
        ("☀️", "Sonne"),
        ("🌙", "Mond"),
        ("⭐", "Stern")
    ],

    "Technik": [
        ("📱", "Handy"),
        ("💻", "Laptop"),
        ("🖥️", "Computer"),
        ("⌨️", "Tastatur"),
        ("🖱️", "Maus"),
        ("🎧", "Kopfhörer"),
        ("📷", "Kamera"),
        ("📺", "Fernseher"),
        ("🎮", "Controller"),
        ("🕹️", "Joystick"),
        ("⌚", "Smartwatch"),
        ("🔋", "Akku"),
        ("💾", "Speicher"),
        ("🖨️", "Drucker")
    ]
}


def build_quiz_pool():

    pool = []

    for category, items in QUIZ_CATEGORIES.items():

        unique = list(
            dict.fromkeys(items)
        )

        for emoji, answer in unique:

            wrong = [
                item
                for item in unique
                if item[1] != answer
            ]

            if len(wrong) < 3:
                continue

            options = [
                (emoji, answer)
            ]

            options.extend(
                random.sample(
                    wrong,
                    3
                )
            )

            random.shuffle(options)

            pool.append({
                "category": category,
                "emoji": emoji,
                "answer": answer,
                "options": options
            })

    random.shuffle(pool)

    return pool


QUIZZES = build_quiz_pool()


def refill_quiz_bag():

    global quiz_bag

    quiz_bag = list(
        range(len(QUIZZES))
    )

    random.shuffle(quiz_bag)


class QuizAnswerButton(discord.ui.Button):

    def __init__(
        self,
        answer,
        index
    ):

        super().__init__(
            label=answer,
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"quiz_answer_{index}_"
                f"{random.randint(100000, 999999)}"
            )
        )

        self.answer = answer

    async def callback(
        self,
        interaction
    ):

        global current_quiz
        global current_quiz_message

        async with quiz_lock:

            if current_quiz is None:
                await interaction.response.send_message(
                    "❌ Diese Frage ist bereits beendet.",
                    ephemeral=True
                )
                return

            if (
                current_quiz_message is None
                or interaction.message.id
                != current_quiz_message.id
            ):
                await interaction.response.send_message(
                    "❌ Diese Quizfrage ist nicht mehr aktiv.",
                    ephemeral=True
                )
                return

            if self.answer != current_quiz["answer"]:

                await interaction.response.send_message(
                    "❌ Falsch!",
                    ephemeral=True
                )

                return

            user_id = str(
                interaction.user.id
            )

            data["quiz_scores"][user_id] = (
                data["quiz_scores"].get(
                    user_id,
                    0
                ) + 1
            )

            answer = current_quiz["answer"]

            save_data()

            current_quiz = None
            current_quiz_message = None

            embed = base_embed(
                "✅ Richtig!",
                f"{interaction.user.mention} hat richtig geantwortet."
            )

            embed.add_field(
                name="Antwort",
                value=answer,
                inline=True
            )

            embed.add_field(
                name="Punkte",
                value=str(
                    data["quiz_scores"][user_id]
                ),
                inline=True
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

        await asyncio.sleep(3)

        await send_new_quiz(
            interaction.channel
        )


class QuizHintButton(discord.ui.Button):

    def __init__(self):

        super().__init__(
            label="Hinweis",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="quiz_hint"
        )

    async def callback(
        self,
        interaction
    ):

        if current_quiz is None:

            await interaction.response.send_message(
                "❌ Keine aktive Frage.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"💡 Kategorie: **{current_quiz['category']}**",
            ephemeral=True
        )


class QuizSkipButton(discord.ui.Button):

    def __init__(self):

        super().__init__(
            label="Überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="quiz_skip"
        )

    async def callback(
        self,
        interaction
    ):

        global current_quiz
        global current_quiz_message

        async with quiz_lock:

            if current_quiz is None:

                await interaction.response.send_message(
                    "❌ Keine aktive Frage.",
                    ephemeral=True
                )

                return

            answer = current_quiz["answer"]

            current_quiz = None
            current_quiz_message = None

            embed = base_embed(
                "⏭️ Übersprungen",
                f"Die richtige Antwort war **{answer}**."
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

        await asyncio.sleep(2)

        await send_new_quiz(
            interaction.channel
        )


class QuizView(discord.ui.View):

    def __init__(self, quiz):

        super().__init__(
            timeout=None
        )

        for index, (_, answer) in enumerate(
            quiz["options"]
        ):

            self.add_item(
                QuizAnswerButton(
                    answer,
                    index
                )
            )

        self.add_item(
            QuizHintButton()
        )

        self.add_item(
            QuizSkipButton()
        )


async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message

    if not quiz_bag:
        refill_quiz_bag()

    index = quiz_bag.pop()

    quiz = QUIZZES[index]

    embed = base_embed(
        "🎮 | Emoji-Quiz",
        f"## {quiz['emoji']}\n\n"
        "Welche Bedeutung hat dieses Emoji?"
    )

    embed.add_field(
        name="Kategorie",
        value=quiz["category"],
        inline=True
    )

    embed.set_footer(
        text="Keine Frage wird wiederholt, bevor der Fragenpool durchlaufen wurde."
    )

    try:

        message = await channel.send(
            embed=embed,
            view=QuizView(quiz)
        )

        current_quiz = quiz
        current_quiz_message = message

    except Exception:

        quiz_bag.append(index)

        raise


@bot.command(name="quiz")
@commands.guild_only()
async def quiz_command(ctx):

    role = ctx.guild.get_role(
        QUIZ_COMMAND_ROLE_ID
    )

    if role is None or role not in ctx.author.roles:

        await ctx.reply(
            "❌ Du hast keine Berechtigung für `!quiz`.",
            delete_after=5
        )

        return

    if ctx.channel.id != QUIZ_CHANNEL_ID:

        await ctx.reply(
            f"❌ Verwende `!quiz` in <#{QUIZ_CHANNEL_ID}>.",
            delete_after=5
        )

        return

    if current_quiz is not None:

        await ctx.reply(
            "⚠️ Es läuft bereits ein Quiz.",
            delete_after=5
        )

        return

    await send_new_quiz(
        ctx.channel
    )


@bot.command(name="punkte")
@commands.guild_only()
async def points_command(ctx):

    score = data["quiz_scores"].get(
        str(ctx.author.id),
        0
    )

    await ctx.reply(
        f"🏆 Du hast **{score} Punkte**.",
        delete_after=7
    )


@bot.command(name="top")
@commands.guild_only()
async def top_command(ctx):

    scores = data["quiz_scores"]

    if not scores:

        await ctx.reply(
            "🏆 Noch keine Punkte.",
            delete_after=7
        )

        return

    ranking = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    lines = []

    for position, (
        user_id,
        score
    ) in enumerate(
        ranking,
        start=1
    ):

        member = ctx.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else f"User {user_id}"
        )

        lines.append(
            f"**{position}.** {name} — **{score} Punkte**"
        )

    embed = base_embed(
        "🏆 | Quiz Top 10",
        "\n".join(lines)
    )

    await ctx.reply(
        embed=embed,
        delete_after=15
    )


# ============================================================
# QUIZ SPAM-SCHUTZ
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:

        # Jede normale Nachricht im Quiz-Kanal wird nach 7 Sekunden gelöscht.
        # Das Quiz-Embed des Bots bleibt bestehen.
        asyncio.create_task(
            delete_after_delay(
                message,
                7
            )
        )

    await bot.process_commands(
        message
    )


async def delete_after_delay(
    message,
    delay
):

    await asyncio.sleep(delay)

    await safe_delete(
        message
    )


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_member_join(member):

    if member.bot:
        return

    if has_nametag_role(member):
        await apply_nametag(
            member,
            force=True
        )


@bot.event
async def on_member_update(
    before,
    after
):

    if before.bot:
        return

    before_role = has_nametag_role(
        before
    )

    after_role = has_nametag_role(
        after
    )

    if not before_role and after_role:

        await apply_nametag(
            after,
            force=True
        )

    elif before_role and not after_role:

        user_id = str(
            after.id
        )

        if user_id in data["nametag_opt_out"]:

            data["nametag_opt_out"].remove(
                user_id
            )

            save_data()


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if member.bot:
        return

    entered = (
        after.channel is not None
        and after.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    )

    left = (
        before.channel is not None
        and before.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id
            != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    if entered:

        # Developer/Supporter betritt den Call:
        # kein eigener Fall.
        if is_support_staff(member):
            return

        await create_support_case(
            member
        )

    if left:

        if str(member.id) in active_support_cases:

            await close_support_case(
                member
            )


# ============================================================
# START
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print("--------------------------------")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("--------------------------------")

    if startup_finished:
        return

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        print(
            f"[START] Server {GUILD_ID} nicht gefunden."
        )

        return

    load_data()

    refill_quiz_bag()

    # Alte Panels/Nachrichten entfernen
    quiz_channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel:

        await clean_bot_messages(
            quiz_channel
        )

        try:

            await send_new_quiz(
                quiz_channel
            )

        except Exception as error:

            print(
                f"[QUIZ] Startfehler: {error}"
            )

    await send_nametag_panel()

    await send_support_panel()

    await send_license_plate_panel()

    await send_shift_panel()

    await send_developer_tasks()

    await send_application_panel()

    # Nametags aktualisieren
    role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role:

        for member in role.members:

            await apply_nametag(
                member
            )

    # Aktive Schichtrollen nach Neustart wiederherstellen
    shift_role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if shift_role:

        for user_id in data["developer_shifts"]:

            member = guild.get_member(
                int(user_id)
            )

            if member:

                try:

                    if shift_role not in member.roles:

                        await member.add_roles(
                            shift_role,
                            reason="Aktive Developer-Schicht wiederhergestellt"
                        )

                except Exception as error:

                    print(
                        f"[SHIFT] Rollenfehler: {error}"
                    )

    startup_finished = True

    print(
        "[START] Alle Systeme geladen."
    )


# ============================================================
# COMMAND FEHLER
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

        await ctx.reply(
            "❌ Du hast dafür keine Berechtigung.",
            delete_after=7
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.reply(
            "❌ Es fehlt ein erforderliches Argument.",
            delete_after=7
        )

        return

    if isinstance(
        error,
        commands.NoPrivateMessage
    ):

        return

    print(
        f"[COMMAND ERROR] {repr(error)}"
    )

    try:

        await ctx.reply(
            "❌ Beim Ausführen des Befehls ist ein Fehler aufgetreten.",
            delete_after=7
        )

    except Exception:
        pass


# ============================================================
# PERSISTENTE VIEWS
# ============================================================

bot.add_view(
    NametagView()
)

bot.add_view(
    SupportPanelView()
)

bot.add_view(
    DeveloperShiftView()
)

bot.add_view(
    LicensePlateView()
)

bot.add_view(
    DeveloperTaskView()
)

bot.add_view(
    DeveloperApplicationView()
)


# ============================================================
# BOT START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gefunden."
        )

    load_data()

    print(
        "[START] Discord Bot wird gestartet..."
    )

    bot.run(
        TOKEN
    )
