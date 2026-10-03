import os
import json
import random
import asyncio

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276
SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439814863151155
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086
OWNER_ROLE_ID = 1544691379613999164

NAMETAG = "RLP | "

DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"


# =========================================================
# INTENTS / BOT
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# DATA
# =========================================================

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
else:
    data = {}

data.setdefault("license_plates", {})
data.setdefault("developer_tasks", {})
data.setdefault("applications", {})

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =========================================================
# HELPERS
# =========================================================

def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def get_channel(channel_id: int):
    return bot.get_channel(channel_id)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


def get_real_text_channel(guild: discord.Guild, selected_channel):
    """
    ChannelSelect kann einen AppCommandChannel liefern.
    Deshalb holen wir den Kanal anhand seiner ID nochmal
    direkt aus der Guild.
    """
    if selected_channel is None:
        return None

    channel_id = getattr(selected_channel, "id", None)

    if channel_id is None:
        return None

    channel = guild.get_channel(channel_id)

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


# =========================================================
# NAMETAG
# =========================================================

class NametagResetButton(Button):
    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Fehler: Mitglied konnte nicht erkannt werden.",
                ephemeral=True
            )
            return

        current_nick = member.nick

        if not current_nick:
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen Nametag.",
                ephemeral=True
            )
            return

        new_nick = current_nick

        prefixes = [
            NAMETAG,
            NAMETAG.replace(" ", "\u00a0")
        ]

        removed = False

        for prefix in prefixes:
            if new_nick.startswith(prefix):
                new_nick = new_nick[len(prefix):]
                removed = True
                break

        if not removed:
            await interaction.response.send_message(
                "ℹ️ Dein Name hat keinen RLP-Nametag.",
                ephemeral=True
            )
            return

        if not new_nick:
            new_nick = None

        try:
            await member.edit(
                nick=new_nick,
                reason="Nametag zurückgesetzt"
            )

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern. "
                "Meine Rolle muss über deiner Rolle stehen.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Nametag Reset Error: {e}")

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


class NametagView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagResetButton())


async def update_nametag_panel():

    channel = get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Hier kannst du deinen **RLP-Nametag** verwalten.\n\n"
            f"Der Nametag lautet:\n`{NAMETAG}`\n\n"
            "Mit dem Button kannst du den Nametag aus deinem "
            "Nickname entfernen."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                if old_embed.fields:

                    for field in old_embed.fields:

                        if field.value == NAMETAG_PANEL_MARKER:

                            await message.edit(
                                embed=embed,
                                view=NametagView()
                            )
                            return

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# LICENSE PLATES
# =========================================================

class LicensePlateModal(Modal):

    def __init__(self):
        super().__init__(title="Kennzeichen erstellen")

        self.plate = TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction: discord.Interaction):

        value = self.plate.value.strip().upper()

        parts = value.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Bitte Prefix und Nummer angeben. Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():
            await interaction.response.send_message(
                "❌ Der letzte Teil des Kennzeichens muss eine Zahl sein.",
                ephemeral=True
            )
            return

        for existing_plate in data["license_plates"].values():

            existing_parts = existing_plate["plate"].split()

            if existing_parts and existing_parts[-1] == number:

                await interaction.response.send_message(
                    f"❌ Die Nummer `{number}` ist bereits vergeben.",
                    ephemeral=True
                )
                return

        user_id = str(interaction.user.id)

        if user_id in data["license_plates"]:

            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen.",
                ephemeral=True
            )
            return

        data["license_plates"][user_id] = {
            "plate": value,
            "name": interaction.user.display_name
        }

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{value}** wurde erstellt.",
            ephemeral=True
        )


class LicensePlateButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen erstellen",
            emoji="🚗",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_license_create"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicensePlateButton())


