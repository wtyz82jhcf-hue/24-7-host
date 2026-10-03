import os
import json
import random
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks


# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

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

# Wer darf Schichten starten/beenden?
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904

# Rolle, die während einer aktiven Schicht vergeben wird
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"

PANEL_MARKER = "RLP_PANEL:"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# STANDARD-DATEN
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

quiz_message_id = None
current_quiz = None
quiz_cleanup_task = None

quiz_lock = asyncio.Lock()
plate_lock = asyncio.Lock()


# ============================================================
# DATENBANK
# ============================================================

def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = json.loads(json.dumps(DEFAULT_DATA))
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        data = json.loads(json.dumps(DEFAULT_DATA))

        if isinstance(loaded, dict):
            for key, value in loaded.items():
                data[key] = value

        # Alte/fehlerhafte Daten absichern
        if not isinstance(data.get("license_plates"), dict):
            data["license_plates"] = {}

        if not isinstance(data.get("developer_shifts"), dict):
            data["developer_shifts"] = {}

        if not isinstance(data.get("team_members"), dict):
            data["team_members"] = {}

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        data = json.loads(json.dumps(DEFAULT_DATA))


def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


# ============================================================
# ALLGEMEINE HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def now_text():
    return now().strftime("%d.%m.%Y %H:%M:%S")


def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    return bot.get_channel(channel_id)


def get_role(guild, role_id):
    if guild is None:
        return None

    return guild.get_role(role_id)


async def safe_delete(message):
    try:
        await message.delete()
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


def member_has_role(member, role_id):
    return any(
        role.id == role_id
        for role in member.roles
    )


# ============================================================
# PANEL-SYSTEM
# ============================================================

async def delete_old_panels():
    """
    Löscht beim Neustart ausschließlich unsere Panels.
    Normale Bot-Nachrichten werden NICHT gelöscht.
    """

    guild = get_guild()

    if guild is None:
        return

    channels = {
        NICKNAME_CHANNEL_ID,
        TEAM_REGISTER_CHANNEL_ID,
        DEVELOPER_SHIFT_CHANNEL_ID,
        DEVELOPER_TASK_CHANNEL_ID,
        APPLICATION_CHANNEL_ID
    }

    for channel_id in channels:

        channel = guild.get_channel(channel_id)

        if channel is None:
            continue

        try:
            async for message in channel.history(limit=None):

                if bot.user is None:
                    continue

                if message.author.id != bot.user.id:
                    continue

                is_panel = False

                for embed in message.embeds:

                    footer = embed.footer.text or ""

                    if footer.startswith(PANEL_MARKER):
                        is_panel = True
                        break

                if is_panel:
                    await safe_delete(message)

        except Exception as error:
            print(
                f"[PANEL] Fehler in {channel_id}: {error}"
            )


async def upsert_panel(
    channel,
    embed,
    view,
    panel_name
):
    """
    Erstellt ein Panel oder aktualisiert das bestehende.
    Dadurch werden Team- und Kennzeichenpanel im selben
    Kanal nicht mehr gegenseitig gelöscht.
    """

    if channel is None:
        return

    embed.set_footer(
        text=f"{PANEL_MARKER}{panel_name}"
    )

    existing = None

    try:

        async for message in channel.history(limit=None):

            if message.author.id != bot.user.id:
                continue

            for old_embed in message.embeds:

                footer = old_embed.footer.text or ""

                if footer == f"{PANEL_MARKER}{panel_name}":

                    if existing is None:
                        existing = message
                    else:
                        await safe_delete(message)

                    break

    except Exception as error:
        print(f"[PANEL] Suche fehlgeschlagen: {error}")

    try:

        if existing:
            await existing.edit(
                embed=embed,
                view=view
            )
        else:
            await channel.send(
                embed=embed,
                view=view
            )

    except Exception as error:
        print(f"[PANEL] Fehler: {error}")


# ============================================================
# NAMETAG
# ============================================================

