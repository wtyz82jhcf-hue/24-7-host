import os
import re
import json
import time
import random
import asyncio
import datetime as dt
from copy import deepcopy

import discord
from discord.ext import commands, tasks


# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

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
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True


# ============================================================
# BOT
# ============================================================

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
    "developer_tasks": {},
    "active_developer_shifts": {},
    "suggestions": {},
    "feedback": [],
    "emoji_quiz": {
        "users": {},
        "current_quiz": None
    },
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
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        return deepcopy(DEFAULT_DATA)

    if not isinstance(loaded, dict):
        loaded = {}

    result = deepcopy(DEFAULT_DATA)

    for key in result:
        if key in loaded:
            result[key] = loaded[key]

    if not isinstance(result["license_plates"], dict):
        result["license_plates"] = {}

    if not isinstance(result["developer_tasks"], dict):
        result["developer_tasks"] = {}

    if not isinstance(result["active_developer_shifts"], dict):
        result["active_developer_shifts"] = {}

    if not isinstance(result["suggestions"], dict):
        result["suggestions"] = {}

    if not isinstance(result["feedback"], list):
        result["feedback"] = []

    if not isinstance(result["emoji_quiz"], dict):
        result["emoji_quiz"] = deepcopy(
            DEFAULT_DATA["emoji_quiz"]
        )

    if not isinstance(
        result["emoji_quiz"].get("users"),
        dict
    ):
        result["emoji_quiz"]["users"] = {}

    if "current_quiz" not in result["emoji_quiz"]:
        result["emoji_quiz"]["current_quiz"] = None

    if not isinstance(result["number_game"], dict):
        result["number_game"] = deepcopy(
            DEFAULT_DATA["number_game"]
        )

    for key, value in DEFAULT_DATA["number_game"].items():
        if key not in result["number_game"]:
            result["number_game"][key] = deepcopy(value)

    if not isinstance(
        result["number_game"]["wrong_attempts"],
        dict
    ):
        result["number_game"]["wrong_attempts"] = {}

    # Alte Bewerbungsdaten werden bewusst nicht übernommen.
    result.pop("applications", None)

    return result


data = load_data()


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
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


# ============================================================
# HELFER
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

    return any(
        role.id == OWNER_ROLE_ID
        for role in member.roles
    )


def is_shift_allowed(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    allowed_roles = {
        OWNER_ROLE_ID,
        SHIFT_PERMISSION_ROLE_ID,
        DEVELOPER_SHIFT_ROLE_ID
    }

    return any(
        role.id in allowed_roles
        for role in member.roles
    )


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


def extract_id(value):
    match = re.search(
        r"\d{5,25}",
        value
    )

    if not match:
        return None

    try:
        return int(match.group(0))
    except ValueError:
        return None


async def send_ephemeral(
    interaction,
    content=None,
    embed=None,
    view=None
):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=content,
                embed=embed,
                view=view,
                ephemeral=True
            )
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


async def get_text_channel(channel_id):
    channel = bot.get_channel(channel_id)

    if isinstance(channel, discord.TextChannel):
        return channel

    try:
        channel = await bot.fetch_channel(channel_id)

        if isinstance(channel, discord.TextChannel):
            return channel

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass

    return None


async def find_panel_message(
    channel,
    marker
):
    try:
        async for message in channel.history(limit=200):
            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            footer = message.embeds[0].footer

            if footer and footer.text == marker:
                return message

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass

    return None


async def ensure_panel(
    channel,
    embed,
    view,
    marker
):
    if channel is None:
        return

    existing = await find_panel_message(
        channel,
        marker
    )

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

    except (
        discord.Forbidden,
        discord.HTTPException
    ) as error:
        print(
            f"[PANEL] Fehler bei {marker}: {error}"
        )


# ============================================================
# COMMUNITY PANEL
# ============================================================

class CommunityPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Feedback",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_community_feedback"
    )
    async def feedback(
        self,
        interaction,
        button
    ):
        embed = discord.Embed(
            title="💬 Feedback",
            description=(
                "Wähle zuerst den **Textkanal** aus, "
                "in den dein Feedback gesendet werden soll."
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=CommunityChannelPickerView("feedback"),
            ephemeral=True
        )

    @discord.ui.button(
        label="Vorschlag",
        emoji="💡",
        style=discord.ButtonStyle.success,
        custom_id="rlp_community_suggestion"
    )
    async def suggestion(
        self,
        interaction,
        button
    ):
        embed = discord.Embed(
            title="💡 Vorschlag",
            description=(
                "Wähle zuerst den **Textkanal** aus, "
                "in den dein Vorschlag gesendet werden soll."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            view=CommunityChannelPickerView("suggestion"),
            ephemeral=True
        )


class CommunityChannelPickerView(discord.ui.View):

    def __init__(self, action):
        super().__init__(timeout=120)
        self.add_item(
            CommunityChannelSelect(action)
        )


class CommunityChannelSelect(discord.ui.ChannelSelect):

    def __init__(self, action):
        self.action = action

        super().__init__(
            placeholder="💬 Textkanal auswählen...",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text
            ]
        )

    async def callback(self, interaction):

        channel = self.values[0]

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await send_ephemeral(
                interaction,
                "❌ Bitte einen Textkanal auswählen."
            )
            return

        if self.action == "feedback":
            await interaction.response.send_modal(
                FeedbackModal(channel)
            )
            return

        if self.action == "suggestion":
            await interaction.response.send_modal(
                SuggestionModal(channel)
            )
            return

        await send_ephemeral(
            interaction,
            "❌ Unbekannte Aktion."
        )


# ============================================================
# FEEDBACK
# ============================================================

class FeedbackModal(
    discord.ui.Modal,
    title="💬 Feedback schreiben"
):

    feedback = discord.ui.TextInput(
        label="Dein Feedback",
        placeholder="Schreibe dein Feedback...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=2,
        max_length=3000
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        channel = self.target_channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await send_ephemeral(
                interaction,
                "❌ Der ausgewählte Chat wurde nicht gefunden."
            )
            return

        embed = discord.Embed(
            title="💬 Neues Feedback",
            description=self.feedback.value,
            color=discord.Color.blurple(),
            timestamp=dt.datetime.now(dt.timezone.utc)
        )

        embed.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🆔 User ID",
            value=str(interaction.user.id),
            inline=True
        )

        try:
            message = await channel.send(
                embed=embed
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann in diesem Chat nicht schreiben."
            )
            return

        except discord.HTTPException:
            await send_ephemeral(
                interaction,
                "❌ Das Feedback konnte nicht gesendet werden."
            )
            return

        data["feedback"].append({
            "user_id": interaction.user.id,
            "channel_id": channel.id,
            "message_id": message.id,
            "text": self.feedback.value,
            "created_at": dt.datetime.now(
                dt.timezone.utc
            ).isoformat()
        })

        save_data()

        await send_ephemeral(
            interaction,
            f"✅ Feedback wurde nach {channel.mention} gesendet."
        )


# ============================================================
# VORSCHLAG
# ============================================================

class SuggestionModal(
    discord.ui.Modal,
    title="💡 Vorschlag schreiben"
):

    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        placeholder="Schreibe deinen Vorschlag...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=2,
        max_length=3000
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        channel = self.target_channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await send_ephemeral(
                interaction,
                "❌ Der ausgewählte Chat wurde nicht gefunden."
            )
            return

        ids = []

        for key in data["suggestions"]:
            try:
                ids.append(int(key))
            except (
                ValueError,
                TypeError
            ):
                pass

        suggestion_id = (
            max(ids) + 1
            if ids
            else 1
        )

        embed = discord.Embed(
            title=f"💡 Vorschlag #{suggestion_id}",
            description=self.suggestion.value,
            color=discord.Color.gold(),
            timestamp=dt.datetime.now(dt.timezone.utc)
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

        embed.set_footer(
            text=f"Vorschlag ID: {suggestion_id}"
        )

        try:
            message = await channel.send(
                embed=embed,
                view=SuggestionReviewView()
            )

            try:
                await message.add_reaction("👍")
                await message.add_reaction("👎")
            except discord.HTTPException:
                pass

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )
            return

        except discord.HTTPException:
            await send_ephemeral(
                interaction,
                "❌ Der Vorschlag konnte nicht gesendet werden."
            )
            return

        data["suggestions"][str(suggestion_id)] = {
            "user_id": interaction.user.id,
            "channel_id": channel.id,
            "message_id": message.id,
            "text": self.suggestion.value,
            "status": "open",
            "created_at": dt.datetime.now(
                dt.timezone.utc
            ).isoformat()
        }

        save_data()

        await send_ephemeral(
            interaction,
            f"✅ Vorschlag wurde nach {channel.mention} gesendet."
        )


# ============================================================
# VORSCHLAG REVIEW
# ============================================================

class SuggestionReviewView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    def get_suggestion(self, message_id):

        for suggestion_id, suggestion in data[
            "suggestions"
        ].items():

            if str(
                suggestion.get("message_id")
            ) == str(message_id):

                return suggestion_id, suggestion

        return None, None

    @discord.ui.button(
        label="Annehmen",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="rlp_suggestion_accept"
    )
    async def accept(
        self,
        interaction,
        button
    ):
        if not has_suggestion_review_permission(
            interaction.user
        ):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung."
            )
            return

        suggestion_id, suggestion = self.get_suggestion(
            interaction.message.id
        )

        if suggestion is None:
            await send_ephemeral(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )
            return

        suggestion["status"] = "accepted"
        save_data()

        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()

            for field in embed.fields:
                if field.name == "📊 Status":
                    field.value = "🟢 Angenommen"

            try:
                await interaction.message.edit(
                    embed=embed
                )
            except discord.HTTPException:
                pass

        await send_ephemeral(
            interaction,
            f"✅ Vorschlag #{suggestion_id} wurde angenommen."
        )

    @discord.ui.button(
        label="Ablehnen",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_suggestion_reject"
    )
    async def reject(
        self,
        interaction,
        button
    ):
        if not has_suggestion_review_permission(
            interaction.user
        ):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung."
            )
            return

        suggestion_id, suggestion = self.get_suggestion(
            interaction.message.id
        )

        if suggestion is None:
            await send_ephemeral(
                interaction,
                "❌ Vorschlag nicht gefunden."
            )
            return

        suggestion["status"] = "rejected"
        save_data()

        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()

            for field in embed.fields:
                if field.name == "📊 Status":
                    field.value = "🔴 Abgelehnt"

            try:
                await interaction.message.edit(
                    embed=embed
                )
            except discord.HTTPException:
                pass

        await send_ephemeral(
            interaction,
            f"❌ Vorschlag #{suggestion_id} wurde abgelehnt."
        )


# ============================================================
# OWNER PANEL
# ============================================================

class OwnerPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def check_owner(self, interaction):

        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Keine Berechtigung."
            )
            return False

        return True

    async def picker(
        self,
        interaction,
        action,
        title
    ):
        if not await self.check_owner(interaction):
            return

        embed = discord.Embed(
            title=title,
            description=(
                "Bitte wähle zuerst den **Textkanal** aus."
            ),
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            view=OwnerChannelPickerView(action),
            ephemeral=True
        )

    @discord.ui.button(
        label="Ankündigung",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_owner_announcement"
    )
    async def announcement(self, interaction, button):
        await self.picker(
            interaction,
            "announcement",
            "📢 Ankündigung"
        )

    @discord.ui.button(
        label="Bot Say",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_owner_bot_say"
    )
    async def bot_say(self, interaction, button):
        await self.picker(
            interaction,
            "bot_say",
            "💬 Bot Say"
        )

    @discord.ui.button(
        label="Giveaway",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="rlp_owner_giveaway"
    )
    async def giveaway(self, interaction, button):
        await self.picker(
            interaction,
            "giveaway",
            "🎁 Giveaway"
        )

    @discord.ui.button(
        label="User Info",
        emoji="👤",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_owner_user_info"
    )
    async def user_info(self, interaction, button):
        await self.picker(
            interaction,
            "user_info",
            "👤 User Info"
        )

    @discord.ui.button(
        label="Rollen Info",
        emoji="🎭",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_owner_role_info"
    )
    async def role_info(self, interaction, button):
        await self.picker(
            interaction,
            "role_info",
            "🎭 Rollen Info"
        )

    @discord.ui.button(
        label="Server Info",
        emoji="🖥️",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_owner_server_info"
    )
    async def server_info(self, interaction, button):
        await self.picker(
            interaction,
            "server_info",
            "🖥️ Server Info"
        )

    @discord.ui.button(
        label="Lock",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_owner_lock"
    )
    async def lock(self, interaction, button):
        await self.picker(
            interaction,
            "lock",
            "🔒 Lock"
        )

    @discord.ui.button(
        label="Unlock",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="rlp_owner_unlock"
    )
    async def unlock(self, interaction, button):
        await self.picker(
            interaction,
            "unlock",
            "🔓 Unlock"
        )

    @discord.ui.button(
        label="Status",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_owner_status"
    )
    async def status(self, interaction, button):
        await self.picker(
            interaction,
            "status",
            "📊 Status"
        )

    @discord.ui.button(
        label="Clear",
        emoji="🧹",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_owner_clear"
    )
    async def clear(self, interaction, button):
        await self.picker(
            interaction,
            "clear",
            "🧹 Clear"
        )


class OwnerChannelPickerView(discord.ui.View):

    def __init__(self, action):
        super().__init__(timeout=120)
        self.add_item(
            OwnerChannelSelect(action)
        )