async def update_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description="Hier kannst du dein Kennzeichen erstellen.",
        color=discord.Color.blue()
    )

    if data["license_plates"]:

        lines = []

        for plate_data in data["license_plates"].values():

            lines.append(
                f"🚗 `{plate_data['plate']}` — **{plate_data['name']}**"
            )

        embed.add_field(
            name="Vergebene Kennzeichen",
            value="\n".join(lines),
            inline=False
        )

    else:

        embed.add_field(
            name="Vergebene Kennzeichen",
            value="Noch keine Kennzeichen.",
            inline=False
        )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                if old_embed.fields:

                    for field in old_embed.fields:

                        if field.value == LICENSE_PANEL_MARKER:

                            await message.edit(
                                embed=embed,
                                view=LicensePlateView()
                            )
                            return

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# APPLICATIONS
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
            label="Warum möchtest du beitreten?",
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

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="📝 Grund",
            value=self.reason_input.value,
            inline=False
        )

        embed.add_field(
            name="Discord",
            value=interaction.user.mention,
            inline=False
        )

        try:

            await channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde gesendet.",
                ephemeral=True
            )

        except Exception as e:

            print(f"Application Error: {e}")

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


class ApplicationButton(Button):

    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.success,
            custom_id="rlp_application_button"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def update_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                if old_embed.fields:

                    for field in old_embed.fields:

                        if field.value == APPLICATION_PANEL_MARKER:

                            await message.edit(
                                embed=embed,
                                view=ApplicationView()
                            )
                            return

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# DEVELOPER TASKS
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

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        task_id = str(random.randint(100000, 999999))

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "author": interaction.user.id,
            "completed": False
        }

        save_data()

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel:

            embed = discord.Embed(
                title="🛠️ Neue Developer Aufgabe",
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention
            )

            embed.add_field(
                name="Task ID",
                value=task_id
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(Button):

    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

    async def callback(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


async def update_developer_task_panel():

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Developer Aufgaben",
        description="Erstelle hier neue Developer-Aufgaben.",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                if old_embed.fields:

                    for field in old_embed.fields:

                        if field.value == DEV_TASK_PANEL_MARKER:

                            await message.edit(
                                embed=embed,
                                view=DeveloperTaskView()
                            )
                            return

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# DEVELOPER SHIFT
# =========================================================

class DeveloperShiftStartButton(Button):

    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_shift_start"
        )

    async def callback(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:

            await interaction.response.send_message(
                "❌ Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            await interaction.user.add_roles(
                role,
                reason="Developer Schicht gestartet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if log_channel:

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


class DeveloperShiftEndButton(Button):

    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_shift_end"
        )

    async def callback(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:

            await interaction.response.send_message(
                "❌ Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            await interaction.user.remove_roles(
                role,
                reason="Developer Schicht beendet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if log_channel:

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


class DeveloperShiftView(View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(DeveloperShiftStartButton())
        self.add_item(DeveloperShiftEndButton())


async def update_developer_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🖥️ Developer Schicht",
        description=(
            "Hier kannst du deine Developer-Schicht verwalten.\n\n"
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=SHIFT_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                if old_embed.fields:

                    for field in old_embed.fields:

                        if field.value == SHIFT_PANEL_MARKER:

                            await message.edit(
                                embed=embed,
                                view=DeveloperShiftView()
                            )
                            return

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇩🇪", "deutschland"),
    ("🇺🇸🗽", "usa"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🌞", "sonne"),
    ("🌙", "mond"),
    ("🚗", "auto"),
    ("✈️", "flugzeug"),
    ("🏠", "haus"),
    ("⚽", "fußball"),
    ("🎮", "gaming"),
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🌳", "baum"),
    ("🌊", "meer"),
    ("❄️", "schnee"),
    ("🔥", "feuer"),
    ("❤️", "herz")
]

quiz_message_id = None
quiz_answer = None
quiz_lock = asyncio.Lock()
quiz_starting = False
used_quiz_questions = set()


async def send_quiz_question():

    global quiz_message_id
    global quiz_answer
    global quiz_starting

    async with quiz_lock:

        if quiz_starting:
            return

        quiz_starting = True

        try:

            channel = get_channel(QUIZ_CHANNEL_ID)

            if channel is None:
                return

            available = [
                q for q in QUIZ_QUESTIONS
                if q not in used_quiz_questions
            ]

            if not available:

                used_quiz_questions.clear()
                available = QUIZ_QUESTIONS.copy()

            question, answer = random.choice(available)

            used_quiz_questions.add((question, answer))

            message = await channel.send(
                f"❓ **Was bedeutet dieses Emoji?**\n\n"
                f"# {question}"
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower()

        finally:

            quiz_starting = False


# =========================================================
# OWNER PANEL
# =========================================================

def is_owner(member: discord.Member):
    return has_role(member, OWNER_ROLE_ID)


# ---------------------------------------------------------
# ANKÜNDIGUNG MODAL
# ---------------------------------------------------------

class AnnouncementModal(Modal):

    def __init__(self, channel: discord.TextChannel):

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
                "❌ Der Bot kann in diesem Kanal keine Nachrichten "
                "oder Embeds senden.",
                ephemeral=True
            )

        except Exception as e:

            print(f"Announcement Error: {e}")

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


# ---------------------------------------------------------
# BOT SAY MODAL
# ---------------------------------------------------------

class BotSayModal(Modal):

    def __init__(self, channel: discord.TextChannel):

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

            await self.channel.send(
                self.message_input.value
            )

            await interaction.response.send_message(
                f"✅ Nachricht wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann in diesem Kanal nicht schreiben.",
                ephemeral=True
            )

        except Exception as e:

            print(f"Bot Say Error: {e}")

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


# ---------------------------------------------------------
# CHANNEL SELECT
# ---------------------------------------------------------

class OwnerChannelSelectView(View):

    def __init__(self, action: str):

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

        try:

            selected_channel = self.select.values[0]

            # =================================================
            # WICHTIGER FIX:
            # ChannelSelect kann AppCommandChannel liefern.
            # Wir holen deshalb den echten TextChannel über ID.
            # =================================================

            channel = get_real_text_channel(
                interaction.guild,
                selected_channel
            )

            if channel is None:

                await interaction.response.send_message(
                    "❌ Der ausgewählte Kanal konnte nicht als "
                    "Textkanal gefunden werden.",
                    ephemeral=True
                )
                return

            # -------------------------------------------------
            # ANKÜNDIGUNG
            # -------------------------------------------------

            if self.action == "announcement":

                await interaction.response.send_modal(
                    AnnouncementModal(channel)
                )

                return

            # -------------------------------------------------
            # BOT SAY
            # -------------------------------------------------

            if self.action == "say":

                await interaction.response.send_modal(
                    BotSayModal(channel)
                )

                return

            # -------------------------------------------------
            # LOCK
            # -------------------------------------------------

            if self.action == "lock":

                await interaction.response.defer(
                    ephemeral=True
                )

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

            # -------------------------------------------------
            # UNLOCK
            # -------------------------------------------------

            if self.action == "unlock":

                await interaction.response.defer(
                    ephemeral=True
                )

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

                return

        except discord.Forbidden:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Der Bot hat für diesen Kanal "
                    "nicht genügend Berechtigungen.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Der Bot hat für diesen Kanal "
                    "nicht genügend Berechtigungen.",
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


# ---------------------------------------------------------
# OWNER ANNOUNCEMENT BUTTON
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# OWNER SAY BUTTON
# ---------------------------------------------------------

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
            "💬 **Wähle den Kanal, in dem der Bot schreiben soll:**",
            view=OwnerChannelSelectView("say"),
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER LOCK BUTTON
# ---------------------------------------------------------

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
            "🔒 **Wähle den Kanal, der gesperrt werden soll:**",
            view=OwnerChannelSelectView("lock"),
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER UNLOCK BUTTON
# ---------------------------------------------------------

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
            "🔓 **Wähle den Kanal, der entsperrt werden soll:**",
            view=OwnerChannelSelectView("unlock"),
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER STATUS
# ---------------------------------------------------------

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

        latency = round(
            bot.latency * 1000
        )

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

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER SERVER INFO
# ---------------------------------------------------------

class OwnerServerInfoButton(Button):

    def __init__(self):

        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_server_info"
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
            title="🖥️ Server Informationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="Server ID",
            value=str(guild.id),
            inline=True
        )

        embed.add_field(
            name="Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="Kanäle",
            value=str(len(guild.channels)),
            inline=True
        )

        embed.add_field(
            name="Rollen",
            value=str(len(guild.roles)),
            inline=True
        )

        if guild.owner:

            embed.add_field(
                name="Owner",
                value=guild.owner.mention,
                inline=True
            )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ---------------------------------------------------------
# OWNER PANEL VIEW
# ---------------------------------------------------------

class OwnerPanelView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            OwnerAnnouncementButton()
        )

        self.add_item(
            OwnerSayButton()
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


async def send_owner_panel(channel):

    embed = discord.Embed(
        title="👑 Owner Panel",
        description=(
            "Hier kannst du verschiedene Server- und "
            "Bot-Funktionen verwalten.\n\n"

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
# SUPPORT VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    log_channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if log_channel is None:
        return

    support_channel = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if support_channel is None:
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
# COMMANDS
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

    await send_owner_panel(
        ctx.channel
    )


@bot.command()
async def owner(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )

        return

    await send_owner_panel(
        ctx.channel
    )


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    # -----------------------------------------------------
    # QUIZ
    # -----------------------------------------------------

    if message.channel.id == QUIZ_CHANNEL_ID:

        if quiz_answer is None:

            await asyncio.sleep(6)

            await safe_delete(message)

            return

        user_answer = (
            message.content
            .strip()
            .lower()
        )

        if user_answer == quiz_answer:

            current_question_id = quiz_message_id

            await safe_delete(message)

            if current_question_id:

                try:

                    question_message = (
                        await message.channel.fetch_message(
                            current_question_id
                        )
                    )

                    await safe_delete(
                        question_message
                    )

                except Exception:
                    pass

            quiz_message_id = None
            quiz_answer = None

            success_message = await message.channel.send(
                f"✅ **Richtig!** {message.author.mention}"
            )

            await asyncio.sleep(4)

            await safe_delete(
                success_message
            )

            await send_quiz_question()

            return

        await safe_delete(message)

        wrong_message = await message.channel.send(
            f"❌ **Falsch!** {message.author.mention}"
        )

        await asyncio.sleep(4)

        await safe_delete(
            wrong_message
        )

        return

    await bot.process_commands(message)


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

    print(
        f"Command Error: {error}"
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

    bot.add_view(
        NametagView()
    )

    bot.add_view(
        LicensePlateView()
    )

    bot.add_view(
        ApplicationView()
    )

    bot.add_view(
        DeveloperTaskView()
    )

    bot.add_view(
        DeveloperShiftView()
    )

    bot.add_view(
        OwnerPanelView()
    )

    try:

        await update_nametag_panel()

    except Exception as e:

        print(
            f"Nametag Panel Fehler: {e}"
        )

    try:

        await update_license_panel()

    except Exception as e:

        print(
            f"Kennzeichen Panel Fehler: {e}"
        )

    try:

        await update_application_panel()

    except Exception as e:

        print(
            f"Bewerbungs Panel Fehler: {e}"
        )

    try:

        await update_developer_task_panel()

    except Exception as e:

        print(
            f"Developer Task Panel Fehler: {e}"
        )

    try:

        await update_developer_shift_panel()

    except Exception as e:

        print(
            f"Developer Shift Panel Fehler: {e}"
        )

    try:

        await send_quiz_question()

    except Exception as e:

        print(
            f"Quiz Fehler: {e}"
        )


# =========================================================
# START
# =========================================================

bot.run(TOKEN)