def remove_nametag_from_name(name):
    if name.startswith(NAMETAG):
        return name[len(NAMETAG):].strip()

    return name


async def apply_nametag(member):
    role = get_role(
        member.guild,
        NAMETAG_ROLE_ID
    )

    if role is None:
        return False

    try:

        if role not in member.roles:
            await member.add_roles(
                role,
                reason="RLP Nametag aktiviert"
            )

        if not member.display_name.startswith(NAMETAG):

            new_name = (
                NAMETAG +
                remove_nametag_from_name(
                    member.display_name
                )
            )

            await member.edit(
                nick=new_name[:32],
                reason="RLP Nametag aktiviert"
            )

        return True

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return False


async def remove_nametag(member):
    role = get_role(
        member.guild,
        NAMETAG_ROLE_ID
    )

    try:

        if role and role in member.roles:
            await member.remove_roles(
                role,
                reason="RLP Nametag deaktiviert"
            )

        new_name = remove_nametag_from_name(
            member.display_name
        )

        if not new_name:
            new_name = member.name

        await member.edit(
            nick=new_name[:32],
            reason="RLP Nametag deaktiviert"
        )

        return True

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return False


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag aktivieren",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="rlp_nametag_enable"
    )
    async def enable(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        data["nametag_opt_out"] = [
            x for x in data["nametag_opt_out"]
            if str(x) != user_id
        ]

        save_data()

        success = await apply_nametag(
            interaction.user
        )

        if success:

            await interaction.response.send_message(
                "✅ Dein RLP-Nametag wurde aktiviert.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Ich konnte dein Nametag nicht setzen. "
                "Prüfe die Rollen-Hierarchie und meine Rechte.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Nametag entfernen",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="rlp_nametag_disable"
    )
    async def disable(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["nametag_opt_out"]:
            data["nametag_opt_out"].append(user_id)

        save_data()

        success = await remove_nametag(
            interaction.user
        )

        if success:

            await interaction.response.send_message(
                "✅ Dein RLP-Nametag wurde entfernt.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Ich konnte dein Nametag nicht vollständig entfernen.",
                ephemeral=True
            )


async def send_nametag_panel():

    channel = get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ RLP Nametag",
        description=(
            "**Nametag-Verwaltung**\n\n"
            "Mit den Buttons kannst du dein RLP-Nametag "
            "jederzeit aktivieren oder entfernen.\n\n"
            f"**Aktives Nametag:** `{NAMETAG}`\n\n"
            "Die Einstellung wird gespeichert und bleibt "
            "auch nach einem Bot-Neustart erhalten."
        ),
        color=discord.Color.blurple()
    )

    await upsert_panel(
        channel,
        embed,
        NametagView(),
        "nametag"
    )


# ============================================================
# KENNZEICHEN-SYSTEM
# ============================================================

def normalize_plate(value):
    return " ".join(
        value.upper().strip().split()
    )


def split_plate(value):
    """
    RLP 01
    RY ZE 01
    NRW 123

    Alles vor der letzten Gruppe = Name/Kürzel.
    Letzte Gruppe = Nummer.

    Wichtig:
    Nur die Nummer wird global geprüft.
    """

    value = normalize_plate(value)

    parts = value.split()

    if len(parts) < 2:
        return None, None

    name = " ".join(parts[:-1])
    number = parts[-1]

    if not name or not number:
        return None, None

    return name, number


def get_saved_plate(user_id):
    value = data["license_plates"].get(
        str(user_id)
    )

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return value.get("plate")

    return None


def plate_number(plate):
    parts = normalize_plate(plate).split()

    if not parts:
        return ""

    return parts[-1]


def find_plate_number(number):
    """
    Sucht ausschließlich nach der Nummer.

    RLP 01
    RY 01

    sind deshalb beide nicht gleichzeitig erlaubt.
    """

    number = str(number).upper().strip()

    for user_id, value in data[
        "license_plates"
    ].items():

        if isinstance(value, str):
            plate = value
        else:
            plate = value.get(
                "plate",
                ""
            )

        if plate_number(plate) == number:
            return user_id, plate

    return None, None


class PlateModal(
    discord.ui.Modal,
    title="Kennzeichen registrieren"
):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        min_length=2,
        max_length=25,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        async with plate_lock:

            user_id = str(
                interaction.user.id
            )

            existing = get_saved_plate(
                user_id
            )

            if existing:

                await interaction.response.send_message(
                    f"❌ Du hast bereits `{existing}` registriert.\n"
                    "Lösche dein aktuelles Kennzeichen zuerst.",
                    ephemeral=True
                )
                return

            plate = normalize_plate(
                str(self.plate.value)
            )

            name, number = split_plate(
                plate
            )

            if name is None or number is None:

                await interaction.response.send_message(
                    "❌ Ungültiges Format.\n\n"
                    "Beispiele:\n"
                    "`RLP 01`\n"
                    "`RY ZE 01`",
                    ephemeral=True
                )
                return

            # ==================================================
            # ENTSCHEIDEND:
            # NUR DIE NUMMER DARF NICHT DOPPELT VORKOMMEN.
            # ==================================================

            existing_user, existing_plate = (
                find_plate_number(number)
            )

            if existing_user is not None:

                await interaction.response.send_message(
                    f"❌ Die Nummer **{number}** ist bereits vergeben.\n\n"
                    f"Ein anderes Mitglied besitzt bereits "
                    f"`{existing_plate}`.\n\n"
                    "Der Buchstaben-/Namensbereich darf doppelt "
                    "vorkommen, die Nummer jedoch nicht.",
                    ephemeral=True
                )
                return

            data["license_plates"][user_id] = {
                "plate": plate,
                "registered_at": now_text()
            }

            save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **`{plate}`** wurde registriert.",
            ephemeral=True
        )

        await send_license_plate_panel()


