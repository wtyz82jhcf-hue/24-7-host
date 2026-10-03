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

TEAM_REGISTER_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348
QUIZ_COMMAND_ROLE_ID = 1530188150456979526

SUPPORT_ROLE_ID = 1540817417222094968

# NEUE / FESTE DEVELOPER-SCHICHT-ROLLE
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

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
    "team_members": {},
    "support_case_counter": 0
}

data = {}

startup_finished = False

current_quiz = None
current_quiz_message_id = None
quiz_bag = []

active_support_cases = {}
active_applications = {}

quiz_lock = asyncio.Lock()
support_lock = asyncio.Lock()

quiz_cleanup_task = None


# ============================================================
# DATEN LADEN / SPEICHERN
# ============================================================

def load_data():
    global data

    data = json.loads(
        json.dumps(DEFAULT_DATA)
    )

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            saved = json.load(file)

        if not isinstance(saved, dict):
            saved = {}

        for key in DEFAULT_DATA:
            if key in saved:
                data[key] = saved[key]

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        save_data()


def save_data():
    try:
        temp_file = f"{DATA_FILE}.tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


# ============================================================
# ALLGEMEIN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def get_channel(channel_id):
    return bot.get_channel(channel_id)


def timestamp():
    return now().strftime(
        "%d.%m.%Y %H:%M:%S UTC"
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


def make_embed(
    title,
    description=None
):
    embed = discord.Embed(
        title=title,
        description=description,
        timestamp=now()
    )

    embed.set_footer(
        text="RLP • System"
    )

    return embed


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def clean_panel_channel(channel):
    if channel is None:
        return

    try:
        async for message in channel.history(limit=None):
            if bot.user and message.author.id == bot.user.id:
                await safe_delete(message)

    except Exception as error:
        print(f"[PANEL CLEAN] {error}")


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


async def apply_nametag(
    member,
    force=False
):
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

    clean_name = clean_nametag(
        member.display_name
    )

    new_name = f"{NAMETAG}{clean_name}"[:32]

    if member.display_name == new_name:
        return

    try:
        await member.edit(
            nick=new_name,
            reason="RLP Nametag"
        )

    except discord.Forbidden:
        print(
            f"[NAMETAG] Keine Berechtigung für {member}"
        )

    except Exception as error:
        print(f"[NAMETAG] Fehler: {error}")


async def remove_nametag(member):
    if member.bot:
        return

    user_id = str(member.id)

    if user_id not in data["nametag_opt_out"]:
        data["nametag_opt_out"].append(user_id)

    save_data()

    clean_name = clean_nametag(
        member.display_name
    )

    try:
        await member.edit(
            nick=clean_name[:32],
            reason="RLP Nametag entfernt"
        )

    except Exception as error:
        print(f"[NAMETAG] Fehler: {error}")


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🏷️",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_nametag_remove"
    )
    async def remove(
        self,
        interaction,
        button
    ):
        await remove_nametag(
            interaction.user
        )

        await interaction.response.send_message(
            "✅ Dein RLP-Nametag wurde entfernt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Nametag aktivieren",
        emoji="🔄",
        style=discord.ButtonStyle.success,
        custom_id="rlp_nametag_enable"
    )
    async def enable(
        self,
        interaction,
        button
    ):
        user_id = str(
            interaction.user.id
        )

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(
                user_id
            )

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
    channel = get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_panel_channel(channel)

    embed = make_embed(
        "🏷️ RLP | Nametag",
        "Verwalte hier deinen persönlichen RLP-Nametag."
    )

    embed.add_field(
        name="🤖 Automatisch",
        value=(
            "Mit der RLP-Nametag-Rolle wird automatisch "
            "`RLP ` vor deinen Namen gesetzt."
        ),
        inline=False
    )

    embed.add_field(
        name="🔴 Entfernen",
        value="Entfernt den Nametag für deinen Account.",
        inline=False
    )

    embed.add_field(
        name="🟢 Aktivieren",
        value="Aktiviert den Nametag wieder.",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# ============================================================
# TEAM REGISTRIERUNG
# ============================================================

class TeamRegistrationModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Team registrieren"
        )

        self.name_input = discord.ui.TextInput(
            label="Name",
            placeholder="Dein Discord-Name",
            max_length=100,
            required=True
        )

        self.add_item(
            self.name_input
        )

    async def on_submit(
        self,
        interaction
    ):
        user_id = str(
            interaction.user.id
        )

        data["team_members"][user_id] = {
            "name": self.name_input.value,
            "discord_name": interaction.user.display_name,
            "registered_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            "✅ Du wurdest erfolgreich eingetragen.",
            ephemeral=True
        )

        await send_team_panel()


class TeamRegistrationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Eintragen",
        emoji="📝",
        style=discord.ButtonStyle.success,
        custom_id="team_register_add"
    )
    async def add(
        self,
        interaction,
        button
    ):
        user_id = str(
            interaction.user.id
        )

        if user_id in data["team_members"]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits eingetragen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TeamRegistrationModal()
        )

    @discord.ui.button(
        label="Austragen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="team_register_remove"
    )
    async def remove(
        self,
        interaction,
        button
    ):
        user_id = str(
            interaction.user.id
        )

        if user_id not in data["team_members"]:
            await interaction.response.send_message(
                "⚠️ Du bist nicht eingetragen.",
                ephemeral=True
            )
            return

        del data["team_members"][user_id]

        save_data()

        await interaction.response.send_message(
            "✅ Du wurdest aus der Liste entfernt.",
            ephemeral=True
        )

        await send_team_panel()


