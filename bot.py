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

# Rolle, die Schichten starten/beenden darf
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904

# Rolle, die während einer aktiven Schicht vergeben wird
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

# Wie im alten System kann diese Rolle auch für Support verwendet werden.
SUPPORT_ROLE_ID = DEVELOPER_SHIFT_ROLE_ID

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"


# ============================================================
# BOT
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

data_lock = asyncio.Lock()
license_lock = asyncio.Lock()
quiz_lock = asyncio.Lock()

startup_finished = False
quiz_cleanup_task = None
current_quiz_message_id = None


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


def now_string():
    return utc_now().strftime("%d.%m.%Y %H:%M")


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = json.loads(json.dumps(DEFAULT_DATA))
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        data = json.loads(json.dumps(DEFAULT_DATA))

        if isinstance(loaded, dict):
            for key, value in loaded.items():
                data[key] = value

    except Exception as e:
        print(f"[DATA] Fehler beim Laden: {e}")
        data = json.loads(json.dumps(DEFAULT_DATA))


def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


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


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except Exception as e:
        print(f"[SEND] Fehler: {e}")
        return None


# ============================================================
# KENNZEICHEN
# ============================================================

def normalize_plate_name(value):
    value = value.upper().strip()
    value = " ".join(value.split())
    return value


def get_plate_number(plate):
    parts = plate.split()

    if not parts:
        return ""

    return parts[-1].upper()


def get_user_plate(user_id):
    user_id = str(user_id)

    entry = data.get("license_plates", {}).get(user_id)

    if not entry:
        return None

    if isinstance(entry, str):
        return entry

    return entry.get("plate")


def find_plate_by_number(number):
    number = str(number).upper().strip()

    for user_id, entry in data.get("license_plates", {}).items():
        if isinstance(entry, str):
            plate = entry
        else:
            plate = entry.get("plate", "")

        if get_plate_number(plate) == number:
            return user_id, plate

    return None, None


def is_number_taken(number):
    user_id, plate = find_plate_by_number(number)
    return user_id is not None


def parse_plate(text):
    text = normalize_plate_name(text)

    parts = text.split()

    if len(parts) < 2:
        return None, None

    name = " ".join(parts[:-1])
    number = parts[-1]

    if not name or not number:
        return None, None

    return name, number


# ============================================================
# PANEL SYSTEM
# ============================================================

PANEL_PREFIX = "RLP_PANEL:"


async def delete_old_panels():
    guild = get_guild()

    if guild is None:
        return

    panel_channels = {
        TEAM_REGISTER_CHANNEL_ID,
        DEVELOPER_SHIFT_CHANNEL_ID,
        DEVELOPER_TASK_CHANNEL_ID,
        APPLICATION_CHANNEL_ID,
        NICKNAME_CHANNEL_ID
    }

    for channel_id in panel_channels:
        channel = guild.get_channel(channel_id)

        if channel is None:
            continue

        try:
            async for message in channel.history(limit=None):
                if message.author.id != bot.user.id:
                    continue

                is_panel = False

                for embed in message.embeds:
                    footer = embed.footer.text or ""

                    if footer.startswith(PANEL_PREFIX):
                        is_panel = True
                        break

                if is_panel:
                    await safe_delete(message)

        except Exception as e:
            print(f"[PANEL] Fehler beim Löschen alter Panels: {e}")


async def upsert_panel(channel, embed, view, panel_name):
    if channel is None:
        return

    embed.set_footer(text=f"{PANEL_PREFIX}{panel_name}")

    found = None

    try:
        async for message in channel.history(limit=None):
            if message.author.id != bot.user.id:
                continue

            for old_embed in message.embeds:
                footer = old_embed.footer.text or ""

                if footer == f"{PANEL_PREFIX}{panel_name}":
                    if found is None:
                        found = message
                    else:
                        await safe_delete(message)

                    break

    except Exception as e:
        print(f"[PANEL] Suche fehlgeschlagen: {e}")

    try:
        if found:
            await found.edit(embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)

    except Exception as e:
        print(f"[PANEL] Fehler beim Panel: {e}")


