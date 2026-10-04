import os
import json
import time
import asyncio
import traceback
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands


# =========================================================
# KONFIGURATION
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
BUG_CHANNEL_ID = 1556072637170716732

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

PREFIX = "?"

BOT_START_TIME = time.time()


# =========================================================
# INTENTS
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
# DATEN
# =========================================================

DEFAULT_DATA = {
    "license_plates": {},
    "applications": {},
    "developer_tasks": {},
    "active_developer_shifts": {},
    "suggestions": {},
    "feedback": [],
    "bugs": []
}


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA.copy())
        return {
            "license_plates": {},
            "applications": {},
            "developer_tasks": {},
            "active_developer_shifts": {},
            "suggestions": {},
            "feedback": [],
            "bugs": []
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("⚠️ bot_data.json konnte nicht gelesen werden.")
        data = {}

    changed = False

    for key, default in DEFAULT_DATA.items():
        if key not in data:
            data[key] = default.copy() if isinstance(default, dict) else list(default)
            changed = True

    # Alte / beschädigte Daten absichern
    if not isinstance(data["license_plates"], dict):
        data["license_plates"] = {}
        changed = True

    if not isinstance(data["applications"], dict):
        data["applications"] = {}
        changed = True

    if not isinstance(data["developer_tasks"], dict):
        data["developer_tasks"] = {}
        changed = True

    if not isinstance(data["active_developer_shifts"], dict):
        data["active_developer_shifts"] = {}
        changed = True

    if not isinstance(data["suggestions"], dict):
        data["suggestions"] = {}
        changed = True

    if not isinstance(data["feedback"], list):
        data["feedback"] = []
        changed = True

    if not isinstance(data["bugs"], list):
        data["bugs"] = []
        changed = True

    if changed:
        save_data(data)

    return data


def save_data(data):
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")


data = load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def now_string():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def make_embed(
    title,
    description="",
    color=discord.Color.blurple()
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="RLP Bot")
    return embed


def has_role(member, role_id):
    if not isinstance(member, discord.Member):
        return False

    return any(role.id == role_id for role in member.roles)


def is_owner(member):
    return has_role(member, OWNER_ROLE_ID)


def is_shift_permission(member):
    return has_role(member, SHIFT_PERMISSION_ROLE_ID)


def get_guild():
    return bot.get_guild(GUILD_ID)


def get_text_channel(channel_id):
    channel = bot.get_channel(channel_id)

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


def safe_display_name(member):
    if member is None:
        return "Unbekannt"

    return member.display_name


async def safe_interaction_error(interaction, text):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)
    except Exception:
        pass


# =========================================================
# PANEL MARKER
# =========================================================

def panel_marker(marker):
    return f"<!-- {marker} -->"


# =========================================================
# PANEL FINDEN / AKTUALISIEREN
# =========================================================

async def find_panel_message(channel, marker):
    if not isinstance(channel, discord.TextChannel):
        return None

    try:
        async for message in channel.history(limit=100):
            if panel_marker(marker) in message.content:
                return message

            if message.embeds:
                for embed in message.embeds:
                    if marker in (embed.title or ""):
                        return message

                    if marker in (embed.description or ""):
                        return message

        return None

    except Exception as e:
        print(f"Panel-Suche fehlgeschlagen: {e}")
        return None


async def update_panel(
    channel_id,
    marker,
    embed,
    view
):
    channel = get_text_channel(channel_id)

    if channel is None:
        print(f"⚠️ Panel-Channel {channel_id} nicht gefunden.")
        return

    message = await find_panel_message(channel, marker)

    content = panel_marker(marker)

    try:
        if message:
            await message.edit(
                content=content,
                embed=embed,
                view=view
            )
            return message

        message = await channel.send(
            content=content,
            embed=embed,
            view=view
        )

        return message

    except discord.Forbidden:
        print(f"❌ Keine Rechte im Panel-Channel {channel_id}.")

    except Exception as e:
        print(f"❌ Panel konnte nicht aktualisiert werden: {e}")

    return None


# =========================================================
# NAMETAG SYSTEM
# =========================================================

def remove_nametag_prefix(nickname):
    if not nickname:
        return nickname

    prefixes = [
        "RLP | ",
        "RLP |\u00a0"
    ]

    for prefix in prefixes:
        if nickname.startswith(prefix):
            return nickname[len(prefix):]

    return nickname


class NametagSetButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag setzen",
            emoji="🏷️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_nametag_set"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        member = interaction.user

        if not has_role(member, NAMETAG_ROLE_ID):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung für das Nametag-System."
            )

        current = member.nick or member.name

        if current.startswith(NAMETAG):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast bereits einen RLP-Nametag."
            )

        new_name = NAMETAG + current

        if len(new_name) > 32:
            return await safe_interaction_error(
                interaction,
                "❌ Dein Name wäre mit Nametag zu lang für Discord."
            )

        try:
            await member.edit(nick=new_name)

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde gesetzt: `{new_name}`",
                ephemeral=True
            )

        except discord.Forbidden:
            await safe_interaction_error(
                interaction,
                "❌ Der Bot kann deinen Nickname nicht ändern. "
                "Prüfe die Bot-Rolle und deren Position."
            )

        except Exception as e:
            print(f"Nametag Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Beim Setzen des Nametags ist ein Fehler aufgetreten."
            )


class NametagResetButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            emoji="♻️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        member = interaction.user
        current = member.nick

        if not current:
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keinen eigenen Nickname."
            )

        new_name = remove_nametag_prefix(current)

        if new_name == current:
            return await safe_interaction_error(
                interaction,
                "❌ Bei dir ist kein RLP-Nametag vorhanden."
            )

        try:
            await member.edit(nick=new_name)

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde entfernt. Neuer Name: `{new_name}`",
                ephemeral=True
            )

        except discord.Forbidden:
            await safe_interaction_error(
                interaction,
                "❌ Der Bot kann deinen Nickname nicht ändern."
            )

        except Exception as e:
            print(f"Nametag Reset Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Beim Entfernen ist ein Fehler aufgetreten."
            )


class NametagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagSetButton())
        self.add_item(NametagResetButton())


def nametag_embed():
    return make_embed(
        "🏷️ RLP Nametag-System",
        (
            "Verwalte hier deinen RLP-Nametag.\n\n"
            "🏷️ **Nametag setzen**\n"
            "Setzt `RLP | ` vor deinen aktuellen Namen.\n\n"
            "♻️ **Nametag entfernen**\n"
            "Entfernt ausschließlich den `RLP | `-Präfix.\n\n"
            "Deine Rollen werden dabei nicht verändert."
        ),
        discord.Color.blue()
    )


# =========================================================
# KENNZEICHEN SYSTEM
# =========================================================

def normalize_plate(text):
    return " ".join(text.strip().upper().split())


def extract_plate_number(plate):
    parts = normalize_plate(plate).split()

    if not parts:
        return None

    last = parts[-1]

    if not last.isdigit():
        return None

    return int(last)


def plate_number_is_used(number):
    for plate_data in data["license_plates"].values():
        if not isinstance(plate_data, dict):
            continue

        existing_plate = plate_data.get("plate", "")
        existing_number = extract_plate_number(existing_plate)

        if existing_number == number:
            return True

    return False


def get_user_plate(user_id):
    entry = data["license_plates"].get(str(user_id))

    if isinstance(entry, dict):
        return entry.get("plate")

    # Falls alte Daten direkt als String gespeichert wurden
    if isinstance(entry, str):
        return entry

    return None


def license_plate_embed():
    embed = make_embed(
        "🚗 RLP Kennzeichen-System",
        (
            "Hier kannst du dein Kennzeichen eintragen.\n\n"
            "• Jeder Benutzer kann **ein Kennzeichen** besitzen.\n"
            "• Die **Nummer am Ende** muss serverweit einmalig sein.\n"
            "• Der Präfix darf sich wiederholen.\n"
            "• Bereits gespeicherte Kennzeichen bleiben auch nach "
            "einem Bot-Neustart erhalten.\n\n"
            "Beispiel: `RLP 01` oder `RY ZE 01`"
        ),
        discord.Color.green()
    )

    if data["license_plates"]:
        lines = []

        for user_id, plate_data in data["license_plates"].items():
            try:
                uid = int(user_id)
            except Exception:
                uid = 0

            member = get_guild().get_member(uid) if get_guild() else None

            if isinstance(plate_data, dict):
                plate = plate_data.get("plate", "Unbekannt")
            else:
                plate = str(plate_data)

            if member:
                name = member.display_name
            else:
                name = f"User {uid}"

            lines.append(f"🚗 `{plate}` — **{name}**")

        lines.sort(key=lambda x: x.lower())

        text = "\n".join(lines)

        if len(text) > 3900:
            text = text[:3850] + "\n…"

        embed.add_field(
            name=f"📋 Eingetragene Kennzeichen ({len(lines)})",
            value=text or "Keine Kennzeichen eingetragen.",
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Eingetragene Kennzeichen",
            value="Noch keine Kennzeichen eingetragen.",
            inline=False
        )

    return embed


