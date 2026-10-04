import os
import re
import json
import time
import random
import asyncio
import datetime
from copy import deepcopy

import discord
from discord.ext import commands, tasks


# ============================================================
# CONFIG
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
    "💻 Developed by RyZe 🚀",
]


# ============================================================
# INTENTS / BOT
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
# DATA
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
        return deepcopy(DEFAULT_DATA)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        return deepcopy(DEFAULT_DATA)

    if not isinstance(loaded, dict):
        loaded = {}

    data = deepcopy(DEFAULT_DATA)

    for key, value in loaded.items():
        if key in data:
            data[key] = value

    if not isinstance(data.get("license_plates"), dict):
        data["license_plates"] = {}

    if not isinstance(data.get("applications"), dict):
        data["applications"] = {}

    if not isinstance(data.get("developer_tasks"), dict):
        data["developer_tasks"] = {}

    if not isinstance(data.get("active_developer_shifts"), dict):
        data["active_developer_shifts"] = {}

    if not isinstance(data.get("suggestions"), dict):
        data["suggestions"] = {}

    if not isinstance(data.get("feedback"), list):
        data["feedback"] = []

    if not isinstance(data.get("emoji_quiz"), dict):
        data["emoji_quiz"] = {}

    if not isinstance(data.get("number_game"), dict):
        data["number_game"] = deepcopy(DEFAULT_DATA["number_game"])

    for key, value in DEFAULT_DATA["number_game"].items():
        if key not in data["number_game"]:
            data["number_game"][key] = deepcopy(value)

    if not isinstance(data["number_game"].get("wrong_attempts"), dict):
        data["number_game"]["wrong_attempts"] = {}

    return data


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


# ============================================================
# HELPERS
# ============================================================

async def delete_after_seconds(message, seconds=4):
    try:
        await asyncio.sleep(seconds)
        await message.delete()
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


def is_owner(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    return any(role.id == OWNER_ROLE_ID for role in member.roles)


def is_shift_allowed(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    allowed_roles = {
        SHIFT_PERMISSION_ROLE_ID,
        DEVELOPER_SHIFT_ROLE_ID
    }

    return any(role.id in allowed_roles for role in member.roles)


def has_suggestion_review_permission(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    if is_owner(member):
        return True

    return any(
        role.id == SUGGESTION_REVIEW_ROLE_ID
        for role in member.roles
    )


def normalize_plate(value):
    value = value.upper().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def get_member_display(guild, user_id):
    member = guild.get_member(int(user_id))
    if member:
        return member.display_name

    return f"User {user_id}"


def get_text_channels(guild):
    return [
        channel
        for channel in guild.text_channels
        if channel.permissions_for(guild.me).send_messages
    ]


def make_panel_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(text="RLP Bot System")

    return embed


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


# ============================================================
# OWNER CHANNEL SELECT SYSTEM
# ============================================================

class OwnerChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, action):
        self.action = action

        super().__init__(
            placeholder="📁 Ziel-Chat auswählen...",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für das Owner Panel.",
                ephemeral=True
            )
            return

        selected_channel = self.values[0]

        if not isinstance(selected_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bitte einen normalen Textkanal auswählen.",
                ephemeral=True
            )
            return

        if self.action == "announcement":
            await interaction.response.send_modal(
                OwnerAnnouncementModal(selected_channel)
            )
            return

        if self.action == "bot_say":
            await interaction.response.send_modal(
                OwnerBotSayModal(selected_channel)
            )
            return

        if self.action == "giveaway":
            await interaction.response.send_modal(
                OwnerGiveawayModal(selected_channel)
            )
            return

        if self.action == "user_info":
            await interaction.response.send_modal(
                OwnerUserInfoModal(selected_channel)
            )
            return

        if self.action == "role_info":
            await interaction.response.send_modal(
                OwnerRoleInfoModal(selected_channel)
            )
            return

        if self.action == "server_info":
            embed = discord.Embed(
                title="🖥️ Server Informationen",
                color=discord.Color.blurple()
            )

            guild = interaction.guild

            embed.add_field(
                name="🏠 Server",
                value=guild.name,
                inline=False
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

            await selected_channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Server-Info wurde nach {selected_channel.mention} gesendet.",
                ephemeral=True
            )
            return

        if self.action == "lock":
            overwrite = selected_channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = False

            await selected_channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite,
                reason="Owner Panel - Kanal gesperrt"
            )

            await selected_channel.send(
                "🔒 **Dieser Kanal wurde gesperrt.**"
            )

            await interaction.response.send_message(
                f"🔒 {selected_channel.mention} wurde gesperrt.",
                ephemeral=True
            )
            return

        if self.action == "unlock":
            overwrite = selected_channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = None

            await selected_channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite,
                reason="Owner Panel - Kanal entsperrt"
            )

            await selected_channel.send(
                "🔓 **Dieser Kanal wurde entsperrt.**"
            )

            await interaction.response.send_message(
                f"🔓 {selected_channel.mention} wurde entsperrt.",
                ephemeral=True
            )
            return

        if self.action == "status":
            uptime = int(time.time() - BOT_START_TIME)

            days, remainder = divmod(uptime, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

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
                value=f"{round(bot.latency * 1000)} ms",
                inline=True
            )

            embed.add_field(
                name="⏱️ Uptime",
                value=f"{days}d {hours}h {minutes}m {seconds}s",
                inline=False
            )

            await selected_channel.send(embed=embed)

            await interaction.response.send_message(
                f"📊 Status wurde nach {selected_channel.mention} gesendet.",
                ephemeral=True
            )
            return

        if self.action == "clear":
            await interaction.response.send_modal(
                OwnerClearModal(selected_channel)
            )
            return


class OwnerChannelPickerView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=120)
        self.add_item(OwnerChannelSelect(action))


