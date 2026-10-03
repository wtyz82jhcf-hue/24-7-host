import os
import json
import random
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.environ.get("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NICKNAME_CHANNEL_ID = 1555684071911202836
SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348
NAMETAG = "RLP "

SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

DATA_FILE = "bot_data.json"

PANEL_MARKER = "RLP_PANEL:"


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATEN
# =========================================================

DEFAULT_DATA = {
    "nametag_opt_out": [],
    "quiz_scores": {},
    "developer_shifts": {},
    "developer_tasks": {},
    "developer_task_counter": 0,
    "license_plates": {},
    "support_case_counter": 0
}

data = {}
startup_finished = False
quiz_cleanup_task = None

quiz_message_id = None
current_quiz = None
quiz_lock = asyncio.Lock()


# =========================================================
# DATENBANK
# =========================================================

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
                if key in data:
                    data[key] = value

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        data = json.loads(json.dumps(DEFAULT_DATA))

    save_data()


def save_data():
    try:
        temporary_file = DATA_FILE + ".tmp"

        with open(temporary_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temporary_file, DATA_FILE)

    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


def now_text():
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")


load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    guild = get_guild()

    if guild is None:
        return None

    return guild.get_channel(channel_id)


def get_role(role_id):
    guild = get_guild()

    if guild is None:
        return None

    return guild.get_role(role_id)


def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def get_panel_marker(message):
    if not message.embeds:
        return None

    embed = message.embeds[0]

    if not embed.footer:
        return None

    text = embed.footer.text or ""

    if text.startswith(PANEL_MARKER):
        return text

    return None


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except discord.Forbidden:
        print(f"[DISCORD] Keine Berechtigung für Channel {getattr(channel, 'id', '?')}")
    except discord.HTTPException as error:
        print(f"[DISCORD] Fehler beim Senden: {error}")

    return None


# =========================================================
# NAMETAG
# =========================================================

def is_nametag_opted_out(member_id):
    return str(member_id) in data["nametag_opt_out"]


def add_nametag_to_name(name):
    if name.startswith(NAMETAG):
        return name

    return NAMETAG + name


def remove_nametag_from_name(name):
    if name.startswith(NAMETAG):
        return name[len(NAMETAG):]

    return name


async def apply_nametag(member):
    if member.bot:
        return

    if is_nametag_opted_out(member.id):
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is not None and role not in member.roles:
        try:
            await member.add_roles(
                role,
                reason="RLP Nametag-System"
            )
        except discord.HTTPException as error:
            print(f"[NAMETAG] Rollenfehler bei {member}: {error}")

    current_name = member.nick or member.name

    if not current_name.startswith(NAMETAG):
        new_name = add_nametag_to_name(current_name)

        if len(new_name) > 32:
            new_name = new_name[:32]

        try:
            await member.edit(
                nick=new_name,
                reason="RLP Nametag-System"
            )
        except discord.HTTPException as error:
            print(f"[NAMETAG] Nickname-Fehler bei {member}: {error}")


async def remove_nametag(member):
    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is not None and role in member.roles:
        try:
            await member.remove_roles(
                role,
                reason="RLP Nametag entfernt"
            )
        except discord.HTTPException as error:
            print(f"[NAMETAG] Rollen-Entfernungsfehler: {error}")

    current_name = member.nick or member.name

    if current_name.startswith(NAMETAG):
        new_name = remove_nametag_from_name(current_name)

        try:
            await member.edit(
                nick=new_name if new_name else None,
                reason="RLP Nametag entfernt"
            )
        except discord.HTTPException as error:
            print(f"[NAMETAG] Nickname-Fehler beim Entfernen: {error}")


# =========================================================
# NAMETAG PANEL
# =========================================================

class NametagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag aktivieren",
        style=discord.ButtonStyle.success,
        custom_id="rlp_nametag_activate"
    )
    async def activate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(user_id)

        save_data()

        await apply_nametag(interaction.user)

        await interaction.response.send_message(
            "✅ Dein **RLP Nametag** wurde aktiviert.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Nametag entfernen",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_nametag_remove"
    )
    async def remove(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id not in data["nametag_opt_out"]:
            data["nametag_opt_out"].append(user_id)

        save_data()

        await remove_nametag(interaction.user)

        await interaction.response.send_message(
            "✅ Dein **RLP Nametag** wurde entfernt und bleibt deaktiviert.",
            ephemeral=True
        )


def create_nametag_embed():
    embed = discord.Embed(
        title="🏷️ RLP Nametag",
        description=(
            "Verwalte hier dein persönliches **RLP Nametag**.\n\n"
            "Mit **Nametag aktivieren** wird dein RLP Nametag gesetzt.\n"
            "Mit **Nametag entfernen** wird es entfernt und bleibt deaktiviert."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=PANEL_MARKER + "nametag"
    )

    return embed


# =========================================================
# KENNZEICHEN
# =========================================================

def normalize_plate(plate):
    plate = plate.upper().strip()

    plate = " ".join(
        part for part in plate.split()
        if part
    )

    return plate


def split_plate(plate):
    parts = normalize_plate(plate).split()

    if len(parts) < 2:
        return None, None

    number = parts[-1]
    prefix = " ".join(parts[:-1])

    if not prefix:
        return None, None

    if not number.isdigit():
        return None, None

    return prefix, number


def get_user_plate(user_id):
    entry = data["license_plates"].get(str(user_id))

    if not isinstance(entry, dict):
        return None

    plate = entry.get("plate")

    if not plate:
        return None

    return plate


def find_plate_number(number, ignore_user_id=None):
    for user_id, entry in data["license_plates"].items():
        if ignore_user_id is not None and str(user_id) == str(ignore_user_id):
            continue

        if not isinstance(entry, dict):
            continue

        plate = entry.get("plate")

        if not plate:
            continue

        _, saved_number = split_plate(plate)

        if saved_number == number:
            return user_id, plate

    return None, None


def get_all_plates():
    plates = []

    for user_id, entry in data["license_plates"].items():
        if not isinstance(entry, dict):
            continue

        plate = entry.get("plate")

        if not plate:
            continue

        plates.append(
            (
                int(user_id),
                plate
            )
        )

    plates.sort(
        key=lambda item: item[1]
    )

    return plates


class PlateModal(discord.ui.Modal, title="Kennzeichen registrieren"):
    plate_input = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01 oder RY ZE 02",
        min_length=2,
        max_length=20,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        user_id = str(interaction.user.id)

        existing_plate = get_user_plate(user_id)

        if existing_plate:
            await interaction.response.send_message(
                f"❌ Du hast bereits das Kennzeichen **{existing_plate}** registriert.\n"
                "Entferne es zuerst, wenn du ein anderes registrieren möchtest.",
                ephemeral=True
            )
            return

        plate = normalize_plate(self.plate_input.value)

        prefix, number = split_plate(plate)

        if prefix is None or number is None:
            await interaction.response.send_message(
                "❌ Ungültiges Kennzeichen.\n\n"
                "Das Kennzeichen muss aus einem Präfix und einer **Zahl** bestehen, "
                "z. B. `RLP 01`, `RY 02` oder `RY ZE 03`.",
                ephemeral=True
            )
            return

        existing_user, existing_plate = find_plate_number(
            number
        )

        if existing_user is not None:
            await interaction.response.send_message(
                f"❌ Die Nummer **{number}** ist bereits vergeben.\n"
                "Die Nummer muss serverweit eindeutig sein.",
                ephemeral=True
            )
            return

        data["license_plates"][user_id] = {
            "plate": plate,
            "registered_at": now_text()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde erfolgreich registriert.",
            ephemeral=True
        )

        await update_license_plate_panel()


class PlateDeleteConfirm(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Kennzeichen entfernen",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        plate = get_user_plate(user_id)

        if not plate:
            await interaction.response.edit_message(
                content="❌ Du hast kein Kennzeichen registriert.",
                embed=None,
                view=None
            )
            return

        del data["license_plates"][user_id]

        save_data()

        await interaction.response.edit_message(
            content=(
                f"✅ Das Kennzeichen **{plate}** wurde entfernt.\n"
                "Die Nummer ist jetzt wieder frei."
            ),
            embed=None,
            view=None
        )

        await update_license_plate_panel()

    @discord.ui.button(
        label="Abbrechen",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="Abgebrochen.",
            embed=None,
            view=None
        )


class PlateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen registrieren",
        emoji="🚘",
        style=discord.ButtonStyle.success,
        custom_id="rlp_plate_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            PlateModal()
        )

    @discord.ui.button(
        label="Mein Kennzeichen entfernen",
        emoji="🗑️",
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
                "❌ Du hast kein Kennzeichen registriert.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Soll **{plate}** wirklich entfernt werden?",
            view=PlateDeleteConfirm(),
            ephemeral=True
        )


def create_license_plate_embed():
    plates = get_all_plates()

    embed = discord.Embed(
        title="🚘 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen registrieren oder entfernen.\n\n"
            "**Wichtig:**\n"
            "• Jeder Benutzer kann nur **ein** Kennzeichen besitzen.\n"
            "• Die **Nummer** ist serverweit einmalig.\n"
            "• Der Präfix darf sich wiederholen.\n"
            "• Nach dem Entfernen wird die Nummer wieder frei."
        ),
        color=discord.Color.dark_blue()
    )

    if plates:
        lines = []

        for user_id, plate in plates:
            member = get_guild().get_member(user_id)

            if member:
                name = member.display_name
            else:
                name = f"User {user_id}"

            lines.append(
                f"🚘 **{plate}** — {name}"
            )

        description = "\n".join(lines)

        if len(description) > 3900:
            description = description[:3890] + "\n..."

        embed.add_field(
            name="Registrierte Kennzeichen",
            value=description,
            inline=False
        )

    else:
        embed.add_field(
            name="Registrierte Kennzeichen",
            value="Noch keine Kennzeichen registriert.",
            inline=False
        )

    embed.set_footer(
        text=PANEL_MARKER + "license_plates"
    )

    return embed


# =========================================================
# TEAM-SYSTEM
# =========================================================

# ABSICHTLICH KEIN TEAM-SYSTEM.
#
# Es gibt hier:
# - keine Team-Rolle
# - kein Team-Panel
# - keine Team-Registrierung
# - keine Team-Daten
# - keine automatische Team-Rollenvergabe
#
# Dadurch kann dieses Script niemandem aufgrund einer
# Team-Registrierung eine Rolle geben.


# =========================================================
# SCHICHTSYSTEM
# =========================================================

class ShiftView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="rlp_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Vorgang funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Schicht zu starten.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        if user_id in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
            "started_at": now_text()
        }

        save_data()

        active_role = member.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is not None and active_role not in member.roles:
            try:
                await member.add_roles(
                    active_role,
                    reason="RLP Schicht gestartet"
                )
            except discord.HTTPException as error:
                print(f"[SHIFT] Fehler beim Rollen-Geben: {error}")

        await send_shift_log(
            member,
            "Schicht gestartet",
            "🟢"
        )

        await interaction.response.send_message(
            "🟢 Deine Schicht wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Vorgang funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Schicht zu beenden.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        shift = data["developer_shifts"].get(user_id)

        if not shift:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        started_at = shift.get("started_at")

        del data["developer_shifts"][user_id]

        save_data()

        active_role = member.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is not None and active_role in member.roles:
            try:
                await member.remove_roles(
                    active_role,
                    reason="RLP Schicht beendet"
                )
            except discord.HTTPException as error:
                print(f"[SHIFT] Fehler beim Rollen-Entfernen: {error}")

        await send_shift_log(
            member,
            "Schicht beendet",
            "🔴",
            started_at
        )

        await interaction.response.send_message(
            "🔴 Deine Schicht wurde beendet.",
            ephemeral=True
        )


def create_shift_embed():
    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            "Verwalte hier deine aktuelle Entwickler-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Startet deine Schicht und gibt dir die aktive Schicht-Rolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Schicht und entfernt die aktive Schicht-Rolle."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text=PANEL_MARKER + "shift"
    )

    return embed