class OwnerChannelSelect(discord.ui.ChannelSelect):

    def __init__(self, action):
        self.action = action

        super().__init__(
            placeholder="📁 Textkanal auswählen...",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text
            ]
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Keine Berechtigung."
            )
            return

        channel = self.values[0]

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await send_ephemeral(
                interaction,
                "❌ Bitte einen Textkanal auswählen."
            )
            return

        if self.action == "announcement":
            await interaction.response.send_modal(
                OwnerAnnouncementModal(channel)
            )
            return

        if self.action == "bot_say":
            await interaction.response.send_modal(
                OwnerBotSayModal(channel)
            )
            return

        if self.action == "giveaway":
            await interaction.response.send_modal(
                OwnerGiveawayModal(channel)
            )
            return

        if self.action == "user_info":
            await interaction.response.send_modal(
                OwnerUserInfoModal(channel)
            )
            return

        if self.action == "role_info":
            await interaction.response.send_modal(
                OwnerRoleInfoModal(channel)
            )
            return

        if self.action == "clear":
            await interaction.response.send_modal(
                OwnerClearModal(channel)
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        # ----------------------------------------------------
        # SERVER INFO
        # ----------------------------------------------------

        if self.action == "server_info":

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
                name="😀 Emojis",
                value=str(len(guild.emojis)),
                inline=True
            )

            if guild.owner:
                embed.add_field(
                    name="👑 Server Owner",
                    value=guild.owner.mention,
                    inline=False
                )

            if guild.icon:
                embed.set_thumbnail(
                    url=guild.icon.url
                )

            try:
                await channel.send(embed=embed)

                await interaction.followup.send(
                    f"✅ Server-Info wurde nach {channel.mention} gesendet.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Der Bot kann dort nicht schreiben.",
                    ephemeral=True
                )

            return

        # ----------------------------------------------------
        # LOCK / UNLOCK
        # ----------------------------------------------------

        if self.action in ("lock", "unlock"):

            overwrite = channel.overwrites_for(
                guild.default_role
            )

            if self.action == "lock":
                overwrite.send_messages = False

                result = "gesperrt"
                message_text = (
                    "🔒 **Dieser Kanal wurde gesperrt.**"
                )

            else:
                overwrite.send_messages = None

                result = "entsperrt"
                message_text = (
                    "🔓 **Dieser Kanal wurde entsperrt.**"
                )

            try:
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=overwrite,
                    reason="RLP Owner Panel"
                )

                try:
                    await channel.send(
                        message_text
                    )
                except discord.Forbidden:
                    pass

                await interaction.followup.send(
                    f"✅ {channel.mention} wurde {result}.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Der Bot darf diesen Kanal nicht bearbeiten.",
                    ephemeral=True
                )

            except discord.HTTPException:
                await interaction.followup.send(
                    "❌ Der Kanal konnte nicht bearbeitet werden.",
                    ephemeral=True
                )

            return

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if self.action == "status":

            uptime = int(
                time.time() - BOT_START_TIME
            )

            days, remainder = divmod(
                uptime,
                86400
            )

            hours, remainder = divmod(
                remainder,
                3600
            )

            minutes, seconds = divmod(
                remainder,
                60
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
                value=f"{round(bot.latency * 1000)} ms",
                inline=True
            )

            embed.add_field(
                name="⏱️ Uptime",
                value=(
                    f"{days}d {hours}h "
                    f"{minutes}m {seconds}s"
                ),
                inline=False
            )

            embed.add_field(
                name="🏠 Server",
                value=str(len(bot.guilds)),
                inline=True
            )

            total_members = sum(
                guild.member_count or 0
                for guild in bot.guilds
            )

            embed.add_field(
                name="👥 Nutzer",
                value=str(total_members),
                inline=True
            )

            try:
                await channel.send(embed=embed)

                await interaction.followup.send(
                    f"✅ Status wurde nach {channel.mention} gesendet.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Der Bot kann dort nicht schreiben.",
                    ephemeral=True
                )

            return

        await interaction.followup.send(
            "❌ Unbekannte Owner-Aktion.",
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
        placeholder="Schreibe die Ankündigung...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.text.value,
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        try:
            await self.target_channel.send(
                embed=embed
            )

            await send_ephemeral(
                interaction,
                f"✅ Ankündigung wurde nach {self.target_channel.mention} gesendet."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )


class OwnerBotSayModal(
    discord.ui.Modal,
    title="💬 Bot Say"
):

    text = discord.ui.TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot schreiben?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        try:
            await self.target_channel.send(
                self.text.value
            )

            await send_ephemeral(
                interaction,
                f"✅ Nachricht wurde nach {self.target_channel.mention} gesendet."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )


class OwnerGiveawayModal(
    discord.ui.Modal,
    title="🎁 Giveaway"
):

    giveaway_title = discord.ui.TextInput(
        label="Titel",
        placeholder="Giveaway Titel",
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

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        embed = discord.Embed(
            title=f"🎁 {self.giveaway_title.value}",
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
            text=f"Giveaway von {interaction.user.display_name}"
        )

        try:
            message = await self.target_channel.send(
                embed=embed
            )

            await message.add_reaction("🎉")

            await send_ephemeral(
                interaction,
                f"🎁 Giveaway wurde nach {self.target_channel.mention} gesendet."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )


class OwnerUserInfoModal(
    discord.ui.Modal,
    title="👤 User Info"
):

    user = discord.ui.TextInput(
        label="User ID oder Erwähnung",
        placeholder="123456789012345678",
        required=True,
        max_length=100
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        user_id = extract_id(
            self.user.value
        )

        if user_id is None:
            await send_ephemeral(
                interaction,
                "❌ Keine gültige User-ID gefunden."
            )
            return

        member = interaction.guild.get_member(
            user_id
        )

        if member is None:
            try:
                member = await interaction.guild.fetch_member(
                    user_id
                )
            except (
                discord.NotFound,
                discord.HTTPException
            ):
                await send_ephemeral(
                    interaction,
                    "❌ User wurde nicht auf dem Server gefunden."
                )
                return

        embed = discord.Embed(
            title="👤 User Informationen",
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
                "F"
            ),
            inline=False
        )

        if member.joined_at:
            embed.add_field(
                name="📥 Beigetreten",
                value=discord.utils.format_dt(
                    member.joined_at,
                    "F"
                ),
                inline=False
            )

        roles = [
            role.mention
            for role in member.roles
            if role != interaction.guild.default_role
        ]

        embed.add_field(
            name="🎭 Rollen",
            value=", ".join(roles)
            if roles
            else "Keine",
            inline=False
        )

        try:
            await self.target_channel.send(
                embed=embed
            )

            await send_ephemeral(
                interaction,
                f"✅ User-Info wurde nach {self.target_channel.mention} gesendet."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )


class OwnerRoleInfoModal(
    discord.ui.Modal,
    title="🎭 Rollen Info"
):

    role = discord.ui.TextInput(
        label="Rollen ID oder Erwähnung",
        placeholder="123456789012345678",
        required=True,
        max_length=100
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        role_id = extract_id(
            self.role.value
        )

        if role_id is None:
            await send_ephemeral(
                interaction,
                "❌ Keine gültige Rollen-ID gefunden."
            )
            return

        role = interaction.guild.get_role(
            role_id
        )

        if role is None:
            await send_ephemeral(
                interaction,
                "❌ Rolle wurde nicht gefunden."
            )
            return

        embed = discord.Embed(
            title="🎭 Rollen Informationen",
            color=(
                role.color
                if role.color.value
                else discord.Color.blurple()
            )
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
            name="📊 Position",
            value=str(role.position),
            inline=True
        )

        embed.add_field(
            name="🔐 Erwähnbar",
            value="Ja" if role.mentionable else "Nein",
            inline=True
        )

        embed.add_field(
            name="🤖 Managed",
            value="Ja" if role.managed else "Nein",
            inline=True
        )

        try:
            await self.target_channel.send(
                embed=embed
            )

            await send_ephemeral(
                interaction,
                f"✅ Rollen-Info wurde nach {self.target_channel.mention} gesendet."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot kann dort nicht schreiben."
            )


class OwnerClearModal(
    discord.ui.Modal,
    title="🧹 Nachrichten löschen"
):

    amount = discord.ui.TextInput(
        label="Anzahl",
        placeholder="1 bis 100",
        required=True,
        max_length=3
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction):

        try:
            amount = int(self.amount.value)
        except ValueError:
            await send_ephemeral(
                interaction,
                "❌ Bitte eine gültige Zahl eingeben."
            )
            return

        if amount < 1 or amount > 100:
            await send_ephemeral(
                interaction,
                "❌ Die Anzahl muss zwischen 1 und 100 liegen."
            )
            return

        try:
            deleted = await self.target_channel.purge(
                limit=amount
            )

            report = await self.target_channel.send(
                f"🧹 **{len(deleted)} Nachrichten gelöscht.**"
            )

            asyncio.create_task(
                delete_after_seconds(
                    report,
                    5
                )
            )

            await send_ephemeral(
                interaction,
                f"✅ {len(deleted)} Nachrichten gelöscht."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Der Bot hat keine Lösch-Berechtigung."
            )

        except discord.HTTPException:
            await send_ephemeral(
                interaction,
                "❌ Nachrichten konnten nicht gelöscht werden."
            )


# ============================================================
# NAMETAG
# ============================================================

class NametagModal(
    discord.ui.Modal,
    title="🏷️ Nametag ändern"
):

    nametag = discord.ui.TextInput(
        label="Nametag",
        placeholder="z. B. Max",
        required=True,
        min_length=1,
        max_length=25
    )

    async def on_submit(self, interaction):

        role = interaction.guild.get_role(
            NAMETAG_ROLE_ID
        )

        if role is None:
            await send_ephemeral(
                interaction,
                "❌ Nametag-Rolle wurde nicht gefunden."
            )
            return

        if role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(
                    role,
                    reason="RLP Nametag System"
                )
            except discord.Forbidden:
                await send_ephemeral(
                    interaction,
                    "❌ Nametag-Rolle konnte nicht vergeben werden."
                )
                return

        name = self.nametag.value.strip()

        final_name = f"{NAMETAG}{name}"

        if len(final_name) > 32:
            await send_ephemeral(
                interaction,
                "❌ Der fertige Name ist zu lang."
            )
            return

        try:
            await interaction.user.edit(
                nick=final_name,
                reason="RLP Nametag System"
            )

            await send_ephemeral(
                interaction,
                f"✅ Dein Name wurde zu **{final_name}** geändert."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Ich kann deinen Nicknamen nicht ändern."
            )


class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag setzen",
        emoji="🏷️",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_nametag_set"
    )
    async def set_nametag(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            NametagModal()
        )

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_nametag_remove"
    )
    async def remove_nametag(
        self,
        interaction,
        button
    ):
        try:
            await interaction.user.edit(
                nick=None,
                reason="RLP Nametag entfernt"
            )

            await send_ephemeral(
                interaction,
                "✅ Dein Nametag wurde entfernt."
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "❌ Ich kann deinen Nicknamen nicht ändern."
            )


# ============================================================
# KENNZEICHEN
# ============================================================

class LicensePlateModal(
    discord.ui.Modal,
    title="🚘 Kennzeichen eintragen"
):

    plate = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RY ZE 01",
        required=True,
        min_length=2,
        max_length=20
    )

    async def on_submit(self, interaction):

        plate = normalize_plate(
            self.plate.value
        )

        # Buchstaben, Zahlen und Leerzeichen.
        # Damit funktionieren z. B.:
        # RY ZE 01
        # GM AB 123
        # RY-AB 123
        # RY 123
        if not re.fullmatch(
            r"[A-ZÄÖÜ0-9]+(?:[ -][A-ZÄÖÜ0-9]+)*",
            plate
        ):
            await send_ephemeral(
                interaction,
                (
                    "❌ Ungültiges Kennzeichen.\n"
                    "Erlaubt sind Buchstaben, Zahlen, "
                    "Leerzeichen und Bindestriche."
                )
            )
            return

        # Prüfen, ob das Kennzeichen schon jemand anderem gehört.
        for user_id, saved_plate in data[
            "license_plates"
        ].items():

            if normalize_plate(saved_plate) == plate:

                if str(user_id) != str(
                    interaction.user.id
                ):
                    await send_ephemeral(
                        interaction,
                        "❌ Dieses Kennzeichen ist bereits vergeben."
                    )
                    return

        # Altes Kennzeichen des Users wird überschrieben.
        data["license_plates"][
            str(interaction.user.id)
        ] = plate

        save_data()

        # Panel sofort aktualisieren.
        await refresh_license_panel()

        await send_ephemeral(
            interaction,
            f"✅ Kennzeichen **{plate}** wurde gespeichert."
        )