async def show_owner_channel_picker(interaction, action, title):
    embed = discord.Embed(
        title=title,
        description=(
            "Wähle jetzt den **Chat**, in den die Aktion ausgeführt "
            "werden soll."
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        view=OwnerChannelPickerView(action),
        ephemeral=True
    )


# ============================================================
# OWNER MODALS
# ============================================================

class OwnerAnnouncementModal(discord.ui.Modal, title="📢 Ankündigung"):

    text = discord.ui.TextInput(
        label="Ankündigung",
        placeholder="Text der Ankündigung...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction):
        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.text.value,
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Angekündigt von {interaction.user.display_name}"
        )

        channel = interaction.client.get_channel(
            interaction.message.channel.id
        )

        # Der echte Zielkanal wird aus dem Picker übergeben.
        # Discord Modals behalten ihn über self.target_channel.
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        await target.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Ankündigung wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


def bind_modal_channel(modal, channel):
    modal.target_channel = channel
    return modal


# Monkey-patch style helper für die Channel-gebundenen Modals
_original_announcement_init = OwnerAnnouncementModal.__init__


class OwnerBotSayModal(discord.ui.Modal, title="💬 Bot Say"):

    text = discord.ui.TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot schreiben?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction):
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        await target.send(self.text.value)

        await interaction.response.send_message(
            f"✅ Nachricht wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class OwnerGiveawayModal(discord.ui.Modal, title="🎁 Giveaway"):

    title_text = discord.ui.TextInput(
        label="Giveaway Titel",
        placeholder="🎁 Giveaway",
        required=True,
        max_length=200
    )

    description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Was gibt es zu gewinnen?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3000
    )

    duration = discord.ui.TextInput(
        label="Dauer",
        placeholder="z. B. 24 Stunden",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction):
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎁 {self.title_text.value}",
            description=self.description.value,
            color=discord.Color.gold()
        )

        embed.add_field(
            name="⏱️ Dauer",
            value=self.duration.value,
            inline=False
        )

        embed.add_field(
            name="🎉 Teilnahme",
            value="Reagiere mit 🎉",
            inline=False
        )

        embed.set_footer(
            text=f"Gestartet von {interaction.user.display_name}"
        )

        message = await target.send(embed=embed)

        try:
            await message.add_reaction("🎉")
        except discord.HTTPException:
            pass

        await interaction.response.send_message(
            f"🎁 Giveaway wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class OwnerUserInfoModal(discord.ui.Modal, title="👤 User Info"):

    user = discord.ui.TextInput(
        label="User ID oder Erwähnung",
        placeholder="123456789012345678",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction):
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        raw = self.user.value.strip()
        match = re.search(r"\d+", raw)

        if not match:
            await interaction.response.send_message(
                "❌ Keine gültige User-ID gefunden.",
                ephemeral=True
            )
            return

        user_id = int(match.group(0))

        member = interaction.guild.get_member(user_id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except Exception:
                await interaction.response.send_message(
                    "❌ User wurde auf diesem Server nicht gefunden.",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="👤 User Informationen",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

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
            name="🎭 Rollen",
            value=", ".join(
                role.mention
                for role in member.roles[1:]
            ) or "Keine",
            inline=False
        )

        if member.joined_at:
            embed.add_field(
                name="📅 Server beigetreten",
                value=discord.utils.format_dt(
                    member.joined_at,
                    "F"
                ),
                inline=False
            )

        await target.send(embed=embed)

        await interaction.response.send_message(
            f"✅ User-Info wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class OwnerRoleInfoModal(discord.ui.Modal, title="🎭 Rollen Info"):

    role = discord.ui.TextInput(
        label="Rollen ID oder Erwähnung",
        placeholder="123456789012345678",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction):
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        match = re.search(r"\d+", self.role.value.strip())

        if not match:
            await interaction.response.send_message(
                "❌ Keine gültige Rollen-ID gefunden.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            int(match.group(0))
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎭 Rollen Informationen",
            color=role.color
        )

        embed.add_field(
            name="🎭 Rolle",
            value=role.mention,
            inline=True
        )

        embed.add_field(
            name="🆔 ID",
            value=str(role.id),
            inline=True
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(len(role.members)),
            inline=True
        )

        embed.add_field(
            name="📌 Position",
            value=str(role.position),
            inline=True
        )

        embed.add_field(
            name="🔐 Mentionable",
            value="Ja" if role.mentionable else "Nein",
            inline=True
        )

        await target.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Rollen-Info wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class OwnerClearModal(discord.ui.Modal, title="🧹 Nachrichten löschen"):

    amount = discord.ui.TextInput(
        label="Anzahl",
        placeholder="z. B. 10",
        required=True,
        max_length=4
    )

    async def on_submit(self, interaction):
        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        try:
            amount = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte eine Zahl eingeben.",
                ephemeral=True
            )
            return

        amount = max(1, min(amount, 100))

        try:
            deleted = await target.purge(limit=amount)

            report = await target.send(
                f"🧹 **{len(deleted)} Nachrichten gelöscht.**"
            )

            asyncio.create_task(
                delete_after_seconds(report, 5)
            )

            await interaction.response.send_message(
                f"✅ {len(deleted)} Nachrichten in {target.mention} gelöscht.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot hat dort keine Löschrechte.",
                ephemeral=True
            )


# ============================================================
# OWNER BUTTONS
# ============================================================

class OwnerPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ankündigung",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="owner_announcement"
    )
    async def announcement(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "announcement",
            "📢 Ziel-Chat für Ankündigung"
        )

    @discord.ui.button(
        label="Bot Say",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="owner_bot_say"
    )
    async def bot_say(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "bot_say",
            "💬 Ziel-Chat für Bot Say"
        )

    @discord.ui.button(
        label="Giveaway",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="owner_giveaway"
    )
    async def giveaway(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "giveaway",
            "🎁 Ziel-Chat für Giveaway"
        )

    @discord.ui.button(
        label="User Info",
        emoji="👤",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_user_info"
    )
    async def user_info(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "user_info",
            "👤 Ziel-Chat für User Info"
        )

    @discord.ui.button(
        label="Rollen Info",
        emoji="🎭",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_role_info"
    )
    async def role_info(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "role_info",
            "🎭 Ziel-Chat für Rollen Info"
        )

    @discord.ui.button(
        label="Server Info",
        emoji="🖥️",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_server_info"
    )
    async def server_info(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "server_info",
            "🖥️ Ziel-Chat für Server Info"
        )

    @discord.ui.button(
        label="🔒 Lock",
        style=discord.ButtonStyle.danger,
        custom_id="owner_lock"
    )
    async def lock(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "lock",
            "🔒 Kanal zum Sperren auswählen"
        )

    @discord.ui.button(
        label="🔓 Unlock",
        style=discord.ButtonStyle.success,
        custom_id="owner_unlock"
    )
    async def unlock(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "unlock",
            "🔓 Kanal zum Entsperren auswählen"
        )

    @discord.ui.button(
        label="📊 Status",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_status"
    )
    async def status(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "status",
            "📊 Ziel-Chat für Status"
        )

    @discord.ui.button(
        label="🧹 Clear",
        style=discord.ButtonStyle.danger,
        custom_id="owner_clear"
    )
    async def clear(self, interaction, button):
        await show_owner_channel_picker(
            interaction,
            "clear",
            "🧹 Ziel-Chat zum Löschen"
        )


# ============================================================
# PATCH: MODAL CHANNEL BINDING
# ============================================================

# Wir überschreiben die Picker-Callback-Funktion, damit die
# ausgewählte Ziel-Channel-ID sauber an jedes Modal weitergegeben wird.

async def owner_channel_callback(self, interaction):

    if not is_owner(interaction.user):
        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )
        return

    selected_channel = self.values[0]

    if not isinstance(selected_channel, discord.TextChannel):
        await interaction.response.send_message(
            "❌ Bitte einen Textkanal auswählen.",
            ephemeral=True
        )
        return

    if self.action == "announcement":
        modal = OwnerAnnouncementModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "bot_say":
        modal = OwnerBotSayModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "giveaway":
        modal = OwnerGiveawayModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "user_info":
        modal = OwnerUserInfoModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "role_info":
        modal = OwnerRoleInfoModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "clear":
        modal = OwnerClearModal()
        modal.target_channel = selected_channel
        await interaction.response.send_modal(modal)

    elif self.action == "server_info":

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server Informationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=False
        )

        embed.add_field(
            name="🆔 ID",
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

        await selected_channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Server-Info wurde nach {selected_channel.mention} gesendet.",
            ephemeral=True
        )

    elif self.action in ("lock", "unlock"):

        overwrite = selected_channel.overwrites_for(
            interaction.guild.default_role
        )

        if self.action == "lock":
            overwrite.send_messages = False
            text = "🔒 **Dieser Kanal wurde gesperrt.**"
            result = "gesperrt"

        else:
            overwrite.send_messages = None
            text = "🔓 **Dieser Kanal wurde entsperrt.**"
            result = "entsperrt"

        try:
            await selected_channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite,
                reason="Owner Panel"
            )

            await selected_channel.send(text)

            await interaction.response.send_message(
                f"✅ {selected_channel.mention} wurde {result}.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot hat keine Rechte für diese Aktion.",
                ephemeral=True
            )

    elif self.action == "status":

        uptime = int(time.time() - BOT_START_TIME)

        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

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
            value=f"{round(bot.latency * 1000)} ms",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=False
        )

        await selected_channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Status wurde nach {selected_channel.mention} gesendet.",
            ephemeral=True
        )


