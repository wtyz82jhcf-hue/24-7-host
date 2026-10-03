import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
import json
import os
import random
import asyncio
import time

# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NAMETAG_CHANNEL_ID = 1555684071911202836
NAMETAG_ROLE_ID = 1520102928398942348

LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715

DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"

# =========================================================
# BOT
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =========================================================
# DATEN
# =========================================================

default_data = {
    "quiz_points": {},
    "plates": {},
    "support_cases": 0,
    "tasks": [],
    "nametag_original_names": {},
    "quiz_round": 0
}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in default_data.items():
            if key not in data:
                data[key] = value

    except Exception:
        data = default_data.copy()
else:
    data = default_data.copy()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Fehler beim Speichern:", e)


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def is_owner(member: discord.Member):
    return any(role.id == OWNER_ROLE_ID for role in member.roles)


def has_shift_permission(member: discord.Member):
    return any(role.id == SHIFT_PERMISSION_ROLE_ID for role in member.roles)


async def safe_delete(message):
    try:
        await message.delete()
    except:
        pass


def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    guild = get_guild()

    if guild:
        return guild.get_channel(channel_id)

    return bot.get_channel(channel_id)


def format_uptime(seconds):
    seconds = int(seconds)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}T")

    if hours:
        parts.append(f"{hours}Std")

    if minutes:
        parts.append(f"{minutes}Min")

    parts.append(f"{seconds}Sek")

    return " ".join(parts)


# =========================================================
# STARTZEIT
# =========================================================

bot_start_time = time.time()


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇩🇪🍺🚗", "Deutschland"),
    ("🇫🇷🗼🥐", "Frankreich"),
    ("🇮🇹🍕🏛️", "Italien"),
    ("🇪🇸💃🥘", "Spanien"),
    ("🇬🇧🎡👑", "Vereinigtes Königreich"),
    ("🇺🇸🗽🍔", "USA"),
    ("🇯🇵🗾🍣", "Japan"),
    ("🇧🇷⚽🌴", "Brasilien"),
    ("🇨🇭🏔️🧀", "Schweiz"),
    ("🇦🇹🏔️🎿", "Österreich"),
    ("🇳🇱🌷🚲", "Niederlande"),
    ("🇬🇷🏛️🌊", "Griechenland"),
    ("🇹🇷🕌☕", "Türkei"),
    ("🇪🇬🐫🏜️", "Ägypten"),
    ("🇦🇺🦘🌏", "Australien"),
    ("🇨🇦🍁🏒", "Kanada"),
    ("🇲🇽🌮🌵", "Mexiko"),
    ("🇳🇴❄️🏔️", "Norwegen"),
    ("🇸🇪🧊🏠", "Schweden"),
    ("🇫🇮❄️🌲", "Finnland"),
    ("🇩🇰🧜‍♀️🏰", "Dänemark"),
    ("🇵🇹⚽🌊", "Portugal"),
    ("🇮🇳🐘🕌", "Indien"),
    ("🇰🇷🎮🍜", "Südkorea"),
    ("🇨🇳🐼🏯", "China"),
    ("🇷🇺❄️🐻", "Russland"),
    ("🇿🇦🦁🌍", "Südafrika"),
    ("🇦🇷⚽🥩", "Argentinien"),
    ("🇵🇱🥟🏰", "Polen"),
    ("🇧🇪🍫🧇", "Belgien"),

    ("🐶🏠", "Hund"),
    ("🐱🧶", "Katze"),
    ("🦁👑", "König der Löwen"),
    ("🐼🎋", "Panda"),
    ("🦈🌊", "Hai"),
    ("🐬🌊", "Delfin"),
    ("🦒🌳", "Giraffe"),
    ("🐘🌍", "Elefant"),
    ("🐧❄️", "Pinguin"),
    ("🦊🌲", "Fuchs"),

    ("🍕🇮🇹", "Pizza"),
    ("🍔🍟", "Burger"),
    ("🌭🇺🇸", "Hotdog"),
    ("🍣🇯🇵", "Sushi"),
    ("🌮🇲🇽", "Taco"),
    ("🍝🇮🇹", "Pasta"),
    ("🥨🇩🇪", "Brezel"),
    ("🍫😋", "Schokolade"),
    ("🍦❄️", "Eis"),
    ("🍎🍏", "Apfel"),

    ("⚽🥅", "Fußball"),
    ("🏀⛹️", "Basketball"),
    ("🎾🥎", "Tennis"),
    ("🏎️🏁", "Formel 1"),
    ("🏊🌊", "Schwimmen"),
    ("🚴🚲", "Radfahren"),
    ("🥊👊", "Boxen"),
    ("🏆🥇", "Wettkampf"),

    ("🌞🌙", "Tag und Nacht"),
    ("🌧️☔", "Regen"),
    ("❄️⛄", "Winter"),
    ("🌸🌱", "Frühling"),
    ("☀️🏖️", "Sommer"),
    ("🍂🍁", "Herbst"),

    ("🎬🍿", "Kino"),
    ("🎮🕹️", "Gaming"),
    ("🎵🎤", "Musik"),
    ("📚✏️", "Schule"),
    ("🚗🛣️", "Auto fahren"),
    ("✈️🌍", "Reisen"),
    ("🏠🛋️", "Zuhause"),
    ("📱💬", "Chatten"),
    ("💻⌨️", "Computer"),

    ("🦸‍♂️🛡️", "Superheld"),
    ("🧙‍♂️✨", "Zauberer"),
    ("🏴‍☠️🚢", "Pirat"),
    ("👮🚓", "Polizei"),
    ("👨‍🚒🔥", "Feuerwehr"),
    ("👨‍⚕️🏥", "Arzt"),

    ("🌍🌎🌏", "Erde"),
    ("🌙⭐", "Nacht"),
    ("☀️🔥", "Sonne"),
    ("🌊🏄", "Meer"),
    ("🏔️❄️", "Berg"),
    ("🌋🔥", "Vulkan"),
]