# ============================================================
# NAMETAG
# ============================================================

class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag aktivieren",
        style=discord.ButtonStyle.success,
        custom_id="rlp_nametag_enable"
    )
    async def enable(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild

        if guild is None:
            return

        member = guild.get_member(interaction.user.id)

        if member is None:
            return

        role = guild.get_role(NAMETAG_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "Die Nametag-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        data["nametag_opt_out"] = [
            x for x in data["nametag_opt_out"]
            if str(x) != str(member.id)
        ]

        save_data()

        try:
            if not member.display_name.startswith(NAMETAG):
                new_name = NAMETAG + member.display_name

                if len(new_name) > 32:
                    new_name = new_name[:32]

                await member.edit(nick=new_name)

            await member.add_roles(role)

            await interaction.response.send_message(
                "Dein Nametag wurde aktiviert.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich habe keine Berechtigung, deinen Namen oder die Rolle zu ändern.",
                ephemeral=True
            )


    @discord.ui.button(
        label="Nametag deaktivieren",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_nametag_disable"
    )
    async def disable(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild

        if guild is None:
            return

        member = guild.get_member(interaction.user.id)

        if member is None:
            return

        data["nametag_opt_out"].append(member.id)
        data["nametag_opt_out"] = list(
            set(data["nametag_opt_out"])
        )

        save_data()

        role = guild.get_role(NAMETAG_ROLE_ID)

        try:
            if role:
                await member.remove_roles(role)

            current_name = member.display_name

            if current_name.startswith(NAMETAG):
                new_name = current_name[len(NAMETAG):]

                if not new_name:
                    new_name = member.name

                await member.edit(nick=new_name[:32])

            await interaction.response.send_message(
                "Dein Nametag wurde deaktiviert.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich habe keine Berechtigung, deinen Namen oder die Rolle zu ändern.",
                ephemeral=True
            )


async def send_nametag_panel():
    channel = get_channel(NICKNAME_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Hier kannst du deinen **RLP-Nametag** aktivieren oder deaktivieren.\n\n"
            f"Nametag: `{NAMETAG}`"
        ),
        color=discord.Color.blue()
    )

    await upsert_panel(
        channel,
        embed,
        NametagView(),
        "nametag"
    )


# ============================================================
# KENNZEICHEN VIEW
# ============================================================

class PlateRemoveConfirmView(discord.ui.View):

    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id

    @discord.ui.button(
        label="Kennzeichen löschen",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Diese Schaltfläche gehört nicht dir.",
                ephemeral=True
            )
            return

        async with license_lock:
            user_id = str(interaction.user.id)

            if user_id not in data["license_plates"]:
                await interaction.response.send_message(
                    "Du hast kein Kennzeichen registriert.",
                    ephemeral=True
                )
                return

            old_plate = data["license_plates"][user_id]

            del data["license_plates"][user_id]
            save_data()

        await interaction.response.edit_message(
            content=(
                f"Das Kennzeichen `{old_plate}` wurde gelöscht.\n"
                "Die Nummer ist jetzt wieder frei."
            ),
            embed=None,
            view=None
        )

        await send_license_plate_panel()


class PlateRemoveView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Mein Kennzeichen löschen",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_plate_remove"
    )
    async def remove(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        plate = get_user_plate(interaction.user.id)

        if not plate:
            await interaction.response.send_message(
                "Du hast aktuell kein Kennzeichen registriert.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Kennzeichen löschen",
            description=(
                f"Dein aktuelles Kennzeichen ist:\n\n"
                f"**`{plate}`**\n\n"
                "Möchtest du es wirklich löschen?"
            ),
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=PlateRemoveConfirmView(interaction.user.id),
            ephemeral=True
        )


class PlateRegistrationModal(discord.ui.Modal, title="Kennzeichen registrieren"):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        min_length=2,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        async with license_lock:

            user_id = str(interaction.user.id)

            # Jeder User darf nur ein Kennzeichen haben.
            existing = get_user_plate(interaction.user.id)

            if existing:
                await interaction.response.send_message(
                    f"Du hast bereits das Kennzeichen `{existing}` registriert.\n"
                    "Lösche es zuerst, wenn du ein anderes verwenden möchtest.",
                    ephemeral=True
                )
                return

            plate_text = normalize_plate(self.plate.value)

            name, number = parse_plate(plate_text)

            if name is None or number is None:
                await interaction.response.send_message(
                    "Ungültiges Format.\n"
                    "Beispiel: `RLP 01`",
                    ephemeral=True
                )
                return

            # Nur die Nummer muss einzigartig sein.
            #
            # Deshalb:
            # RLP 01 -> erlaubt
            # RY 01  -> NICHT erlaubt
            # RLP 02 -> erlaubt
            #
            # Der Name/Kürzel darf mehrfach vorkommen.

            existing_user_id, existing_plate = find_plate_by_number(number)

            if existing_user_id is not None:
                await interaction.response.send_message(
                    f"Die Nummer **{number}** ist bereits vergeben.\n"
                    "Jede Nummer darf nur einmal verwendet werden.",
                    ephemeral=True
                )
                return

            data["license_plates"][user_id] = plate_text
            save_data()

        await interaction.response.send_message(
            f"Dein Kennzeichen **`{plate_text}`** wurde erfolgreich registriert.",
            ephemeral=True
        )

        await send_license_plate_panel()


class LicensePlateView(discord.ui.View):

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
        if get_user_plate(interaction.user.id):
            await interaction.response.send_message(
                "Du hast bereits ein Kennzeichen registriert.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            PlateRegistrationModal()
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
        plate = get_user_plate(interaction.user.id)

        if not plate:
            await interaction.response.send_message(
                "Du hast aktuell kein Kennzeichen.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Kennzeichen löschen",
            description=(
                f"Dein Kennzeichen:\n\n"
                f"**`{plate}`**\n\n"
                "Beim Löschen wird die Nummer wieder für andere Mitglieder freigegeben."
            ),
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=PlateRemoveConfirmView(interaction.user.id),
            ephemeral=True
        )


async def send_license_plate_panel():
    channel = get_channel(TEAM_REGISTER_CHANNEL_ID)

    if channel is None:
        return

    entries = []

    for user_id, entry in data.get("license_plates", {}).items():

        if isinstance(entry, str):
            plate = entry
        else:
            plate = entry.get("plate", "")

        if not plate:
            continue

        member = channel.guild.get_member(int(user_id))

        if member:
            entries.append(
                f"`{plate}` — {member.mention}"
            )
        else:
            entries.append(
                f"`{plate}` — <@{user_id}>"
            )

    entries.sort(key=lambda x: x.lower())

    if entries:
        plate_text = "\n".join(entries)
    else:
        plate_text = "Noch keine Kennzeichen registriert."

    if len(plate_text) > 3800:
        plate_text = plate_text[:3800] + "\n…"

    embed = discord.Embed(
        title="🚘 Kennzeichen-System",
        description=(
            "Registriere hier dein Kennzeichen.\n\n"
            "**Wichtig:**\n"
            "• Jeder User kann nur ein Kennzeichen haben.\n"
            "• Der Buchstaben-/Namensbereich darf mehrfach vorkommen.\n"
            "• **Die Nummer darf serverweit nur einmal vorkommen.**\n\n"
            "Beispiele:\n"
            "✅ `RLP 01`\n"
            "❌ `RY 01` wenn `01` bereits vergeben ist\n"
            "✅ `RY 02`"
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📋 Registrierte Kennzeichen",
        value=plate_text,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        LicensePlateView(),
        "license_plates"
    )


# ============================================================
# TEAM REGISTRIERUNG
# ============================================================

class TeamRegisterModal(discord.ui.Modal, title="Team registrieren"):

    name = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        data["team_members"][user_id] = {
            "name": str(self.name.value).strip(),
            "registered_at": now_string()
        }

        save_data()

        await interaction.response.send_message(
            "Du wurdest erfolgreich für das Team registriert.",
            ephemeral=True
        )

        await send_team_panel()


class TeamRegistrationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Für Team registrieren",
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
            TeamRegisterModal()
        )


async def send_team_panel():

    channel = get_channel(TEAM_REGISTER_CHANNEL_ID)

    if channel is None:
        return

    members = data.get("team_members", {})

    if members:
        lines = []

        for user_id, info in members.items():
            name = info.get("name", "Unbekannt")
            lines.append(
                f"• <@{user_id}> — **{name}**"
            )

        member_text = "\n".join(lines)

        if len(member_text) > 3800:
            member_text = member_text[:3800] + "\n…"
    else:
        member_text = "Noch keine Registrierungen."

    embed = discord.Embed(
        title="👥 Team-Registrierung",
        description=(
            "Hier kannst du dich für das Team registrieren."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Registrierte Mitglieder",
        value=member_text,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        TeamRegistrationView(),
        "team"
    )


# ============================================================
# SCHICHTEN
# ============================================================

def has_shift_permission(member):
    return any(
        role.id == SHIFT_PERMISSION_ROLE_ID
        for role in member.roles
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
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            return

        if not has_shift_permission(member):
            await interaction.response.send_message(
                "Du hast nicht die benötigte Rolle, um eine Schicht zu starten.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        if user_id in data["developer_shifts"]:
            await interaction.response.send_message(
                "Du hast bereits eine aktive Schicht.",
                ephemeral=True
            )
            return

        shift_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if shift_role is None:
            await interaction.response.send_message(
                "Die Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                shift_role,
                reason="Developer-Schicht gestartet"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich kann dir die Schicht-Rolle nicht geben. "
                "Prüfe die Rollen-Hierarchie.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
            "started_at": now_string()
        }

        save_data()

        await interaction.response.send_message(
            "Deine Schicht wurde gestartet.",
            ephemeral=True
        )

        await send_shift_panel()

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="rlp_shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            return

        if not has_shift_permission(member):
            await interaction.response.send_message(
                "Du hast nicht die benötigte Rolle, um eine Schicht zu beenden.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        if user_id not in data["developer_shifts"]:
            await interaction.response.send_message(
                "Du hast aktuell keine aktive Schicht.",
                ephemeral=True
            )
            return

        shift_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        try:
            if shift_role:
                await member.remove_roles(
                    shift_role,
                    reason="Developer-Schicht beendet"
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich kann dir die Schicht-Rolle nicht entfernen. "
                "Prüfe die Rollen-Hierarchie.",
                ephemeral=True
            )
            return

        started_at = data["developer_shifts"][user_id].get(
            "started_at",
            "Unbekannt"
        )

        del data["developer_shifts"][user_id]
        save_data()

        await interaction.response.send_message(
            f"Deine Schicht wurde beendet.\n"
            f"Start: `{started_at}`\n"
            f"Ende: `{now_string()}`",
            ephemeral=True
        )

        await send_shift_panel()


async def send_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    active = data.get("developer_shifts", {})

    if active:
        lines = []

        for user_id, info in active.items():
            started = info.get("started_at", "Unbekannt")

            lines.append(
                f"🟢 <@{user_id}> — seit `{started}`"
            )

        active_text = "\n".join(lines)

    else:
        active_text = "Aktuell ist niemand auf Schicht."

    embed = discord.Embed(
        title="⏱️ Developer-Schichten",
        description=(
            "Nur Mitglieder mit der erforderlichen Berechtigungsrolle "
            "können eine Schicht starten oder beenden."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Aktive Schichten",
        value=active_text,
        inline=False
    )

    embed.add_field(
        name="Berechtigungsrolle",
        value=f"<@&{SHIFT_PERMISSION_ROLE_ID}>",
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

class DeveloperTaskModal(discord.ui.Modal, title="Developer Task erstellen"):

    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        data["developer_task_counter"] += 1

        task_id = data["developer_task_counter"]

        data["developer_tasks"][str(task_id)] = {
            "task": str(self.task.value),
            "creator": interaction.user.id,
            "created_at": now_string(),
            "status": "offen"
        }

        save_data()

        await interaction.response.send_message(
            f"Task **#{task_id}** wurde erstellt.",
            ephemeral=True
        )

        await send_developer_tasks()


class DeveloperTaskView(discord.ui.View):

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
            DeveloperTaskModal()
        )


async def send_developer_tasks():

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    tasks = data.get("developer_tasks", {})

    if tasks:
        lines = []

        for task_id, info in tasks.items():

            status = info.get("status", "offen")
            task = info.get("task", "Keine Beschreibung")

            emoji = "🟢" if status == "erledigt" else "🟡"

            lines.append(
                f"{emoji} **#{task_id}** — {task}"
            )

        task_text = "\n".join(lines)

        if len(task_text) > 3800:
            task_text = task_text[:3800] + "\n…"

    else:
        task_text = "Noch keine Tasks."

    embed = discord.Embed(
        title="🛠️ Developer Task Center",
        description="Hier können Developer Aufgaben erstellen und verwalten.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Aufgaben",
        value=task_text,
        inline=False
    )

    await upsert_panel(
        channel,
        embed,
        DeveloperTaskView(),
        "tasks"
    )


# ============================================================
# BEWERBUNGEN
# ============================================================

class ApplicationModal(discord.ui.Modal, title="Developer Bewerbung"):

    reason = discord.ui.TextInput(
        label="Warum möchtest du Developer werden?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    experience = discord.ui.TextInput(
        label="Erfahrung",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(APPLICATION_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "Der Bewerbungs-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🧑‍💻 Neue Developer-Bewerbung",
            color=discord.Color.orange(),
            timestamp=utc_now()
        )

        embed.add_field(
            name="Bewerber",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="Warum Developer?",
            value=str(self.reason.value),
            inline=False
        )

        embed.add_field(
            name="Erfahrung",
            value=str(self.experience.value),
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "Deine Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class ApplicationView(discord.ui.View):

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

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🧑‍💻 Developer Bewerbung",
        description=(
            "Du möchtest Teil des Developer-Teams werden?\n\n"
            "Klicke unten auf den Button und fülle die Bewerbung aus."
        ),
        color=discord.Color.blue()
    )

    await upsert_panel(
        channel,
        embed,
        ApplicationView(),
        "application"
    )


# ============================================================
# QUIZ
# ============================================================

QUIZZES = [
    {
        "question": "🇩🇪 Wie viele Bundesländer hat Deutschland?",
        "answers": ["16"],
        "display": "16"
    },
    {
        "question": "🌍 Wie heißt die Hauptstadt von Frankreich?",
        "answers": ["paris"],
        "display": "Paris"
    },
    {
        "question": "🚗 Wie viele Räder hat ein normales Auto?",
        "answers": ["4", "vier"],
        "display": "4"
    },
    {
        "question": "🌊 Wie heißt der größte Ozean der Erde?",
        "answers": ["pazifik", "pazifischer ozean"],
        "display": "Pazifik"
    },
    {
        "question": "🪐 Wie heißt der Planet, auf dem wir leben?",
        "answers": ["erde"],
        "display": "Erde"
    },
    {
        "question": "☀️ Wie heißt unser Stern?",
        "answers": ["sonne"],
        "display": "Sonne"
    }
]

quiz_pool = []


def refill_quiz():
    global quiz_pool

    quiz_pool = QUIZZES.copy()
    random.shuffle(quiz_pool)


async def clean_quiz_channel():

    channel = get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    async for message in channel.history(limit=None):
        await safe_delete(message)


async def send_new_quiz(channel=None):

    global current_quiz_message_id

    if channel is None:
        channel = get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    async with quiz_lock:

        if not quiz_pool:
            refill_quiz()

        quiz = quiz_pool.pop()

        embed = discord.Embed(
            title="🧠 Emoji Quiz",
            description=(
                f"## {quiz['question']}\n\n"
                "Schreibe deine Antwort in den Kanal."
            ),
            color=discord.Color.blue()
        )

        embed.set_footer(
            text="RLP • Aktuelles Quiz"
        )

        message = await channel.send(
            embed=embed
        )

        current_quiz_message_id = message.id


async def quiz_cleanup_loop():

    global current_quiz_message_id

    await bot.wait_until_ready()

    while not bot.is_closed():

        channel = get_channel(QUIZ_CHANNEL_ID)

        if channel is not None:

            async with quiz_lock:

                keep_id = current_quiz_message_id

                try:
                    async for message in channel.history(limit=None):

                        if keep_id is not None and message.id == keep_id:
                            continue

                        await safe_delete(message)

                except Exception as e:
                    print(f"[QUIZ CLEANUP] {e}")

        await asyncio.sleep(5)


# ============================================================
# SUPPORT
# ============================================================

support_cases = {}


@bot.event
async def on_voice_state_update(member, before, after):

    if member.bot:
        return

    # Support Voice betreten
    if (
        after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):
        data["support_case_counter"] += 1

        case_id = data["support_case_counter"]

        support_cases[str(member.id)] = {
            "case": case_id,
            "joined": now_string()
        }

        save_data()

        log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

        if log_channel:
            embed = discord.Embed(
                title="📞 Support",
                description=(
                    f"{member.mention} ist dem Support beigetreten."
                ),
                color=discord.Color.green(),
                timestamp=utc_now()
            )

            embed.add_field(
                name="Fall",
                value=f"#{case_id}"
            )

            await log_channel.send(embed=embed)

    # Support Voice verlassen
    if (
        before.channel
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):

        case = support_cases.pop(str(member.id), None)

        if case:

            log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

            if log_channel:
                embed = discord.Embed(
                    title="📞 Support beendet",
                    description=(
                        f"{member.mention} hat den Support verlassen."
                    ),
                    color=discord.Color.red(),
                    timestamp=utc_now()
                )

                embed.add_field(
                    name="Fall",
                    value=f"#{case['case']}"
                )

                await log_channel.send(embed=embed)


# ============================================================
# QUIZ NACHRICHTEN
# ============================================================

@bot.event
async def on_message(message):

    global current_quiz_message_id

    if message.author.bot:
        return

    # Quiz-Kanal:
    #
    # Die Cleanup-Schleife löscht alles alle 5 Sekunden.
    # Hier wird nur eine Antwort verarbeitet.
    if message.channel.id == QUIZ_CHANNEL_ID:

        async with quiz_lock:

            if (
                current_quiz_message_id is not None
                and message.id != current_quiz_message_id
            ):

                content = message.content.strip().lower()

                # Aktuelles Quiz herausfinden
                # anhand des aktuellen Pools ist das nicht zuverlässig,
                # deshalb wird die Frage aus dem letzten Embed gelesen.
                channel = message.channel

                try:
                    quiz_message = await channel.fetch_message(
                        current_quiz_message_id
                    )

                    if quiz_message.embeds:
                        description = (
                            quiz_message.embeds[0].description or ""
                        )

                        correct_quiz = None

                        for quiz in QUIZZES:

                            if quiz["question"] in description:
                                correct_quiz = quiz
                                break

                        if correct_quiz:

                            if content in [
                                x.lower()
                                for x in correct_quiz["answers"]
                            ]:

                                user_id = str(message.author.id)

                                data["quiz_scores"][user_id] = (
                                    data["quiz_scores"].get(user_id, 0) + 1
                                )

                                save_data()

                                await message.reply(
                                    f"✅ Richtig, {message.author.mention}!",
                                    delete_after=2
                                )

                                await safe_delete(quiz_message)

                                current_quiz_message_id = None

                                await asyncio.sleep(1)

                                await send_new_quiz(channel)

                except Exception as e:
                    print(f"[QUIZ] Antwortfehler: {e}")

        return

    await bot.process_commands(message)


# ============================================================
# COMMANDS
# ============================================================

@bot.command(name="score")
async def score_command(ctx):

    score = data["quiz_scores"].get(
        str(ctx.author.id),
        0
    )

    await ctx.send(
        f"🧠 {ctx.author.mention}, dein Quiz-Score ist **{score}**.",
        delete_after=10
    )


@bot.command(name="tasks")
async def tasks_command(ctx):

    if not isinstance(ctx.author, discord.Member):
        return

    if not has_shift_permission(ctx.author):
        await ctx.send(
            "Du hast keine Berechtigung für diesen Befehl.",
            delete_after=5
        )
        return

    await send_developer_tasks()

    await ctx.send(
        "Das Task-Panel wurde aktualisiert.",
        delete_after=5
    )


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    if member.id in data.get("nametag_opt_out", []):
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    try:
        await member.add_roles(
            role,
            reason="Automatischer Nametag"
        )

        name = member.display_name

        if not name.startswith(NAMETAG):

            new_name = NAMETAG + name

            if len(new_name) > 32:
                new_name = new_name[:32]

            await member.edit(
                nick=new_name
            )

    except discord.Forbidden:
        pass


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    global startup_finished
    global quiz_cleanup_task

    if startup_finished:
        return

    print(f"[START] Eingeloggt als {bot.user}")

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("[START] Server nicht gefunden.")
        return

    print(f"[START] Server: {guild.name}")

    load_data()

    # --------------------------------------------------------
    # Persistent Views registrieren
    # --------------------------------------------------------

    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(TeamRegistrationView())
    bot.add_view(ShiftView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(ApplicationView())

    # --------------------------------------------------------
    # Alte Panels einmalig entfernen
    # --------------------------------------------------------

    await delete_old_panels()

    # --------------------------------------------------------
    # Quiz-Kanal komplett sauber machen
    # --------------------------------------------------------

    await clean_quiz_channel()

    # --------------------------------------------------------
    # Quiz starten
    # --------------------------------------------------------

    refill_quiz()

    await send_new_quiz(
        get_channel(QUIZ_CHANNEL_ID)
    )

    # --------------------------------------------------------
    # Panels
    # --------------------------------------------------------

    await send_nametag_panel()
    await send_team_panel()
    await send_license_plate_panel()
    await send_shift_panel()
    await send_developer_tasks()
    await send_application_panel()

    # --------------------------------------------------------
    # Nametags wiederherstellen
    # --------------------------------------------------------

    for member in guild.members:

        if member.bot:
            continue

        if member.id in data.get("nametag_opt_out", []):
            continue

        role = guild.get_role(NAMETAG_ROLE_ID)

        if role is None:
            continue

        try:
            if role not in member.roles:
                await member.add_roles(
                    role,
                    reason="Nametag beim Bot-Start wiederherstellen"
                )

            if not member.display_name.startswith(NAMETAG):

                new_name = NAMETAG + member.display_name

                if len(new_name) > 32:
                    new_name = new_name[:32]

                await member.edit(
                    nick=new_name
                )

        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    # --------------------------------------------------------
    # Aktive Schichten wiederherstellen
    # --------------------------------------------------------

    shift_role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if shift_role:

        for user_id in list(
            data.get("developer_shifts", {}).keys()
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
                        reason="Aktive Schicht beim Bot-Start wiederherstellen"
                    )

            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

    startup_finished = True

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

    print("[START] Bot vollständig gestartet.")


# ============================================================
# FEHLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "Du hast keine Berechtigung für diesen Befehl.",
            delete_after=5
        )
        return

    print(f"[COMMAND ERROR] {error}")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gefunden."
        )

    load_data()

    print("[START] Bot wird gestartet...")

    bot.run(TOKEN)