class LicenseView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen eintragen / ändern",
        emoji="🚘",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_license_register"
    )
    async def register(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @discord.ui.button(
        label="Aktualisieren",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_license_refresh"
    )
    async def refresh(
        self,
        interaction,
        button
    ):
        await refresh_license_panel()

        await send_ephemeral(
            interaction,
            "🔄 Kennzeichenliste wurde aktualisiert."
        )


async def refresh_license_panel():

    channel = await get_text_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

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

    lines = []

    for user_id, plate in data[
        "license_plates"
    ].items():

        try:
            member = channel.guild.get_member(
                int(user_id)
            )
        except (
            ValueError,
            TypeError
        ):
            member = None

        user_text = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"🚘 **{plate}** — {user_text}"
        )

    lines.sort(
        key=lambda value: value.lower()
    )

    if not lines:

        embed.add_field(
            name="📋 Registrierte Kennzeichen",
            value="Noch keine Kennzeichen eingetragen.",
            inline=False
        )

    else:

        chunks = []
        current = []
        current_length = 0

        for line in lines:

            if (
                current
                and current_length + len(line) + 1 > 1000
            ):
                chunks.append(
                    "\n".join(current)
                )
                current = []
                current_length = 0

            current.append(line)
            current_length += len(line) + 1

        if current:
            chunks.append(
                "\n".join(current)
            )

        for index, chunk in enumerate(
            chunks,
            start=1
        ):
            embed.add_field(
                name=(
                    "📋 Registrierte Kennzeichen"
                    if index == 1
                    else f"📋 Weitere Kennzeichen {index}"
                ),
                value=chunk,
                inline=False
            )

    embed.set_footer(
        text=LICENSE_PANEL_MARKER
    )

    existing = await find_panel_message(
        channel,
        LICENSE_PANEL_MARKER
    )

    try:
        if existing:
            await existing.edit(
                embed=embed,
                view=LicenseView()
            )
        else:
            await channel.send(
                embed=embed,
                view=LicenseView()
            )

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


# ============================================================
# DEVELOPER TASKS
# ============================================================