OwnerChannelSelect.callback = owner_channel_callback


# ============================================================
# COMMUNITY CHANNEL SELECT
# ============================================================

class CommunityChannelSelect(discord.ui.ChannelSelect):

    def __init__(self, action):
        self.action = action

        super().__init__(
            placeholder="💬 Ziel-Chat auswählen...",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction):

        selected = self.values[0]

        if not isinstance(selected, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bitte einen Textkanal auswählen.",
                ephemeral=True
            )
            return

        if self.action == "feedback":
            modal = FeedbackModal()
            modal.target_channel = selected

            await interaction.response.send_modal(modal)
            return

        if self.action == "suggestion":
            modal = SuggestionModal()
            modal.target_channel = selected

            await interaction.response.send_modal(modal)
            return


class CommunityChannelPickerView(discord.ui.View):

    def __init__(self, action):
        super().__init__(timeout=120)

        self.add_item(
            CommunityChannelSelect(action)
        )


# ============================================================
# COMMUNITY MODALS
# ============================================================

class FeedbackModal(discord.ui.Modal, title="💬 Feedback"):

    feedback = discord.ui.TextInput(
        label="Dein Feedback",
        placeholder="Schreibe dein Feedback...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3000
    )

    async def on_submit(self, interaction):

        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 Neues Feedback",
            description=self.feedback.value,
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=True
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        message = await target.send(embed=embed)

        data["feedback"].append({
            "user_id": interaction.user.id,
            "text": self.feedback.value,
            "message_id": message.id,
            "channel_id": target.id,
            "timestamp": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        })

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Feedback wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class SuggestionModal(discord.ui.Modal, title="💡 Vorschlag"):

    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Was möchtest du vorschlagen?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3000
    )

    async def on_submit(self, interaction):

        target = getattr(self, "target_channel", None)

        if target is None:
            await interaction.response.send_message(
                "❌ Zielkanal fehlt.",
                ephemeral=True
            )
            return

        suggestion_id = str(
            max(
                [int(x) for x in data["suggestions"].keys()]
                or [0]
            ) + 1
        )

        embed = discord.Embed(
            title=f"💡 Vorschlag #{suggestion_id}",
            description=self.suggestion.value,
            color=discord.Color.gold()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📊 Status",
            value="🟡 Offen",
            inline=True
        )

        message = await target.send(embed=embed)

        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.HTTPException:
            pass

        data["suggestions"][suggestion_id] = {
            "user_id": interaction.user.id,
            "text": self.suggestion.value,
            "message_id": message.id,
            "channel_id": target.id,
            "status": "open"
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Vorschlag wurde nach {target.mention} gesendet.",
            ephemeral=True
        )


class CommunityPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Feedback",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="community_feedback"
    )
    async def feedback(self, interaction, button):

        await interaction.response.send_message(
            "💬 **Feedback**\n\n"
            "Wähle zuerst den Chat aus, in den dein Feedback "
            "gesendet werden soll.",
            view=CommunityChannelPickerView("feedback"),
            ephemeral=True
        )

    @discord.ui.button(
        label="Vorschlag",
        emoji="💡",
        style=discord.ButtonStyle.success,
        custom_id="community_suggestion"
    )
    async def suggestion(self, interaction, button):

        await interaction.response.send_message(
            "💡 **Vorschlag**\n\n"
            "Wähle zuerst den Chat aus, in den dein Vorschlag "
            "gesendet werden soll.",
            view=CommunityChannelPickerView("suggestion"),
            ephemeral=True
        )


# ============================================================
# NAMETAG
# ============================================================

class NametagModal(discord.ui.Modal, title="🏷️ Nametag ändern"):

    nametag = discord.ui.TextInput(
        label="Nametag",
        placeholder="z. B. Max",
        required=True,
        max_length=30
    )

    async def on_submit(self, interaction):

        role = interaction.guild.get_role(NAMETAG_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Nametag-Rolle nicht gefunden.",
                ephemeral=True
            )
            return

        if role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role)
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich kann dir die Nametag-Rolle nicht geben.",
                    ephemeral=True
                )
                return

        name = self.nametag.value.strip()

        if not name:
            await interaction.response.send_message(
                "❌ Kein gültiger Nametag.",
                ephemeral=True
            )
            return

        final_name = f"{NAMETAG}{name}"

        if len(final_name) > 32:
            await interaction.response.send_message(
                "❌ Der Name ist zu lang.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.edit(nick=final_name)

            await interaction.response.send_message(
                f"✅ Dein Name wurde zu **{final_name}** geändert.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag setzen",
        emoji="🏷️",
        style=discord.ButtonStyle.primary,
        custom_id="nametag_set"
    )
    async def set_nametag(self, interaction, button):

        await interaction.response.send_modal(
            NametagModal()
        )

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="nametag_remove"
    )
    async def remove_nametag(self, interaction, button):

        try:
            await interaction.user.edit(nick=None)

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


# ============================================================
# LICENSE PLATES
# ============================================================

class LicensePlateModal(discord.ui.Modal, title="🚘 Kennzeichen eintragen"):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RY ZE 01",
        required=True,
        min_length=2,
        max_length=20
    )

    async def on_submit(self, interaction):

        plate = normalize_plate(self.plate.value)

        if not re.fullmatch(
            r"[A-ZÄÖÜ0-9]+(?: [A-ZÄÖÜ0-9]+)*",
            plate
        ):
            await interaction.response.send_message(
                "❌ Das Kennzeichen darf nur Buchstaben, Zahlen "
                "und Leerzeichen enthalten.",
                ephemeral=True
            )
            return

        for user_id, saved_plate in data["license_plates"].items():

            if normalize_plate(saved_plate) == plate:
                if str(user_id) != str(interaction.user.id):
                    await interaction.response.send_message(
                        "❌ Dieses Kennzeichen ist bereits vergeben.",
                        ephemeral=True
                    )
                    return

        # Alten Eintrag des Users ersetzen
        data["license_plates"][str(interaction.user.id)] = plate

        save_data()

        # Panel SOFORT aktualisieren
        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde eingetragen.",
            ephemeral=True
        )


class LicenseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen eintragen / ändern",
        emoji="🚘",
        style=discord.ButtonStyle.primary,
        custom_id="license_register"
    )
    async def register(self, interaction, button):

        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @discord.ui.button(
        label="Aktualisieren",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="license_refresh"
    )
    async def refresh(self, interaction, button):

        await refresh_license_panel()

        await interaction.response.send_message(
            "🔄 Kennzeichenliste wurde aktualisiert.",
            ephemeral=True
        )


async def refresh_license_panel():

    channel = bot.get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🚘 RLP Kennzeichen-System",
        description=(
            "Hier werden alle aktuell registrierten "
            "Kennzeichen angezeigt.\n\n"
            "Klicke auf **Kennzeichen eintragen / ändern**, "
            "um dein Kennzeichen zu registrieren."
        ),
        color=discord.Color.blue()
    )

    if data["license_plates"]:

        lines = []

        for user_id, plate in data["license_plates"].items():

            member = channel.guild.get_member(int(user_id))

            if member:
                user_text = member.mention
            else:
                user_text = f"<@{user_id}>"

            lines.append(
                f"🚘 **{plate}** — {user_text}"
            )

        lines.sort(
            key=lambda x: x.lower()
        )

        embed.add_field(
            name="📋 Registrierte Kennzeichen",
            value="\n".join(lines),
            inline=False
        )

    else:
        embed.add_field(
            name="📋 Registrierte Kennzeichen",
            value="Noch keine Kennzeichen eingetragen.",
            inline=False
        )

    embed.set_footer(
        text=LICENSE_PANEL_MARKER
    )

    existing = None

    async for message in channel.history(limit=100):
        if (
            message.author.id == bot.user.id
            and message.embeds
            and message.embeds[0].footer
            and message.embeds[0].footer.text == LICENSE_PANEL_MARKER
        ):
            existing = message
            break

    if existing:
        try:
            await existing.edit(
                embed=embed,
                view=LicenseView()
            )
            return
        except discord.HTTPException:
            pass

    await channel.send(
        embed=embed,
        view=LicenseView()
    )