class PlateDeleteConfirm(
    discord.ui.View
):

    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(
        label="Endgültig löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "❌ Diese Bestätigung gehört nicht dir.",
                ephemeral=True
            )
            return

        async with plate_lock:

            user_id = str(
                interaction.user.id
            )

            old = get_saved_plate(
                user_id
            )

            if not old:

                await interaction.response.edit_message(
                    content="❌ Du hast kein Kennzeichen mehr.",
                    embed=None,
                    view=None
                )
                return

            del data["license_plates"][
                user_id
            ]

            save_data()

        await interaction.response.edit_message(
            content=(
                f"✅ `{old}` wurde gelöscht.\n"
                f"Die Nummer **{plate_number(old)}** ist "
                "jetzt wieder frei."
            ),
            embed=None,
            view=None
        )

        await send_license_plate_panel()


class PlateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen registrieren",
        style=discord.ButtonStyle.success,
        emoji="🚘",
        custom_id="rlp_plate_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if get_saved_plate(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            PlateModal()
        )

    @discord.ui.button(
        label="Mein Kennzeichen löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="rlp_plate_delete"
    )
    async def delete(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        plate = get_saved_plate(
            interaction.user.id
        )

        if not plate:

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell kein Kennzeichen.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🗑️ Kennzeichen löschen",
            description=(
                f"Dein Kennzeichen:\n\n"
                f"### `{plate}`\n\n"
                f"Die Nummer **{plate_number(plate)}** "
                "wird danach wieder freigegeben."
            ),
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=PlateDeleteConfirm(
                interaction.user.id
            ),
            ephemeral=True
        )