quiz_state = {
    "message_id": None,
    "answer": None,
    "round": 0
}

quiz_lock = asyncio.Lock()


async def get_quiz_channel():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(QUIZ_CHANNEL_ID)
        except:
            return None

    return channel


async def send_quiz_question():
    async with quiz_lock:

        channel = await get_quiz_channel()

        if channel is None:
            print("Quiz-Kanal nicht gefunden.")
            return

        emoji, answer = random.choice(QUIZ_QUESTIONS)

        quiz_state["round"] += 1
        quiz_state["answer"] = answer.lower().strip()

        embed = discord.Embed(
            title="🎮 Emoji-Quiz",
            description=(
                "Errate den Begriff anhand der Emojis!\n\n"
                f"# {emoji}\n\n"
                "💡 Schreibe deine Antwort einfach in den Chat."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Runde {quiz_state['round']} • 1 Punkt pro richtiger Antwort"
        )

        try:
            message = await channel.send(embed=embed)

            quiz_state["message_id"] = message.id

            data["quiz_round"] = quiz_state["round"]
            save_data()

        except Exception as e:
            print("Quiz konnte nicht gesendet werden:", e)


async def ensure_quiz():
    channel = await get_quiz_channel()

    if channel is None:
        return

    if quiz_state["message_id"] is None:
        await send_quiz_question()
        return

    try:
        message = await channel.fetch_message(
            quiz_state["message_id"]
        )

        if message is None:
            await send_quiz_question()

    except:
        quiz_state["message_id"] = None
        quiz_state["answer"] = None

        await send_quiz_question()


@tasks.loop(seconds=5)
async def quiz_cleanup():
    channel = await get_quiz_channel()

    if channel is None:
        return

    active_id = quiz_state["message_id"]

    try:
        messages = []

        async for message in channel.history(limit=100):
            if active_id and message.id == active_id:
                continue

            messages.append(message)

        for message in messages:
            try:
                await message.delete()
            except:
                pass

    except Exception as e:
        print("Quiz-Cleanup Fehler:", e)

    await ensure_quiz()


# =========================================================
# OWNER PANEL
# =========================================================

class OwnerAnnouncementModal(Modal, title="📢 Ankündigung erstellen"):

    titel = TextInput(
        label="Titel",
        placeholder="Titel der Ankündigung",
        required=True,
        max_length=100
    )

    text = TextInput(
        label="Text",
        placeholder="Was möchtest du ankündigen?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📢 {self.titel.value}",
            description=self.text.value,
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            "📢 Wohin soll die Ankündigung gesendet werden?",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed)


class OwnerSayModal(Modal, title="💬 Bot schreiben lassen"):

    text = TextInput(
        label="Nachricht",
        placeholder="Text des Bots",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✅ Nachricht gesendet.",
            ephemeral=True
        )

        await interaction.channel.send(self.text.value)


class OwnerEmbedModal(Modal, title="✨ Eigenes Embed"):

    titel = TextInput(
        label="Titel",
        placeholder="Embed-Titel",
        required=True,
        max_length=100
    )

    text = TextInput(
        label="Text",
        placeholder="Embed-Inhalt",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=3000
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.titel.value,
            description=self.text.value,
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=f"Erstellt von {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            "✅ Embed erstellt.",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed)


class OwnerPanelView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ankündigung",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="owner_announcement"
    )
    async def announcement(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Nur Inhaber können das Ownerpanel benutzen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            OwnerAnnouncementModal()
        )

    @discord.ui.button(
        label="Bot schreiben lassen",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_say"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Nur Inhaber können das Ownerpanel benutzen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            OwnerSayModal()
        )

    @discord.ui.button(
        label="Embed erstellen",
        emoji="✨",
        style=discord.ButtonStyle.primary,
        custom_id="owner_embed"
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Nur Inhaber können das Ownerpanel benutzen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            OwnerEmbedModal()
        )

    @discord.ui.button(
        label="Nachrichten löschen",
        emoji="🧹",
        style=discord.ButtonStyle.danger,
        custom_id="owner_clear"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        class ClearModal(Modal, title="🧹 Nachrichten löschen"):

            amount = TextInput(
                label="Anzahl",
                placeholder="z.B. 20",
                required=True,
                max_length=3
            )

            async def on_submit(self, modal_interaction):

                try:
                    amount = int(self.amount.value)

                    if amount < 1 or amount > 100:
                        raise ValueError

                except:
                    await modal_interaction.response.send_message(
                        "❌ Bitte eine Zahl zwischen 1 und 100 eingeben.",
                        ephemeral=True
                    )
                    return

                deleted = await modal_interaction.channel.purge(
                    limit=amount
                )

                await modal_interaction.response.send_message(
                    f"🧹 {len(deleted)} Nachrichten gelöscht.",
                    ephemeral=True
                )

        await interaction.response.send_modal(ClearModal())

    @discord.ui.button(
        label="Channel sperren",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="owner_lock"
    )
    async def lock(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = False

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔒 Dieser Channel wurde gesperrt."
        )

    @discord.ui.button(
        label="Channel entsperren",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="owner_unlock"
    )
    async def unlock(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = None

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔓 Dieser Channel wurde entsperrt."
        )

    @discord.ui.button(
        label="Quiz starten",
        emoji="🎮",
        style=discord.ButtonStyle.success,
        custom_id="owner_quiz_start"
    )
    async def quiz_start(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        quiz_state["message_id"] = None
        quiz_state["answer"] = None

        await send_quiz_question()

        if not quiz_cleanup.is_running():
            quiz_cleanup.start()

        await interaction.response.send_message(
            "🎮 Das Emoji-Quiz wurde gestartet!",
            ephemeral=True
        )

    @discord.ui.button(
        label="Quiz zurücksetzen",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_quiz_reset"
    )
    async def quiz_reset(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = await get_quiz_channel()

        if channel and quiz_state["message_id"]:

            try:
                message = await channel.fetch_message(
                    quiz_state["message_id"]
                )

                await message.delete()

            except:
                pass

        quiz_state["message_id"] = None
        quiz_state["answer"] = None

        await interaction.response.send_message(
            "🔄 Quiz wurde zurückgesetzt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Bot-Status",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="owner_status"
    )
    async def status(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        uptime = format_uptime(
            time.time() - bot_start_time
        )

        embed = discord.Embed(
            title="📊 Bot-Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🏓 Ping",
            value=f"{round(bot.latency * 1000)} ms",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime,
            inline=True
        )

        embed.add_field(
            name="🎮 Quiz-Runde",
            value=str(quiz_state["round"]),
            inline=True
        )

        embed.add_field(
            name="🚘 Kennzeichen",
            value=str(len(data["plates"])),
            inline=True
        )

        embed.add_field(
            name="📋 Aufgaben",
            value=str(len(data["tasks"])),
            inline=True
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(interaction.guild.member_count),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Serverinfo",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_serverinfo"
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🌐 Serverinformationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
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
            name="🆔 Server-ID",
            value=str(guild.id),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_owner_panel(channel):

    # Alte Ownerpanel-Nachrichten entfernen
    try:
        async for message in channel.history(limit=100):
            if message.author == bot.user and message.embeds:

                if message.embeds[0].title == "👑 Inhaber Control Center":
                    await message.delete()

    except:
        pass

    embed = discord.Embed(
        title="👑 Inhaber Control Center",
        description=(
            "Willkommen im Inhaberpanel.\n\n"
            "Hier kannst du wichtige Bot- und Serverfunktionen "
            "direkt über Buttons steuern.\n\n"
            "🔐 **Nur Inhaber haben Zugriff.**\n"
            f"Benötigte Rolle: <@&{OWNER_ROLE_ID}>"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="📢 Kommunikation",
        value=(
            "📢 Ankündigungen\n"
            "💬 Bot schreiben lassen\n"
            "✨ Eigene Embeds"
        ),
        inline=True
    )

    embed.add_field(
        name="🛠️ Verwaltung",
        value=(
            "🧹 Nachrichten löschen\n"
            "🔒 Channel sperren\n"
            "🔓 Channel entsperren"
        ),
        inline=True
    )

    embed.add_field(
        name="🎮 Systeme",
        value=(
            "🎮 Emoji-Quiz starten\n"
            "🔄 Quiz zurücksetzen\n"
            "📊 Bot-Status"
        ),
        inline=True
    )

    embed.add_field(
        name="🌐 Informationen",
        value="Serverinformationen anzeigen",
        inline=False
    )

    embed.set_footer(
        text="RLP Bot • Inhaber Control Center"
    )

    await channel.send(
        embed=embed,
        view=OwnerPanelView()
    )


# =========================================================
# NAMETAG
# =========================================================

async def normalize_nametag(member):

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    has_role = role in member.roles

    current_name = member.nick or member.name

    if has_role:

        if not current_name.startswith(NAMETAG):

            if str(member.id) not in data["nametag_original_names"]:
                data["nametag_original_names"][str(member.id)] = current_name

            new_name = NAMETAG + current_name

            try:
                await member.edit(nick=new_name)
            except:
                pass

            save_data()

    else:

        if current_name.startswith(NAMETAG):

            original = data["nametag_original_names"].get(
                str(member.id)
            )

            if original:
                try:
                    await member.edit(nick=original)
                except:
                    pass

                del data["nametag_original_names"][
                    str(member.id)
                ]

                save_data()

            else:

                try:
                    await member.edit(
                        nick=current_name[len(NAMETAG):]
                    )
                except:
                    pass


class NametagResetButton(Button):

    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id="nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ User nicht gefunden.",
                ephemeral=True
            )
            return

        current_name = member.nick or member.name

        if current_name.startswith(NAMETAG):

            new_name = current_name[len(NAMETAG):]

            try:
                await member.edit(nick=new_name)

                data["nametag_original_names"].pop(
                    str(member.id),
                    None
                )

                save_data()

                await interaction.response.send_message(
                    "✅ Dein Nametag wurde zurückgesetzt.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich darf deinen Nicknamen nicht ändern.",
                    ephemeral=True
                )

        else:

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen RLP-Nametag.",
                ephemeral=True
            )


class NametagView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagResetButton())


async def send_nametag_panel(channel):

    try:
        async for message in channel.history(limit=100):

            if message.author == bot.user and message.embeds:

                if message.embeds[0].title == "🏷️ Nametag":

                    await message.delete()

    except:
        pass

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Das Nametag-System wird automatisch anhand "
            "der vorhandenen Rolle verwaltet.\n\n"
            f"Besitzt du die Rolle <@&{NAMETAG_ROLE_ID}>, "
            f"wird dein Name mit **{NAMETAG}** versehen.\n\n"
            "Wenn du deinen Namen zurücksetzen möchtest, "
            "klicke auf den Button."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# KENNZEICHEN
# =========================================================

class PlateModal(Modal, title="🚘 Kennzeichen registrieren"):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01",
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):

        value = self.plate.value.strip().upper()

        parts = value.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus Präfix und Nummer bestehen.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Kennzeichen-Komponente muss eine Zahl sein.",
                ephemeral=True
            )
            return

        for user_id, existing in data["plates"].items():

            existing_number = existing.split()[-1]

            if existing_number == number:

                await interaction.response.send_message(
                    f"❌ Die Nummer **{number}** ist bereits vergeben.",
                    ephemeral=True
                )
                return

        user_id = str(interaction.user.id)

        if user_id in data["plates"]:

            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen.\n"
                f"Deins: `{data['plates'][user_id]}`",
                ephemeral=True
            )
            return

        data["plates"][user_id] = value

        save_data()

        await update_plate_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{value}** wurde registriert.",
            ephemeral=True
        )


class PlateDeleteButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen löschen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="plate_delete"
        )

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        if user_id not in data["plates"]:

            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        old = data["plates"].pop(user_id)

        save_data()

        await update_plate_panel()

        await interaction.response.send_message(
            f"🗑️ Dein Kennzeichen **{old}** wurde gelöscht.",
            ephemeral=True
        )


class PlateRegisterButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen registrieren",
            emoji="🚘",
            style=discord.ButtonStyle.success,
            custom_id="plate_register"
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            PlateModal()
        )


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(PlateRegisterButton())
        self.add_item(PlateDeleteButton())


async def update_plate_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    messages = []

    try:
        async for message in channel.history(limit=100):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].title == "🚘 Kennzeichen-System"
            ):
                messages.append(message)

    except:
        return

    for message in messages[1:]:
        try:
            await message.delete()
        except:
            pass

    lines = []

    for user_id, plate in data["plates"].items():

        member = channel.guild.get_member(
            int(user_id)
        )

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"`{plate}` — **{name}**"
        )

    if lines:
        description = "\n".join(lines)
    else:
        description = "Noch keine Kennzeichen vergeben."

    embed = discord.Embed(
        title="🚘 Kennzeichen-System",
        description=description,
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Die Nummer am Ende muss serverweit einzigartig sein."
    )

    if messages:
        try:
            await messages[0].edit(
                embed=embed,
                view=LicensePlateView()
            )
        except:
            pass
    else:
        await channel.send(
            embed=embed,
            view=LicensePlateView()
        )