# ============================================================
# APPLICATION SYSTEM
# ============================================================

class ApplicationModal(discord.ui.Modal, title="📋 Bewerbung"):

    name = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name...",
        required=True,
        max_length=100
    )

    age = discord.ui.TextInput(
        label="Alter",
        placeholder="Dein Alter...",
        required=True,
        max_length=3
    )

    experience = discord.ui.TextInput(
        label="Erfahrung",
        placeholder="Deine RP-Erfahrung...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    motivation = discord.ui.TextInput(
        label="Motivation",
        placeholder="Warum möchtest du dich bewerben?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):

        review_channel = bot.get_channel(
            REVIEW_CHANNEL_ID
        )

        if review_channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Neue Bewerbung",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=True
        )

        embed.add_field(
            name="🎮 Erfahrung",
            value=self.experience.value,
            inline=False
        )

        embed.add_field(
            name="💭 Motivation",
            value=self.motivation.value,
            inline=False
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await review_channel.send(
            content=interaction.user.mention,
            embed=embed
        )

        data["applications"][str(interaction.user.id)] = {
            "name": self.name.value,
            "age": self.age.value,
            "experience": self.experience.value,
            "motivation": self.motivation.value
        }

        save_data()

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class ApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        emoji="📋",
        style=discord.ButtonStyle.success,
        custom_id="application_start"
    )
    async def apply(self, interaction, button):

        await interaction.response.send_modal(
            ApplicationModal()
        )


# ============================================================
# DEVELOPER TASKS
# ============================================================

class DeveloperTaskModal(discord.ui.Modal, title="💻 Entwickler Aufgabe"):

    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Welche Aufgabe soll eingetragen werden?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        task_id = str(
            max(
                [int(x) for x in data["developer_tasks"].keys()]
                or [0]
            ) + 1
        )

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "created_by": interaction.user.id,
            "status": "offen",
            "created_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:
            embed = discord.Embed(
                title=f"💻 Entwickler Aufgabe #{task_id}",
                description=self.task.value,
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📊 Status",
                value="🟡 Offen",
                inline=True
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Entwickler-Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="dev_task_create"
    )
    async def create(self, interaction, button):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


# ============================================================
# DEVELOPER SHIFT
# ============================================================