async def send_license_plate_panel():

    channel = get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if channel is None:
        return

    entries = []

    for user_id, value in data[
        "license_plates"
    ].items():

        if isinstance(value, str):
            plate = value
        else:
            plate = value.get(
                "plate",
                ""
            )

        if not plate:
            continue

        member = channel.guild.get_member(
            int(user_id)
        )

        mention = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        entries.append(
            (
                plate_number(plate),
                f"🚘 `{plate}` — {mention}"
            )
        )

    entries.sort(
        key=lambda item: (
            int(item[0])
            if item[0].isdigit()
            else item[0]
        )
    )

    if entries:

        lines = [
            item[1]
            for item in entries
        ]

        content = "\n".join(lines)

    else:

        content = (
            "Noch keine Kennzeichen registriert."
        )

    if len(content) > 3900:
        content = content[:3900] + "\n…"

    embed = discord.Embed(
        title="🚘 Kennzeichen-System",
        description=(
            "**Registriere dein persönliches Kennzeichen.**\n\n"
            "• Jeder User darf **ein** Kennzeichen besitzen.\n"
            "• Der Buchstaben-/Namensbereich darf mehrfach vorkommen.\n"
            "• **Die Nummer darf serverweit nur einmal vorkommen.**\n"
            "• Nach dem Löschen wird die Nummer sofort wieder frei.\n\n"
            "**Beispiele**\n"
            "✅ `RLP 01`\n"
            "❌ `RY 01` wenn `01` bereits vergeben ist\n"
            "✅ `RY 02`"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📋 Aktuelle Kennzeichen",
        value=content,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        PlateView(),
        "license_plates"
    )


# ============================================================
# TEAM-REGISTRIERUNG
# ============================================================

class TeamModal(
    discord.ui.Modal,
    title="Team-Registrierung"
):

    name = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=50,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(
            interaction.user.id
        )

        data["team_members"][user_id] = {
            "name": str(
                self.name.value
            ).strip(),
            "registered_at": now_text()
        }

        # WICHTIG:
        # HIER WIRD KEINE ROLLE VERGEBEN.
        save_data()

        await interaction.response.send_message(
            "✅ Du wurdest erfolgreich registriert.",
            ephemeral=True
        )

        await send_team_panel()


class TeamView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Registrieren",
        style=discord.ButtonStyle.success,
        emoji="👥",
        custom_id="rlp_team_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            TeamModal()
        )