async def send_shift_log(
    member,
    action,
    emoji,
    started_at=None
):
    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title=f"{emoji} {action}",
        color=(
            discord.Color.green()
            if "gestartet" in action
            else discord.Color.red()
        ),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Benutzer",
        value=f"{member.mention}\n`{member.id}`",
        inline=False
    )

    if started_at:
        embed.add_field(
            name="Schicht gestartet",
            value=started_at,
            inline=False
        )

    embed.set_footer(
        text="RLP Schicht-Log"
    )

    await safe_send(
        channel,
        embed=embed
    )


# =========================================================
# TASK SYSTEM
# =========================================================

class TaskModal(discord.ui.Modal, title="Neue Entwickler-Aufgabe"):
    task_input = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibung der Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        global data

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        data["developer_task_counter"] += 1

        task_id = data["developer_task_counter"]

        data["developer_tasks"][str(task_id)] = {
            "task": self.task_input.value,
            "created_by": interaction.user.id,
            "created_at": now_text(),
            "completed": False
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )

        await update_task_panel()


class TaskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TaskModal()
        )


def create_task_embed():
    embed = discord.Embed(
        title="📝 Entwickler-Aufgaben",
        description="Hier werden aktuelle Entwickler-Aufgaben verwaltet.",
        color=discord.Color.blurple()
    )

    tasks = data.get("developer_tasks", {})

    active_tasks = [
        (task_id, task)
        for task_id, task in tasks.items()
        if not task.get("completed", False)
    ]

    if not active_tasks:
        embed.add_field(
            name="Aktuelle Aufgaben",
            value="Keine offenen Aufgaben.",
            inline=False
        )

    else:
        lines = []

        for task_id, task in active_tasks[:20]:
            lines.append(
                f"**#{task_id}** — {task.get('task', 'Keine Beschreibung')}"
            )

        embed.add_field(
            name="Aktuelle Aufgaben",
            value="\n".join(lines),
            inline=False
        )

    embed.set_footer(
        text=PANEL_MARKER + "tasks"
    )

    return embed


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(discord.ui.Modal, title="Bewerbung"):
    name_input = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=100,
        required=True
    )

    age_input = discord.ui.TextInput(
        label="Alter",
        placeholder="Dein Alter",
        max_length=3,
        required=True
    )

    text_input = discord.ui.TextInput(
        label="Bewerbung",
        placeholder="Warum möchtest du dich bewerben?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        review_channel = get_channel(
            REVIEW_CHANNEL_ID
        )

        if review_channel is None:
            await interaction.response.send_message(
                "❌ Der Bewerbungs-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="Discord",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="Bewerbung",
            value=self.text_input.value,
            inline=False
        )

        embed.set_footer(
            text="RLP Bewerbungssystem"
        )

        await safe_send(
            review_channel,
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        emoji="📨",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_application_open"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ApplicationModal()
        )