class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Dienst starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="dev_shift_start"
    )
    async def start(self, interaction, button):

        if not is_shift_allowed(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        if user_id in data["active_developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        now = datetime.datetime.now(
            datetime.timezone.utc
        )

        data["active_developer_shifts"][user_id] = {
            "started": now.isoformat()
        }

        save_data()

        log_channel = bot.get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:
            await log_channel.send(
                f"🟢 {interaction.user.mention} hat den "
                f"Entwicklerdienst gestartet."
            )

        await interaction.response.send_message(
            "🟢 Dein Entwicklerdienst wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Dienst beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="dev_shift_stop"
    )
    async def stop(self, interaction, button):

        if not is_shift_allowed(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        shift = data["active_developer_shifts"].get(
            user_id
        )

        if not shift:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        try:
            started = datetime.datetime.fromisoformat(
                shift["started"]
            )

            now = datetime.datetime.now(
                datetime.timezone.utc
            )

            duration = now - started

            total_seconds = int(
                duration.total_seconds()
            )

            hours, remainder = divmod(
                total_seconds,
                3600
            )

            minutes, seconds = divmod(
                remainder,
                60
            )

            duration_text = (
                f"{hours}h {minutes}m {seconds}s"
            )

        except Exception:
            duration_text = "Unbekannt"

        del data["active_developer_shifts"][user_id]

        save_data()

        log_channel = bot.get_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:
            await log_channel.send(
                f"🔴 {interaction.user.mention} hat den "
                f"Entwicklerdienst beendet.\n"
                f"⏱️ Dauer: **{duration_text}**"
            )

        await interaction.response.send_message(
            f"🔴 Dienst beendet.\n⏱️ Dauer: **{duration_text}**",
            ephemeral=True
        )


# ============================================================
# EMOJI QUIZ
# ============================================================

QUIZ_QUESTIONS = [
    {
        "emoji": "🦁👑",
        "answer": "der könig der löwen",
        "hint": "Ein Disney-Film.",
        "letter": "K"
    },
    {
        "emoji": "❄️👸",
        "answer": "frozen",
        "hint": "Ein Film mit Elsa.",
        "letter": "F"
    },
    {
        "emoji": "🧙⚡",
        "answer": "harry potter",
        "hint": "Ein Zauberer.",
        "letter": "H"
    },
    {
        "emoji": "🕷️🦸",
        "answer": "spiderman",
        "hint": "Ein Superheld.",
        "letter": "S"
    },
    {
        "emoji": "🚢🧊",
        "answer": "titanic",
        "hint": "Ein berühmtes Schiff.",
        "letter": "T"
    },
]


def get_quiz_user_state(user_id):

    key = str(user_id)

    if key not in data["emoji_quiz"]:
        data["emoji_quiz"][key] = {
            "tips": 0,
            "letters": 0,
            "skips": 0,
            "reset_at": time.time() + 7200,
            "score": 0
        }

    state = data["emoji_quiz"][key]

    if time.time() >= state.get("reset_at", 0):
        state["tips"] = 0
        state["letters"] = 0
        state["skips"] = 0
        state["reset_at"] = time.time() + 7200
        save_data()

    return state


def current_quiz():
    return data["emoji_quiz"].get(
        "_current_quiz"
    )


def start_new_quiz():

    question = random.choice(
        QUIZ_QUESTIONS
    )

    data["emoji_quiz"]["_current_quiz"] = {
        "emoji": question["emoji"],
        "answer": question["answer"],
        "hint": question["hint"],
        "letter": question["letter"],
        "started": time.time()
    }

    save_data()

    return question


class EmojiAnswerModal(discord.ui.Modal, title="🧩 Quiz Antwort"):

    answer = discord.ui.TextInput(
        label="Deine Antwort",
        placeholder="Was ist die Lösung?",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction):

        quiz = current_quiz()

        if not quiz:
            await interaction.response.send_message(
                "❌ Aktuell läuft kein Quiz.",
                ephemeral=True
            )
            return

        answer = self.answer.value.lower().strip()

        if answer == quiz["answer"]:
            state = get_quiz_user_state(
                interaction.user.id
            )

            state["score"] += 1

            save_data()

            await interaction.response.send_message(
                f"🎉 **Richtig!**\n"
                f"Du hast jetzt **{state['score']} Punkte**.",
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                "❌ Leider falsch.",
                ephemeral=True
            )


class EmojiQuizView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Neues Quiz",
        emoji="▶️",
        style=discord.ButtonStyle.primary,
        custom_id="emoji_new"
    )
    async def new_quiz(self, interaction, button):

        question = start_new_quiz()

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🧩 Emoji Quiz",
                description=(
                    f"Errate den Begriff:\n\n"
                    f"# {question['emoji']}"
                ),
                color=discord.Color.blurple()
            ),
            view=self
        )

    @discord.ui.button(
        label="Tipp anfordern",
        emoji="💡",
        style=discord.ButtonStyle.secondary,
        custom_id="emoji_hint"
    )
    async def hint(self, interaction, button):

        state = get_quiz_user_state(
            interaction.user.id
        )

        if state["tips"] >= 3:
            await interaction.response.send_message(
                "❌ Deine Tipps sind aufgebraucht: **3/3**.\n"
                "Sie werden alle 2 Stunden zurückgesetzt.",
                ephemeral=True
            )
            return

        quiz = current_quiz()

        if not quiz:
            await interaction.response.send_message(
                "❌ Starte zuerst ein neues Quiz.",
                ephemeral=True
            )
            return

        state["tips"] += 1

        save_data()

        await interaction.response.send_message(
            f"💡 **Tipp:** {quiz['hint']}\n"
            f"Nutzung: **{state['tips']}/3**",
            ephemeral=True
        )

    @discord.ui.button(
        label="Anfangsbuchstaben",
        emoji="🔤",
        style=discord.ButtonStyle.secondary,
        custom_id="emoji_letter"
    )
    async def letter(self, interaction, button):

        state = get_quiz_user_state(
            interaction.user.id
        )

        if state["letters"] >= 3:
            await interaction.response.send_message(
                "❌ Deine Anfangsbuchstaben sind aufgebraucht: "
                "**3/3**.\n"
                "Sie werden alle 2 Stunden zurückgesetzt.",
                ephemeral=True
            )
            return

        quiz = current_quiz()

        if not quiz:
            await interaction.response.send_message(
                "❌ Starte zuerst ein neues Quiz.",
                ephemeral=True
            )
            return

        state["letters"] += 1

        save_data()

        await interaction.response.send_message(
            f"🔤 Der Anfangsbuchstabe ist: "
            f"**{quiz['letter']}**\n"
            f"Nutzung: **{state['letters']}/3**",
            ephemeral=True
        )

    @discord.ui.button(
        label="Aufgabe überspringen",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="emoji_skip"
    )
    async def skip(self, interaction, button):

        state = get_quiz_user_state(
            interaction.user.id
        )

        if state["skips"] >= 3:
            await interaction.response.send_message(
                "❌ Deine Überspringen-Nutzungen sind aufgebraucht: "
                "**3/3**.\n"
                "Sie werden alle 2 Stunden zurückgesetzt.",
                ephemeral=True
            )
            return

        state["skips"] += 1

        question = start_new_quiz()

        save_data()

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🧩 Emoji Quiz",
                description=(
                    f"⏭️ Aufgabe übersprungen.\n\n"
                    f"Errate jetzt:\n\n"
                    f"# {question['emoji']}"
                ),
                color=discord.Color.blurple()
            ),
            view=self
        )

    @discord.ui.button(
        label="Bestenliste",
        emoji="🏆",
        style=discord.ButtonStyle.success,
        custom_id="emoji_leaderboard"
    )
    async def leaderboard(self, interaction, button):

        entries = []

        for user_id, state in data["emoji_quiz"].items():

            if user_id == "_current_quiz":
                continue

            entries.append(
                (
                    int(state.get("score", 0)),
                    user_id
                )
            )

        entries.sort(
            reverse=True
        )

        lines = []

        for index, (score, user_id) in enumerate(
            entries[:10],
            start=1
        ):
            lines.append(
                f"**{index}.** <@{user_id}> — "
                f"**{score} Punkte**"
            )

        embed = discord.Embed(
            title="🏆 Emoji Quiz Bestenliste",
            description="\n".join(lines)
            if lines
            else "Noch keine Punkte vorhanden.",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Antworten",
        emoji="✍️",
        style=discord.ButtonStyle.primary,
        custom_id="emoji_answer"
    )
    async def answer(self, interaction, button):

        if not current_quiz():
            await interaction.response.send_message(
                "❌ Starte zuerst ein neues Quiz.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            EmojiAnswerModal()
        )


# ============================================================
# NUMBER GAME
# ============================================================