async def send_team_panel():

    channel = get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if channel is None:
        return

    members = data.get(
        "team_members",
        {}
    )

    if members:

        lines = []

        for user_id, info in members.items():

            name = info.get(
                "name",
                "Unbekannt"
            )

            lines.append(
                f"• <@{user_id}> — **{name}**"
            )

        content = "\n".join(lines)

        if len(content) > 3900:
            content = content[:3900] + "\n…"

    else:

        content = (
            "Noch keine Team-Registrierungen."
        )

    embed = discord.Embed(
        title="👥 Team-Registrierung",
        description=(
            "Hier kannst du dich für das Team registrieren.\n\n"
            "Die Registrierung speichert deine Angaben, "
            "vergibt aber **keine Rolle automatisch**."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Registrierte Mitglieder",
        value=content,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        TeamView(),
        "team"
    )


# ============================================================
# SCHICHT-SYSTEM
# ============================================================

def can_manage_shift(member):
    return member_has_role(
        member,
        SHIFT_PERMISSION_ROLE_ID
    )


class ShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="▶️",
        custom_id="rlp_shift_start"
    )
    async def start(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        if not can_manage_shift(member):

            await interaction.response.send_message(
                "❌ Du besitzt nicht die erforderliche Rolle.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        if user_id in data[
            "developer_shifts"
        ]:

            await interaction.response.send_message(
                "ℹ️ Du hast bereits eine aktive Schicht.",
                ephemeral=True
            )
            return

        role = get_role(
            interaction.guild,
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Die Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Schicht-Rolle nicht vergeben. "
                "Prüfe die Rollen-Hierarchie.",
                ephemeral=True
            )
            return

        started = now_text()

        data["developer_shifts"][user_id] = {
            "started_at": started
        }

        save_data()

        await interaction.response.send_message(
            "🟢 Deine Schicht wurde gestartet.",
            ephemeral=True
        )

        await send_shift_panel()

        await send_shift_log(
            member,
            "start",
            started
        )

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="rlp_shift_end"
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        if not can_manage_shift(member):

            await interaction.response.send_message(
                "❌ Du besitzt nicht die erforderliche Rolle.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        shift = data[
            "developer_shifts"
        ].get(user_id)

        if not shift:

            await interaction.response.send_message(
                "ℹ️ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        role = get_role(
            interaction.guild,
            DEVELOPER_SHIFT_ROLE_ID
        )

        try:

            if role and role in member.roles:

                await member.remove_roles(
                    role,
                    reason="Developer-Schicht beendet"
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Schicht-Rolle nicht entfernen.",
                ephemeral=True
            )
            return

        ended = now_text()
        started = shift.get(
            "started_at",
            "Unbekannt"
        )

        del data[
            "developer_shifts"
        ][user_id]

        save_data()

        await interaction.response.send_message(
            "🔴 Deine Schicht wurde beendet.",
            ephemeral=True
        )

        await send_shift_panel()

        await send_shift_log(
            member,
            "end",
            ended,
            started
        )


async def send_shift_log(
    member,
    action,
    timestamp,
    started=None
):

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    # Falls du einen separaten Log-Kanal möchtest,
    # kann hier später einfach die Channel-ID geändert werden.
    log_channel = channel

    if log_channel is None:
        return

    if action == "start":

        embed = discord.Embed(
            title="🟢 Schicht gestartet",
            description=(
                f"{member.mention} hat eine "
                "**Developer-Schicht gestartet.**"
            ),
            color=discord.Color.green(),
            timestamp=now()
        )

        embed.add_field(
            name="Start",
            value=timestamp,
            inline=False
        )

    else:

        embed = discord.Embed(
            title="🔴 Schicht beendet",
            description=(
                f"{member.mention} hat die "
                "**Developer-Schicht beendet.**"
            ),
            color=discord.Color.red(),
            timestamp=now()
        )

        embed.add_field(
            name="Start",
            value=started or "Unbekannt",
            inline=True
        )

        embed.add_field(
            name="Ende",
            value=timestamp,
            inline=True
        )

    # Log als normale Nachricht.
    # Das Panel-System erkennt es NICHT als Panel.
    await log_channel.send(
        embed=embed
    )


async def send_shift_panel():

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    active = data.get(
        "developer_shifts",
        {}
    )

    if active:

        lines = []

        for user_id, info in active.items():

            started = info.get(
                "started_at",
                "Unbekannt"
            )

            lines.append(
                f"🟢 <@{user_id}> — seit `{started}`"
            )

        content = "\n".join(lines)

    else:

        content = (
            "🟢 Aktuell ist niemand auf Schicht."
        )

    embed = discord.Embed(
        title="⏱️ Developer-Schichten",
        description=(
            "Über dieses Panel können berechtigte "
            "Developer ihre Schicht starten und beenden.\n\n"
            f"**Berechtigungsrolle:** <@&{SHIFT_PERMISSION_ROLE_ID}>\n"
            f"**Aktive Schichtrolle:** <@&{DEVELOPER_SHIFT_ROLE_ID}>"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Aktive Schichten",
        value=content,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        ShiftView(),
        "shifts"
    )


# ============================================================
# DEVELOPER TASKS
# ============================================================

class TaskModal(
    discord.ui.Modal,
    title="Developer Task"
):

    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        data[
            "developer_task_counter"
        ] += 1

        task_id = data[
            "developer_task_counter"
        ]

        data[
            "developer_tasks"
        ][str(task_id)] = {
            "task": str(
                self.task.value
            ),
            "creator": interaction.user.id,
            "created_at": now_text(),
            "status": "offen"
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Task **#{task_id}** erstellt.",
            ephemeral=True
        )

        await send_task_panel()


class TaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Task erstellen",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="rlp_task_create"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            TaskModal()
        )


async def send_task_panel():

    channel = get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    tasks_data = data.get(
        "developer_tasks",
        {}
    )

    if not tasks_data:

        content = (
            "Noch keine Aufgaben vorhanden."
        )

    else:

        lines = []

        for task_id, info in tasks_data.items():

            status = info.get(
                "status",
                "offen"
            )

            emoji = (
                "🟢"
                if status == "erledigt"
                else "🟡"
            )

            lines.append(
                f"{emoji} **#{task_id}** — "
                f"{info.get('task', 'Keine Beschreibung')}"
            )

        content = "\n".join(lines)

        if len(content) > 3900:
            content = content[:3900] + "\n…"

    embed = discord.Embed(
        title="🛠️ Developer Task Center",
        description=(
            "Hier können neue Developer-Aufgaben "
            "erstellt und angezeigt werden."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Aufgaben",
        value=content,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        TaskView(),
        "tasks"
    )


# ============================================================
# BEWERBUNG
# ============================================================

class ApplicationModal(
    discord.ui.Modal,
    title="Developer Bewerbung"
):

    reason = discord.ui.TextInput(
        label="Warum möchtest du Developer werden?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    experience = discord.ui.TextInput(
        label="Welche Erfahrung hast du?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = get_channel(
            REVIEW_CHANNEL_ID
        )

        if channel is None:
            channel = get_channel(
                APPLICATION_CHANNEL_ID
            )

        if channel is None:

            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🧑‍💻 Neue Developer-Bewerbung",
            color=discord.Color.orange(),
            timestamp=now()
        )

        embed.add_field(
            name="Bewerber",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Warum Developer?",
            value=str(
                self.reason.value
            ),
            inline=False
        )

        embed.add_field(
            name="Erfahrung",
            value=str(
                self.experience.value
            ),
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer Bewerbung",
        style=discord.ButtonStyle.primary,
        emoji="🧑‍💻",
        custom_id="rlp_application"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ApplicationModal()
        )


async def send_application_panel():

    channel = get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🧑‍💻 Developer Bewerbung",
        description=(
            "Du möchtest Teil des Developer-Teams werden?\n\n"
            "Klicke auf den Button und fülle die Bewerbung "
            "vollständig aus."
        ),
        color=discord.Color.blurple()
    )

    await upsert_panel(
        channel,
        embed,
        ApplicationView(),
        "application"
    )