# =========================================================
# ENTWICKLER-SCHICHT
# =========================================================

class ShiftStartButton(Button):

    def __init__(self):
        super().__init__(
            label="Dienst starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="shift_start"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.user

        if not has_shift_permission(member):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für den Entwicklerdienst.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Dienstrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role in member.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                role,
                reason="Entwicklerdienst gestartet"
            )

            await interaction.response.send_message(
                "🟢 Dein Entwicklerdienst wurde gestartet.",
                ephemeral=True
            )

            channel = bot.get_channel(
                DEVELOPER_SHIFT_CHANNEL_ID
            )

            if channel:

                embed = discord.Embed(
                    title="🟢 Entwicklerdienst gestartet",
                    description=(
                        f"{member.mention} ist jetzt im Dienst."
                    ),
                    color=discord.Color.green()
                )

                await channel.send(embed=embed)

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Dienstrolle nicht vergeben.",
                ephemeral=True
            )


class ShiftEndButton(Button):

    def __init__(self):
        super().__init__(
            label="Dienst beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="shift_end"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.user

        if not has_shift_permission(member):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role not in member.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        try:

            await member.remove_roles(
                role,
                reason="Entwicklerdienst beendet"
            )

            await interaction.response.send_message(
                "🔴 Dein Entwicklerdienst wurde beendet.",
                ephemeral=True
            )

            channel = bot.get_channel(
                DEVELOPER_SHIFT_CHANNEL_ID
            )

            if channel:

                embed = discord.Embed(
                    title="🔴 Entwicklerdienst beendet",
                    description=(
                        f"{member.mention} hat den Dienst beendet."
                    ),
                    color=discord.Color.red()
                )

                await channel.send(embed=embed)

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Dienstrolle nicht entfernen.",
                ephemeral=True
            )