def wrong_timeout_minutes(wrong_count):

    if wrong_count < 4:
        return 0

    level = 1 + ((wrong_count - 4) // 10)

    minutes = 5 * level

    return min(
        minutes,
        24 * 60
    )


async def handle_number_game(message):

    if message.channel.id != NUMBER_GAME_CHANNEL_ID:
        return False

    if message.author.bot:
        return False

    content = message.content.strip()

    if not re.fullmatch(r"\d+", content):
        return False

    number = int(content)

    number_game = data["number_game"]

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
    # RICHTIGE ZAHL
    # --------------------------------------------------------

    if number == expected:

        # Nicht zweimal hintereinander
        if last_user_id == message.author.id:

            warning = await message.channel.send(
                f"⚠️ **Nicht möglich!**\n"
                f"Die Zahl `{expected}` muss von einer "
                f"anderen Person geschrieben werden.\n"
                f"Die Zahl bleibt bei `{expected}`."
            )

            asyncio.create_task(
                delete_after_seconds(
                    warning,
                    4
                )
            )

            return True

        number_game["current_number"] = expected + 1
        number_game["last_user_id"] = message.author.id
        number_game["last_message_id"] = message.id

        save_data()

        try:
            await message.add_reaction("✅")
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        # Easter Eggs bei 100, 200, 300...
        if number % 100 == 0:

            if number_game.get(
                "last_easter_egg",
                0
            ) != number:

                number_game["last_easter_egg"] = number

                save_data()

                easter_egg = await message.channel.send(
                    f"🎉 **{number} erreicht!**\n"
                    f"Starke Leistung — weiter geht's mit "
                    f"`{number + 1}`!"
                )

                asyncio.create_task(
                    delete_after_seconds(
                        easter_egg,
                        4
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

    wrong_attempts[user_id] = int(
        wrong_attempts.get(
            user_id,
            0
        )
    ) + 1

    wrong_count = wrong_attempts[user_id]

    # Bei jedem Fehler wieder auf 1
    number_game["current_number"] = 1
    number_game["last_user_id"] = None
    number_game["last_message_id"] = message.id

    save_data()

    timeout_minutes = wrong_timeout_minutes(
        wrong_count
    )

    bot_message = await message.channel.send(
        f"❌ Falsch ({message.author.display_name})!"
    )

    # Beide Nachrichten nach 5 Sekunden löschen
    asyncio.create_task(
        delete_after_seconds(
            bot_message,
            5
        )
    )

    asyncio.create_task(
        delete_after_seconds(
            message,
            5
        )
    )

    # Timeout bei:
    # 4 -> 5 Minuten
    # 14 -> 10 Minuten
    # 24 -> 15 Minuten
    # 34 -> 20 Minuten
    if timeout_minutes > 0:

        try:

            until = (
                discord.utils.utcnow()
                + datetime.timedelta(
                    minutes=timeout_minutes
                )
            )

            await message.author.timeout(
                until,
                reason=(
                    "RLP Zahlenspiel – zu viele "
                    "Fehlversuche"
                )
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    return True


# ============================================================
# PANELS
# ============================================================

async def send_nametag_panel(channel):

    embed = make_panel_embed(
        "🏷️ RLP Nametag-System",
        (
            "Hier kannst du deinen RLP-Nametag verwalten.\n\n"
            "🏷️ **Nametag setzen**\n"
            "🗑️ **Nametag entfernen**"
        )
    )

    embed.set_footer(
        text=NAMETAG_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


async def send_application_panel(channel):

    embed = make_panel_embed(
        "📋 RLP Bewerbungs-System",
        (
            "Du möchtest dich für unser Team bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        discord.Color.green()
    )

    embed.set_footer(
        text=APPLICATION_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


async def send_dev_task_panel(channel):

    embed = make_panel_embed(
        "💻 Entwickler Aufgaben",
        (
            "Hier können neue Entwickler-Aufgaben "
            "erstellt werden."
        )
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


async def send_dev_shift_panel(channel):

    embed = make_panel_embed(
        "🧑‍💻 Entwicklerdienst",
        (
            "Nutze die Buttons, um deinen Entwicklerdienst "
            "zu starten oder zu beenden."
        )
    )

    embed.set_footer(
        text=DEV_SHIFT_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


async def send_community_panel(channel):

    embed = discord.Embed(
        title="🌐 RLP Community",
        description=(
            "Willkommen im Community-System!\n\n"
            "💬 **Feedback**\n"
            "Klicke auf Feedback und wähle danach den Chat aus, "
            "in den deine Nachricht gesendet werden soll.\n\n"
            "💡 **Vorschlag**\n"
            "Klicke auf Vorschlag und wähle danach den Chat aus, "
            "in den dein Vorschlag gesendet werden soll."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=COMMUNITY_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=CommunityPanelView()
    )


async def send_owner_panel(channel):

    embed = discord.Embed(
        title="👑 RLP Owner Panel",
        description=(
            "Willkommen im Owner Panel.\n\n"
            "Bei **jeder Aktion** musst du zuerst einen "
            "Ziel-Chat auswählen.\n\n"
            "📢 **Ankündigung**\n"
            "Eine Ankündigung in einen ausgewählten Chat senden.\n\n"
            "💬 **Bot Say**\n"
            "Eine normale Bot-Nachricht senden.\n\n"
            "🎁 **Giveaway**\n"
            "Ein Giveaway-Embed erstellen.\n\n"
            "👤 **User Info**\n"
            "Informationen über einen User senden.\n\n"
            "🎭 **Rollen Info**\n"
            "Informationen über eine Rolle senden.\n\n"
            "🖥️ **Server Info**\n"
            "Serverinformationen senden.\n\n"
            "🔒 **Lock / Unlock**\n"
            "Einen ausgewählten Kanal sperren oder entsperren.\n\n"
            "📊 **Status**\n"
            "Bot-Status in einen ausgewählten Chat senden.\n\n"
            "🧹 **Clear**\n"
            "Nachrichten in einem ausgewählten Chat löschen."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=OWNER_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=OwnerPanelView()
    )


async def send_emoji_quiz_panel(channel):

    embed = discord.Embed(
        title="🧩 RLP Emoji Quiz",
        description=(
            "Errate Filme, Figuren und Begriffe anhand von Emojis.\n\n"
            "▶️ Neues Quiz\n"
            "💡 Tipp anfordern\n"
            "🔤 Anfangsbuchstaben\n"
            "⏭️ Aufgabe überspringen\n"
            "🏆 Bestenliste\n"
            "✍️ Antwort eingeben\n\n"
            "Tipp, Anfangsbuchstaben und Überspringen sind "
            "jeweils **3-mal pro 2 Stunden** möglich."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=EMOJI_QUIZ_PANEL_MARKER
    )

    await channel.send(
        embed=embed,
        view=EmojiQuizView()
    )


async def send_number_game_panel(channel):

    embed = discord.Embed(
        title="🔢 RLP Zahlenspiel",
        description=(
            "Zählt gemeinsam hoch.\n\n"
            "Die Zahlen müssen bei **1** beginnen und "
            "immer um 1 steigen.\n\n"
            "⚠️ Eine Person darf nicht zweimal hintereinander "
            "die richtige Zahl schreiben.\n\n"
            "❌ Bei einer falschen Zahl beginnt die Runde "
            "wieder bei **1**.\n\n"
            "⏱️ Bei zu vielen Fehlversuchen gibt es "
            "automatische Timeouts."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=NUMBER_GAME_PANEL_MARKER
    )

    await channel.send(
        embed=embed
    )


# ============================================================
# COMMANDS
# ============================================================

@bot.command(
    name="ownerpanel",
    aliases=["owner"]
)
async def ownerpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung für das Owner Panel."
        )
        return

    # Dynamisch genau dort, wo ?ownerpanel geschrieben wurde
    await send_owner_panel(ctx.channel)


@bot.command(
    name="communitypanel"
)
async def communitypanel(ctx):

    await send_community_panel(
        ctx.channel
    )


@bot.command(
    name="nametagpanel"
)
async def nametagpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await send_nametag_panel(
        ctx.channel
    )


@bot.command(
    name="licensepanel",
    aliases=["kennzeichenpanel"]
)
async def licensepanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await refresh_license_panel()


@bot.command(
    name="bewerbungpanel",
    aliases=["applicationpanel"]
)
async def applicationpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await send_application_panel(
        ctx.channel
    )


@bot.command(
    name="devtaskpanel"
)
async def devtaskpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await send_dev_task_panel(
        ctx.channel
    )


@bot.command(
    name="devshiftpanel"
)
async def devshiftpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await send_dev_shift_panel(
        ctx.channel
    )


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
async def emojiquizpanel(ctx):

    await send_emoji_quiz_panel(
        ctx.channel
    )


@bot.command(
    name="numbergamepanel",
    aliases=["zahlenspielpanel"]
)
async def numbergamepanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await send_number_game_panel(
        ctx.channel
    )


# ============================================================
# HELP
# ============================================================

@bot.command(
    name="help"
)
async def help_command(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot Hilfe",
        description="Hier findest du die verfügbaren Befehle.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🌐 Community",
        value=(
            "`?communitypanel` – Community Panel\n"
            "`?emojiquiz` – Emoji Quiz"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            "`?ownerpanel` – Owner Panel\n"
            "`?owner` – Owner Panel"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Systeme",
        value=(
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
            "`?bewerbungpanel`\n"
            "`?devtaskpanel`\n"
            "`?devshiftpanel`\n"
            "`?numbergamepanel`"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):

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
            "❌ Es fehlen Argumente für diesen Befehl."
        )
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du hast nicht die benötigten Rechte."
        )
        return

    if isinstance(
        error,
        commands.CheckFailure
    ):
        await ctx.send(
            "❌ Du kannst diesen Befehl nicht verwenden."
        )
        return

    print(
        f"[COMMAND ERROR] {ctx.command}: {error}"
    )


# ============================================================
# ON MESSAGE
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Zahlenspiel zuerst behandeln
    handled = await handle_number_game(
        message
    )

    if handled:
        return

    await bot.process_commands(
        message
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"=========================================="
    )

    print(
        f"Bot online: {bot.user}"
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    print(
        f"Guilds: {len(bot.guilds)}"
    )

    print(
        f"=========================================="
    )

    # Persistent Views
    bot.add_view(
        NametagView()
    )

    bot.add_view(
        LicenseView()
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
        CommunityPanelView()
    )

    bot.add_view(
        OwnerPanelView()
    )

    bot.add_view(
        EmojiQuizView()
    )

    # --------------------------------------------------------
    # WICHTIG:
    # Community / Owner / Emoji Quiz werden NICHT automatisch
    # in irgendeinen festen Kanal gepostet.
    #
    # ?ownerpanel      -> Panel im aktuellen Kanal
    # ?communitypanel  -> Panel im aktuellen Kanal
    # ?emojiquiz       -> Panel im aktuellen Kanal
    # --------------------------------------------------------

    if not change_status_loop.is_running():
        change_status_loop.start()


# ============================================================
# STATUS LOOP
# ============================================================

@tasks.loop(seconds=20)
async def change_status_loop():

    if not bot.is_ready():
        return

    text = random.choice(
        STATUS_TEXTS
    )

    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(
                name=text
            )
        )
    except Exception as e:
        print(
            f"[STATUS] Fehler: {e}"
        )


# ============================================================
# START
# ============================================================

async def start_bot():

    if not TOKEN:
        print(
            "❌ DISCORD_TOKEN wurde nicht gefunden."
        )
        return

    await bot.start(
        TOKEN
    )


if __name__ == "__main__":

    try:
        asyncio.run(
            start_bot()
        )

    except KeyboardInterrupt:
        print(
            "Bot wurde beendet."
        )