def create_application_embed():
    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bei RLP bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=PANEL_MARKER + "application"
    )

    return embed


# =========================================================
# PANEL SYSTEM
# =========================================================

async def upsert_panel(
    channel_id,
    embed,
    view
):
    channel = get_channel(channel_id)

    if channel is None:
        print(f"[PANEL] Channel nicht gefunden: {channel_id}")
        return

    marker = get_panel_marker_from_embed(embed)

    if marker is None:
        print("[PANEL] Kein Marker vorhanden.")
        return

    existing_message = None

    try:
        async for message in channel.history(limit=200):
            if not message.author.bot:
                continue

            if get_panel_marker(message) == marker:
                existing_message = message
                break

    except discord.HTTPException as error:
        print(f"[PANEL] History-Fehler: {error}")

    if existing_message:
        try:
            await existing_message.edit(
                embed=embed,
                view=view
            )
            return
        except discord.HTTPException:
            pass

    await safe_send(
        channel,
        embed=embed,
        view=view
    )


def get_panel_marker_from_embed(embed):
    if not embed.footer:
        return None

    footer = embed.footer.text or ""

    if footer.startswith(PANEL_MARKER):
        return footer

    return None


async def clean_old_panels():
    panel_channels = [
        QUIZ_CHANNEL_ID,
        APPLICATION_CHANNEL_ID,
        NICKNAME_CHANNEL_ID,
        DEVELOPER_TASK_CHANNEL_ID,
        DEVELOPER_SHIFT_CHANNEL_ID
    ]

    seen = set()

    for channel_id in panel_channels:
        if channel_id in seen:
            continue

        seen.add(channel_id)

        channel = get_channel(channel_id)

        if channel is None:
            continue

        try:
            async for message in channel.history(limit=200):
                if not message.author.bot:
                    continue

                marker = get_panel_marker(message)

                if marker:
                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

        except discord.HTTPException as error:
            print(f"[PANEL] Cleanup-Fehler: {error}")


