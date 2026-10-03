import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
import os
import json
import random as random_module
import asyncio
import time
from datetime import datetime

# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789254679602
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276
SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439814863151155
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

# Community
SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200
BUG_CHANNEL_ID = 1556072637170716732

# Rollen
NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086
OWNER_ROLE_ID = 1544691379613999164

# Diese Rolle darf Vorschläge annehmen/ablehnen
SUGGESTION_REVIEW_ROLE_ID = 1530188150456979526

NAMETAG = "RLP | "
DATA_FILE = "bot_data.json"

# Panel-Marker
NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"

START_TIME = time.time()

# =========================================================
# BOT
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

quiz_lock = asyncio.Lock()
quiz_message_id = None
quiz_answer = None
quiz_starting = False

used_quiz_questions = set()

# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇺🇸🗽", "usa"),
    ("🇩🇪🍺", "deutschland"),
    ("🇫🇷🗼", "frankreich"),
    ("🇮🇹🍕", "italien"),
    ("🇯🇵🗾", "japan"),
    ("🇬🇧👑", "uk"),
    ("🌞🌍", "sonne"),
    ("🌧️☔", "regen"),
    ("🔥💧", "wasser"),
    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🦁", "löwe"),
    ("🐘", "elefant"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🚗", "auto"),
    ("✈️", "flugzeug"),
    ("🚲", "fahrrad"),
]

# =========================================================
# DATEN
# =========================================================

def default_data():
    return {
        "license_plates": {},
        "developer_tasks": [],
        "suggestions": {}
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        defaults = default_data()

        for key, value in defaults.items():
            if key not in data:
                data[key] = value

        return data

    except Exception as e:
        print(f"DATA LOAD ERROR: {e}")
        return default_data()


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"DATA SAVE ERROR: {e}")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    return bot.get_channel(channel_id)


def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def is_owner(member):
    return has_role(member, OWNER_ROLE_ID)


def is_suggestion_reviewer(member):
    return has_role(member, SUGGESTION_REVIEW_ROLE_ID)


def is_shift_allowed(member):
    return has_role(member, SHIFT_PERMISSION_ROLE_ID)


def safe_delete(message):
    async def delete():
        try:
            await message.delete()
        except Exception:
            pass

    return delete()


def uptime_text():
    seconds = int(time.time() - START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}T")
    if hours:
        parts.append(f"{hours}Std.")
    if minutes:
        parts.append(f"{minutes}Min.")

    parts.append(f"{seconds}Sek.")

    return " ".join(parts)


async def find_panel_message(marker):
    guild = get_guild()

    if guild is None:
        return None

    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=100):
                if message.author.id != bot.user.id:
                    continue

                for embed in message.embeds:
                    for field in embed.fields:
                        if field.value == marker:
                            return message

        except Exception:
            continue

    return None


async def delete_old_panels(channel, marker):
    try:
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue

            found = False

            for embed in message.embeds:
                for field in embed.fields:
                    if field.value == marker:
                        found = True
                        break

            if found:
                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:
        print(f"Panel Delete Error: {e}")


# =========================================================
# NAMETAG
# =========================================================

class NametagView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            NametagButton(
                label="Nametag setzen",
                emoji="🏷️",
                action="set",
                custom_id="rlp_nametag_set"
            )
        )

        self.add_item(
            NametagButton(
                label="Nametag entfernen",
                emoji="🗑️",
                action="remove",
                custom_id="rlp_nametag_remove"
            )
        )


class NametagButton(Button):
    def __init__(self, label, emoji, action, custom_id):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.primary if action == "set" else discord.ButtonStyle.danger,
            custom_id=custom_id
        )

        self.action = action

    async def callback(self, interaction):

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Nur Server-Mitglieder können das benutzen.",
                ephemeral=True
            )
            return

        member = interaction.user

        if self.action == "set":

            current_name = member.nick or member.name

            if current_name.startswith(NAMETAG):
                await interaction.response.send_message(
                    "🏷️ Du hast bereits einen Nametag.",
                    ephemeral=True
                )
                return

            new_name = NAMETAG + current_name

            try:
                await member.edit(nick=new_name)

                await interaction.response.send_message(
                    f"✅ Dein Nametag wurde gesetzt: `{new_name}`",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich kann deinen Nicknamen nicht ändern. Prüfe meine Rechte und Rollen-Hierarchie.",
                    ephemeral=True
                )

            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )

        else:

            current_name = member.nick

            if not current_name:
                await interaction.response.send_message(
                    "ℹ️ Du hast keinen Nicknamen.",
                    ephemeral=True
                )
                return

            new_name = current_name

            if new_name.startswith(NAMETAG):
                new_name = new_name[len(NAMETAG):]

            elif new_name.startswith("RLP |\u00a0"):
                new_name = new_name[len("RLP |\u00a0"):]

            else:
                await interaction.response.send_message(
                    "ℹ️ Dein Nametag ist bereits nicht vorhanden.",
                    ephemeral=True
                )
                return

            if not new_name.strip():
                new_name = None

            try:
                await member.edit(nick=new_name)

                await interaction.response.send_message(
                    "✅ Nametag wurde entfernt.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich kann deinen Nicknamen nicht ändern.",
                    ephemeral=True
                )

            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )


async def update_nametag_panel():

    channel = get_channel(NAMETAG_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    # WICHTIG:
    # Hier werden alte Panels NICHT gelöscht.
    # Dadurch bleiben die Nametags der Mitglieder komplett unangetastet.

    existing = None

    try:
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue

            for embed in message.embeds:
                for field in embed.fields:
                    if field.value == NAMETAG_PANEL_MARKER:
                        existing = message
                        break

    except Exception:
        pass

    if existing:
        return

    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            "Hier kannst du deinen **RLP |** Nametag verwalten.\n\n"
            "🏷️ **Nametag setzen**\n"
            "Setzt `RLP | ` vor deinen Namen.\n\n"
            "🗑️ **Nametag entfernen**\n"
            "Entfernt nur den `RLP | ` Nametag."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    await channel.send(embed=embed, view=NametagView())


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(Modal):
    def __init__(self):
        super().__init__(title="Kennzeichen registrieren")

        self.plate = TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 123",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction):

        value = self.plate.value.strip().upper()

        parts = value.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss einen Präfix und eine Nummer enthalten.",
                ephemeral=True
            )
            return

        numeric_token = parts[-1]

        if not numeric_token.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Kennzeichen-Komponente muss eine Zahl sein.",
                ephemeral=True
            )
            return

        plates = data["license_plates"]

        for user_id, plate in plates.items():

            old_parts = plate["plate"].split()

            if old_parts and old_parts[-1] == numeric_token:
                await interaction.response.send_message(
                    f"❌ Die Nummer `{numeric_token}` ist bereits vergeben.",
                    ephemeral=True
                )
                return

        plates[str(interaction.user.id)] = {
            "plate": value,
            "user_id": interaction.user.id
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{value}` wurde registriert.",
            ephemeral=True
        )

        await update_license_panel()


class LicensePlateView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            Button(
                label="Kennzeichen registrieren",
                emoji="🚗",
                style=discord.ButtonStyle.success,
                custom_id="rlp_license_register"
            )
        )

        self.children[0].callback = self.register_callback

    async def register_callback(self, interaction):
        await interaction.response.send_modal(LicensePlateModal())


async def update_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    await delete_old_panels(channel, LICENSE_PANEL_MARKER)

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen registrieren.\n\n"
            "⚠️ Die Nummer am Ende des Kennzeichens muss **global einzigartig** sein."
        ),
        color=discord.Color.blue()
    )

    if data["license_plates"]:

        lines = []

        for plate_data in data["license_plates"].values():

            user = channel.guild.get_member(plate_data["user_id"])

            if user:
                name = user.display_name
            else:
                name = f"User {plate_data['user_id']}"

            lines.append(
                f"🚗 `{plate_data['plate']}` — **{name}**"
            )

        embed.add_field(
            name="Registrierte Kennzeichen",
            value="\n".join(lines),
            inline=False
        )

    else:

        embed.add_field(
            name="Registrierte Kennzeichen",
            value="Noch keine Kennzeichen registriert.",
            inline=False
        )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# BEWERBUNG
# =========================================================

class ApplicationModal(Modal):
    def __init__(self):
        super().__init__(title="Bewerbung")

        self.name_input = TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )

        self.age_input = TextInput(
            label="Alter",
            placeholder="Dein Alter",
            required=True,
            max_length=3
        )

        self.reason_input = TextInput(
            label="Warum möchtest du ins Team?",
            placeholder="Schreibe etwas über dich...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.name_input)
        self.add_item(self.age_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction):

        channel = get_channel(APPLICATION_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bewerbungskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Neue Bewerbung",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="📝 Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="💬 Grund",
            value=self.reason_input.value,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)

        button = Button(
            label="Bewerben",
            emoji="📋",
            style=discord.ButtonStyle.success,
            custom_id="rlp_application_button"
        )

        button.callback = self.application_callback

        self.add_item(button)

    async def application_callback(self, interaction):
        await interaction.response.send_modal(ApplicationModal())


async def update_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    await delete_old_panels(channel, APPLICATION_PANEL_MARKER)

    embed = discord.Embed(
        title="📋 Team-Bewerbung",
        description=(
            "Du möchtest Teil des Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# DEVELOPER AUFGABEN
# =========================================================

class DeveloperTaskModal(Modal):
    def __init__(self):
        super().__init__(title="Developer Aufgabe")

        self.task = TextInput(
            label="Aufgabe",
            placeholder="Was soll erledigt werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.task)

    async def on_submit(self, interaction):

        if not is_shift_allowed(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        task = {
            "id": len(data["developer_tasks"]) + 1,
            "task": self.task.value,
            "author_id": interaction.user.id,
            "created_at": datetime.utcnow().isoformat(),
            "done": False
        }

        data["developer_tasks"].append(task)
        save_data()

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if isinstance(channel, discord.TextChannel):

            embed = discord.Embed(
                title=f"🖥️ Developer Aufgabe #{task['id']}",
                description=task["task"],
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention,
                inline=False
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Developer-Aufgabe erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(View):
    def __init__(self):
        super().__init__(timeout=None)

        button = Button(
            label="Aufgabe erstellen",
            emoji="🖥️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

        button.callback = self.task_callback
        self.add_item(button)

    async def task_callback(self, interaction):
        await interaction.response.send_modal(DeveloperTaskModal())


async def update_developer_task_panel():

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    await delete_old_panels(channel, DEV_TASK_PANEL_MARKER)

    embed = discord.Embed(
        title="🖥️ Developer Aufgaben",
        description=(
            "Hier können berechtigte Teammitglieder neue Developer-Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# DEVELOPER SCHICHT
# =========================================================

class DeveloperShiftView(View):
    def __init__(self):
        super().__init__(timeout=None)

        start_button = Button(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_dev_shift_start"
        )

        end_button = Button(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_dev_shift_end"
        )

        start_button.callback = self.start_callback
        end_button.callback = self.end_callback

        self.add_item(start_button)
        self.add_item(end_button)

    async def start_callback(self, interaction):

        if not is_shift_allowed(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist bereits in einer Developer-Schicht.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                role,
                reason=f"Developer-Schicht gestartet von {interaction.user}"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if isinstance(log_channel, discord.TextChannel):
                await log_channel.send(
                    f"🟢 **Developer-Schicht gestartet**\n"
                    f"👤 {interaction.user.mention}"
                )

            await interaction.response.send_message(
                "🟢 Deine Developer-Schicht wurde gestartet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Schicht-Rolle nicht vergeben.",
                ephemeral=True
            )

    async def end_callback(self, interaction):

        if not is_shift_allowed(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht in einer Developer-Schicht.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.remove_roles(
                role,
                reason=f"Developer-Schicht beendet von {interaction.user}"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if isinstance(log_channel, discord.TextChannel):
                await log_channel.send(
                    f"🔴 **Developer-Schicht beendet**\n"
                    f"👤 {interaction.user.mention}"
                )

            await interaction.response.send_message(
                "🔴 Deine Developer-Schicht wurde beendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Schicht-Rolle nicht entfernen.",
                ephemeral=True
            )


async def update_developer_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    await delete_old_panels(channel, SHIFT_PANEL_MARKER)

    embed = discord.Embed(
        title="🖥️ Developer-Schicht",
        description=(
            "Nutze die Buttons, um deine Developer-Schicht zu starten oder zu beenden."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel",
        value=SHIFT_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# VORSCHLÄGE
# =========================================================

def build_suggestion_embed(suggestion):

    status = suggestion.get("status", "offen")

    if status == "angenommen":
        color = discord.Color.green()
        status_text = "🟢 Angenommen"

    elif status == "abgelehnt":
        color = discord.Color.red()
        status_text = "🔴 Abgelehnt"

    else:
        color = discord.Color.gold()
        status_text = "🟡 Offen"

    votes_for = len(suggestion.get("for_votes", []))
    votes_against = len(suggestion.get("against_votes", []))

    embed = discord.Embed(
        title="💡 Community-Vorschlag",
        description=suggestion["text"],
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 Eingereicht von",
        value=f"<@{suggestion['author_id']}>",
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=False
    )

    embed.add_field(
        name="🟢 Dafür",
        value=f"**{votes_for}**",
        inline=True
    )

    embed.add_field(
        name="🔴 Dagegen",
        value=f"**{votes_against}**",
        inline=True
    )

    embed.add_field(
        name="🆔 Vorschlag",
        value=f"`{suggestion['id']}`",
        inline=False
    )

    embed.set_footer(
        text="RLP Community • Vorschlagssystem"
    )

    return embed


class SuggestionView(View):
    def __init__(self):
        super().__init__(timeout=None)

        accept = Button(
            label="Annehmen",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_accept"
        )

        reject = Button(
            label="Ablehnen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_reject"
        )

        for_button = Button(
            label="Für den Vorschlag",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_for"
        )

        against_button = Button(
            label="Gegen den Vorschlag",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_against"
        )

        accept.callback = self.accept_callback
        reject.callback = self.reject_callback
        for_button.callback = self.for_callback
        against_button.callback = self.against_callback

        self.add_item(accept)
        self.add_item(reject)
        self.add_item(for_button)
        self.add_item(against_button)

    async def accept_callback(self, interaction):

        if not is_suggestion_reviewer(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Vorschläge anzunehmen.",
                ephemeral=True
            )
            return

        suggestion = data["suggestions"].get(str(interaction.message.id))

        if suggestion is None:
            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )
            return

        suggestion["status"] = "angenommen"
        save_data()

        await interaction.response.edit_message(
            embed=build_suggestion_embed(suggestion),
            view=SuggestionView()
        )

    async def reject_callback(self, interaction):

        if not is_suggestion_reviewer(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Vorschläge abzulehnen.",
                ephemeral=True
            )
            return

        suggestion = data["suggestions"].get(str(interaction.message.id))

        if suggestion is None:
            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )
            return

        suggestion["status"] = "abgelehnt"
        save_data()

        await interaction.response.edit_message(
            embed=build_suggestion_embed(suggestion),
            view=SuggestionView()
        )

    async def for_callback(self, interaction):

        suggestion = data["suggestions"].get(str(interaction.message.id))

        if suggestion is None:
            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        for_votes = suggestion.setdefault("for_votes", [])
        against_votes = suggestion.setdefault("against_votes", [])

        if user_id in for_votes or user_id in against_votes:
            await interaction.response.send_message(
                "❌ Du hast bei diesem Vorschlag bereits abgestimmt.",
                ephemeral=True
            )
            return

        for_votes.append(user_id)
        save_data()

        await interaction.response.edit_message(
            embed=build_suggestion_embed(suggestion),
            view=SuggestionView()
        )

    async def against_callback(self, interaction):

        suggestion = data["suggestions"].get(str(interaction.message.id))

        if suggestion is None:
            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        for_votes = suggestion.setdefault("for_votes", [])
        against_votes = suggestion.setdefault("against_votes", [])

        if user_id in for_votes or user_id in against_votes:
            await interaction.response.send_message(
                "❌ Du hast bei diesem Vorschlag bereits abgestimmt.",
                ephemeral=True
            )
            return

        against_votes.append(user_id)
        save_data()

        await interaction.response.edit_message(
            embed=build_suggestion_embed(suggestion),
            view=SuggestionView()
        )


class SuggestionModal(Modal):
    def __init__(self):
        super().__init__(title="Vorschlag einreichen")

        self.text_input = TextInput(
            label="Dein Vorschlag",
            placeholder="Was möchtest du verbessern oder hinzufügen?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text_input)

    async def on_submit(self, interaction):

        channel = get_channel(SUGGESTION_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Vorschlagskanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        next_id = len(data["suggestions"]) + 1

        suggestion = {
            "id": next_id,
            "author_id": interaction.user.id,
            "text": self.text_input.value,
            "status": "offen",
            "for_votes": [],
            "against_votes": []
        }

        message = await channel.send(
            embed=build_suggestion_embed(suggestion),
            view=SuggestionView()
        )

        data["suggestions"][str(message.id)] = suggestion
        save_data()

        await interaction.response.send_message(
            f"✅ Dein Vorschlag wurde in {channel.mention} eingereicht.",
            ephemeral=True
        )


# =========================================================
# COMMUNITY PANEL
# =========================================================

class FeedbackModal(Modal):
    def __init__(self):
        super().__init__(title="Feedback")

        self.text_input = TextInput(
            label="Dein Feedback",
            placeholder="Was möchtest du uns mitteilen?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text_input)

    async def on_submit(self, interaction):

        channel = get_channel(FEEDBACK_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Feedback-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 Neues Feedback",
            description=self.text_input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


class BugModal(Modal):
    def __init__(self):
        super().__init__(title="Bug melden")

        self.text_input = TextInput(
            label="Bug",
            placeholder="Beschreibe den Fehler...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text_input)

    async def on_submit(self, interaction):

        channel = get_channel(BUG_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bug-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🐞 Neuer Bug",
            description=self.text_input.value,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Gemeldet von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Der Bug wurde gemeldet.",
            ephemeral=True
        )


class CommunityPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

        suggestion = Button(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

        feedback = Button(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_feedback"
        )

        bug = Button(
            label="Bug melden",
            emoji="🐞",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_community_bug"
        )

        suggestion.callback = self.suggestion_callback
        feedback.callback = self.feedback_callback
        bug.callback = self.bug_callback

        self.add_item(suggestion)
        self.add_item(feedback)
        self.add_item(bug)

    async def suggestion_callback(self, interaction):
        await interaction.response.send_modal(SuggestionModal())

    async def feedback_callback(self, interaction):
        await interaction.response.send_modal(FeedbackModal())

    async def bug_callback(self, interaction):
        await interaction.response.send_modal(BugModal())


async def update_community_panel():

    message = await find_panel_message(COMMUNITY_PANEL_MARKER)

    if message is None:
        return

    channel = message.channel

    try:
        await message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="💬 Community",
        description=(
            "Hier kannst du uns deine Meinung mitteilen.\n\n"
            "💡 **Vorschlag**\n"
            "Sende einen Vorschlag an das Vorschlagssystem.\n\n"
            "💬 **Feedback**\n"
            "Sende uns Feedback.\n\n"
            "🐞 **Bug melden**\n"
            "Melde einen Fehler."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=COMMUNITY_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=CommunityPanelView()
    )


# =========================================================
# OWNER PANEL
# =========================================================

class AnnouncementModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Ankündigung")

        self.channel = channel

        self.title_input = TextInput(
            label="Titel",
            placeholder="Titel der Ankündigung",
            required=True,
            max_length=256
        )

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Text der Ankündigung...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.message_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📢 {self.title_input.value}",
            description=self.message_input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        try:
            await self.channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Ankündigung wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann dort keine Nachricht senden.",
                ephemeral=True
            )


class BotSayModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Bot Say")

        self.channel = channel

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.message_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        try:
            await self.channel.send(self.message_input.value)

            await interaction.response.send_message(
                f"✅ Nachricht wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann dort nicht schreiben.",
                ephemeral=True
            )


class OwnerChannelSelectView(View):
    def __init__(self, action):
        super().__init__(timeout=180)

        self.action = action

        self.select = ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        self.select.callback = self.channel_selected

        self.add_item(self.select)

    async def channel_selected(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        selected = self.select.values[0]

        channel = interaction.guild.get_channel(selected.id)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Der ausgewählte Kanal ist kein Textkanal.",
                ephemeral=True
            )
            return

        try:

            if self.action == "announcement":
                await interaction.response.send_modal(
                    AnnouncementModal(channel)
                )
                return

            if self.action == "say":
                await interaction.response.send_modal(
                    BotSayModal(channel)
                )
                return

            if self.action == "lock":

                await interaction.response.defer(ephemeral=True)

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = False

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Channel Lock durch {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔒 {channel.mention} wurde gesperrt.",
                    ephemeral=True
                )

                return

            if self.action == "unlock":

                await interaction.response.defer(ephemeral=True)

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = None

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Channel Unlock durch {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

        except discord.Forbidden:

            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Der Bot hat dort nicht genügend Rechte.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Der Bot hat dort nicht genügend Rechte.",
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"OWNER CHANNEL SELECT ERROR: "
                f"{type(e).__name__}: {e}"
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )


class OwnerAnnouncementButton(Button):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 **Wähle den Kanal für die Ankündigung:**",
            view=OwnerChannelSelectView("announcement"),
            ephemeral=True
        )


class OwnerSayButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_say"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💬 **Wähle den Kanal:**",
            view=OwnerChannelSelectView("say"),
            ephemeral=True
        )


class OwnerLockButton(Button):
    def __init__(self):
        super().__init__(
            label="Channel Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 **Wähle den Kanal:**",
            view=OwnerChannelSelectView("lock"),
            ephemeral=True
        )


class OwnerUnlockButton(Button):
    def __init__(self):
        super().__init__(
            label="Channel Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔓 **Wähle den Kanal:**",
            view=OwnerChannelSelectView("unlock"),
            ephemeral=True
        )


class OwnerStatusButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        latency = round(bot.latency * 1000)

        total_members = sum(
            guild.member_count or 0
            for guild in bot.guilds
        )

        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 Status",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="📡 Ping",
            value=f"{latency} ms",
            inline=True
        )

        embed.add_field(
            name="🌐 Server",
            value=str(len(bot.guilds)),
            inline=True
        )

        embed.add_field(
            name="👥 Nutzer",
            value=str(total_members),
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime_text(),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerServerInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_serverinfo"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server Info",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="🆔 Server ID",
            value=str(guild.id),
            inline=True
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="💬 Textkanäle",
            value=str(len(guild.text_channels)),
            inline=True
        )

        embed.add_field(
            name="🔊 Sprachkanäle",
            value=str(len(guild.voice_channels)),
            inline=True
        )

        embed.add_field(
            name="🎭 Rollen",
            value=str(len(guild.roles)),
            inline=True
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


class OwnerPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(OwnerAnnouncementButton())
        self.add_item(OwnerSayButton())
        self.add_item(OwnerLockButton())
        self.add_item(OwnerUnlockButton())
        self.add_item(OwnerStatusButton())
        self.add_item(OwnerServerInfoButton())


async def send_owner_panel(channel):

    embed = discord.Embed(
        title="👑 Owner Panel",
        description=(
            "Hier kannst du verschiedene Server- und Bot-Funktionen verwalten.\n\n"
            "📢 **Ankündigung**\n"
            "Kanal auswählen → Titel und Nachricht eingeben.\n\n"
            "💬 **Bot Say**\n"
            "Kanal auswählen → Nachricht eingeben.\n\n"
            "🔒 **Channel Lock**\n"
            "Kanal auswählen → Kanal wird gesperrt.\n\n"
            "🔓 **Channel Unlock**\n"
            "Kanal auswählen → Kanal wird entsperrt.\n\n"
            "📊 **Bot Status**\n"
            "Zeigt den Bot-Status.\n\n"
            "🖥️ **Server Info**\n"
            "Zeigt Informationen über den Server."
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Panel",
        value=OWNER_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=OwnerPanelView()
    )


# =========================================================
# QUIZ
# =========================================================

async def reset_quiz():

    global quiz_message_id
    global quiz_answer
    global used_quiz_questions

    channel = get_channel(QUIZ_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    # Altes Quiz löschen, falls bekannt
    if quiz_message_id:

        try:
            old_message = await channel.fetch_message(
                quiz_message_id
            )

            await old_message.delete()

        except Exception:
            pass

    quiz_message_id = None
    quiz_answer = None

    # Falls die ID nach Neustart unbekannt ist:
    # nur Nachrichten löschen, die eindeutig wie unser Quiz aussehen.
    try:

        async for message in channel.history(limit=30):

            if message.author.id != bot.user.id:
                continue

            if message.content.startswith("🧠 **Emoji Quiz"):
                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception:
        pass

    await send_quiz_question()


async def send_quiz_question():

    global quiz_message_id
    global quiz_answer
    global quiz_starting
    global used_quiz_questions

    async with quiz_lock:

        if quiz_starting:
            return

        quiz_starting = True

        try:

            channel = get_channel(QUIZ_CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                return

            available = [
                q for i, q in enumerate(QUIZ_QUESTIONS)
                if i not in used_quiz_questions
            ]

            if not available:

                used_quiz_questions.clear()

                available = QUIZ_QUESTIONS.copy()

            index, question = random_module.choice(
                [
                    (i, q)
                    for i, q in enumerate(QUIZ_QUESTIONS)
                    if i not in used_quiz_questions
                ]
            )

            used_quiz_questions.add(index)

            emoji_text, answer = question

            message = await channel.send(
                f"🧠 **Emoji Quiz**\n\n"
                f"{emoji_text}\n\n"
                f"Schreibe deine Antwort!"
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower()

        finally:

            quiz_starting = False


# =========================================================
# VOICE SUPPORT LOG
# =========================================================

@bot.event
async def on_voice_state_update(member, before, after):

    log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

    if not isinstance(log_channel, discord.TextChannel):
        return

    support_channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if not isinstance(support_channel, discord.VoiceChannel):
        return

    if (
        before.channel != support_channel
        and after.channel == support_channel
    ):

        await log_channel.send(
            f"🔊 **Support beigetreten**\n"
            f"👤 {member.mention}\n"
            f"📍 {support_channel.mention}"
        )

    elif (
        before.channel == support_channel
        and after.channel != support_channel
    ):

        await log_channel.send(
            f"🔇 **Support verlassen**\n"
            f"👤 {member.mention}"
        )


# =========================================================
# MESSAGE / QUIZ
# =========================================================

@bot.event
async def on_message(message):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:

        if quiz_answer is None:

            await asyncio.sleep(6)
            await safe_delete(message)
            return

        user_answer = message.content.strip().lower()

        if user_answer == quiz_answer:

            current_question_id = quiz_message_id

            await safe_delete(message)

            if current_question_id:

                try:
                    question_message = await message.channel.fetch_message(
                        current_question_id
                    )

                    await safe_delete(question_message)

                except Exception:
                    pass

            quiz_message_id = None
            quiz_answer = None

            success_message = await message.channel.send(
                f"✅ **Richtig!** {message.author.mention}"
            )

            await asyncio.sleep(4)

            await safe_delete(success_message)

            await send_quiz_question()

            return

        await safe_delete(message)

        wrong_message = await message.channel.send(
            f"❌ **Falsch!** {message.author.mention}"
        )

        await asyncio.sleep(4)

        await safe_delete(wrong_message)

        return

    await bot.process_commands(message)


# =========================================================
# OWNER / SERVER COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def ownerpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def owner(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🖥️ Server Info",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Server",
        value=guild.name,
        inline=True
    )

    embed.add_field(
        name="Mitglieder",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="Rollen",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="Textkanäle",
        value=str(len(guild.text_channels)),
        inline=True
    )

    embed.add_field(
        name="Sprachkanäle",
        value=str(len(guild.voice_channels)),
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Bot Info",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Bot",
        value=str(bot.user),
        inline=True
    )

    embed.add_field(
        name="Server",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=uptime_text(),
        inline=True
    )

    embed.add_field(
        name="Ping",
        value=f"{round(bot.latency * 1000)} ms",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Info",
        color=discord.Color.blue()
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
        name="Account erstellt",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    embed.add_field(
        name="Server beigetreten",
        value=discord.utils.format_dt(
            member.joined_at,
            style="F"
        ) if member.joined_at else "Unbekannt",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def roleinfo(ctx, role: discord.Role):

    embed = discord.Embed(
        title="🎭 Rollen Info",
        color=role.color
    )

    embed.add_field(
        name="Name",
        value=role.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(role.id),
        inline=True
    )

    embed.add_field(
        name="Mitglieder",
        value=str(len(role.members)),
        inline=True
    )

    embed.add_field(
        name="Position",
        value=str(role.position),
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def channelinfo(
    ctx,
    channel: discord.TextChannel = None
):

    channel = channel or ctx.channel

    embed = discord.Embed(
        title="📺 Kanal Info",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Name",
        value=channel.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(channel.id),
        inline=True
    )

    embed.add_field(
        name="Kategorie",
        value=channel.category.name if channel.category else "Keine",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"🖼️ Avatar von {member.display_name}",
        color=discord.Color.blue()
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


@bot.command()
async def banner(ctx, member: discord.Member = None):

    member = member or ctx.author

    user = await bot.fetch_user(member.id)

    if user.banner is None:
        await ctx.send(
            "ℹ️ Dieser User hat keinen Banner."
        )
        return

    embed = discord.Embed(
        title=f"🖼️ Banner von {member.display_name}",
        color=discord.Color.blue()
    )

    embed.set_image(
        url=user.banner.url
    )

    await ctx.send(embed=embed)


@bot.command()
async def membercount(ctx):

    await ctx.send(
        f"👥 Der Server hat **{ctx.guild.member_count} Mitglieder**."
    )


@bot.command()
async def rolelist(ctx):

    roles = [
        role.mention
        for role in reversed(ctx.guild.roles)
        if role.name != "@everyone"
    ]

    if not roles:
        await ctx.send("Keine Rollen vorhanden.")
        return

    text = "\n".join(roles)

    if len(text) > 4000:
        text = text[:3990] + "..."

    embed = discord.Embed(
        title="🎭 Rollen",
        description=text,
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)


@bot.command()
async def channellist(ctx):

    channels = [
        channel.mention
        for channel in ctx.guild.channels
    ]

    text = "\n".join(channels)

    if len(text) > 4000:
        text = text[:3990] + "..."

    embed = discord.Embed(
        title="📺 Kanäle",
        description=text,
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)


# =========================================================
# COMMUNITY COMMANDS
# =========================================================

@bot.command()
async def suggest(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Benutzung: `!suggest Dein Vorschlag`",
            delete_after=8
        )
        return

    channel = get_channel(SUGGESTION_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        await ctx.send(
            "❌ Vorschlagskanal nicht gefunden.",
            delete_after=5
        )
        return

    suggestion = {
        "id": len(data["suggestions"]) + 1,
        "author_id": ctx.author.id,
        "text": text,
        "status": "offen",
        "for_votes": [],
        "against_votes": []
    }

    message = await channel.send(
        embed=build_suggestion_embed(suggestion),
        view=SuggestionView()
    )

    data["suggestions"][str(message.id)] = suggestion
    save_data()

    await ctx.send(
        f"✅ Dein Vorschlag wurde in {channel.mention} gesendet.",
        delete_after=5
    )


@bot.command()
async def feedback(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Benutzung: `!feedback Dein Feedback`",
            delete_after=8
        )
        return

    channel = get_channel(FEEDBACK_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        await ctx.send(
            "❌ Feedback-Kanal nicht gefunden.",
            delete_after=5
        )
        return

    embed = discord.Embed(
        title="💬 Neues Feedback",
        description=text,
        color=discord.Color.blue()
    )

    embed.add_field(
        name="👤 Von",
        value=ctx.author.mention,
        inline=False
    )

    await channel.send(embed=embed)

    await ctx.send(
        "✅ Feedback wurde gesendet.",
        delete_after=5
    )


@bot.command()
async def bug(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Benutzung: `!bug Beschreibung`",
            delete_after=8
        )
        return

    channel = get_channel(BUG_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        await ctx.send(
            "❌ Bug-Kanal nicht gefunden.",
            delete_after=5
        )
        return

    embed = discord.Embed(
        title="🐞 Neuer Bug",
        description=text,
        color=discord.Color.red()
    )

    embed.add_field(
        name="👤 Gemeldet von",
        value=ctx.author.mention,
        inline=False
    )

    await channel.send(embed=embed)

    await ctx.send(
        "✅ Bug wurde gemeldet.",
        delete_after=5
    )


@bot.command()
async def report(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Benutzung: `!report Beschreibung`",
            delete_after=8
        )
        return

    channel = get_channel(BUG_CHANNEL_ID)

    if isinstance(channel, discord.TextChannel):

        embed = discord.Embed(
            title="🚨 Meldung",
            description=text,
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 Von",
            value=ctx.author.mention,
            inline=False
        )

        await channel.send(embed=embed)

    await ctx.send(
        "✅ Deine Meldung wurde weitergeleitet.",
        delete_after=5
    )


@bot.command()
async def apply(ctx):

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if isinstance(channel, discord.TextChannel):
        await ctx.send(
            f"📋 Bewerben kannst du dich in {channel.mention}.",
            delete_after=8
        )
    else:
        await ctx.send(
            "📋 Der Bewerbungskanal wurde nicht gefunden.",
            delete_after=5
        )


@bot.command()
async def support(ctx):

    channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if isinstance(channel, discord.VoiceChannel):

        await ctx.send(
            f"🔊 Support findest du hier: {channel.mention}"
        )

    else:
        await ctx.send(
            "❌ Support-Kanal nicht gefunden."
        )


@bot.command()
async def supportinfo(ctx):

    channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if isinstance(channel, discord.VoiceChannel):

        await ctx.send(
            f"🔊 **Support**\n\n"
            f"Wenn du Hilfe brauchst, komm in {channel.mention}."
        )

    else:
        await ctx.send(
            "❌ Support-Kanal nicht gefunden."
        )


# =========================================================
# FUN
# =========================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question=None):

    if not question:
        await ctx.send(
            "🎱 Stell mir eine Frage."
        )
        return

    answers = [
        "Ja.",
        "Nein.",
        "Vielleicht.",
        "Sehr wahrscheinlich.",
        "Eher nicht.",
        "Ich denke schon.",
        "Ich glaube nicht."
    ]

    await ctx.send(
        f"🎱 **8-Ball:** {random_module.choice(answers)}"
    )


@bot.command()
async def coinflip(ctx):

    result = random_module.choice(
        ["Kopf", "Zahl"]
    )

    await ctx.send(
        f"🪙 **{result}**"
    )


@bot.command()
async def dice(ctx):

    number = random_module.randint(1, 6)

    await ctx.send(
        f"🎲 Du hast eine **{number}** gewürfelt."
    )


@bot.command()
async def choose(ctx, *, choices=None):

    if not choices:
        await ctx.send(
            "❌ Benutzung: `!choose A | B | C`"
        )
        return

    options = [
        option.strip()
        for option in choices.split("|")
        if option.strip()
    ]

    if len(options) < 2:
        await ctx.send(
            "❌ Gib mindestens zwei Möglichkeiten an."
        )
        return

    await ctx.send(
        f"🤔 Ich wähle: **{random_module.choice(options)}**"
    )


@bot.command(name="random")
async def random_number(ctx, minimum=None, maximum=None):

    try:

        minimum = int(minimum)
        maximum = int(maximum)

    except Exception:

        await ctx.send(
            "❌ Benutzung: `!random 1 100`"
        )
        return

    if minimum > maximum:
        minimum, maximum = maximum, minimum

    number = random_module.randint(
        minimum,
        maximum
    )

    await ctx.send(
        f"🎲 Zufallszahl: **{number}**"
    )


@bot.command()
async def serverage(ctx):

    created = ctx.guild.created_at

    await ctx.send(
        f"📅 Der Server wurde am "
        f"{discord.utils.format_dt(created, style='D')} erstellt."
    )


@bot.command()
async def member(ctx):

    await ctx.send(
        f"👤 Du bist **{ctx.author.display_name}**."
    )


# =========================================================
# PRAKTISCHE COMMANDS
# =========================================================

@bot.command()
async def uptime(ctx):

    await ctx.send(
        f"⏱️ Bot-Uptime: **{uptime_text()}**"
    )


@bot.command()
async def invite(ctx):

    permissions = discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        read_message_history=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions,
        scopes=("bot",)
    )

    await ctx.send(
        f"🔗 **Bot einladen:**\n{url}"
    )


@bot.command()
async def rules(ctx):

    rules_channel = None

    for channel in ctx.guild.text_channels:

        if channel.name.lower() in [
            "regeln",
            "rules",
            "server-regeln"
        ]:
            rules_channel = channel
            break

    if rules_channel:

        await ctx.send(
            f"📜 Unsere Regeln findest du hier: "
            f"{rules_channel.mention}"
        )

    else:

        await ctx.send(
            "📜 Einen festen Regelkanal konnte ich nicht finden."
        )


@bot.command()
async def socials(ctx):

    await ctx.send(
        "🌐 **Socials**\n"
        "Unsere Social-Media-Links kannst du hier eintragen."
    )


@bot.command()
async def website(ctx):

    await ctx.send(
        "🌐 Die Website ist aktuell noch nicht hinterlegt."
    )


@bot.command()
async def team(ctx):

    await ctx.send(
        "👥 **Team**\n"
        "Unser Team findest du auf dem Server."
    )


@bot.command()
async def status(ctx):

    await ctx.send(
        f"🟢 **Online**\n"
        f"📡 Ping: `{round(bot.latency * 1000)}ms`\n"
        f"⏱️ Uptime: `{uptime_text()}`"
    )


# =========================================================
# PANEL COMMANDS
# =========================================================

@bot.command()
async def communitypanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_community_panel_here(ctx.channel)

    await ctx.send(
        "✅ Community-Panel erstellt.",
        delete_after=5
    )


async def send_community_panel_here(channel):

    embed = discord.Embed(
        title="💬 Community",
        description=(
            "Hier kannst du uns deine Meinung mitteilen.\n\n"
            "💡 **Vorschlag**\n"
            "Reiche einen Vorschlag ein.\n\n"
            "💬 **Feedback**\n"
            "Sende uns Feedback.\n\n"
            "🐞 **Bug melden**\n"
            "Melde einen Fehler."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=COMMUNITY_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=CommunityPanelView()
    )


# =========================================================
# HELP
# =========================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot Hilfe",
        description="Hier findest du die wichtigsten Befehle.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🛠️ Allgemein",
        value=(
            "`!ping`\n"
            "`!help`\n"
            "`!uptime`\n"
            "`!invite`\n"
            "`!status`\n"
            "`!serverinfo`\n"
            "`!botinfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="👤 Mitglieder",
        value=(
            "`!userinfo @User`\n"
            "`!avatar @User`\n"
            "`!banner @User`\n"
            "`!membercount`\n"
            "`!roleinfo @Rolle`\n"
            "`!channelinfo #Kanal`\n"
            "`!rolelist`\n"
            "`!channellist`"
        ),
        inline=False
    )

    embed.add_field(
        name="💬 Community",
        value=(
            "`!suggest <Text>`\n"
            "`!feedback <Text>`\n"
            "`!bug <Text>`\n"
            "`!report <Text>`\n"
            "`!apply`\n"
            "`!support`\n"
            "`!supportinfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value=(
            "`!8ball <Frage>`\n"
            "`!coinflip`\n"
            "`!dice`\n"
            "`!choose A | B | C`\n"
            "`!random 1 100`\n"
            "`!serverage`\n"
            "`!member`"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# =========================================================
# COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Es fehlt ein Argument.",
            delete_after=5
        )
        return

    if isinstance(error, commands.MemberNotFound):

        await ctx.send(
            "❌ Mitglied nicht gefunden.",
            delete_after=5
        )
        return

    if isinstance(error, commands.RoleNotFound):

        await ctx.send(
            "❌ Rolle nicht gefunden.",
            delete_after=5
        )
        return

    if isinstance(error, commands.ChannelNotFound):

        await ctx.send(
            "❌ Kanal nicht gefunden.",
            delete_after=5
        )
        return

    print(
        f"COMMAND ERROR in {ctx.command}: "
        f"{type(error).__name__}: {error}"
    )


# =========================================================
# SETUP HOOK
# =========================================================

@bot.event
async def setup_hook():

    # Persistent Buttons / Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(SuggestionView())
    bot.add_view(CommunityPanelView())
    bot.add_view(OwnerPanelView())

    # Alte Slash-Commands dieses Bots entfernen
    try:

        guild_obj = discord.Object(id=GUILD_ID)

        bot.tree.clear_commands(
            guild=guild_obj
        )

        await bot.tree.sync(
            guild=guild_obj
        )

        bot.tree.clear_commands(
            guild=None
        )

        await bot.tree.sync()

        print("Slash-Commands wurden entfernt.")

    except Exception as e:

        print(
            f"Slash-Command Cleanup Fehler: {e}"
        )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("====================================")

    # Panels aktualisieren
    try:
        await update_nametag_panel()
    except Exception as e:
        print(f"Nametag Panel Fehler: {e}")

    try:
        await update_license_panel()
    except Exception as e:
        print(f"Kennzeichen Panel Fehler: {e}")

    try:
        await update_application_panel()
    except Exception as e:
        print(f"Bewerbungs Panel Fehler: {e}")

    try:
        await update_developer_task_panel()
    except Exception as e:
        print(f"Developer Task Panel Fehler: {e}")

    try:
        await update_developer_shift_panel()
    except Exception as e:
        print(f"Developer Shift Panel Fehler: {e}")

    try:
        await update_community_panel()
    except Exception as e:
        print(f"Community Panel Fehler: {e}")

    # Owner Panel nur aktualisieren,
    # wenn bereits eines existiert
    try:

        owner_message = await find_panel_message(
            OWNER_PANEL_MARKER
        )

        if owner_message:

            owner_channel = owner_message.channel

            try:
                await owner_message.delete()
            except Exception:
                pass

            await send_owner_panel(owner_channel)

    except Exception as e:

        print(
            f"Owner Panel Fehler: {e}"
        )

    # Emoji-Quiz aktualisieren
    try:
        await reset_quiz()
    except Exception as e:
        print(f"Quiz Fehler: {e}")


# =========================================================
# START
# =========================================================

if not TOKEN:
    print("❌ DISCORD_TOKEN wurde nicht gefunden.")
else:
    bot.run(TOKEN)