class DeveloperTaskModal(
    discord.ui.Modal,
    title="💻 Entwickler-Aufgabe"
):

    task_title = discord.ui.TextInput(
        label="Titel",
        placeholder="Titel der Aufgabe",
        required=True,
        max_length=200
    )

    description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3000
    )

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Keine Berechtigung."
            )
            return

        ids = []

        for key in data["developer_tasks"]:
            try:
                ids.append(int(key))
            except (
                ValueError,
                TypeError
            ):
                pass

        task_id = (
            max(ids) + 1
            if ids
            else 1
        )

        task_data = {
            "title": self.task_title.value,
            "description": self.description.value,
            "created_by": interaction.user.id,
            "assigned_to": None,
            "status": "open",
            "created_at": dt.datetime.now(
                dt.timezone.utc
            ).isoformat()
        }

        data["developer_tasks"][
            str(task_id)
        ] = task_data

        save_data()

        channel = await get_text_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title=f"💻 Entwickler-Aufgabe #{task_id}",
                description=self.description.value,
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="📌 Titel",
                value=self.task_title.value,
                inline=False
            )

            embed.add_field(
                name="📊 Status",
                value="🟡 Offen",
                inline=True
            )

            embed.add_field(
                name="👤 Erstellt von",
                value=interaction.user.mention,
                inline=True
            )

            embed.set_footer(
                text=f"Developer Task ID: {task_id}"
            )

            try:
                await channel.send(
                    embed=embed,
                    view=DeveloperTaskActionView()
                )
            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        await send_ephemeral(
            interaction,
            f"✅ Aufgabe #{task_id} wurde erstellt."
        )


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_dev_task_create"
    )
    async def create(
        self,
        interaction,
        button
    ):
        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Keine Berechtigung."
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )

    @discord.ui.button(
        label="Aufgaben anzeigen",
        emoji="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_dev_task_list"
    )
    async def list_tasks(
        self,
        interaction,
        button
    ):
        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Keine Berechtigung."
            )
            return

        open_tasks = []

        for task_id, task in data[
            "developer_tasks"
        ].items():

            if task.get("status") != "deleted":
                open_tasks.append(
                    (
                        task_id,
                        task
                    )
                )

        if not open_tasks:
            await send_ephemeral(
                interaction,
                "📋 Es gibt aktuell keine Aufgaben."
            )
            return

        lines = []

        for task_id, task in open_tasks[:20]:

            status = task.get(
                "status",
                "open"
            )

            if status == "open":
                status_text = "🟡 Offen"
            elif status == "claimed":
                status_text = "🔵 Übernommen"
            elif status == "done":
                status_text = "🟢 Erledigt"
            else:
                status_text = status

            lines.append(
                f"**#{task_id}** — "
                f"{task.get('title', 'Ohne Titel')} — "
                f"{status_text}"
            )

        embed = discord.Embed(
            title="📋 Entwickler-Aufgaben",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )

        await send_ephemeral(
            interaction,
            embed=embed
        )


class DeveloperTaskActionView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    def get_task(self, message_id):

        for task_id, task in data[
            "developer_tasks"
        ].items():

            if str(
                task.get("message_id")
            ) == str(message_id):

                return task_id, task

        # Fallback:
        # Bei alten Aufgaben steht die ID im Embed-Footer.
        return None, None

    def get_task_from_embed(self, message):

        if not message.embeds:
            return None, None

        footer = message.embeds[0].footer

        if not footer:
            return None, None

        text = footer.text or ""

        match = re.search(
            r"Developer Task ID:\s*(\d+)",
            text
        )

        if not match:
            return None, None

        task_id = match.group(1)

        task = data[
            "developer_tasks"
        ].get(task_id)

        return task_id, task

    @discord.ui.button(
        label="Aufgabe übernehmen",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="rlp_dev_task_claim"
    )
    async def claim(
        self,
        interaction,
        button
    ):
        if not is_shift_allowed(
            interaction.user
        ):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung."
            )
            return

        task_id, task = self.get_task_from_embed(
            interaction.message
        )

        if task is None:
            await send_ephemeral(
                interaction,
                "❌ Aufgabe wurde nicht gefunden."
            )
            return

        if task.get("status") == "done":
            await send_ephemeral(
                interaction,
                "⚠️ Diese Aufgabe ist bereits erledigt."
            )
            return

        task["status"] = "claimed"
        task["assigned_to"] = interaction.user.id

        save_data()

        await self.update_embed(
            interaction.message,
            task,
            task_id
        )

        await send_ephemeral(
            interaction,
            f"🟢 Aufgabe #{task_id} wurde übernommen."
        )

    @discord.ui.button(
        label="Erledigt",
        emoji="✅",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_dev_task_done"
    )
    async def done(
        self,
        interaction,
        button
    ):
        if not is_shift_allowed(
            interaction.user
        ):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung."
            )
            return

        task_id, task = self.get_task_from_embed(
            interaction.message
        )

        if task is None:
            await send_ephemeral(
                interaction,
                "❌ Aufgabe wurde nicht gefunden."
            )
            return

        task["status"] = "done"
        task["completed_by"] = interaction.user.id
        task["completed_at"] = dt.datetime.now(
            dt.timezone.utc
        ).isoformat()

        save_data()

        await self.update_embed(
            interaction.message,
            task,
            task_id
        )

        await send_ephemeral(
            interaction,
            f"✅ Aufgabe #{task_id} wurde als erledigt markiert."
        )

    @discord.ui.button(
        label="Löschen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_dev_task_delete"
    )
    async def delete(
        self,
        interaction,
        button
    ):
        if not is_owner(interaction.user):
            await send_ephemeral(
                interaction,
                "❌ Nur Owner können Aufgaben löschen."
            )
            return

        task_id, task = self.get_task_from_embed(
            interaction.message
        )

        if task is None:
            await send_ephemeral(
                interaction,
                "❌ Aufgabe wurde nicht gefunden."
            )
            return

        task["status"] = "deleted"

        save_data()

        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass

        await send_ephemeral(
            interaction,
            f"🗑️ Aufgabe #{task_id} wurde gelöscht."
        )

    async def update_embed(
        self,
        message,
        task,
        task_id
    ):
        if not message.embeds:
            return

        embed = message.embeds[0]

        status = task.get(
            "status",
            "open"
        )

        if status == "open":
            status_text = "🟡 Offen"
            color = discord.Color.blurple()

        elif status == "claimed":
            status_text = "🔵 Übernommen"
            color = discord.Color.blue()

        elif status == "done":
            status_text = "🟢 Erledigt"
            color = discord.Color.green()

        else:
            status_text = status
            color = discord.Color.blurple()

        embed.color = color

        for field in embed.fields:

            if field.name == "📊 Status":
                field.value = status_text

        assigned = task.get("assigned_to")

        if assigned:
            found = False

            for field in embed.fields:

                if field.name == "👨‍💻 Bearbeitet von":
                    field.value = f"<@{assigned}>"
                    found = True

            if not found:
                embed.add_field(
                    name="👨‍💻 Bearbeitet von",
                    value=f"<@{assigned}>",
                    inline=True
                )

        try:
            await message.edit(
                embed=embed,
                view=self
            )
        except discord.HTTPException:
            pass