async def send_all_panels():
    await upsert_panel(
        NICKNAME_CHANNEL_ID,
        create_nametag_embed(),
        NametagView()
    )

    await upsert_panel(
        APPLICATION_CHANNEL_ID,
        create_application_embed(),
        ApplicationView()
    )

    await upsert_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        create_task_embed(),
        TaskView()
    )

    await upsert_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        create_shift_embed(),
        ShiftView()
    )

    await update_license_plate_panel()


async def update_license_plate_panel():
    # Kennzeichen-Panel wird im Nametag-Channel abgelegt,
    # falls kein eigener Kennzeichen-Channel vorhanden ist.
    await upsert_panel(
        NICKNAME_CHANNEL_ID,
        create_license_plate_embed(),
        PlateView()
    )


async def update_task_panel():
    await upsert_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        create_task_embed(),
        TaskView()
    )


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_POOL = [
    {
        "emoji": "🚗⛽",
        "answer": "Tanken",
        "options": ["Tanken", "Waschen", "Parken", "Reparieren"]
    },
    {
        "emoji": "🚓🚨",
        "answer": "Polizei",
        "options": ["Polizei", "Feuerwehr", "Abschleppdienst", "Taxi"]
    },
    {
        "emoji": "🚒🔥",
        "answer": "Feuerwehr",
        "options": ["Polizei", "Feuerwehr", "Rettungsdienst", "Werkstatt"]
    },
    {
        "emoji": "🚑🏥",
        "answer": "Rettungsdienst",
        "options": ["Taxi", "Rettungsdienst", "Polizei", "Werkstatt"]
    },
    {
        "emoji": "🔧🚗",
        "answer": "Werkstatt",
        "options": ["Werkstatt", "Tankstelle", "Polizei", "Parkhaus"]
    },
    {
        "emoji": "🅿️🚗",
        "answer": "Parken",
        "options": ["Tanken", "Parken", "Waschen", "Fahren"]
    },
    {
        "emoji": "🚦🔴",
        "answer": "Rote Ampel",
        "options": ["Grüne Ampel", "Rote Ampel", "Baustelle", "Stoppschild"]
    },
    {
        "emoji": "🛑🚗",
        "answer": "Stoppschild",
        "options": ["Stoppschild", "Vorfahrt", "Kreisverkehr", "Ampel"]
    },
    {
        "emoji": "🔄🚘",
        "answer": "Kreisverkehr",
        "options": ["Kreisverkehr", "Autobahn", "Parkplatz", "Tankstelle"]
    },
    {
        "emoji": "🚘💨",
        "answer": "Schnell fahren",
        "options": ["Schnell fahren", "Parken", "Tanken", "Waschen"]
    }
]