async def send_team_panel():
    channel = get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_panel_channel(channel)

    embed = make_embed(
        "👥 | Team-Registrierung",
        "Verwalte hier die Team-Mitgliedschaft."
    )

    embed.add_field(
        name="📝 Eintragen",
        value="Klicke auf **Eintragen** und gib deinen Namen an.",
        inline=False
    )

    if data["team_members"]:
        members = []

        for user_id, member_data in data["team_members"].items():
            members.append(
                f"• **{member_data['name']}** — <@{user_id}>"
            )

        text = "\n".join(members)

        if len(text) > 3500:
            text = text[:3500] + "\n..."

    else:
        text = "Noch niemand eingetragen."

    embed.add_field(
        name="📋 Aktuelle Teammitglieder",
        value=text,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=TeamRegistrationView()
    )


# ============================================================
# DEVELOPER SCHICHT
# ============================================================

def has_support_role(member):
    return any(
        role.id == SUPPORT_ROLE_ID
        for role in member.roles
    )


def has_developer_shift_role(member):
    return any(
        role.id == DEVELOPER_SHIFT_ROLE_ID
        for role in member.roles
    )


def is_team_member(member):
    return str(member.id) in data["team_members"]


async def add_developer_shift_role(member):
    role = member.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:
        print(
            f"[SHIFT] Rolle {DEVELOPER_SHIFT_ROLE_ID} wurde nicht gefunden."
        )
        return False

    try:
        if role not in member.roles:
            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

        return True

    except discord.Forbidden:
        print(
            "[SHIFT] Keine Berechtigung zum Vergeben der Schichtrolle."
        )
        return False

    except Exception as error:
        print(f"[SHIFT] Rollenfehler: {error}")
        return False