class ShiftView(View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(ShiftStartButton())
        self.add_item(ShiftEndButton())


async def send_shift_panel(channel):

    try:
        async for message in channel.history(limit=100):

            if message.author == bot.user and message.embeds:

                if message.embeds[0].title == "🛠️ Entwicklerdienst":

                    await message.delete()

    except:
        pass

    embed = discord.Embed(
        title="🛠️ Entwicklerdienst",
        description=(
            "Hier kannst du deinen Entwicklerdienst verwalten.\n\n"
            "🟢 **Dienst starten**\n"
            "Du erhältst die aktive Dienstrolle.\n\n"
            "🔴 **Dienst beenden**\n"
            "Die aktive Dienstrolle wird entfernt."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=ShiftView()
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(Modal, title="📝 Bewerbung"):

    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        required=True,
        max_length=100
    )

    age = TextInput(
        label="Alter",
        placeholder="Dein Alter",
        required=True,
        max_length=3
    )

    reason = TextInput(
        label="Warum möchtest du dich bewerben?",
        placeholder="Schreibe etwas über dich...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = bot.get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📝 Neue Bewerbung",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name.value,
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=False
        )

        embed.add_field(
            name="💬 Motivation",
            value=self.reason.value,
            inline=False
        )

        embed.set_footer(
            text=f"Bewerbung von {interaction.user} • ID {interaction.user.id}"
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class ApplicationButton(Button):

    def __init__(self):
        super().__init__(
            label="Bewerbung starten",
            emoji="📝",
            style=discord.ButtonStyle.primary,
            custom_id="application_start"
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def send_application_panel(channel):

    try:
        async for message in channel.history(limit=100):

            if message.author == bot.user and message.embeds:

                if message.embeds[0].title == "📝 Bewerbungen":

                    await message.delete()

    except:
        pass

    embed = discord.Embed(
        title="📝 Bewerbungen",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke auf den Button und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# ENTWICKLER-AUFGABEN
# =========================================================

class DeveloperTaskModal(Modal, title="🛠️ Neue Entwickler-Aufgabe"):

    task = TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not has_shift_permission(interaction.user):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        task_data = {
            "author": interaction.user.id,
            "text": self.task.value,
            "done": False
        }

        data["tasks"].append(task_data)

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="🛠️ Neue Entwickler-Aufgabe",
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="👤 Erstellt von",
                value=interaction.user.mention,
                inline=False
            )

            await channel.send(
                embed=embed
            )

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
            custom_id="developer_task_create"
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


async def send_task_panel(channel):

    try:
        async for message in channel.history(limit=100):

            if message.author == bot.user and message.embeds:

                if message.embeds[0].title == "🛠️ Entwickler-Aufgaben":

                    await message.delete()

    except:
        pass

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Hier können berechtigte Entwickler neue "
            "Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# SUPPORT VOICE
# =========================================================

@bot.event
async def on_voice_state_update(member, before, after):

    support_channel = bot.get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    log_channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if support_channel is None or log_channel is None:
        return

    joined = (
        after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    left = (
        before.channel
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    if joined:

        data["support_cases"] += 1
        save_data()

        embed = discord.Embed(
            title="🎧 Support betreten",
            description=(
                f"{member.mention} hat den Support betreten."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="📁 Support-Fall",
            value=str(data["support_cases"])
        )

        await log_channel.send(
            embed=embed
        )

    elif left:

        embed = discord.Embed(
            title="🎧 Support verlassen",
            description=(
                f"{member.mention} hat den Support verlassen."
            ),
            color=discord.Color.red()
        )

        await log_channel.send(
            embed=embed
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
async def quizpunkte(ctx):

    points = data["quiz_points"].get(
        str(ctx.author.id),
        0
    )

    await ctx.send(
        f"🏆 {ctx.author.mention} hat **{points} Quizpunkte**."
    )


@bot.command()
async def kennzeichen(ctx):

    plate = data["plates"].get(
        str(ctx.author.id)
    )

    if plate:

        await ctx.send(
            f"🚘 Dein Kennzeichen ist `{plate}`."
        )

    else:

        await ctx.send(
            "❌ Du hast kein Kennzeichen."
        )


@bot.command()
async def owner(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Dieser Command ist nur für Inhaber."
        )
        return

    await ctx.send(
        "👑 Öffne das Inhaberpanel:",
        view=OwnerPanelView()
    )


@bot.command()
async def ownerpanel(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Dieser Command ist nur für Inhaber."
        )
        return

    await ctx.send(
        "👑 Inhaber Control Center:",
        view=OwnerPanelView()
    )


# =========================================================
# ON MESSAGE
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # -----------------------------------------------------
    # QUIZ
    # -----------------------------------------------------

    if message.channel.id == QUIZ_CHANNEL_ID:

        answer = quiz_state["answer"]

        if answer:

            user_answer = (
                message.content
                .strip()
                .lower()
            )

            await safe_delete(message)

            if user_answer == answer:

                user_id = str(message.author.id)

                current_points = data["quiz_points"].get(
                    user_id,
                    0
                )

                data["quiz_points"][user_id] = (
                    current_points + 1
                )

                save_data()

                channel = await get_quiz_channel()

                if channel:

                    result = await channel.send(
                        f"🎉 {message.author.mention} "
                        f"hat richtig geantwortet!\n"
                        f"🏆 **+1 Punkt**"
                    )

                    await asyncio.sleep(2)

                    await safe_delete(result)

                old_id = quiz_state["message_id"]

                if old_id:

                    try:
                        old_message = await channel.fetch_message(
                            old_id
                        )

                        await old_message.delete()

                    except:
                        pass

                quiz_state["message_id"] = None
                quiz_state["answer"] = None

                await send_quiz_question()

        return

    # -----------------------------------------------------
    # NORMALE COMMANDS
    # -----------------------------------------------------

    await bot.process_commands(message)


# =========================================================
# MEMBER UPDATE
# =========================================================

@bot.event
async def on_member_update(before, after):

    role = after.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    before_has = role in before.roles
    after_has = role in after.roles

    if before_has != after_has:

        await normalize_nametag(after)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("========================================")
    print(f"Bot online: {bot.user}")
    print(f"Server: {GUILD_ID}")
    print("========================================")

    # Persistent Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ShiftView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(OwnerPanelView())

    guild = bot.get_guild(GUILD_ID)

    if guild:

        # -------------------------------------------------
        # NAMETAG NUR PRÜFEN
        # -------------------------------------------------

        for member in guild.members:

            try:
                await normalize_nametag(member)
            except:
                pass

        # -------------------------------------------------
        # NAMETAG PANEL
        # -------------------------------------------------

        nametag_channel = guild.get_channel(
            NAMETAG_CHANNEL_ID
        )

        if nametag_channel:
            await send_nametag_panel(
                nametag_channel
            )

        # -------------------------------------------------
        # KENNZEICHEN PANEL
        # -------------------------------------------------

        await update_plate_panel()

        # -------------------------------------------------
        # SCHICHT PANEL
        # -------------------------------------------------

        shift_channel = guild.get_channel(
            DEVELOPER_SHIFT_CHANNEL_ID
        )

        if shift_channel:
            await send_shift_panel(
                shift_channel
            )

        # -------------------------------------------------
        # BEWERBUNGS PANEL
        # -------------------------------------------------

        application_channel = guild.get_channel(
            APPLICATION_CHANNEL_ID
        )

        if application_channel:
            await send_application_panel(
                application_channel
            )

        # -------------------------------------------------
        # AUFGABEN PANEL
        # -------------------------------------------------

        task_channel = guild.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if task_channel:
            await send_task_panel(
                task_channel
            )

    # -----------------------------------------------------
    # QUIZ STARTEN
    # -----------------------------------------------------

    if not quiz_cleanup.is_running():
        quiz_cleanup.start()

    await ensure_quiz()


# =========================================================
# COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Es fehlt ein Argument."
        )

        return

    print(
        f"Command-Fehler bei {ctx.command}: {error}"
    )


# =========================================================
# START
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