# ============================================================
# DEVELOPER SHIFT
# ============================================================

class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def get_shift_role(self, guild):

        role = guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:
            try:
                role = await guild.fetch_role(
                    DEVELOPER_SHIFT_ROLE_ID
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                return None

        return role

    @discord.ui.button(
        label="Dienst starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="rlp_dev_shift_start"
    )
    async def start(
        self,
        interaction,
        button
    ):
        member = interaction.user

        if not is_shift_allowed(member):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung für den Entwicklerdienst."
            )
            return

        user_id = str(member.id)

        if user_id in data[
            "active_developer_shifts"
        ]:
            await send_ephemeral(
                interaction,
                "⚠️ Du bist bereits im Dienst."
            )
            return

        role = await self.get_shift_role(
            interaction.guild
        )

        if role is None:
            await send_ephemeral(
                interaction,
                "❌ Die Entwicklerdienst-Rolle wurde nicht gefunden."
            )
            return

        # Bot darf die Rolle nicht verwalten, wenn sie
        # über seiner höchsten Rolle liegt.
        if role >= interaction.guild.me.top_role:
            await send_ephemeral(
                interaction,
                "❌ Die Entwicklerdienst-Rolle liegt über meiner Bot-Rolle."
            )
            return

        try:
            await member.add_roles(
                role,
                reason="RLP Entwicklerdienst gestartet"
            )

        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                (
                    "❌ Die Dienstrolle konnte nicht vergeben werden.\n"
                    "Prüfe **Manage Roles** und ob meine Bot-Rolle "
                    "über der Dienstrolle steht."
                )
            )
            return

        except discord.HTTPException:
            await send_ephemeral(
                interaction,
                "❌ Die Dienstrolle konnte nicht vergeben werden."
            )
            return

        now = dt.datetime.now(
            dt.timezone.utc
        )

        data[
            "active_developer_shifts"
        ][user_id] = {
            "started": now.isoformat()
        }

        save_data()

        log_channel = await get_text_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            try:
                await log_channel.send(
                    f"🟢 {member.mention} "
                    f"hat den Entwicklerdienst gestartet."
                )
            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        await send_ephemeral(
            interaction,
            "🟢 Dein Entwicklerdienst wurde gestartet."
        )

    @discord.ui.button(
        label="Dienst beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_dev_shift_stop"
    )
    async def stop(
        self,
        interaction,
        button
    ):
        member = interaction.user

        if not is_shift_allowed(member):
            await send_ephemeral(
                interaction,
                "❌ Du hast keine Berechtigung für den Entwicklerdienst."
            )
            return

        user_id = str(member.id)

        shift = data[
            "active_developer_shifts"
        ].get(user_id)

        if not shift:
            await send_ephemeral(
                interaction,
                "⚠️ Du bist aktuell nicht im Dienst."
            )
            return

        try:
            started = dt.datetime.fromisoformat(
                shift["started"]
            )

            now = dt.datetime.now(
                dt.timezone.utc
            )

            total_seconds = max(
                0,
                int(
                    (
                        now - started
                    ).total_seconds()
                )
            )

            hours, remainder = divmod(
                total_seconds,
                3600
            )

            minutes, seconds = divmod(
                remainder,
                60
            )

            duration = (
                f"{hours}h "
                f"{minutes}m "
                f"{seconds}s"
            )

        except Exception:
            duration = "Unbekannt"

        role = await self.get_shift_role(
            interaction.guild
        )

        if role is not None:

            try:
                await member.remove_roles(
                    role,
                    reason="RLP Entwicklerdienst beendet"
                )

            except discord.Forbidden:
                await send_ephemeral(
                    interaction,
                    (
                        "❌ Die Dienstrolle konnte nicht entfernt werden.\n"
                        "Prüfe **Manage Roles** und die Rollenposition."
                    )
                )
                return

            except discord.HTTPException:
                await send_ephemeral(
                    interaction,
                    "❌ Die Dienstrolle konnte nicht entfernt werden."
                )
                return

        del data[
            "active_developer_shifts"
        ][user_id]

        save_data()

        log_channel = await get_text_channel(
            SHIFT_LOG_CHANNEL_ID
        )

        if log_channel:

            try:
                await log_channel.send(
                    f"🔴 {member.mention} "
                    f"hat den Entwicklerdienst beendet.\n"
                    f"⏱️ Dauer: **{duration}**"
                )
            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        await send_ephemeral(
            interaction,
            (
                f"🔴 Dienst beendet.\n"
                f"⏱️ Dauer: **{duration}**"
            )
        )


# ============================================================
# EMOJI QUIZ
# ============================================================

QUIZ_QUESTIONS = [
    {
        "emoji": "🦁👑",
        "answer": "der könig der löwen",
        "hint": "Ein Film mit Simba.",
        "letter": "K"
    },
    {
        "emoji": "❄️👸",
        "answer": "frozen",
        "hint": "Elsa spielt eine wichtige Rolle.",
        "letter": "F"
    },
    {
        "emoji": "🧙⚡",
        "answer": "harry potter",
        "hint": "Ein berühmter Zauberer.",
        "letter": "H"
    },
    {
        "emoji": "🕷️🦸",
        "answer": "spiderman",
        "hint": "Ein Superheld mit Spinnenkräften.",
        "letter": "S"
    },
    {
        "emoji": "🚢🧊",
        "answer": "titanic",
        "hint": "Ein berühmtes Schiff.",
        "letter": "T"
    }
]


def get_quiz_state(user_id):

    user_id = str(user_id)

    users = data[
        "emoji_quiz"
    ]["users"]

    if user_id not in users:

        users[user_id] = {
            "tips": 0,
            "letters": 0,
            "skips": 0,
            "score": 0,
            "reset_at": time.time() + 7200
        }

        save_data()

    state = users[user_id]

    if time.time() >= state.get(
        "reset_at",
        0
    ):

        state["tips"] = 0
        state["letters"] = 0
        state["skips"] = 0
        state["reset_at"] = time.time() + 7200

        save_data()

    return state


def start_quiz():

    question = random.choice(
        QUIZ_QUESTIONS
    )

    data[
        "emoji_quiz"
    ]["current_quiz"] = {
        "emoji": question["emoji"],
        "answer": question["answer"],
        "hint": question["hint"],
        "letter": question["letter"]
    }

    save_data()

    return question