class LicensePlateModal(discord.ui.Modal, title="Kennzeichen eintragen"):
    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        existing = get_user_plate(interaction.user.id)

        if existing:
            return await interaction.response.send_message(
                f"❌ Du hast bereits das Kennzeichen `{existing}` eingetragen.",
                ephemeral=True
            )

        plate = normalize_plate(str(self.plate.value))

        number = extract_plate_number(plate)

        if number is None:
            return await interaction.response.send_message(
                "❌ Das Kennzeichen muss mit einer Zahl enden.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )

        if not any(char.isalpha() for char in plate):
            return await interaction.response.send_message(
                "❌ Bitte gib ein Kennzeichen mit Präfix und Nummer ein.",
                ephemeral=True
            )

        if plate_number_is_used(number):
            return await interaction.response.send_message(
                f"❌ Die Nummer `{number}` ist bereits vergeben.",
                ephemeral=True
            )

        # WICHTIG:
        # Hier wird nur ein neuer Datensatz hinzugefügt.
        # Es werden KEINE vorhandenen Kennzeichen gelöscht.
        data["license_plates"][user_id] = {
            "plate": plate,
            "created_at": now_string()
        }

        save_data(data)

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{plate}` wurde gespeichert.",
            ephemeral=True
        )

        await refresh_license_panel()


class LicensePlateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen eintragen",
            emoji="🚗",
            style=discord.ButtonStyle.success,
            custom_id="rlp_license_add"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LicensePlateModal())


class LicensePlateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicensePlateButton())


async def refresh_license_panel():
    # Nur das PANEL wird aktualisiert.
    # data["license_plates"] wird hier NICHT verändert.
    await update_panel(
        LICENSE_PLATE_CHANNEL_ID,
        LICENSE_PANEL_MARKER,
        license_plate_embed(),
        LicensePlateView()
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(discord.ui.Modal, title="Bewerbung"):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=50,
        required=True
    )

    age = discord.ui.TextInput(
        label="Alter",
        placeholder="z. B. 18",
        max_length=3,
        required=True
    )

    reason = discord.ui.TextInput(
        label="Warum möchtest du dich bewerben?",
        placeholder="Schreibe etwas über dich...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = get_text_channel(APPLICATION_CHANNEL_ID)

        if channel is None:
            return await interaction.response.send_message(
                "❌ Bewerbungskanal wurde nicht gefunden.",
                ephemeral=True
            )

        embed = make_embed(
            "📨 Neue Bewerbung",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Discord",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="📝 Name",
            value=str(self.name.value),
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=str(self.age.value),
            inline=True
        )

        embed.add_field(
            name="📋 Grund",
            value=str(self.reason.value),
            inline=False
        )

        embed.add_field(
            name="🕒 Eingegangen",
            value=now_string(),
            inline=False
        )

        try:
            await channel.send(embed=embed)

            data["applications"][str(interaction.user.id)] = {
                "name": str(self.name.value),
                "age": str(self.age.value),
                "reason": str(self.reason.value),
                "created_at": now_string()
            }

            save_data(data)

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde erfolgreich eingereicht.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Bewerbungsfehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Die Bewerbung konnte nicht gesendet werden."
            )


class ApplicationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_application_open"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ApplicationModal())


class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


def application_embed():
    return make_embed(
        "📨 Bewerbung",
        (
            "Du möchtest dich bei uns bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular vollständig aus.\n\n"
            "Bitte gib ehrliche und sinnvolle Angaben an."
        ),
        discord.Color.orange()
    )


# =========================================================
# DEVELOPER AUFGABEN
# =========================================================

class DeveloperTaskModal(discord.ui.Modal, title="Developer-Aufgabe"):
    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        if not is_shift_permission(interaction.user):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung dafür."
            )

        channel = get_text_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel is None:
            return await safe_interaction_error(
                interaction,
                "❌ Developer-Aufgaben-Kanal wurde nicht gefunden."
            )

        task_id = str(int(time.time() * 1000))

        data["developer_tasks"][task_id] = {
            "author_id": interaction.user.id,
            "task": str(self.task.value),
            "created_at": now_string(),
            "status": "offen"
        }

        save_data(data)

        embed = make_embed(
            "🛠️ Neue Developer-Aufgabe",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🆔 Aufgabe",
            value=f"`{task_id}`",
            inline=True
        )

        embed.add_field(
            name="📋 Aufgabe",
            value=str(self.task.value),
            inline=False
        )

        embed.add_field(
            name="📊 Status",
            value="🟡 Offen",
            inline=False
        )

        try:
            await channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Die Developer-Aufgabe wurde erstellt.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Developer Task Fehler: {e}")

            await safe_interaction_error(
                interaction,
                "❌ Die Aufgabe konnte nicht erstellt werden."
            )


class DeveloperTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        if not is_shift_permission(interaction.user):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung für Developer-Aufgaben."
            )

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


def developer_task_embed():
    return make_embed(
        "🛠️ Developer-Aufgaben",
        (
            "Hier können berechtigte Entwickler neue Aufgaben erstellen.\n\n"
            "🛠️ **Aufgabe erstellen**\n"
            "Erstellt eine neue Aufgabe im Developer-Aufgabenkanal."
        ),
        discord.Color.blue()
    )


# =========================================================
# DEVELOPER SCHICHT
# =========================================================

async def send_shift_log(
    member,
    action,
    color,
    started_at=None
):
    channel = get_text_channel(SHIFT_LOG_CHANNEL_ID)

    if channel is None:
        return

    embed = make_embed(
        f"🛠️ Developer-Schicht — {action}",
        color=color
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.add_field(
        name="👤 Entwickler",
        value=f"{member.mention}\n`{member.id}`",
        inline=False
    )

    embed.add_field(
        name="📌 Aktion",
        value=action,
        inline=True
    )

    embed.add_field(
        name="🕒 Zeitpunkt",
        value=now_string(),
        inline=True
    )

    if started_at:
        embed.add_field(
            name="⏱️ Schicht gestartet",
            value=started_at,
            inline=False
        )

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Shift Log Fehler: {e}")


class DeveloperShiftStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_dev_shift_start"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        member = interaction.user

        if not is_shift_permission(member):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung für Developer-Schichten."
            )

        key = str(member.id)

        if key in data["active_developer_shifts"]:
            return await safe_interaction_error(
                interaction,
                "❌ Du bist bereits in einer Developer-Schicht."
            )

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            return await safe_interaction_error(
                interaction,
                "❌ Die Developer-Schicht-Rolle wurde nicht gefunden."
            )

        try:
            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

            started = now_string()

            data["active_developer_shifts"][key] = {
                "started_at": started
            }

            save_data(data)

            await send_shift_log(
                member,
                "🟢 Schicht gestartet",
                discord.Color.green(),
                started
            )

            await interaction.response.send_message(
                "🟢 Deine Developer-Schicht wurde gestartet.",
                ephemeral=True
            )

            await refresh_dev_shift_panel()

        except discord.Forbidden:
            await safe_interaction_error(
                interaction,
                "❌ Der Bot kann die Schicht-Rolle nicht vergeben."
            )

        except Exception as e:
            print(f"Shift Start Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Die Schicht konnte nicht gestartet werden."
            )


class DeveloperShiftEndButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_dev_shift_end"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        member = interaction.user

        if not is_shift_permission(member):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung für Developer-Schichten."
            )

        key = str(member.id)

        shift = data["active_developer_shifts"].get(key)

        if not shift:
            return await safe_interaction_error(
                interaction,
                "❌ Du bist aktuell nicht in einer Developer-Schicht."
            )

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        try:
            if role and role in member.roles:
                await member.remove_roles(
                    role,
                    reason="Developer-Schicht beendet"
                )

            started = shift.get("started_at", "Unbekannt")

            data["active_developer_shifts"].pop(key, None)
            save_data(data)

            await send_shift_log(
                member,
                "🔴 Schicht beendet",
                discord.Color.red(),
                started
            )

            await interaction.response.send_message(
                "🔴 Deine Developer-Schicht wurde beendet.",
                ephemeral=True
            )

            await refresh_dev_shift_panel()

        except discord.Forbidden:
            await safe_interaction_error(
                interaction,
                "❌ Der Bot kann die Schicht-Rolle nicht entfernen."
            )

        except Exception as e:
            print(f"Shift End Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Die Schicht konnte nicht beendet werden."
            )


class DeveloperShiftView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(DeveloperShiftStartButton())
        self.add_item(DeveloperShiftEndButton())


def developer_shift_embed():
    embed = make_embed(
        "🛠️ Developer-Schicht",
        (
            "Über dieses Panel kannst du deine Developer-Schicht "
            "starten oder beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "Du erhältst die aktive Developer-Schicht-Rolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Die aktive Developer-Schicht-Rolle wird entfernt.\n\n"
            "Das Panel kann jederzeit aktualisiert werden. "
            "Eine laufende Schicht wird dadurch **nicht beendet**."
        ),
        discord.Color.blurple()
    )

    active = data["active_developer_shifts"]

    if active:
        guild = get_guild()
        lines = []

        for user_id, shift in active.items():
            member = guild.get_member(int(user_id)) if guild else None

            if member:
                name = member.display_name
            else:
                name = f"User {user_id}"

            started = shift.get("started_at", "Unbekannt")

            lines.append(
                f"🟢 **{name}**\n"
                f"└ Start: `{started}`"
            )

        embed.add_field(
            name=f"🟢 Aktive Entwickler ({len(lines)})",
            value="\n\n".join(lines)[:3900],
            inline=False
        )

    else:
        embed.add_field(
            name="🟢 Aktive Entwickler",
            value="Aktuell ist niemand in einer Developer-Schicht.",
            inline=False
        )

    return embed


async def refresh_dev_shift_panel():
    # Nur das Panel wird aktualisiert.
    # active_developer_shifts wird NICHT gelöscht.
    await update_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        DEV_SHIFT_PANEL_MARKER,
        developer_shift_embed(),
        DeveloperShiftView()
    )


# =========================================================
# COMMUNITY SYSTEM
# =========================================================

class SuggestionModal(discord.ui.Modal, title="Vorschlag einreichen"):
    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Was möchtest du verbessern?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = get_text_channel(SUGGESTION_CHANNEL_ID)

        if channel is None:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlagskanal wurde nicht gefunden."
            )

        embed = make_embed(
            "💡 Neuer Vorschlag",
            str(self.suggestion.value),
            discord.Color.gold()
        )

        embed.add_field(
            name="👤 Eingereicht von",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🟡 Status",
            value="Offen",
            inline=True
        )

        embed.add_field(
            name="🟢 Für",
            value="0",
            inline=True
        )

        embed.add_field(
            name="🔴 Gegen",
            value="0",
            inline=True
        )

        try:
            message = await channel.send(
                embed=embed,
                view=SuggestionView()
            )

            data["suggestions"][str(message.id)] = {
                "author_id": interaction.user.id,
                "text": str(self.suggestion.value),
                "status": "offen",
                "for_votes": [],
                "against_votes": []
            }

            save_data(data)

            await interaction.response.send_message(
                "✅ Dein Vorschlag wurde eingereicht.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Suggestion Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Der Vorschlag konnte nicht erstellt werden."
            )


class FeedbackModal(discord.ui.Modal, title="Feedback senden"):
    feedback = discord.ui.TextInput(
        label="Feedback",
        placeholder="Dein Feedback...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = get_text_channel(FEEDBACK_CHANNEL_ID)

        if channel is None:
            return await safe_interaction_error(
                interaction,
                "❌ Feedback-Kanal wurde nicht gefunden."
            )

        embed = make_embed(
            "💬 Neues Feedback",
            str(self.feedback.value),
            discord.Color.blue()
        )

        embed.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=False
        )

        try:
            await channel.send(embed=embed)

            data["feedback"].append({
                "author_id": interaction.user.id,
                "text": str(self.feedback.value),
                "created_at": now_string()
            })

            save_data(data)

            await interaction.response.send_message(
                "✅ Dein Feedback wurde gesendet.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Feedback Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Das Feedback konnte nicht gesendet werden."
            )


class BugModal(discord.ui.Modal, title="Bug melden"):
    bug = discord.ui.TextInput(
        label="Bug",
        placeholder="Beschreibe den Fehler...",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = get_text_channel(BUG_CHANNEL_ID)

        if channel is None:
            return await safe_interaction_error(
                interaction,
                "❌ Bug-Kanal wurde nicht gefunden."
            )

        embed = make_embed(
            "🐞 Neuer Bug",
            str(self.bug.value),
            discord.Color.red()
        )

        embed.add_field(
            name="👤 Gemeldet von",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="🕒 Zeitpunkt",
            value=now_string(),
            inline=False
        )

        try:
            await channel.send(embed=embed)

            data["bugs"].append({
                "author_id": interaction.user.id,
                "text": str(self.bug.value),
                "created_at": now_string()
            })

            save_data(data)

            await interaction.response.send_message(
                "✅ Der Bug wurde gemeldet.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Bug Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Der Bug konnte nicht gemeldet werden."
            )


class SuggestionOpenButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class FeedbackOpenButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_community_feedback"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class BugOpenButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bug melden",
            emoji="🐞",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_community_bug"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            BugModal()
        )


class CommunityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(SuggestionOpenButton())
        self.add_item(FeedbackOpenButton())
        self.add_item(BugOpenButton())


def community_embed():
    return make_embed(
        "🌐 Community",
        (
            "Du hast Feedback, einen Vorschlag oder einen Bug gefunden?\n\n"
            "💡 **Vorschlag**\n"
            "Sende uns deine Idee.\n\n"
            "💬 **Feedback**\n"
            "Teile uns deine Meinung mit.\n\n"
            "🐞 **Bug melden**\n"
            "Melde technische Fehler."
        ),
        discord.Color.blurple()
    )


# =========================================================
# VORSCHLÄGE
# =========================================================

def suggestion_embed(message_id):
    suggestion = data["suggestions"].get(str(message_id))

    if not suggestion:
        return make_embed(
            "💡 Vorschlag",
            "Dieser Vorschlag existiert nicht mehr.",
            discord.Color.red()
        )

    status = suggestion.get("status", "offen")

    status_text = {
        "offen": "🟡 Offen",
        "angenommen": "🟢 Angenommen",
        "abgelehnt": "🔴 Abgelehnt"
    }.get(status, "🟡 Offen")

    embed = make_embed(
        "💡 Vorschlag",
        suggestion.get("text", ""),
        discord.Color.gold()
    )

    author = get_guild().get_member(
        suggestion.get("author_id", 0)
    ) if get_guild() else None

    if author:
        author_text = author.mention
    else:
        author_text = f"`{suggestion.get('author_id', 'Unbekannt')}`"

    embed.add_field(
        name="👤 Eingereicht von",
        value=author_text,
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=True
    )

    embed.add_field(
        name="🟢 Für",
        value=str(len(suggestion.get("for_votes", []))),
        inline=True
    )

    embed.add_field(
        name="🔴 Gegen",
        value=str(len(suggestion.get("against_votes", []))),
        inline=True
    )

    return embed


async def refresh_suggestion(message, message_id):
    try:
        await message.edit(
            embed=suggestion_embed(message_id),
            view=SuggestionView()
        )
    except Exception as e:
        print(f"Suggestion Panel Fehler: {e}")


class SuggestionForButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Für den Vorschlag",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_for"
        )

    async def callback(self, interaction: discord.Interaction):
        message = interaction.message

        if not message:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag konnte nicht gefunden werden."
            )

        suggestion = data["suggestions"].get(str(message.id))

        if not suggestion:
            return await safe_interaction_error(
                interaction,
                "❌ Dieser Vorschlag ist nicht mehr gespeichert."
            )

        uid = interaction.user.id

        if uid in suggestion["for_votes"]:
            suggestion["for_votes"].remove(uid)
            text = "↩️ Deine Für-Stimme wurde entfernt."

        else:
            if uid in suggestion["against_votes"]:
                suggestion["against_votes"].remove(uid)

            suggestion["for_votes"].append(uid)
            text = "🟢 Deine Stimme wurde auf Für geändert."

        save_data(data)

        await refresh_suggestion(message, message.id)

        await interaction.response.send_message(
            text,
            ephemeral=True
        )


class SuggestionAgainstButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Gegen den Vorschlag",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_against"
        )

    async def callback(self, interaction: discord.Interaction):
        message = interaction.message

        if not message:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag konnte nicht gefunden werden."
            )

        suggestion = data["suggestions"].get(str(message.id))

        if not suggestion:
            return await safe_interaction_error(
                interaction,
                "❌ Dieser Vorschlag ist nicht mehr gespeichert."
            )

        uid = interaction.user.id

        if uid in suggestion["against_votes"]:
            suggestion["against_votes"].remove(uid)
            text = "↩️ Deine Gegen-Stimme wurde entfernt."

        else:
            if uid in suggestion["for_votes"]:
                suggestion["for_votes"].remove(uid)

            suggestion["against_votes"].append(uid)
            text = "🔴 Deine Stimme wurde auf Gegen geändert."

        save_data(data)

        await refresh_suggestion(message, message.id)

        await interaction.response.send_message(
            text,
            ephemeral=True
        )


class SuggestionAcceptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Annehmen",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_accept"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        if not has_role(
            interaction.user,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung dafür."
            )

        message = interaction.message

        if not message:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag konnte nicht gefunden werden."
            )

        suggestion = data["suggestions"].get(str(message.id))

        if not suggestion:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        suggestion["status"] = "angenommen"
        save_data(data)

        await refresh_suggestion(message, message.id)

        await interaction.response.send_message(
            "🟢 Der Vorschlag wurde angenommen.",
            ephemeral=True
        )


class SuggestionRejectButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Ablehnen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_reject"
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await safe_interaction_error(
                interaction,
                "❌ Mitglied konnte nicht gefunden werden."
            )

        if not has_role(
            interaction.user,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            return await safe_interaction_error(
                interaction,
                "❌ Du hast keine Berechtigung dafür."
            )

        message = interaction.message

        if not message:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag konnte nicht gefunden werden."
            )

        suggestion = data["suggestions"].get(str(message.id))

        if not suggestion:
            return await safe_interaction_error(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )

        suggestion["status"] = "abgelehnt"
        save_data(data)

        await refresh_suggestion(message, message.id)

        await interaction.response.send_message(
            "🔴 Der Vorschlag wurde abgelehnt.",
            ephemeral=True
        )


class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(SuggestionForButton())
        self.add_item(SuggestionAgainstButton())
        self.add_item(SuggestionAcceptButton())
        self.add_item(SuggestionRejectButton())


# =========================================================
# OWNER SYSTEM
# =========================================================

async def owner_permission_check(interaction):
    if not isinstance(interaction.user, discord.Member):
        await safe_interaction_error(
            interaction,
            "❌ Mitglied konnte nicht gefunden werden."
        )
        return False

    if not is_owner(interaction.user):
        await safe_interaction_error(
            interaction,
            "❌ Du hast nicht genügend Berechtigungen. "
            "Diese Funktion ist nur für Owner verfügbar."
        )
        return False

    return True


# ---------------------------------------------------------
# CHANNEL SELECT
# ---------------------------------------------------------

class OwnerChannelSelectView(discord.ui.View):
    def __init__(self, callback_function):
        super().__init__(timeout=60)

        self.callback_function = callback_function

        self.select = discord.ui.ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        self.select.callback = self.selected
        self.add_item(self.select)

    async def selected(self, interaction):
        if not await owner_permission_check(interaction):
            return

        selected = self.select.values[0]

        channel = interaction.guild.get_channel(selected.id)

        if not isinstance(channel, discord.TextChannel):
            return await safe_interaction_error(
                interaction,
                "❌ Bitte wähle einen normalen Textkanal."
            )

        await self.callback_function(
            interaction,
            channel
        )


# ---------------------------------------------------------
# ANKÜNDIGUNG
# ---------------------------------------------------------

class AnnouncementModal(discord.ui.Modal, title="Ankündigung"):
    title_input = discord.ui.TextInput(
        label="Titel",
        placeholder="Titel der Ankündigung",
        max_length=256,
        required=True
    )

    message_input = discord.ui.TextInput(
        label="Nachricht",
        placeholder="Text der Ankündigung...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction):
        if not await owner_permission_check(interaction):
            return

        embed = make_embed(
            str(self.title_input.value),
            str(self.message_input.value),
            discord.Color.blurple()
        )

        embed.set_author(
            name=f"Ankündigung von {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        try:
            await self.channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Ankündigung wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Announcement Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Ankündigung konnte nicht gesendet werden."
            )


async def owner_announcement_channel(interaction, channel):
    await interaction.response.send_modal(
        AnnouncementModal(channel)
    )


class OwnerAnnouncementButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "📢 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_announcement_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# BOT SAY
# ---------------------------------------------------------

class BotSayModal(discord.ui.Modal, title="Bot Say"):
    message_input = discord.ui.TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot schreiben?",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction):
        if not await owner_permission_check(interaction):
            return

        try:
            await self.channel.send(
                str(self.message_input.value)
            )

            await interaction.response.send_message(
                f"✅ Nachricht wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Bot Say Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Nachricht konnte nicht gesendet werden."
            )


async def owner_say_channel(interaction, channel):
    await interaction.response.send_modal(
        BotSayModal(channel)
    )


class OwnerSayButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_say"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "💬 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_say_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# CHANNEL LOCK
# ---------------------------------------------------------

async def owner_lock_channel(interaction, channel):
    try:
        everyone = interaction.guild.default_role

        await channel.set_permissions(
            everyone,
            send_messages=False,
            reason=f"Channel Lock von {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔒 {channel.mention} wurde gesperrt.",
            ephemeral=True
        )

    except Exception as e:
        print(f"Lock Fehler: {e}")
        await safe_interaction_error(
            interaction,
            "❌ Der Channel konnte nicht gesperrt werden."
        )


class OwnerLockButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Channel Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "🔒 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_lock_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# CHANNEL UNLOCK
# ---------------------------------------------------------

async def owner_unlock_channel(interaction, channel):
    try:
        everyone = interaction.guild.default_role

        await channel.set_permissions(
            everyone,
            send_messages=None,
            reason=f"Channel Unlock von {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔓 {channel.mention} wurde entsperrt.",
            ephemeral=True
        )

    except Exception as e:
        print(f"Unlock Fehler: {e}")
        await safe_interaction_error(
            interaction,
            "❌ Der Channel konnte nicht entsperrt werden."
        )


class OwnerUnlockButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Channel Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "🔓 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_unlock_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# BOT STATUS
# ---------------------------------------------------------

class OwnerStatusButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        uptime = int(time.time() - BOT_START_TIME)

        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = make_embed(
            "📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 Status",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="🏓 Ping",
            value=f"{round(bot.latency * 1000)} ms",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=f"{days}T {hours}H {minutes}M {seconds}S",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# SERVER INFO
# ---------------------------------------------------------

class OwnerServerInfoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_server_info"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        guild = interaction.guild

        embed = make_embed(
            "🖥️ Server Info",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="💬 Channels",
            value=str(len(guild.channels)),
            inline=True
        )

        embed.add_field(
            name="🎭 Rollen",
            value=str(len(guild.roles)),
            inline=True
        )

        embed.add_field(
            name="🆔 Server ID",
            value=str(guild.id),
            inline=False
        )

        embed.add_field(
            name="📅 Erstellt",
            value=discord.utils.format_dt(
                guild.created_at,
                style="F"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# GIVEAWAY
# ---------------------------------------------------------

class GiveawayModal(discord.ui.Modal, title="Giveaway starten"):
    prize = discord.ui.TextInput(
        label="Gewinn",
        placeholder="z. B. 10€ Gutschein",
        max_length=200,
        required=True
    )

    duration = discord.ui.TextInput(
        label="Dauer in Minuten",
        placeholder="z. B. 60",
        max_length=6,
        required=True
    )

    winners = discord.ui.TextInput(
        label="Anzahl Gewinner",
        placeholder="z. B. 1",
        max_length=3,
        required=True
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction):
        if not await owner_permission_check(interaction):
            return

        try:
            duration = int(str(self.duration.value))
            winner_count = int(str(self.winners.value))

            if duration <= 0:
                raise ValueError

            if winner_count <= 0:
                raise ValueError

            if duration > 10080:
                return await safe_interaction_error(
                    interaction,
                    "❌ Maximale Giveaway-Dauer: 10080 Minuten."
                )

        except ValueError:
            return await safe_interaction_error(
                interaction,
                "❌ Dauer und Gewinner müssen gültige positive Zahlen sein."
            )

        embed = make_embed(
            "🎁 GIVEAWAY",
            (
                f"## 🎉 {self.prize.value}\n\n"
                f"⏱️ Dauer: **{duration} Minuten**\n"
                f"🏆 Gewinner: **{winner_count}**\n\n"
                "Reagiere mit 🎉, um teilzunehmen!"
            ),
            discord.Color.gold()
        )

        embed.add_field(
            name="👑 Gestartet von",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🕒 Ende",
            value=discord.utils.format_dt(
                datetime.now(timezone.utc)
                + timedelta(minutes=duration),
                style="R"
            ),
            inline=True
        )

        try:
            message = await self.channel.send(
                embed=embed
            )

            await message.add_reaction("🎉")

            await interaction.response.send_message(
                f"🎁 Giveaway wurde in {self.channel.mention} gestartet.",
                ephemeral=True
            )

            asyncio.create_task(
                run_giveaway(
                    message,
                    duration,
                    winner_count,
                    str(self.prize.value)
                )
            )

        except Exception as e:
            print(f"Giveaway Fehler: {e}")
            await safe_interaction_error(
                interaction,
                "❌ Giveaway konnte nicht gestartet werden."
            )


async def run_giveaway(message, duration, winner_count, prize):
    try:
        await asyncio.sleep(duration * 60)

        message = await message.channel.fetch_message(
            message.id
        )

        reaction = discord.utils.get(
            message.reactions,
            emoji="🎉"
        )

        if reaction is None:
            winners = []
        else:
            users = []

            async for user in reaction.users():
                if user.bot:
                    continue

                users.append(user)

            # doppelte IDs vermeiden
            unique_users = {}

            for user in users:
                unique_users[user.id] = user

            users = list(unique_users.values())

            import random

            if users:
                winners = random.sample(
                    users,
                    min(winner_count, len(users))
                )
            else:
                winners = []

        if winners:
            mentions = ", ".join(
                user.mention for user in winners
            )

            description = (
                f"🎉 **Giveaway beendet!**\n\n"
                f"Gewinn: **{prize}**\n\n"
                f"🏆 Gewinner:\n{mentions}"
            )
        else:
            description = (
                f"🎉 **Giveaway beendet!**\n\n"
                f"Gewinn: **{prize}**\n\n"
                "❌ Es gab keine Teilnehmer."
            )

        embed = make_embed(
            "🎁 GIVEAWAY BEENDET",
            description,
            discord.Color.green()
        )

        await message.edit(
            embed=embed
        )

    except Exception as e:
        print(f"Giveaway Hintergrundfehler: {e}")


async def owner_giveaway_channel(interaction, channel):
    await interaction.response.send_modal(
        GiveawayModal(channel)
    )


class OwnerGiveawayButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Giveaway starten",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_giveaway"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "🎁 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_giveaway_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# NACHRICHTEN LÖSCHEN
# ---------------------------------------------------------

async def owner_clear_channel(interaction, channel):
    try:
        deleted = await channel.purge(
            limit=100
        )

        await interaction.response.send_message(
            f"🧹 Es wurden **{len(deleted)}** Nachrichten "
            f"in {channel.mention} gelöscht.",
            ephemeral=True
        )

    except discord.Forbidden:
        await safe_interaction_error(
            interaction,
            "❌ Ich habe keine Berechtigung, Nachrichten zu löschen."
        )

    except Exception as e:
        print(f"Clear Fehler: {e}")
        await safe_interaction_error(
            interaction,
            "❌ Nachrichten konnten nicht gelöscht werden."
        )


class OwnerClearButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nachrichten löschen",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_clear"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        await interaction.response.send_message(
            "🧹 Wähle den Kanal:",
            view=OwnerChannelSelectView(
                owner_clear_channel
            ),
            ephemeral=True
        )


# ---------------------------------------------------------
# USER INFO
# ---------------------------------------------------------

class OwnerUserInfoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_user_info"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        member = interaction.user

        roles = [
            role.mention
            for role in member.roles
            if role != interaction.guild.default_role
        ]

        embed = make_embed(
            "👤 User Info",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Name",
            value=member.display_name,
            inline=True
        )

        embed.add_field(
            name="🆔 ID",
            value=str(member.id),
            inline=True
        )

        embed.add_field(
            name="🤖 Bot",
            value="Ja" if member.bot else "Nein",
            inline=True
        )

        embed.add_field(
            name="📅 Account erstellt",
            value=discord.utils.format_dt(
                member.created_at,
                style="F"
            ),
            inline=False
        )

        embed.add_field(
            name="📅 Server beigetreten",
            value=discord.utils.format_dt(
                member.joined_at,
                style="F"
            ) if member.joined_at else "Unbekannt",
            inline=False
        )

        embed.add_field(
            name="🎭 Rollen",
            value=", ".join(roles) if roles else "Keine",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# ROLLEN INFO
# ---------------------------------------------------------

class OwnerRolesInfoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Rollen Info",
            emoji="🎭",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_roles_info"
        )

    async def callback(self, interaction):
        if not await owner_permission_check(interaction):
            return

        roles = []

        for role in reversed(interaction.guild.roles):
            if role.is_default():
                continue

            roles.append(
                f"{role.mention} — `{role.id}`"
            )

        text = "\n".join(roles)

        if len(text) > 3900:
            text = text[:3850] + "\n…"

        embed = make_embed(
            "🎭 Server-Rollen",
            text or "Keine Rollen gefunden.",
            discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER PANEL
# ---------------------------------------------------------

class OwnerPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(OwnerAnnouncementButton())
        self.add_item(OwnerSayButton())
        self.add_item(OwnerLockButton())
        self.add_item(OwnerUnlockButton())
        self.add_item(OwnerStatusButton())

        self.add_item(OwnerServerInfoButton())
        self.add_item(OwnerGiveawayButton())
        self.add_item(OwnerClearButton())
        self.add_item(OwnerUserInfoButton())
        self.add_item(OwnerRolesInfoButton())


def owner_panel_embed():
    return make_embed(
        "👑 Owner Panel",
        (
            "Hier stehen die Owner-Funktionen zur Verfügung.\n\n"
            "📢 **Ankündigung** — Embed in einen ausgewählten Kanal senden\n"
            "💬 **Bot Say** — Nachricht als Bot senden\n"
            "🔒 **Channel Lock** — Kanal sperren\n"
            "🔓 **Channel Unlock** — Kanal entsperren\n"
            "📊 **Bot Status** — Status und Ping anzeigen\n"
            "🖥️ **Server Info** — Serverinformationen anzeigen\n"
            "🎁 **Giveaway starten** — Giveaway in einem Kanal starten\n"
            "🧹 **Nachrichten löschen** — bis zu 100 Nachrichten löschen\n"
            "👤 **User Info** — eigene Userinformationen anzeigen\n"
            "🎭 **Rollen Info** — Serverrollen anzeigen\n\n"
            "🔐 Jede Funktion prüft die Owner-Rolle beim Klick."
        ),
        discord.Color.gold()
    )


# =========================================================
# PANEL REFRESH
# =========================================================

async def refresh_nametag_panel():
    # WICHTIG:
    # Dieses Panel verändert KEINEN Nickname.
    # Bestehende Nametags bleiben exakt so, wie sie sind.
    await update_panel(
        NAMETAG_CHANNEL_ID,
        NAMETAG_PANEL_MARKER,
        nametag_embed(),
        NametagView()
    )


async def refresh_application_panel():
    await update_panel(
        APPLICATION_CHANNEL_ID,
        APPLICATION_PANEL_MARKER,
        application_embed(),
        ApplicationView()
    )


async def refresh_dev_task_panel():
    await update_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        DEV_TASK_PANEL_MARKER,
        developer_task_embed(),
        DeveloperTaskView()
    )


async def refresh_community_panel():
    await update_panel(
        SUGGESTION_CHANNEL_ID,
        COMMUNITY_PANEL_MARKER,
        community_embed(),
        CommunityView()
    )


async def refresh_owner_panel():
    # Owner Panel wird in dem Kanal aktualisiert,
    # in dem ?ownerpanel ausgeführt wurde.
    pass


async def refresh_all_panels():
    print("🔄 Aktualisiere Panels...")

    await refresh_nametag_panel()

    # KENNZEICHEN:
    # Nur Panel aktualisieren.
    # KEINE Kennzeichen werden gelöscht.
    await refresh_license_panel()

    await refresh_application_panel()
    await refresh_dev_task_panel()
    await refresh_dev_shift_panel()
    await refresh_community_panel()

    print("✅ Panels aktualisiert.")
    print(
        f"🚗 Gespeicherte Kennzeichen: "
        f"{len(data['license_plates'])}"
    )

    print(
        f"🟢 Aktive Developer-Schichten: "
        f"{len(data['active_developer_shifts'])}"
    )


# =========================================================
# OWNER COMMAND
# =========================================================

@bot.command(name="ownerpanel")
async def ownerpanel_command(ctx):
    if not isinstance(ctx.author, discord.Member):
        return

    if not is_owner(ctx.author):
        return

    try:
        await ctx.send(
            content=panel_marker(OWNER_PANEL_MARKER),
            embed=owner_panel_embed(),
            view=OwnerPanelView()
        )

    except Exception as e:
        print(f"Owner Panel Fehler: {e}")


@bot.command(name="owner")
async def owner_command(ctx):
    if not isinstance(ctx.author, discord.Member):
        return

    if not is_owner(ctx.author):
        return

    try:
        await ctx.send(
            content=panel_marker(OWNER_PANEL_MARKER),
            embed=owner_panel_embed(),
            view=OwnerPanelView()
        )

    except Exception as e:
        print(f"Owner Panel Fehler: {e}")


@bot.command(name="communitypanel")
async def communitypanel_command(ctx):
    if not isinstance(ctx.author, discord.Member):
        return

    if not is_owner(ctx.author):
        return

    try:
        await ctx.send(
            content=panel_marker(COMMUNITY_PANEL_MARKER),
            embed=community_embed(),
            view=CommunityView()
        )

    except Exception as e:
        print(f"Community Panel Fehler: {e}")


# =========================================================
# ON COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(ctx, error):
    # WICHTIG:
    # ?top
    # ?punkte
    # ?weebsite
    # und alle anderen unbekannten Commands
    # werden einfach ignoriert.
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        try:
            await ctx.send(
                f"❌ Es fehlt ein Argument. Nutze `{PREFIX}help`."
            )
        except Exception:
            pass
        return

    if isinstance(error, commands.MemberNotFound):
        try:
            await ctx.send(
                "❌ Dieser Benutzer wurde nicht gefunden."
            )
        except Exception:
            pass
        return

    if isinstance(error, commands.RoleNotFound):
        try:
            await ctx.send(
                "❌ Diese Rolle wurde nicht gefunden."
            )
        except Exception:
            pass
        return

    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.send(
                "❌ Du hast nicht genügend Berechtigungen."
            )
        except Exception:
            pass
        return

    if isinstance(error, commands.CheckFailure):
        return

    print(
        f"COMMAND ERROR in {ctx.command}: "
        f"{type(error).__name__}: {error}"
    )


# =========================================================
# MESSAGE
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)


# =========================================================
# READY
# =========================================================

startup_done = False


@bot.event
async def on_ready():
    global startup_done

    print("=" * 60)
    print(f"🤖 Bot online: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Server: {GUILD_ID}")
    print("=" * 60)

    if startup_done:
        return

    startup_done = True

    try:
        await refresh_all_panels()
    except Exception as e:
        print(f"❌ Fehler beim ersten Panel-Refresh: {e}")
        traceback.print_exc()

    print("✅ Bot vollständig gestartet.")


# =========================================================
# SETUP HOOK
# =========================================================

async def setup_hook():
    # Persistente Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(CommunityView())
    bot.add_view(SuggestionView())
    bot.add_view(OwnerPanelView())

    print("✅ Persistente Views geladen.")


bot.setup_hook = setup_hook


# =========================================================
# START / AUTO-RESTART
# =========================================================

def start_bot():
    if not TOKEN:
        print("❌ DISCORD_TOKEN wurde nicht gefunden.")
        return

    print("🚀 Starte RLP Bot...")

    while True:
        try:
            bot.run(
                TOKEN,
                reconnect=True
            )

            # Wenn bot.run() normal beendet wird,
            # nicht direkt endlos neu starten.
            print("⚠️ Bot wurde beendet.")
            break

        except KeyboardInterrupt:
            print("🛑 Bot manuell beendet.")
            break

        except Exception as e:
            print("=" * 60)
            print("❌ BOT-PROZESS FEHLER")
            print(type(e).__name__, str(e))
            traceback.print_exc()
            print("🔄 Neustart in 5 Sekunden...")
            print("=" * 60)

            time.sleep(5)


if __name__ == "__main__":
    start_bot()