# ============================================================
# EMOJI-QUIZ
# ============================================================

QUIZZES = [
    {
        "emoji": "🇩🇪",
        "question": "Wie viele Bundesländer hat Deutschland?",
        "answers": ["16", "sechzehn"]
    },
    {
        "emoji": "🗼",
        "question": "Welche Stadt wird durch den Eiffelturm dargestellt?",
        "answers": ["paris"]
    },
    {
        "emoji": "🍕🇮🇹",
        "question": "Aus welchem Land stammt die Pizza ursprünglich?",
        "answers": ["italien", "italy"]
    },
    {
        "emoji": "🌍",
        "question": "Wie heißt der Planet, auf dem wir leben?",
        "answers": ["erde", "earth"]
    },
    {
        "emoji": "☀️",
        "question": "Wie heißt unser Stern?",
        "answers": ["sonne", "sun"]
    },
    {
        "emoji": "🐘",
        "question": "Welches Tier ist für seinen langen Rüssel bekannt?",
        "answers": ["elefant", "elefant"]
    },
    {
        "emoji": "🏰🇫🇷",
        "question": "In welchem Land liegt Paris?",
        "answers": ["frankreich", "france"]
    },
    {
        "emoji": "🚗",
        "question": "Wie viele Räder hat ein normales Auto?",
        "answers": ["4", "vier"]
    },
    {
        "emoji": "🌊",
        "question": "Wie heißt der größte Ozean der Erde?",
        "answers": ["pazifik", "pazifischer ozean"]
    },
    {
        "emoji": "🪐",
        "question": "Welcher Planet ist für seine auffälligen Ringe bekannt?",
        "answers": ["saturn"]
    }
]