def create_quiz_embed(question):
    embed = discord.Embed(
        title="🧠 RLP Emoji Quiz",
        description=(
            "Errate den Begriff anhand der Emojis.\n\n"
            f"## {question['emoji']}\n\n"
            "Wähle die richtige Antwort über die Buttons."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Emoji Quiz • Neue Frage automatisch"
    )

    return embed


class QuizView(discord.ui.View):
    def __init__(self, question):
        super().__init__(timeout=30)

        options = question["options"][:]

        for index, option in enumerate(options):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rlp_quiz_{index}"
            )

            async def callback(
                interaction: discord.Interaction,
                selected=option
            ):
                await handle_quiz_answer(
                    interaction,
                    selected,
                    question
                )

            button.callback = callback
            self.add_item(button)


async def handle_quiz_answer(
    interaction,
    selected,
    question
):
    global quiz_message_id
    global current_quiz

    async with quiz_lock:
        if current_quiz is None:
            await interaction.response.send_message(
                "⚠️ Dieses Quiz ist bereits beendet.",
                ephemeral=True
            )
            return

        if current_quiz["answer"] != question["answer"]:
            await interaction.response.send_message(
                "❌ Falsch! Versuch es bei der nächsten Frage erneut.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        data["quiz_scores"][user_id] = (
            data["quiz_scores"].get(user_id, 0) + 1
        )

        save_data()

        quiz_message_id = None
        current_quiz = None

        await interaction.response.send_message(
            "✅ Richtig! Du bekommst einen Punkt.",
            ephemeral=True
        )

        old_message = interaction.message

        try:
            await old_message.delete()
        except discord.HTTPException:
            pass

    await asyncio.sleep(1)

    await send_new_quiz()


async def send_new_quiz():
    global quiz_message_id
    global current_quiz

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    async with quiz_lock:
        question = random.choice(QUIZ_POOL)

        current_quiz = question

        try:
            message = await channel.send(
                embed=create_quiz_embed(question),
                view=QuizView(question)
            )

            quiz_message_id = message.id

        except discord.HTTPException as error:
            print(f"[QUIZ] Fehler beim Senden: {error}")
            current_quiz = None
            quiz_message_id = None