class EmojiAnswerModal(
    discord.ui.Modal,
    title="🧩 Quiz Antwort"
):

    answer = discord.ui.TextInput(
        label="Deine Antwort",
        placeholder="Deine Antwort...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction):

        quiz = data[
            "emoji_quiz"
        ].get("current_quiz")

        if not quiz:
            await send_ephemeral(
                interaction,
                "❌ Aktuell läuft kein Quiz."
            )
            return

        answer = self.answer.value.lower().strip()

        answer = re.sub(
            r"\s+",
            " ",
            answer
        )

        if answer == quiz["answer"]:

            state = get_quiz_state(
                interaction.user.id
            )

            state["score"] += 1

            save_data()

            await send_ephemeral(
                interaction,
                (
                    f"🎉 **Richtig!**\n"
                    f"Du hast jetzt **{state['score']} Punkte**."
                )
            )

        else:

            await send_ephemeral(
                interaction,
                "❌ Leider falsch."
            )


class EmojiQuizView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Neues Quiz",
        emoji="▶️",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_emoji_new"
    )
    async def new_quiz(
        self,
        interaction,
        button
    ):
        question = start_quiz()

        embed = discord.Embed(
            title="🧩 Emoji Quiz",
            description=(
                "Errate den Begriff:\n\n"
                f"# {question['emoji']}"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="Tipp anfordern",
        emoji="💡",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_emoji_hint"
    )
    async def hint(
        self,
        interaction,
        button
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if state["tips"] >= 3:
            await send_ephemeral(
                interaction,
                (
                    "❌ Deine Tipps sind aufgebraucht: **3/3**.\n"
                    "Sie werden alle 2 Stunden zurückgesetzt."
                )
            )
            return

        quiz = data[
            "emoji_quiz"
        ].get("current_quiz")

        if not quiz:
            await send_ephemeral(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )
            return

        state["tips"] += 1
        save_data()

        await send_ephemeral(
            interaction,
            (
                f"💡 **Tipp:** {quiz['hint']}\n"
                f"Nutzung: **{state['tips']}/3**"
            )
        )

    @discord.ui.button(
        label="Anfangsbuchstaben",
        emoji="🔤",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_emoji_letter"
    )
    async def letter(
        self,
        interaction,
        button
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if state["letters"] >= 3:
            await send_ephemeral(
                interaction,
                (
                    "❌ Deine Anfangsbuchstaben sind aufgebraucht: "
                    "**3/3**.\n"
                    "Sie werden alle 2 Stunden zurückgesetzt."
                )
            )
            return

        quiz = data[
            "emoji_quiz"
        ].get("current_quiz")

        if not quiz:
            await send_ephemeral(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )
            return

        state["letters"] += 1
        save_data()

        await send_ephemeral(
            interaction,
            (
                f"🔤 Anfangsbuchstabe: **{quiz['letter']}**\n"
                f"Nutzung: **{state['letters']}/3**"
            )
        )

    @discord.ui.button(
        label="Aufgabe überspringen",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_emoji_skip"
    )
    async def skip(
        self,
        interaction,
        button
    ):
        state = get_quiz_state(
            interaction.user.id
        )

        if state["skips"] >= 3:
            await send_ephemeral(
                interaction,
                (
                    "❌ Deine Überspringen-Nutzungen "
                    "sind aufgebraucht: **3/3**.\n"
                    "Sie werden alle 2 Stunden zurückgesetzt."
                )
            )
            return

        state["skips"] += 1

        question = start_quiz()

        embed = discord.Embed(
            title="🧩 Emoji Quiz",
            description=(
                "⏭️ Aufgabe übersprungen.\n\n"
                f"Neue Aufgabe:\n\n"
                f"# {question['emoji']}"
            ),
            color=discord.Color.blurple()
        )

        save_data()

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="Bestenliste",
        emoji="🏆",
        style=discord.ButtonStyle.success,
        custom_id="rlp_emoji_leaderboard"
    )
    async def leaderboard(
        self,
        interaction,
        button
    ):
        entries = []

        for user_id, state in data[
            "emoji_quiz"
        ]["users"].items():

            try:
                score = int(
                    state.get(
                        "score",
                        0
                    )
                )
                numeric_user_id = int(user_id)
            except (
                ValueError,
                TypeError
            ):
                continue

            entries.append(
                (
                    score,
                    numeric_user_id
                )
            )

        entries.sort(
            reverse=True
        )

        lines = []

        for index, (
            score,
            user_id
        ) in enumerate(
            entries[:10],
            start=1
        ):
            lines.append(
                f"**{index}.** <@{user_id}> — "
                f"**{score} Punkte**"
            )

        embed = discord.Embed(
            title="🏆 Emoji Quiz Bestenliste",
            description=(
                "\n".join(lines)
                if lines
                else "Noch keine Punkte."
            ),
            color=discord.Color.gold()
        )

        await send_ephemeral(
            interaction,
            embed=embed
        )

    @discord.ui.button(
        label="Antworten",
        emoji="✍️",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_emoji_answer"
    )
    async def answer(
        self,
        interaction,
        button
    ):
        quiz = data[
            "emoji_quiz"
        ].get("current_quiz")

        if not quiz:
            await send_ephemeral(
                interaction,
                "❌ Starte zuerst ein neues Quiz."
            )
            return

        await interaction.response.send_modal(
            EmojiAnswerModal()
        )


# ============================================================
# ZAHLENSPIEL
# ============================================================

def wrong_timeout_minutes(wrong_count):

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


async def handle_number_game(message):

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

    try:
        number = int(content)
    except ValueError:
        return False

    number_game = data["number_game"]

    try:
        expected = int(
            number_game.get(
                "current_number",
                1
            )
        )
    except (
        ValueError,
        TypeError
    ):
        expected = 1

    last_user_id = number_game.get(
        "last_user_id"
    )

    user_id = str(message.author.id)

    # --------------------------------------------------------
    # RICHTIG
    # --------------------------------------------------------

    if number == expected:

        if str(last_user_id) == str(
            message.author.id
        ):

            warning = await message.channel.send(
                (
                    f"⚠️ **Nicht möglich!**\n"
                    f"Die Zahl `{expected}` muss von "
                    f"einer anderen Person geschrieben werden.\n"
                    f"Die Zahl bleibt bei `{expected}`."
                )
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

        if number % 100 == 0:

            if number_game.get(
                "last_easter_egg",
                0
            ) != number:

                number_game["last_easter_egg"] = number
                save_data()

                easter_egg = await message.channel.send(
                    (
                        f"🎉 **{number} erreicht!**\n"
                        f"Starke Leistung — weiter geht's mit "
                        f"`{number + 1}`!"
                    )
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

    try:
        previous = int(
            wrong_attempts.get(
                user_id,
                0
            )
        )
    except (
        ValueError,
        TypeError
    ):
        previous = 0

    wrong_count = previous + 1

    wrong_attempts[user_id] = wrong_count

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

    if timeout_minutes > 0:

        try:
            until = (
                discord.utils.utcnow()
                + dt.timedelta(
                    minutes=timeout_minutes
                )
            )

            await message.author.timeout(
                until,
                reason="RLP Zahlenspiel – zu viele Fehlversuche"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    return True


# ============================================================
# PANEL EMBEDS
# ============================================================

def nametag_embed():

    embed = discord.Embed(
        title="🏷️ RLP Nametag-System",
        description=(
            "Verwalte hier deinen RLP-Nametag.\n\n"
            "🏷️ **Nametag setzen**\n"
            "🗑️ **Nametag entfernen**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=NAMETAG_PANEL_MARKER
    )

    return embed


def dev_task_embed():

    embed = discord.Embed(
        title="💻 Entwickler Aufgaben",
        description=(
            "Hier können Entwickler-Aufgaben erstellt "
            "und bearbeitet werden."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    return embed


def dev_shift_embed():

    embed = discord.Embed(
        title="🧑‍💻 Entwicklerdienst",
        description=(
            "Nutze die Buttons, um deinen "
            "Entwicklerdienst zu starten oder zu beenden.\n\n"
            "🟢 **Dienst starten**\n"
            "🔴 **Dienst beenden**"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=DEV_SHIFT_PANEL_MARKER
    )

    return embed


def community_embed():

    embed = discord.Embed(
        title="🌐 RLP Community",
        description=(
            "Willkommen im Community-System!\n\n"
            "💬 **Feedback**\n"
            "Chat auswählen → Nachricht eingeben → senden.\n\n"
            "💡 **Vorschlag**\n"
            "Chat auswählen → Vorschlag eingeben → senden."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=COMMUNITY_PANEL_MARKER
    )

    return embed


def owner_embed():

    embed = discord.Embed(
        title="👑 RLP Owner Panel",
        description=(
            "Bei jeder Funktion wird zuerst ein "
            "**Ziel-Chat** ausgewählt.\n\n"
            "📢 Ankündigung\n"
            "💬 Bot Say\n"
            "🎁 Giveaway\n"
            "👤 User Info\n"
            "🎭 Rollen Info\n"
            "🖥️ Server Info\n"
            "🔒 Lock\n"
            "🔓 Unlock\n"
            "📊 Status\n"
            "🧹 Clear"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=OWNER_PANEL_MARKER
    )

    return embed


def emoji_quiz_embed():

    embed = discord.Embed(
        title="🧩 RLP Emoji Quiz",
        description=(
            "Errate Begriffe anhand von Emojis.\n\n"
            "▶️ Neues Quiz\n"
            "💡 Tipp anfordern\n"
            "🔤 Anfangsbuchstaben\n"
            "⏭️ Aufgabe überspringen\n"
            "🏆 Bestenliste\n"
            "✍️ Antwort eingeben\n\n"
            "Tipp, Anfangsbuchstaben und Überspringen "
            "können jeweils 3-mal pro 2 Stunden "
            "verwendet werden."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=EMOJI_QUIZ_PANEL_MARKER
    )

    return embed


def number_game_embed():

    embed = discord.Embed(
        title="🔢 RLP Zahlenspiel",
        description=(
            "Zählt gemeinsam hoch.\n\n"
            "▶️ Start bei **1**\n"
            "➡️ Danach immer +1\n"
            "⚠️ Eine Person darf nicht zweimal "
            "hintereinander richtig zählen.\n"
            "❌ Eine falsche Zahl setzt das Spiel "
            "wieder auf **1**."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=NUMBER_GAME_PANEL_MARKER
    )

    return embed


# ============================================================
# PANELS
# ============================================================

async def ensure_fixed_panels():

    nametag_channel = await get_text_channel(
        NAMETAG_CHANNEL_ID
    )

    if nametag_channel:
        await ensure_panel(
            nametag_channel,
            nametag_embed(),
            NametagView(),
            NAMETAG_PANEL_MARKER
        )

    license_channel = await get_text_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if license_channel:
        await refresh_license_panel()

    task_channel = await get_text_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if task_channel:
        await ensure_panel(
            task_channel,
            dev_task_embed(),
            DeveloperTaskView(),
            DEV_TASK_PANEL_MARKER
        )

    shift_channel = await get_text_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if shift_channel:
        await ensure_panel(
            shift_channel,
            dev_shift_embed(),
            DeveloperShiftView(),
            DEV_SHIFT_PANEL_MARKER
        )

    number_channel = await get_text_channel(
        NUMBER_GAME_CHANNEL_ID
    )

    if number_channel:
        await ensure_panel(
            number_channel,
            number_game_embed(),
            None,
            NUMBER_GAME_PANEL_MARKER
        )


# ============================================================
# COMMANDS
# ============================================================

@bot.command(
    name="ownerpanel",
    aliases=["owner"]
)
@commands.guild_only()
async def ownerpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung für das Owner Panel."
        )
        return

    await ctx.send(
        embed=owner_embed(),
        view=OwnerPanelView()
    )


@bot.command(
    name="communitypanel"
)
@commands.guild_only()
async def communitypanel(ctx):

    await ctx.send(
        embed=community_embed(),
        view=CommunityPanelView()
    )


@bot.command(
    name="nametagpanel"
)
@commands.guild_only()
async def nametagpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.send(
        embed=nametag_embed(),
        view=NametagView()
    )


@bot.command(
    name="licensepanel",
    aliases=["kennzeichenpanel"]
)
@commands.guild_only()
async def licensepanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await refresh_license_panel()

    await ctx.send(
        "✅ Das Kennzeichen-Panel wurde aktualisiert."
    )


@bot.command(
    name="devtaskpanel",
    aliases=["developertaskpanel", "devtasks"]
)
@commands.guild_only()
async def devtaskpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.send(
        embed=dev_task_embed(),
        view=DeveloperTaskView()
    )


@bot.command(
    name="devshiftpanel"
)
@commands.guild_only()
async def devshiftpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.send(
        embed=dev_shift_embed(),
        view=DeveloperShiftView()
    )


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
@commands.guild_only()
async def emojiquizpanel(ctx):

    await ctx.send(
        embed=emoji_quiz_embed(),
        view=EmojiQuizView()
    )


@bot.command(
    name="numbergamepanel",
    aliases=["zahlenspielpanel"]
)
@commands.guild_only()
async def numbergamepanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Keine Berechtigung."
        )
        return

    await ctx.send(
        embed=number_game_embed()
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
        description="Alle verfügbaren Befehle:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🌐 Community",
        value=(
            "`?communitypanel`\n"
            "`?emojiquiz`"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            "`?ownerpanel`\n"
            "`?owner`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Systeme",
        value=(
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
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
# COMMAND ERROR
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
            "❌ Es fehlen benötigte Argumente."
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
        f"[COMMAND ERROR] {ctx.command}: {repr(error)}"
    )


# ============================================================
# MESSAGE EVENT
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

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

    print("=" * 50)
    print(f"Bot online: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Server: {len(bot.guilds)}")
    print("=" * 50)

    if not getattr(
        bot,
        "_persistent_views_added",
        False
    ):

        bot.add_view(
            NametagView()
        )

        bot.add_view(
            LicenseView()
        )

        bot.add_view(
            DeveloperTaskView()
        )

        bot.add_view(
            DeveloperTaskActionView()
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

        bot.add_view(
            SuggestionReviewView()
        )

        bot._persistent_views_added = True

    if not getattr(
        bot,
        "_panels_initialized",
        False
    ):

        bot._panels_initialized = True

        try:
            await ensure_fixed_panels()
        except Exception as error:
            print(
                f"[PANELS] Fehler: {repr(error)}"
            )

    if not change_status_loop.is_running():
        change_status_loop.start()


# ============================================================
# STATUS
# ============================================================

@tasks.loop(seconds=20)
async def change_status_loop():

    if not bot.is_ready():
        return

    try:
        status_text = random.choice(
            STATUS_TEXTS
        )

        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(
                name=status_text
            )
        )

    except Exception as error:
        print(
            f"[STATUS ERROR] {error}"
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