quiz_pool = []


def refill_quiz():
    global quiz_pool

    quiz_pool = QUIZZES.copy()
    random.shuffle(quiz_pool)


async def clear_quiz_channel():

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    try:

        async for message in channel.history(
            limit=None
        ):
            await safe_delete(message)

    except Exception as error:
        print(
            f"[QUIZ] Fehler beim Leeren: {error}"
        )


async def send_new_quiz():

    global quiz_message_id
    global current_quiz

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    async with quiz_lock:

        if not quiz_pool:
            refill_quiz()

        quiz = quiz_pool.pop()

        current_quiz = quiz

        embed = discord.Embed(
            title="🧩 RLP Emoji Quiz",
            description=(
                f"# {quiz['emoji']}\n\n"
                f"### {quiz['question']}\n\n"
                "💬 **Schreibe deine Antwort in den Kanal.**\n"
                "⏱️ Der Quiz-Kanal wird automatisch sauber gehalten."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="RLP • Emoji Quiz"
        )

        message = await channel.send(
            embed=embed
        )

        quiz_message_id = message.id


async def quiz_cleanup_loop():

    global quiz_message_id

    await bot.wait_until_ready()

    while not bot.is_closed():

        channel = get_channel(
            QUIZ_CHANNEL_ID
        )

        if channel is not None:

            try:

                async with quiz_lock:

                    keep_id = quiz_message_id

                    async for message in channel.history(
                        limit=None
                    ):

                        if (
                            keep_id is not None
                            and message.id == keep_id
                        ):
                            continue

                        await safe_delete(message)

            except Exception as error:
                print(
                    f"[QUIZ CLEANUP] {error}"
                )

        await asyncio.sleep(5)


async def handle_quiz_message(message):

    global quiz_message_id
    global current_quiz

    if message.author.bot:
        return

    async with quiz_lock:

        if current_quiz is None:
            return

        if (
            quiz_message_id is None
            or message.id == quiz_message_id
        ):
            return

        answer = (
            message.content
            .strip()
            .lower()
        )

        correct_answers = [
            str(answer).lower()
            for answer in current_quiz[
                "answers"
            ]
        ]

        if answer not in correct_answers:
            return

        user_id = str(
            message.author.id
        )

        data["quiz_scores"][user_id] = (
            data["quiz_scores"].get(
                user_id,
                0
            ) + 1
        )

        save_data()

        old_message_id = quiz_message_id

        try:

            await message.delete()

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        if old_message_id:

            try:

                old_message = await message.channel.fetch_message(
                    old_message_id
                )

                await old_message.delete()

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        quiz_message_id = None
        current_quiz = None

        await asyncio.sleep(1)

        await send_new_quiz()


# ============================================================
# SUPPORT-LOG
# ============================================================

support_cases = {}


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if member.bot:
        return

    # Betritt Support
    if (
        after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):

        data["support_case_counter"] += 1

        case_id = data[
            "support_case_counter"
        ]

        support_cases[str(member.id)] = {
            "case": case_id,
            "started_at": now_text()
        }

        save_data()

        log_channel = get_channel(
            SUPPORT_LOG_CHANNEL_ID
        )

        if log_channel:

            embed = discord.Embed(
                title="📞 Support gestartet",
                description=(
                    f"{member.mention} ist dem Support beigetreten."
                ),
                color=discord.Color.green(),
                timestamp=now()
            )

            embed.add_field(
                name="Fall",
                value=f"#{case_id}",
                inline=True
            )

            embed.add_field(
                name="Start",
                value=now_text(),
                inline=True
            )

            await log_channel.send(
                embed=embed
            )

    # Verlässt Support
    if (
        before.channel
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):

        case = support_cases.pop(
            str(member.id),
            None
        )

        if case:

            log_channel = get_channel(
                SUPPORT_LOG_CHANNEL_ID
            )

            if log_channel:

                embed = discord.Embed(
                    title="📞 Support beendet",
                    description=(
                        f"{member.mention} hat den Support verlassen."
                    ),
                    color=discord.Color.red(),
                    timestamp=now()
                )

                embed.add_field(
                    name="Fall",
                    value=f"#{case['case']}",
                    inline=True
                )

                embed.add_field(
                    name="Start",
                    value=case.get(
                        "started_at",
                        "Unbekannt"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="Ende",
                    value=now_text(),
                    inline=False
                )

                await log_channel.send(
                    embed=embed
                )


# ============================================================
# NACHRICHTEN
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if (
        message.guild
        and message.guild.id == GUILD_ID
        and message.channel.id == QUIZ_CHANNEL_ID
    ):

        await handle_quiz_message(
            message
        )

        return

    await bot.process_commands(
        message
    )


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    if str(member.id) in [
        str(x)
        for x in data.get(
            "nametag_opt_out",
            []
        )
    ]:
        return

    await apply_nametag(
        member
    )


# ============================================================
# COMMANDS
# ============================================================

@bot.command(name="score")
async def score(ctx):

    user_id = str(
        ctx.author.id
    )

    value = data[
        "quiz_scores"
    ].get(
        user_id,
        0
    )

    await ctx.send(
        f"🧩 {ctx.author.mention} hat "
        f"**{value} Punkte** im Emoji-Quiz.",
        delete_after=10
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    global startup_finished
    global quiz_cleanup_task

    if startup_finished:
        return

    print(
        f"[START] Eingeloggt als {bot.user}"
    )

    guild = get_guild()

    if guild is None:

        print(
            "[START] Server nicht gefunden."
        )

        return

    load_data()

    # --------------------------------------------------------
    # Persistent Views
    # --------------------------------------------------------

    bot.add_view(
        NametagView()
    )

    bot.add_view(
        PlateView()
    )

    bot.add_view(
        TeamView()
    )

    bot.add_view(
        ShiftView()
    )

    bot.add_view(
        TaskView()
    )

    bot.add_view(
        ApplicationView()
    )

    # --------------------------------------------------------
    # Alte Panels sauber entfernen
    # --------------------------------------------------------

    await delete_old_panels()

    # --------------------------------------------------------
    # Quiz sauber starten
    # --------------------------------------------------------

    await clear_quiz_channel()

    refill_quiz()

    await send_new_quiz()

    # --------------------------------------------------------
    # Panels erstellen
    # --------------------------------------------------------

    await send_nametag_panel()

    await send_team_panel()

    await send_license_plate_panel()

    await send_shift_panel()

    await send_task_panel()

    await send_application_panel()

    # --------------------------------------------------------
    # Nametags wiederherstellen
    # --------------------------------------------------------

    opt_out = {
        str(x)
        for x in data.get(
            "nametag_opt_out",
            []
        )
    }

    for member in guild.members:

        if member.bot:
            continue

        if str(member.id) in opt_out:
            continue

        await apply_nametag(
            member
        )

    # --------------------------------------------------------
    # Aktive Schichten wiederherstellen
    # --------------------------------------------------------

    shift_role = get_role(
        guild,
        DEVELOPER_SHIFT_ROLE_ID
    )

    if shift_role:

        for user_id in list(
            data.get(
                "developer_shifts",
                {}
            ).keys()
        ):

            try:

                member = guild.get_member(
                    int(user_id)
                )

                if member is None:
                    continue

                if shift_role not in member.roles:

                    await member.add_roles(
                        shift_role,
                        reason=(
                            "Aktive Schicht "
                            "nach Bot-Neustart wiederhergestellt"
                        )
                    )

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

    # --------------------------------------------------------
    # Quiz Cleanup starten
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
        "[START] Bot vollständig gestartet."
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

    print(
        f"[COMMAND] {error}"
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

    bot.run(TOKEN)