async def clear_quiz_channel():
    global quiz_message_id
    global current_quiz

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    quiz_message_id = None
    current_quiz = None

    try:
        async for message in channel.history(limit=None):
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    except discord.HTTPException as error:
        print(f"[QUIZ] Cleanup-Fehler: {error}")


async def quiz_cleanup_loop():
    global quiz_message_id

    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            channel = get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is not None:
                active_id = quiz_message_id

                async for message in channel.history(limit=None):
                    if active_id is not None and message.id == active_id:
                        continue

                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

        except Exception as error:
            print(f"[QUIZ CLEANUP] Fehler: {error}")

        await asyncio.sleep(5)


# =========================================================
# SUPPORT VOICE LOG
# =========================================================

async def send_support_voice_log(
    member,
    action
):
    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🎧 Support Voice",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Benutzer",
        value=f"{member.mention}\n`{member.id}`",
        inline=False
    )

    embed.add_field(
        name="Aktion",
        value=action,
        inline=False
    )

    embed.add_field(
        name="Channel",
        value=f"<#{SUPPORT_VOICE_CHANNEL_ID}>",
        inline=False
    )

    await safe_send(
        channel,
        embed=embed
    )


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    global startup_finished
    global quiz_cleanup_task

    print(f"Bot online: {bot.user}")

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("[STARTUP] Server nicht gefunden.")
        return

    if startup_finished:
        return

    startup_finished = True

    # Persistente Views registrieren.
    bot.add_view(NametagView())
    bot.add_view(PlateView())
    bot.add_view(ShiftView())
    bot.add_view(TaskView())
    bot.add_view(ApplicationView())

    # Alte Panels entfernen.
    await clean_old_panels()

    # Alle Panels neu erstellen.
    await send_all_panels()

    # Nametags wiederherstellen.
    for member in guild.members:
        if member.bot:
            continue

        if not is_nametag_opted_out(member.id):
            await apply_nametag(member)

    # Aktive Schichten wiederherstellen.
    active_role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if active_role is not None:
        for user_id in list(data["developer_shifts"].keys()):
            try:
                member = guild.get_member(
                    int(user_id)
                )

                if member is None:
                    continue

                if active_role not in member.roles:
                    await member.add_roles(
                        active_role,
                        reason="RLP aktive Schicht wiederhergestellt"
                    )

            except Exception as error:
                print(
                    f"[SHIFT] Wiederherstellungsfehler: {error}"
                )

    # Quiz komplett leeren und neues Quiz starten.
    await clear_quiz_channel()
    await send_new_quiz()

    if quiz_cleanup_task is None or quiz_cleanup_task.done():
        quiz_cleanup_task = asyncio.create_task(
            quiz_cleanup_loop()
        )

    print("[STARTUP] Alle Systeme geladen.")


@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID:
        return

    if member.bot:
        return

    await apply_nametag(member)


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):
    if member.bot:
        return

    support_channel_id = SUPPORT_VOICE_CHANNEL_ID

    joined_support = (
        after.channel is not None
        and after.channel.id == support_channel_id
    )

    left_support = (
        before.channel is not None
        and before.channel.id == support_channel_id
    )

    if joined_support and not left_support:
        await send_support_voice_log(
            member,
            "🟢 Support-Voice betreten"
        )

    elif left_support and not joined_support:
        await send_support_voice_log(
            member,
            "🔴 Support-Voice verlassen"
        )


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        await bot.process_commands(message)
        return

    if message.guild.id != GUILD_ID:
        await bot.process_commands(message)
        return

    if message.channel.id == QUIZ_CHANNEL_ID:
        # Quiz-Nachrichten werden vom Cleanup-Loop entfernt.
        # Die aktive Quiz-Nachricht bleibt bestehen.
        pass

    await bot.process_commands(message)


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def quizscore(ctx):
    score = data["quiz_scores"].get(
        str(ctx.author.id),
        0
    )

    await ctx.send(
        f"🧠 {ctx.author.mention}, dein Quiz-Score ist **{score}**."
    )


@bot.command()
async def kennzeichen(ctx):
    plate = get_user_plate(ctx.author.id)

    if plate:
        await ctx.send(
            f"🚘 Dein Kennzeichen ist **{plate}**."
        )
    else:
        await ctx.send(
            "🚘 Du hast noch kein Kennzeichen registriert."
        )


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