async def remove_developer_shift_role(member):
    role = member.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:
        print(
            f"[SHIFT] Rolle {DEVELOPER_SHIFT_ROLE_ID} wurde nicht gefunden."
        )
        return False

    try:
        if role in member.roles:
            await member.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )

        return True

    except discord.Forbidden:
        print(
            "[SHIFT] Keine Berechtigung zum Entfernen der Schichtrolle."
        )
        return False

    except Exception as error:
        print(f"[SHIFT] Rollenfehler: {error}")
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
        user_id = str(
            interaction.user.id
        )

        if not is_team_member(interaction.user):
            await interaction.response.send_message(
                "❌ Du musst zuerst im Team registriert sein.",
                ephemeral=True
            )
            return

        if user_id in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Deine Schicht läuft bereits.",
                ephemeral=True
            )
            return

        role_success = await add_developer_shift_role(
            interaction.user
        )

        if not role_success:
            await interaction.response.send_message(
                "❌ Die Schichtrolle konnte nicht vergeben werden.\n"
                "Bitte überprüfe die Rollen-Hierarchie des Bots.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
            "started_at": now().isoformat(),
            "name": interaction.user.display_name
        }

        save_data()

        await interaction.response.send_message(
            "🟢 **Developer-Schicht gestartet.**\n"
            f"Dir wurde die Schichtrolle <@&{DEVELOPER_SHIFT_ROLE_ID}> vergeben.",
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
        user_id = str(
            interaction.user.id
        )

        shift = data["developer_shifts"].get(
            user_id
        )

        if shift is None:
            await interaction.response.send_message(
                "⚠️ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        try:
            started = datetime.fromisoformat(
                shift["started_at"]
            )

            duration = (
                now() - started
            ).total_seconds()

        except Exception:
            duration = 0

        role_success = await remove_developer_shift_role(
            interaction.user
        )

        if not role_success:
            await interaction.response.send_message(
                "❌ Die Schichtrolle konnte nicht entfernt werden.\n"
                "Bitte überprüfe die Rollen-Hierarchie des Bots.",
                ephemeral=True
            )
            return

        del data["developer_shifts"][user_id]

        save_data()

        await interaction.response.send_message(
            "🔴 **Developer-Schicht beendet.**\n"
            f"⏱️ Dauer: **{format_duration(duration)}**\n"
            "Die Schichtrolle wurde entfernt.",
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

    embed = make_embed(
        "⏱️ | Developer-Schicht",
        f"{member.mention}"
    )

    if action == "start":
        embed.description = (
            f"🟢 {member.mention} "
            "hat eine Developer-Schicht gestartet."
        )

        embed.add_field(
            name="Status",
            value="🟢 Aktiv",
            inline=True
        )

        embed.add_field(
            name="Start",
            value=timestamp(),
            inline=True
        )

    else:
        embed.description = (
            f"🔴 {member.mention} "
            "hat seine Developer-Schicht beendet."
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
            name="Ende",
            value=timestamp(),
            inline=True
        )

    await channel.send(
        embed=embed
    )


async def send_shift_panel():
    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_panel_channel(channel)

    embed = make_embed(
        "⏱️ | Developer-Schichten",
        "Professionelle Verwaltung deiner Developer-Schicht."
    )

    embed.add_field(
        name="▶️ Schicht starten",
        value=(
            "Startet deine Schicht und vergibt automatisch "
            f"die Rolle <@&{DEVELOPER_SHIFT_ROLE_ID}>."
        ),
        inline=False
    )

    embed.add_field(
        name="⏹️ Schicht beenden",
        value=(
            "Beendet deine Schicht, entfernt die Schichtrolle "
            "und protokolliert die Dauer."
        ),
        inline=False
    )

    embed.add_field(
        name="💾 Speicherung",
        value=(
            "Aktive Schichten werden dauerhaft gespeichert "
            "und nach einem Bot-Neustart wiederhergestellt."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Schichtrolle",
        value=f"<@&{DEVELOPER_SHIFT_ROLE_ID}>",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# ============================================================
# SUPPORT
# ============================================================

def support_staff(member):
    if member.bot:
        return False

    return has_support_role(member)


def next_case_id():
    data["support_case_counter"] += 1

    save_data()

    return f"RLP-{data['support_case_counter']:05d}"


async def find_supporter_in_call():
    channel = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if channel is None:
        return None

    for member in channel.members:
        if support_staff(member):
            return member

    return None


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

    async def on_submit(
        self,
        interaction
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

        if not support_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Du besitzt die benötigte Support-Rolle nicht.",
                ephemeral=True
            )
            return

        case["comment"] = self.comment.value

        await interaction.response.send_message(
            "✅ Kommentar wurde gespeichert.",
            ephemeral=True
        )

        await update_support_case_message(case)


class SupportTransferSelect(discord.ui.UserSelect):

    def __init__(self, case_user_id):
        super().__init__(
            placeholder="Supporter auswählen...",
            min_values=1,
            max_values=1
        )

        self.case_user_id = case_user_id

    async def callback(
        self,
        interaction
    ):
        case = active_support_cases.get(
            str(self.case_user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Support-Fall nicht gefunden.",
                ephemeral=True
            )
            return

        if not support_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Du besitzt die benötigte Support-Rolle nicht.",
                ephemeral=True
            )
            return

        target = self.values[0]

        if not support_staff(target):
            await interaction.response.send_message(
                "❌ Diese Person besitzt die Support-Rolle nicht.",
                ephemeral=True
            )
            return

        case["supporter_id"] = target.id
        case["supporter_name"] = target.display_name

        await interaction.response.send_message(
            f"✅ Fall wurde an {target.mention} übertragen.",
            ephemeral=True
        )

        await update_support_case_message(case)


class SupportTransferView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=120)

        self.add_item(
            SupportTransferSelect(user_id)
        )


class SupportCaseView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)

        self.user_id = user_id

        accept_button = discord.ui.Button(
            label="Annehmen",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"support_accept:{user_id}"
        )

        transfer_button = discord.ui.Button(
            label="Übertragen",
            emoji="🔄",
            style=discord.ButtonStyle.primary,
            custom_id=f"support_transfer:{user_id}"
        )

        comment_button = discord.ui.Button(
            label="Kommentar",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id=f"support_comment:{user_id}"
        )

        accept_button.callback = self.accept
        transfer_button.callback = self.transfer
        comment_button.callback = self.comment

        self.add_item(accept_button)
        self.add_item(transfer_button)
        self.add_item(comment_button)

    async def accept(
        self,
        interaction
    ):
        case = active_support_cases.get(
            str(self.user_id)
        )

        if case is None:
            await interaction.response.send_message(
                "❌ Der Support-Fall ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if not support_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Du besitzt die Support-Rolle nicht.",
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

        await update_support_case_message(case)

    async def transfer(
        self,
        interaction
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

        if not support_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Du besitzt die Support-Rolle nicht.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔄 Wähle einen Supporter:",
            view=SupportTransferView(self.user_id),
            ephemeral=True
        )

    async def comment(
        self,
        interaction
    ):
        if not support_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Du besitzt die Support-Rolle nicht.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SupportCommentModal(self.user_id)
        )


def support_embed(
    case,
    closed=False
):
    created = datetime.fromisoformat(
        case["created_at"]
    )

    duration = (
        now() - created
    ).total_seconds()

    embed = make_embed(
        f"{E_CHECK} Support Fall "
        f"{'geschlossen' if closed else 'Gestartet'}"
    )

    embed.description = (
        "Ein Support-Fall wurde automatisch "
        "durch den Support-Voice-Channel erstellt."
        if not closed
        else
        "Der Nutzer hat den Support-Voice-Channel verlassen. "
        "Der Fall wurde automatisch geschlossen."
    )

    embed.add_field(
        name=f"{E_CASE} CaseID",
        value=f"`{case['case_id']}`",
        inline=True
    )

    embed.add_field(
        name=f"{E_CLOCK} Erstellt am",
        value=created.strftime(
            "%d.%m.%Y %H:%M:%S UTC"
        ),
        inline=True
    )

    embed.add_field(
        name=f"{E_USER} Nutzer",
        value=f"<@{case['user_id']}>",
        inline=True
    )

    if case.get("supporter_id"):
        supporter_text = (
            f"<@{case['supporter_id']}>"
        )
    else:
        supporter_text = "Noch nicht angenommen"

    embed.add_field(
        name=f"{E_SUPPORTER} Supporter",
        value=supporter_text,
        inline=True
    )

    embed.add_field(
        name=f"{E_DURATION} Dauer",
        value=format_duration(duration),
        inline=True
    )

    embed.add_field(
        name="📌 Status",
        value=(
            "🔴 Geschlossen"
            if closed
            else
            "🟢 Offen"
        ),
        inline=True
    )

    if case.get("comment"):
        embed.add_field(
            name="💬 Kommentar",
            value=case["comment"][:1024],
            inline=False
        )

    embed.set_footer(
        text="RLP Support System"
    )

    return embed


async def create_support_case(member):
    async with support_lock:
        if str(member.id) in active_support_cases:
            return

        case = {
            "case_id": next_case_id(),
            "user_id": member.id,
            "created_at": now().isoformat(),
            "supporter_id": None,
            "supporter_name": None,
            "comment": "",
            "message_id": None
        }

        supporter = await find_supporter_in_call()

        if supporter and supporter.id != member.id:
            case["supporter_id"] = supporter.id
            case["supporter_name"] = supporter.display_name

        active_support_cases[
            str(member.id)
        ] = case

        channel = get_channel(
            SUPPORT_LOG_CHANNEL_ID
        )

        if channel is None:
            return

        message = await channel.send(
            embed=support_embed(case),
            view=SupportCaseView(member.id)
        )

        case["message_id"] = message.id


async def update_support_case_message(case):
    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    message_id = case.get("message_id")

    if not message_id:
        return

    try:
        message = await channel.fetch_message(
            message_id
        )

        await message.edit(
            embed=support_embed(case),
            view=SupportCaseView(
                case["user_id"]
            )
        )

    except Exception as error:
        print(f"[SUPPORT UPDATE] {error}")


async def close_support_case(member):
    case = active_support_cases.pop(
        str(member.id),
        None
    )

    if case is None:
        return

    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    try:
        message = await channel.fetch_message(
            case["message_id"]
        )

        await message.edit(
            embed=support_embed(
                case,
                closed=True
            ),
            view=None
        )

    except Exception as error:
        print(f"[SUPPORT CLOSE] {error}")


# ============================================================
# KENNZEICHEN
# ============================================================

def normalize_plate(plate):
    return " ".join(
        plate.upper().strip().split()
    )


def user_plate_entry(user_id):
    for entry_id, entry in data["license_plates"].items():
        if int(entry.get("user_id", 0)) == int(user_id):
            return entry_id, entry

    return None, None


def user_has_plate(user_id):
    _, entry = user_plate_entry(user_id)
    return entry is not None


def plate_is_taken(plate):
    normalized = normalize_plate(plate)

    for entry in data["license_plates"].values():
        stored = normalize_plate(
            entry.get("plate", "")
        )

        if stored == normalized:
            return True

    return False


def next_plate_id():
    existing = data["license_plates"].keys()

    number = 1

    while str(number) in existing:
        number += 1

    return str(number)


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

        self.add_item(
            self.plate
        )

    async def on_submit(
        self,
        interaction
    ):
        user_id = interaction.user.id

        # Nur ein Kennzeichen pro Person
        if user_has_plate(user_id):
            await interaction.response.send_message(
                "🚫 **Du hast bereits ein Kennzeichen eingetragen.**\n"
                "Wenn du einen Fehler gemacht hast, "
                "trage dein vorhandenes Kennzeichen zuerst aus.",
                ephemeral=True
            )
            return

        plate = normalize_plate(
            self.plate.value
        )

        if len(plate) < 3:
            await interaction.response.send_message(
                "❌ Bitte gib ein gültiges Kennzeichen ein.",
                ephemeral=True
            )
            return

        # Serverweit nur einmal
        if plate_is_taken(plate):
            await interaction.response.send_message(
                "🚫 **Dieses Kennzeichen ist bereits vergeben.**\n"
                "Bitte verwende ein anderes Kennzeichen.",
                ephemeral=True
            )
            return

        entry_id = next_plate_id()

        data["license_plates"][entry_id] = {
            "user_id": user_id,
            "plate": plate,
            "name": interaction.user.display_name,
            "created_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde erfolgreich eingetragen.",
            ephemeral=True
        )

        await send_license_plate_panel()


class LicensePlateRemoveConfirmView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Ja, austragen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="license_plate_confirm_remove"
    )
    async def confirm(
        self,
        interaction,
        button
    ):
        user_id = interaction.user.id

        entry_id, entry = user_plate_entry(
            user_id
        )

        if entry is None:
            await interaction.response.send_message(
                "⚠️ Du hast aktuell kein Kennzeichen eingetragen.",
                ephemeral=True
            )
            return

        plate = entry.get(
            "plate",
            "Unbekannt"
        )

        del data["license_plates"][entry_id]

        save_data()

        await interaction.response.edit_message(
            content=(
                f"✅ Dein Kennzeichen **{plate}** wurde ausgetragen "
                "und ist wieder frei."
            ),
            view=None
        )

        await send_license_plate_panel()

    @discord.ui.button(
        label="Abbrechen",
        emoji="↩️",
        style=discord.ButtonStyle.secondary,
        custom_id="license_plate_cancel_remove"
    )
    async def cancel(
        self,
        interaction,
        button
    ):
        await interaction.response.edit_message(
            content="↩️ Das Austragen wurde abgebrochen.",
            view=None
        )


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
        if user_has_plate(interaction.user.id):
            entry_id, entry = user_plate_entry(
                interaction.user.id
            )

            plate = (
                entry.get("plate", "Unbekannt")
                if entry
                else "Unbekannt"
            )

            await interaction.response.send_message(
                "🚫 **Du hast bereits ein Kennzeichen eingetragen.**\n"
                f"Aktuell: **{plate}**\n\n"
                "Wenn du einen Fehler gemacht hast, "
                "nutze zuerst **Kennzeichen austragen**.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @discord.ui.button(
        label="Kennzeichen austragen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="license_plate_remove"
    )
    async def remove(
        self,
        interaction,
        button
    ):
        entry_id, entry = user_plate_entry(
            interaction.user.id
        )

        if entry is None:
            await interaction.response.send_message(
                "⚠️ Du hast aktuell kein Kennzeichen eingetragen.",
                ephemeral=True
            )
            return

        plate = entry.get(
            "plate",
            "Unbekannt"
        )

        await interaction.response.send_message(
            f"⚠️ Möchtest du **{plate}** wirklich austragen?\n"
            "Danach kann das Kennzeichen wieder von jemand anderem "
            "verwendet werden.",
            view=LicensePlateRemoveConfirmView(),
            ephemeral=True
        )


async def send_license_plate_panel():
    channel = get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_panel_channel(channel)

    embed = make_embed(
        "🚘 | Kennzeichen-System",
        "Verwalte hier dein persönliches Kennzeichen."
    )

    embed.add_field(
        name="📝 Kennzeichen eintragen",
        value=(
            "Jede Person kann genau **ein Kennzeichen** besitzen."
        ),
        inline=False
    )

    embed.add_field(
        name="🗑️ Kennzeichen austragen",
        value=(
            "Falls du einen Fehler gemacht hast, kannst du "
            "dein Kennzeichen wieder austragen."
        ),
        inline=False
    )

    embed.add_field(
        name="🔐 Doppelte Kennzeichen",
        value=(
            "Ein Kennzeichen kann serverweit nur **einmal** "
            "vergeben werden."
        ),
        inline=False
    )

    if data["license_plates"]:
        entries = []

        sorted_entries = sorted(
            data["license_plates"].values(),
            key=lambda x: x.get(
                "plate",
                ""
            ).lower()
        )

        for entry in sorted_entries:
            entries.append(
                f"🚘 **{entry.get('plate', 'Unbekannt')}** "
                f"— <@{entry.get('user_id')}>"
            )

        text = "\n".join(entries)

        if len(text) > 3500:
            text = text[:3500] + "\n..."

    else:
        text = "Noch keine Kennzeichen eingetragen."

    embed.add_field(
        name="📋 Aktuelle Kennzeichen",
        value=text,
        inline=False
    )

    embed.set_footer(
        text="RLP Kennzeichen-System • Automatisch aktualisiert"
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
            placeholder="Was soll gemacht werden?",
            style=discord.TextStyle.paragraph,
            max_length=1500,
            required=False
        )

        self.add_item(
            self.title_input
        )

        self.add_item(
            self.description_input
        )

    async def on_submit(
        self,
        interaction
    ):
        if not (
            interaction.user.guild_permissions.manage_guild
            or support_staff(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du darfst keine Developer-Aufgaben erstellen.",
                ephemeral=True
            )
            return

        data["developer_task_counter"] += 1

        task_id = str(
            data["developer_task_counter"]
        )

        data["developer_tasks"][task_id] = {
            "title": self.title_input.value,
            "description": (
                self.description_input.value
                or "Keine Beschreibung."
            ),
            "creator": interaction.user.display_name,
            "claimed_by": None,
            "status": "Offen",
            "created_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** erstellt.",
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
        custom_id="dev_task_create"
    )
    async def create(
        self,
        interaction,
        button
    ):
        if not (
            interaction.user.guild_permissions.manage_guild
            or support_staff(interaction.user)
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )

    @discord.ui.button(
        label="Aktualisieren",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_task_refresh"
    )
    async def refresh(
        self,
        interaction,
        button
    ):
        await interaction.response.send_message(
            "🔄 Aufgabenliste wird aktualisiert.",
            ephemeral=True
        )

        await send_developer_tasks()


@bot.command(name="devclaim")
async def devclaim(
    ctx,
    task_id=None
):
    if not task_id:
        await ctx.reply(
            "Verwendung: `!devclaim <ID>`",
            delete_after=7
        )
        return

    task = data["developer_tasks"].get(
        str(task_id)
    )

    if task is None:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden.",
            delete_after=7
        )
        return

    task["claimed_by"] = ctx.author.display_name
    task["status"] = "In Bearbeitung"

    save_data()

    await ctx.reply(
        f"🛠️ Aufgabe **#{task_id}** übernommen.",
        delete_after=7
    )

    await send_developer_tasks()


@bot.command(name="devdone")
async def devdone(
    ctx,
    task_id=None
):
    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdone <ID>`",
            delete_after=7
        )
        return

    task = data["developer_tasks"].get(
        str(task_id)
    )

    if task is None:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden.",
            delete_after=7
        )
        return

    task["status"] = "Erledigt"

    save_data()

    await ctx.reply(
        f"✅ Aufgabe **#{task_id}** erledigt.",
        delete_after=7
    )

    await send_developer_tasks()


@bot.command(name="devdelete")
@commands.has_permissions(
    manage_guild=True
)
async def devdelete(
    ctx,
    task_id=None
):
    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdelete <ID>`",
            delete_after=7
        )
        return

    if str(task_id) not in data["developer_tasks"]:
        await ctx.reply(
            "❌ Aufgabe nicht gefunden.",
            delete_after=7
        )
        return

    del data["developer_tasks"][
        str(task_id)
    ]

    save_data()

    await ctx.reply(
        f"🗑️ Aufgabe **#{task_id}** gelöscht.",
        delete_after=7
    )

    await send_developer_tasks()


async def send_developer_tasks():
    channel = get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    await clean_panel_channel(channel)

    embed = make_embed(
        "🛠️ | Developer Task Center",
        "Professionelle Verwaltung aller Developer-Aufgaben."
    )

    embed.add_field(
        name="➕ Neue Aufgabe",
        value=(
            "Über den Button kann eine berechtigte Person "
            "eine neue Aufgabe erstellen."
        ),
        inline=False
    )

    if not data["developer_tasks"]:
        embed.add_field(
            name="📋 Aufgaben",
            value="Aktuell sind keine Aufgaben vorhanden.",
            inline=False
        )

    else:
        status_order = {
            "Offen": 0,
            "In Bearbeitung": 1,
            "Erledigt": 2
        }

        tasks = sorted(
            data["developer_tasks"].items(),
            key=lambda item:
            status_order.get(
                item[1].get("status"),
                99
            )
        )

        for task_id, task in tasks[:15]:
            status = task.get(
                "status",
                "Offen"
            )

            if status == "Offen":
                status_text = "🟡 Offen"
            elif status == "In Bearbeitung":
                status_text = "🔵 In Bearbeitung"
            else:
                status_text = "🟢 Erledigt"

            claimed = (
                task.get("claimed_by")
                or "Niemand"
            )

            text = (
                f"**Beschreibung:** "
                f"{task.get('description', 'Keine Beschreibung.')[:600]}\n"
                f"**Status:** {status_text}\n"
                f"**Bearbeiter:** {claimed}\n"
                f"**Erstellt von:** "
                f"{task.get('creator', 'Unbekannt')}"
            )

            embed.add_field(
                name=(
                    f"#{task_id} • "
                    f"{task.get('title', 'Aufgabe')}"
                ),
                value=text,
                inline=False
            )

    embed.set_footer(
        text="RLP Developer Task Center"
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
        emoji="🧑‍💻",
        style=discord.ButtonStyle.success,
        custom_id="developer_apply"
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
            "📩 Die Bewerbung wurde gestartet. "
            "Bitte prüfe deine DMs.",
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
            "🧑‍💻 **RLP Developer-Bewerbung**\n\n"
            "Beantworte jede Frage einzeln.\n"
            "Mit `abbrechen` kannst du jederzeit abbrechen."
        )

        answers = []

        for number, question in enumerate(
            APPLICATION_QUESTIONS,
            start=1
        ):
            await dm.send(
                f"**Frage {number}/{len(APPLICATION_QUESTIONS)}**\n"
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
                    "⌛ Deine Bewerbung wurde wegen "
                    "Inaktivität beendet."
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

        embed = make_embed(
            "🧑‍💻 | Neue Developer-Bewerbung",
            f"**Bewerber:** {user.mention}\n"
            f"**ID:** `{user.id}`"
        )

        for number, answer in enumerate(
            answers,
            start=1
        ):
            embed.add_field(
                name=f"Frage {number}",
                value=answer[:1024],
                inline=False
            )

        await review_channel.send(
            embed=embed
        )

        await dm.send(
            "✅ Deine Bewerbung wurde erfolgreich "
            "an das Team weitergeleitet."
        )

    except discord.Forbidden:
        try:
            await user.send(
                "❌ Deine DMs sind geschlossen. "
                "Bitte aktiviere Direktnachrichten für diesen Server."
            )
        except Exception:
            pass

    except Exception as error:
        print(f"[APPLICATION] {error}")

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

    await clean_panel_channel(channel)

    embed = make_embed(
        "🧑‍💻 | Developer Recruitment",
        "Du möchtest Teil des Developer-Teams werden?"
    )

    embed.add_field(
        name="📝 Bewerbung",
        value=(
            "Klicke auf **Developer bewerben**. "
            "Die Bewerbung findet anschließend "
            "sicher über deine DMs statt."
        ),
        inline=False
    )

    embed.add_field(
        name="🔐 Datenschutz",
        value=(
            "Deine Antworten werden direkt an den "
            "internen Bewerbungsbereich weitergeleitet."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
# EMOJI QUIZ
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


def build_quizzes():
    quizzes = []

    for category, items in QUIZ_CATEGORIES.items():
        unique = list(dict.fromkeys(items))

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

            quizzes.append({
                "category": category,
                "emoji": emoji,
                "answer": answer,
                "options": options
            })

    random.shuffle(quizzes)

    return quizzes


QUIZZES = build_quizzes()


def refill_quiz():
    global quiz_bag

    quiz_bag = list(
        range(len(QUIZZES))
    )

    random.shuffle(quiz_bag)


class QuizView(discord.ui.View):

    def __init__(
        self,
        quiz,
        question_id
    ):
        super().__init__(timeout=None)

        for index, (_, answer) in enumerate(
            quiz["options"]
        ):
            button = discord.ui.Button(
                label=answer,
                style=discord.ButtonStyle.secondary,
                custom_id=(
                    f"quiz_answer:"
                    f"{question_id}:"
                    f"{index}"
                )
            )

            async def callback(
                interaction,
                answer=answer,
                question_id=question_id
            ):
                await handle_quiz_answer(
                    interaction,
                    answer,
                    question_id
                )

            button.callback = callback

            self.add_item(button)

        hint = discord.ui.Button(
            label="Hinweis",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id=f"quiz_hint:{question_id}"
        )

        async def hint_callback(interaction):
            if (
                current_quiz is None
                or current_quiz["question_id"] != question_id
            ):
                await interaction.response.send_message(
                    "❌ Diese Frage ist nicht mehr aktiv.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"💡 Kategorie: **{current_quiz['category']}**",
                ephemeral=True
            )

        hint.callback = hint_callback

        self.add_item(hint)

        skip = discord.ui.Button(
            label="Überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id=f"quiz_skip:{question_id}"
        )

        async def skip_callback(interaction):
            await handle_quiz_skip(
                interaction,
                question_id
            )

        skip.callback = skip_callback

        self.add_item(skip)


async def send_new_quiz(channel):
    global current_quiz
    global current_quiz_message_id

    async with quiz_lock:
        if current_quiz is not None:
            return

        if not quiz_bag:
            refill_quiz()

        index = quiz_bag.pop()

        quiz = dict(
            QUIZZES[index]
        )

        question_id = str(
            random.randint(100000, 999999)
        )

        quiz["question_id"] = question_id

        embed = make_embed(
            "🎮 | RLP Emoji-Quiz",
            f"## {quiz['emoji']}\n\n"
            "Welche Bedeutung hat dieses Emoji?"
        )

        embed.add_field(
            name="Kategorie",
            value=quiz["category"],
            inline=True
        )

        embed.add_field(
            name="🎯 Auswahl",
            value="Wähle eine der Antworten.",
            inline=True
        )

        embed.set_footer(
            text=(
                "RLP Quiz • Fragen werden erst nach "
                "dem vollständigen Pool wiederholt."
            )
        )

        try:
            message = await channel.send(
                embed=embed,
                view=QuizView(
                    quiz,
                    question_id
                )
            )

        except Exception:
            quiz_bag.append(index)
            raise

        current_quiz = quiz
        current_quiz_message_id = message.id


async def quiz_cleanup_loop():
    global current_quiz_message_id

    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            channel = get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is not None:
                async for message in channel.history(
                    limit=None
                ):
                    # Die aktuell aktive Quiznachricht bleibt.
                    if (
                        current_quiz_message_id
                        and message.id == current_quiz_message_id
                    ):
                        continue

                    # Alles andere wird gelöscht.
                    await safe_delete(message)

        except asyncio.CancelledError:
            raise

        except Exception as error:
            print(
                f"[QUIZ CLEANUP] {error}"
            )

        await asyncio.sleep(5)


async def handle_quiz_answer(
    interaction,
    answer,
    question_id
):
    global current_quiz
    global current_quiz_message_id

    async with quiz_lock:
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Diese Frage ist bereits beendet.",
                ephemeral=True
            )
            return

        if current_quiz["question_id"] != question_id:
            await interaction.response.send_message(
                "❌ Diese Quizfrage ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if current_quiz_message_id != interaction.message.id:
            await interaction.response.send_message(
                "❌ Diese Quiznachricht ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if answer != current_quiz["answer"]:
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

        save_data()

        correct = current_quiz["answer"]

        current_quiz = None
        current_quiz_message_id = None

        embed = make_embed(
            "✅ Richtig!",
            f"{interaction.user.mention} "
            "hat die richtige Antwort gewählt."
        )

        embed.add_field(
            name="Antwort",
            value=correct,
            inline=True
        )

        embed.add_field(
            name="Deine Punkte",
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


async def handle_quiz_skip(
    interaction,
    question_id
):
    global current_quiz
    global current_quiz_message_id

    async with quiz_lock:
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Keine aktive Frage.",
                ephemeral=True
            )
            return

        if current_quiz["question_id"] != question_id:
            await interaction.response.send_message(
                "❌ Diese Frage ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        correct = current_quiz["answer"]

        current_quiz = None
        current_quiz_message_id = None

        embed = make_embed(
            "⏭️ Frage übersprungen",
            f"Die richtige Antwort war **{correct}**."
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    await asyncio.sleep(2)

    await send_new_quiz(
        interaction.channel
    )


@bot.command(name="quiz")
@commands.guild_only()
async def quiz_command(ctx):
    role = ctx.guild.get_role(
        QUIZ_COMMAND_ROLE_ID
    )

    if role is None or role not in ctx.author.roles:
        await ctx.reply(
            "❌ Du hast keine Berechtigung für `!quiz`.",
            delete_after=7
        )
        return

    if ctx.channel.id != QUIZ_CHANNEL_ID:
        await ctx.reply(
            f"❌ Nutze `!quiz` in <#{QUIZ_CHANNEL_ID}>.",
            delete_after=7
        )
        return

    if current_quiz is not None:
        await ctx.reply(
            "⚠️ Es läuft bereits ein Quiz.",
            delete_after=7
        )
        return

    await send_new_quiz(
        ctx.channel
    )


@bot.command(name="punkte")
@commands.guild_only()
async def punkte_command(ctx):
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
            "🏆 Noch keine Quizpunkte vorhanden.",
            delete_after=7
        )
        return

    ranking = sorted(
        scores.items(),
        key=lambda item: item[1],
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
            f"**{position}.** {name} — "
            f"**{score} Punkte**"
        )

    embed = make_embed(
        "🏆 | Emoji-Quiz Top 10",
        "\n".join(lines)
    )

    await ctx.reply(
        embed=embed,
        delete_after=15
    )


# ============================================================
# VOICE SUPPORT EVENT
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):
    if member.bot:
        return

    entered_support = (
        after.channel is not None
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    left_support = (
        before.channel is not None
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    if entered_support:
        if support_staff(member):
            return

        await create_support_case(member)

    if left_support:
        if str(member.id) in active_support_cases:
            await close_support_case(member)


# ============================================================
# MEMBER EVENTS / NAMETAG
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

    before_has = has_nametag_role(before)
    after_has = has_nametag_role(after)

    if not before_has and after_has:
        await apply_nametag(
            after,
            force=True
        )

    if before_has and not after_has:
        user_id = str(after.id)

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(
                user_id
            )

            save_data()


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():
    global startup_finished
    global quiz_cleanup_task

    print("================================")
    print(f"BOT ONLINE: {bot.user}")
    print("================================")

    if startup_finished:
        return

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        print(
            "[START] Server nicht gefunden."
        )
        return

    load_data()

    refill_quiz()

    # --------------------------------------------------------
    # PANELS NEU AUFBAUEN
    # --------------------------------------------------------

    quiz_channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel:
        await clean_panel_channel(
            quiz_channel
        )

        try:
            await send_new_quiz(
                quiz_channel
            )

        except Exception as error:
            print(
                f"[QUIZ START] {error}"
            )

    await send_nametag_panel()

    await send_team_panel()

    await send_license_plate_panel()

    await send_shift_panel()

    await send_developer_tasks()

    await send_application_panel()

    # --------------------------------------------------------
    # NAMETAGS AKTUALISIEREN
    # --------------------------------------------------------

    nametag_role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if nametag_role:
        for member in nametag_role.members:
            await apply_nametag(member)

    # --------------------------------------------------------
    # AKTIVE DEVELOPER-SCHICHTEN WIEDERHERSTELLEN
    # --------------------------------------------------------

    shift_role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if shift_role:
        for user_id in list(
            data["developer_shifts"].keys()
        ):
            member = guild.get_member(
                int(user_id)
            )

            if member:
                try:
                    if shift_role not in member.roles:
                        await member.add_roles(
                            shift_role,
                            reason="Aktive Developer-Schicht wiederherstellen"
                        )

                except discord.Forbidden:
                    print(
                        f"[SHIFT RESTORE] Keine Berechtigung für {member}"
                    )

                except Exception as error:
                    print(
                        f"[SHIFT RESTORE] {error}"
                    )

    # --------------------------------------------------------
    # SUPPORT-FÄLLE BEI RESTART WIEDERHERSTELLEN
    # --------------------------------------------------------

    support_voice = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if support_voice:
        for member in support_voice.members:
            if member.bot:
                continue

            if support_staff(member):
                continue

            if str(member.id) not in active_support_cases:
                await create_support_case(member)

    # --------------------------------------------------------
    # QUIZ CLEANUP STARTEN
    # --------------------------------------------------------

    if (
        quiz_cleanup_task is None
        or quiz_cleanup_task.done()
    ):
        quiz_cleanup_task = asyncio.create_task(
            quiz_cleanup_loop()
        )

    startup_finished = True

    print(
        "[START] Alle Systeme erfolgreich geladen."
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
# PERSISTENTE PANELS
# ============================================================

bot.add_view(
    NametagView()
)

bot.add_view(
    TeamRegistrationView()
)

bot.add_view(
    LicensePlateView()
)

bot.add_view(
    DeveloperShiftView()
)

bot.add_view(
    DeveloperTaskView()
)

bot.add_view(
    DeveloperApplicationView()
)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gefunden."
        )

    load_data()

    print(
        "[START] Bot wird gestartet..."
    )

    bot.run(
        TOKEN
    )
