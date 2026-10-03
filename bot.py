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

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

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

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True


# ============================================================
# BOT
# ============================================================

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
    "active_team_members": [],
    "developer_tasks": {},
    "developer_task_counter": 0,
    "developer_shifts": {}
}

data = {}

active_support_cases = {}
active_applications = {}

current_quiz = None
current_quiz_message = None
quiz_bag = []

startup_finished = False
quiz_lock = asyncio.Lock()


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def timestamp():
    return now().strftime("%d.%m.%Y %H:%M:%S UTC")


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


def load_data():
    global data

    data = json.loads(json.dumps(DEFAULT_DATA))

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)

        for key in DEFAULT_DATA:
            if key in saved:
                data[key] = saved[key]

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        save_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


def base_embed(title, description=None):
    embed = discord.Embed(
        title=title,
        description=description,
        timestamp=now()
    )
    return embed


def get_channel(channel_id):
    return bot.get_channel(channel_id)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def clean_bot_messages(channel):
    if channel is None:
        return

    try:
        async for message in channel.history(limit=None):
            if message.author.id == bot.user.id:
                await safe_delete(message)
    except Exception as error:
        print(f"[CLEAN] Fehler in {getattr(channel, 'name', channel)}: {error}")


async def clean_panel(channel):
    if channel is None:
        return

    try:
        async for message in channel.history(limit=None):
            if message.author.id == bot.user.id:
                await safe_delete(message)
    except Exception as error:
        print(f"[PANEL] Fehler: {error}")


# ============================================================
# NAMETAG
# ============================================================

def has_nametag_role(member):
    return any(role.id == NAMETAG_ROLE_ID for role in member.roles)


def clean_nametag(name):
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def apply_nametag(member, force=False):
    if member.bot:
        return

    if not has_nametag_role(member):
        return

    user_id = str(member.id)

    if user_id in data["nametag_opt_out"] and not force:
        return

    if force and user_id in data["nametag_opt_out"]:
        data["nametag_opt_out"].remove(user_id)
        save_data()

    clean_name = clean_nametag(member.display_name)

    new_name = f"{NAMETAG}{clean_name}"

    if len(new_name) > 32:
        new_name = new_name[:32]

    if member.display_name == new_name:
        return

    try:
        await member.edit(
            nick=new_name,
            reason="RLP Nametag"
        )
    except discord.Forbidden:
        print(f"[NAMETAG] Keine Berechtigung für {member}")
    except Exception as error:
        print(f"[NAMETAG] Fehler bei {member}: {error}")


async def remove_nametag(member):
    if member.bot:
        return

    user_id = str(member.id)

    if user_id not in data["nametag_opt_out"]:
        data["nametag_opt_out"].append(user_id)
        save_data()

    clean_name = clean_nametag(member.display_name)

    try:
        await member.edit(
            nick=clean_name[:32],
            reason="RLP Nametag entfernt"
        )
    except discord.Forbidden:
        print(f"[NAMETAG] Keine Berechtigung zum Entfernen bei {member}")
    except Exception as error:
        print(f"[NAMETAG] Fehler: {error}")


async def update_all_nametags(guild):
    role = guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[NAMETAG] Rolle nicht gefunden.")
        return

    for member in role.members:
        await apply_nametag(member)


class NametagPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

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
        await remove_nametag(interaction.user)

        await interaction.response.send_message(
            "✅ Dein RLP-Nametag wurde entfernt. "
            "Die Einstellung bleibt auch nach einem Neustart gespeichert.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Nametag wieder aktivieren",
        style=discord.ButtonStyle.success,
        custom_id="rlp_nametag_enable"
    )
    async def enable(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(user_id)
            save_data()

        await apply_nametag(interaction.user, force=True)

        await interaction.response.send_message(
            "✅ Dein RLP-Nametag wurde wieder aktiviert.",
            ephemeral=True
        )


async def send_nametag_panel():
    channel = get_channel(NICKNAME_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "🏷️ RLP Nametag",
        "Hier kannst du deinen RLP-Nametag verwalten."
    )

    embed.add_field(
        name="Automatisch",
        value="Mit der RLP-Rolle wird `RLP ` automatisch vor deinen Namen gesetzt.",
        inline=False
    )

    embed.add_field(
        name="Entfernen",
        value="Du kannst den Nametag unten entfernen.",
        inline=False
    )

    embed.add_field(
        name="Wieder aktivieren",
        value="Wenn du ihn wieder möchtest, kannst du ihn jederzeit aktivieren.",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=NametagPanelView()
    )


# ============================================================
# QUIZ
# ============================================================

QUIZ_CATEGORIES = {

    "Länder": [
        ("🇩🇪", "Deutschland"),
        ("🇫🇷", "Frankreich"),
        ("🇮🇹", "Italien"),
        ("🇪🇸", "Spanien"),
        ("🇵🇹", "Portugal"),
        ("🇬🇧", "Vereinigtes Königreich"),
        ("🇮🇪", "Irland"),
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
        ("🇮🇸", "Island"),
        ("🇬🇷", "Griechenland"),
        ("🇹🇷", "Türkei"),
        ("🇺🇦", "Ukraine"),
        ("🇺🇸", "USA"),
        ("🇨🇦", "Kanada"),
        ("🇲🇽", "Mexiko"),
        ("🇧🇷", "Brasilien"),
        ("🇦🇷", "Argentinien"),
        ("🇨🇱", "Chile"),
        ("🇨🇴", "Kolumbien"),
        ("🇵🇪", "Peru"),
        ("🇯🇵", "Japan"),
        ("🇨🇳", "China"),
        ("🇰🇷", "Südkorea"),
        ("🇮🇳", "Indien"),
        ("🇹🇭", "Thailand"),
        ("🇻🇳", "Vietnam"),
        ("🇦🇺", "Australien"),
        ("🇳🇿", "Neuseeland"),
        ("🇿🇦", "Südafrika"),
        ("🇪🇬", "Ägypten"),
        ("🇲🇦", "Marokko"),
        ("🇰🇪", "Kenia"),
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
        ("🩶", "Grau"),
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
        ("🐦", "Vogel"),
        ("🦄", "Einhorn"),
        ("🐝", "Biene"),
        ("🦋", "Schmetterling"),
        ("🐢", "Schildkröte"),
        ("🐍", "Schlange"),
        ("🦎", "Eidechse"),
        ("🐊", "Krokodil"),
        ("🐘", "Elefant"),
        ("🦒", "Giraffe"),
        ("🦓", "Zebra"),
        ("🦍", "Gorilla"),
        ("🐪", "Kamel"),
    ],

    "Essen": [
        ("🍕", "Pizza"),
        ("🍔", "Burger"),
        ("🍟", "Pommes"),
        ("🌭", "Hotdog"),
        ("🌮", "Taco"),
        ("🌯", "Burrito"),
        ("🍝", "Pasta"),
        ("🍜", "Ramen"),
        ("🍣", "Sushi"),
        ("🍛", "Curry"),
        ("🍚", "Reis"),
        ("🥨", "Brezel"),
        ("🥪", "Sandwich"),
        ("🌭", "Hotdog"),
        ("🍗", "Hähnchen"),
        ("🥩", "Steak"),
        ("🍳", "Ei"),
        ("🧀", "Käse"),
        ("🍞", "Brot"),
        ("🥞", "Pfannkuchen"),
        ("🧇", "Waffel"),
        ("🍎", "Apfel"),
        ("🍌", "Banane"),
        ("🍓", "Erdbeere"),
        ("🍉", "Wassermelone"),
    ],

    "Getränke": [
        ("💧", "Wasser"),
        ("🥛", "Milch"),
        ("☕", "Kaffee"),
        ("🍵", "Tee"),
        ("🧃", "Saft"),
        ("🥤", "Softdrink"),
        ("🧋", "Bubble Tea"),
        ("🍋", "Limonade"),
        ("🫖", "Tee"),
        ("🥥", "Kokoswasser"),
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
        ("🛵", "Roller"),
        ("🚲", "Fahrrad"),
        ("✈️", "Flugzeug"),
        ("🚁", "Helikopter"),
        ("🚀", "Rakete"),
        ("🚂", "Zug"),
        ("🚢", "Schiff"),
        ("⛵", "Segelboot"),
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
        ("⛷️", "Skifahren"),
        ("🏂", "Snowboarden"),
    ],

    "Natur": [
        ("🌳", "Baum"),
        ("🌲", "Tanne"),
        ("🌴", "Palme"),
        ("🌵", "Kaktus"),
        ("🌻", "Sonnenblume"),
        ("🌹", "Rose"),
        ("🌷", "Tulpe"),
        ("🌺", "Blume"),
        ("🍀", "Klee"),
        ("🌿", "Kräuter"),
        ("🌊", "Welle"),
        ("🏔️", "Berg"),
        ("🌋", "Vulkan"),
        ("🏜️", "Wüste"),
        ("🌈", "Regenbogen"),
        ("☀️", "Sonne"),
        ("🌙", "Mond"),
        ("⭐", "Stern"),
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
        ("🖨️", "Drucker"),
        ("📡", "Antenne"),
    ],

    "Berufe": [
        ("👨‍⚕️", "Arzt"),
        ("👩‍⚕️", "Ärztin"),
        ("👨‍🚒", "Feuerwehrmann"),
        ("👮", "Polizist"),
        ("👨‍🏫", "Lehrer"),
        ("👨‍🍳", "Koch"),
        ("👨‍🔧", "Mechaniker"),
        ("👨‍💻", "Programmierer"),
        ("👨‍🎨", "Künstler"),
        ("👨‍🚀", "Astronaut"),
        ("👨‍✈️", "Pilot"),
        ("👷", "Bauarbeiter"),
        ("🧑‍⚖️", "Richter"),
        ("🧑‍🔬", "Wissenschaftler"),
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
        ("🎵", "Musik hören"),
    ],

    "Gegenstände": [
        ("🔑", "Schlüssel"),
        ("🎒", "Rucksack"),
        ("✏️", "Bleistift"),
        ("🖊️", "Stift"),
        ("📕", "Buch"),
        ("📓", "Notizbuch"),
        ("🪑", "Stuhl"),
        ("🛏️", "Bett"),
        ("🚪", "Tür"),
        ("🪟", "Fenster"),
        ("🕯️", "Kerze"),
        ("🔦", "Taschenlampe"),
        ("🧸", "Teddybär"),
        ("🎁", "Geschenk"),
        ("⏰", "Wecker"),
    ],
}


def unique_items(items):
    result = []
    seen = set()

    for emoji, name in items:
        key = (emoji, name)

        if key not in seen:
            seen.add(key)
            result.append((emoji, name))

    return result


def build_quiz_pool():
    pool = []

    for category, items in QUIZ_CATEGORIES.items():
        items = unique_items(items)

        for emoji, answer in items:
            wrong_items = [
                item
                for item in items
                if item[1] != answer
            ]

            if len(wrong_items) < 3:
                continue

            wrong = random.sample(wrong_items, 3)

            options = [(emoji, answer)] + wrong
            random.shuffle(options)

            pool.append({
                "category": category,
                "emoji": emoji,
                "answer": answer,
                "options": options
            })

    random.shuffle(pool)

    return pool


QUIZZES = build_quiz_pool()


def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(range(len(QUIZZES)))
    random.shuffle(quiz_bag)


async def send_new_quiz(channel):
    global current_quiz
    global current_quiz_message

    if not quiz_bag:
        refill_quiz_bag()

    index = quiz_bag.pop()
    quiz = QUIZZES[index]

    embed = base_embed(
        "🎮 Emoji-Quiz",
        f"Welche Bedeutung hat dieses Emoji?\n\n"
        f"# {quiz['emoji']}"
    )

    embed.add_field(
        name="Kategorie",
        value=quiz["category"],
        inline=True
    )

    embed.set_footer(
        text="Die Frage kommt erst wieder, wenn der Fragenpool einmal durch ist."
    )

    view = QuizView(quiz)

    try:
        message = await channel.send(
            embed=embed,
            view=view
        )

        current_quiz = quiz
        current_quiz_message = message

    except Exception:
        quiz_bag.append(index)
        raise


class QuizAnswerButton(discord.ui.Button):

    def __init__(self, emoji, answer, index):
        super().__init__(
            label=answer,
            style=discord.ButtonStyle.secondary,
            custom_id=f"quiz_answer_{index}_{random.randint(100000, 999999)}"
        )

        self.answer = answer
        self.emoji_value = emoji

    async def callback(self, interaction):
        global current_quiz
        global current_quiz_message

        async with quiz_lock:

            if current_quiz is None:
                await interaction.response.send_message(
                    "❌ Diese Frage ist bereits beendet.",
                    ephemeral=True
                )
                return

            if current_quiz_message is None:
                await interaction.response.send_message(
                    "❌ Diese Frage ist nicht mehr aktiv.",
                    ephemeral=True
                )
                return

            if interaction.message.id != current_quiz_message.id:
                await interaction.response.send_message(
                    "❌ Diese Frage ist nicht mehr aktiv.",
                    ephemeral=True
                )
                return

            if self.answer != current_quiz["answer"]:
                await interaction.response.send_message(
                    "❌ Falsch! Versuch es weiter.",
                    ephemeral=True
                )
                return

            user_id = str(interaction.user.id)

            data["quiz_scores"][user_id] = (
                data["quiz_scores"].get(user_id, 0) + 1
            )

            save_data()

            correct_answer = current_quiz["answer"]

            current_quiz = None
            current_quiz_message = None

            embed = base_embed(
                "✅ Richtig!",
                f"{interaction.user.mention} hat die richtige Antwort gegeben."
            )

            embed.add_field(
                name="Antwort",
                value=correct_answer,
                inline=True
            )

            embed.add_field(
                name="Punkte",
                value=str(data["quiz_scores"][user_id]),
                inline=True
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

        await asyncio.sleep(3)

        await send_new_quiz(interaction.channel)


class QuizHintButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="💡 Hinweis",
            style=discord.ButtonStyle.secondary,
            custom_id="quiz_hint"
        )

    async def callback(self, interaction):
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Keine aktive Frage.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"💡 Kategorie: **{current_quiz['category']}**",
            ephemeral=True
        )


class QuizSkipButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="⏭️ Überspringen",
            style=discord.ButtonStyle.danger,
            custom_id="quiz_skip"
        )

    async def callback(self, interaction):
        global current_quiz
        global current_quiz_message

        async with quiz_lock:

            if current_quiz is None:
                await interaction.response.send_message(
                    "❌ Keine aktive Frage.",
                    ephemeral=True
                )
                return

            answer = current_quiz["answer"]

            current_quiz = None
            current_quiz_message = None

            embed = base_embed(
                "⏭️ Übersprungen",
                f"Die richtige Antwort war **{answer}**."
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

        await asyncio.sleep(2)

        await send_new_quiz(interaction.channel)


class QuizView(discord.ui.View):

    def __init__(self, quiz):
        super().__init__(timeout=None)

        for index, (emoji, answer) in enumerate(quiz["options"]):
            self.add_item(
                QuizAnswerButton(
                    emoji,
                    answer,
                    index
                )
            )

        self.add_item(QuizHintButton())
        self.add_item(QuizSkipButton())


@bot.command(name="quiz")
@commands.guild_only()
async def quiz_command(ctx):

    role = ctx.guild.get_role(QUIZ_COMMAND_ROLE_ID)

    if role is None or role not in ctx.author.roles:
        await ctx.reply(
            "❌ Du hast keine Berechtigung für `!quiz`.",
            delete_after=5
        )
        return

    if ctx.channel.id != QUIZ_CHANNEL_ID:
        await ctx.reply(
            f"❌ Nutze `!quiz` im vorgesehenen Quiz-Kanal <#{QUIZ_CHANNEL_ID}>.",
            delete_after=7
        )
        return

    if current_quiz is not None:
        await ctx.reply(
            "⚠️ Es läuft bereits eine Quizfrage.",
            delete_after=5
        )
        return

    await send_new_quiz(ctx.channel)


@bot.command(name="punkte")
@commands.guild_only()
async def points_command(ctx):

    score = data["quiz_scores"].get(str(ctx.author.id), 0)

    await ctx.reply(
        f"🏆 Du hast **{score} Punkte**.",
        delete_after=10
    )


@bot.command(name="top")
@commands.guild_only()
async def top_command(ctx):

    scores = data["quiz_scores"]

    if not scores:
        await ctx.reply(
            "🏆 Noch keine Punkte vorhanden."
        )
        return

    sorted_scores = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    lines = []

    for position, (user_id, score) in enumerate(sorted_scores, start=1):

        try:
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"User {user_id}"
        except Exception:
            name = f"User {user_id}"

        lines.append(
            f"**{position}.** {name} — **{score} Punkte**"
        )

    embed = base_embed(
        "🏆 Quiz Top 10",
        "\n".join(lines)
    )

    await ctx.reply(embed=embed)


# ============================================================
# SUPPORT
# ============================================================

def is_support_staff(member):
    if member.bot:
        return False

    if str(member.id) in data["active_team_members"]:
        return True

    if member.guild_permissions.manage_guild:
        return True

    if member.guild_permissions.administrator:
        return True

    return False


def create_case_id():
    return f"CASE-{random.randint(100000, 999999)}"


async def assign_supporters():
    voice_channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if voice_channel is None:
        return

    for user_id, case in list(active_support_cases.items()):

        user = voice_channel.guild.get_member(int(user_id))

        if user is None:
            continue

        if user not in voice_channel.members:
            continue

        if case["supporter_id"] is not None:
            continue

        for member in voice_channel.members:

            if member.id == user.id:
                continue

            if member.bot:
                continue

            if is_support_staff(member):
                case["supporter_id"] = member.id
                case["supporter_name"] = member.display_name
                break


async def create_support_case(member):

    user_id = str(member.id)

    if user_id in active_support_cases:
        await assign_supporters()
        return

    case_id = create_case_id()

    active_support_cases[user_id] = {
        "case_id": case_id,
        "user_id": member.id,
        "user_name": str(member),
        "supporter_id": None,
        "supporter_name": None,
        "created_at": now().isoformat()
    }

    await assign_supporters()

    log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

    if log_channel:

        embed = base_embed(
            "🎫 Support-Fall eröffnet",
            f"CaseID: `{case_id}`"
        )

        embed.add_field(
            name="User",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="Supporter",
            value="Noch keiner",
            inline=True
        )

        embed.add_field(
            name="Gestartet",
            value=timestamp(),
            inline=False
        )

        await log_channel.send(embed=embed)


async def close_support_case(member):

    user_id = str(member.id)
    case = active_support_cases.pop(user_id, None)

    if case is None:
        return

    created = datetime.fromisoformat(case["created_at"])
    duration = (now() - created).total_seconds()

    supporter = case["supporter_name"] or "Kein Supporter zugewiesen"

    log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

    if log_channel:

        embed = base_embed(
            "🔒 Support-Fall geschlossen",
            f"CaseID: `{case['case_id']}`"
        )

        embed.add_field(
            name="User",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="Supporter",
            value=supporter,
            inline=True
        )

        embed.add_field(
            name="Erstellt",
            value=created.strftime("%d.%m.%Y %H:%M:%S UTC"),
            inline=False
        )

        embed.add_field(
            name="Dauer",
            value=format_duration(duration),
            inline=True
        )

        embed.add_field(
            name="Status",
            value="Geschlossen",
            inline=True
        )

        await log_channel.send(embed=embed)


class SupportView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Support öffnen",
        style=discord.ButtonStyle.primary,
        custom_id="support_open_info"
    )
    async def open_support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            f"🎫 **Support:**\n"
            f"Betrete den Sprachkanal <#{SUPPORT_VOICE_CHANNEL_ID}>.\n\n"
            f"Sobald du den Kanal betrittst, wird automatisch ein Support-Fall erstellt.",
            ephemeral=True
        )


async def send_support_panel():

    channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "🎫 Support",
        "Du brauchst Hilfe? Betrete einfach den Support-Sprachkanal."
    )

    embed.add_field(
        name="Sprachkanal",
        value=f"<#{SUPPORT_VOICE_CHANNEL_ID}>",
        inline=False
    )

    embed.add_field(
        name="Automatisch",
        value=(
            "Beim Betreten wird ein Case erstellt. "
            "Wenn ein registrierter Team-Supporter im Kanal ist, "
            "wird dieser automatisch als Supporter erkannt."
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=SupportView()
    )


# ============================================================
# TEAM REGISTRIERUNG
# ============================================================

class TeamRegistrationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="➕ Als Team registrieren",
        style=discord.ButtonStyle.success,
        custom_id="team_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id in data["active_team_members"]:
            await interaction.response.send_message(
                "ℹ️ Du bist bereits als Teammitglied registriert.",
                ephemeral=True
            )
            return

        data["active_team_members"].append(user_id)
        save_data()

        await interaction.response.send_message(
            "✅ Du bist jetzt als Teammitglied registriert.",
            ephemeral=True
        )

    @discord.ui.button(
        label="➖ Registrierung entfernen",
        style=discord.ButtonStyle.danger,
        custom_id="team_unregister"
    )
    async def unregister(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["active_team_members"]:
            await interaction.response.send_message(
                "ℹ️ Du bist nicht registriert.",
                ephemeral=True
            )
            return

        data["active_team_members"].remove(user_id)
        save_data()

        await interaction.response.send_message(
            "✅ Deine Team-Registrierung wurde entfernt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="📋 Team anzeigen",
        style=discord.ButtonStyle.secondary,
        custom_id="team_list"
    )
    async def list_team(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        names = []

        for user_id in data["active_team_members"]:
            member = guild.get_member(int(user_id))

            if member:
                names.append(member.mention)

        if not names:
            text = "Aktuell ist niemand registriert."
        else:
            text = "\n".join(names)

        await interaction.response.send_message(
            f"👥 **Registriertes Team**\n\n{text}",
            ephemeral=True
        )


async def send_team_panel():

    channel = get_channel(TEAM_REGISTER_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "👥 Team-Registrierung",
        "Hier kannst du dich für Team-/Support-Funktionen registrieren."
    )

    embed.add_field(
        name="Registrieren",
        value="Klicke auf den Registrierungsbutton.",
        inline=False
    )

    embed.add_field(
        name="Support",
        value="Registrierte Teammitglieder können automatisch als Supporter erkannt werden.",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=TeamRegistrationView()
    )


# ============================================================
# DEVELOPER SCHICHTEN
# ============================================================

class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="▶️ Schicht starten",
        style=discord.ButtonStyle.success,
        custom_id="dev_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Schicht.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
            "started_at": now().isoformat(),
            "name": interaction.user.display_name
        }

        save_data()

        await interaction.response.send_message(
            "▶️ Deine Developer-Schicht wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="⏹️ Schicht beenden",
        style=discord.ButtonStyle.danger,
        custom_id="dev_shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)
        shift = data["developer_shifts"].pop(user_id, None)

        if shift is None:
            await interaction.response.send_message(
                "⚠️ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        started = datetime.fromisoformat(shift["started_at"])
        duration = (now() - started).total_seconds()

        save_data()

        await interaction.response.send_message(
            f"⏹️ Schicht beendet.\n"
            f"**Dauer:** {format_duration(duration)}",
            ephemeral=True
        )


async def send_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "⏱️ Developer-Schichten",
        "Starte oder beende hier deine Developer-Schicht."
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# ============================================================
# DEVELOPER AUFGABEN
# ============================================================

def next_task_id():
    data["developer_task_counter"] += 1
    save_data()

    return str(data["developer_task_counter"])


def task_text(task_id, task):

    status = task.get("status", "offen")
    creator = task.get("creator", "Unbekannt")
    claimed = task.get("claimed_by", "Niemand")

    return (
        f"### #{task_id} — {task['title']}\n"
        f"**Status:** {status}\n"
        f"**Erstellt von:** {creator}\n"
        f"**Bearbeiter:** {claimed}\n"
    )


async def send_developer_tasks():

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "🛠️ Developer-Aufgaben",
        "Verwalte hier Developer-Aufgaben."
    )

    if not data["developer_tasks"]:
        embed.description = "Aktuell gibt es keine Aufgaben."

    else:
        for task_id, task in list(data["developer_tasks"].items())[:20]:

            embed.add_field(
                name=f"#{task_id} — {task['title']}",
                value=(
                    f"Status: **{task.get('status', 'offen')}**\n"
                    f"Bearbeiter: **{task.get('claimed_by', 'Niemand')}**"
                ),
                inline=False
            )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


class DeveloperTaskModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(title="Neue Developer-Aufgabe")

        self.title_input = discord.ui.TextInput(
            label="Aufgabe",
            placeholder="Was soll erledigt werden?",
            max_length=100
        )

        self.description_input = discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Weitere Informationen...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Du brauchst die Berechtigung `Server verwalten`.",
                ephemeral=True
            )
            return

        task_id = next_task_id()

        data["developer_tasks"][task_id] = {
            "title": self.title_input.value,
            "description": self.description_input.value,
            "creator": interaction.user.display_name,
            "claimed_by": "Niemand",
            "status": "offen",
            "created_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe `#{task_id}` wurde erstellt.",
            ephemeral=True
        )

        await send_developer_tasks()


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="➕ Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        custom_id="dev_task_create"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Du brauchst `Server verwalten`.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )

    @discord.ui.button(
        label="📋 Aufgaben aktualisieren",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_task_refresh"
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            "🔄 Aufgaben werden aktualisiert.",
            ephemeral=True
        )

        await send_developer_tasks()


@bot.command(name="devtask")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def devtask(ctx, *, title=None):

    if not title:
        await ctx.reply(
            "Verwendung: `!devtask Aufgabe`"
        )
        return

    task_id = next_task_id()

    data["developer_tasks"][task_id] = {
        "title": title,
        "description": "",
        "creator": ctx.author.display_name,
        "claimed_by": "Niemand",
        "status": "offen",
        "created_at": now().isoformat()
    }

    save_data()

    await ctx.reply(
        f"✅ Aufgabe `#{task_id}` erstellt."
    )

    await send_developer_tasks()


@bot.command(name="devclaim")
@commands.guild_only()
async def devclaim(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devclaim <ID>`"
        )
        return

    task = data["developer_tasks"].get(str(task_id))

    if task is None:
        await ctx.reply("❌ Aufgabe nicht gefunden.")
        return

    task["claimed_by"] = ctx.author.display_name
    task["status"] = "in Bearbeitung"

    save_data()

    await ctx.reply(
        f"✅ Aufgabe `#{task_id}` wurde von dir übernommen."
    )

    await send_developer_tasks()


@bot.command(name="devdone")
@commands.guild_only()
async def devdone(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdone <ID>`"
        )
        return

    task = data["developer_tasks"].get(str(task_id))

    if task is None:
        await ctx.reply("❌ Aufgabe nicht gefunden.")
        return

    task["status"] = "erledigt"

    save_data()

    await ctx.reply(
        f"✅ Aufgabe `#{task_id}` ist erledigt."
    )

    await send_developer_tasks()


@bot.command(name="devdelete")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def devdelete(ctx, task_id=None):

    if not task_id:
        await ctx.reply(
            "Verwendung: `!devdelete <ID>`"
        )
        return

    if str(task_id) not in data["developer_tasks"]:
        await ctx.reply("❌ Aufgabe nicht gefunden.")
        return

    del data["developer_tasks"][str(task_id)]

    save_data()

    await ctx.reply(
        f"🗑️ Aufgabe `#{task_id}` wurde gelöscht."
    )

    await send_developer_tasks()


@bot.command(name="devtasks")
@commands.guild_only()
async def devtasks(ctx):

    await send_developer_tasks()

    await ctx.reply(
        "🔄 Developer-Aufgaben wurden aktualisiert.",
        delete_after=5
    )


# ============================================================
# DEVELOPER BEWERBUNG
# ============================================================

APPLICATION_QUESTIONS = [
    "Wie heißt du und wie alt bist du?",
    "Wie lange bist du bereits auf Discord aktiv?",
    "Warum möchtest du Developer werden?",
    "Welche Programmiersprachen beherrschst du?",
    "Welche Erfahrungen mit Discord-Bots hast du?",
    "Warum sollten wir dich ins Developer-Team aufnehmen?"
]


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Developer bewerben",
        style=discord.ButtonStyle.success,
        custom_id="developer_application_start"
    )
    async def start_application(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = interaction.user.id

        if user_id in active_applications:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine laufende Bewerbung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📩 Ich habe dir eine DM geschickt. "
            "Beantworte dort die Fragen.",
            ephemeral=True
        )

        asyncio.create_task(
            run_application(interaction.user)
        )


async def run_application(user):

    user_id = user.id

    try:
        dm = await user.create_dm()

        await dm.send(
            "📝 **Developer-Bewerbung**\n\n"
            "Beantworte bitte nacheinander die folgenden Fragen.\n"
            "Du kannst `abbrechen` schreiben, um die Bewerbung zu beenden."
        )

        answers = []

        active_applications[user_id] = True

        for number, question in enumerate(APPLICATION_QUESTIONS, start=1):

            await dm.send(
                f"**Frage {number}/{len(APPLICATION_QUESTIONS)}**\n{question}"
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
                    "⌛ Deine Bewerbung wurde wegen Inaktivität beendet."
                )
                return

            if message.content.lower().strip() == "abbrechen":
                await dm.send(
                    "❌ Bewerbung abgebrochen."
                )
                return

            answers.append(message.content)

        review_channel = get_channel(REVIEW_CHANNEL_ID)

        if review_channel is None:
            await dm.send(
                "❌ Der Bewerbungs-Kanal konnte nicht gefunden werden."
            )
            return

        embed = base_embed(
            "📝 Neue Developer-Bewerbung",
            f"Von: {user.mention}\n"
            f"User-ID: `{user.id}`"
        )

        for index, answer in enumerate(answers, start=1):
            question = APPLICATION_QUESTIONS[index - 1]

            embed.add_field(
                name=f"Frage {index}: {question}",
                value=answer[:1024],
                inline=False
            )

        await review_channel.send(
            embed=embed
        )

        await dm.send(
            "✅ Deine Bewerbung wurde erfolgreich an das Developer-Team weitergeleitet."
        )

    except discord.Forbidden:
        try:
            await user.send(
                "❌ Ich konnte keine DM-Bewerbung starten. "
                "Bitte erlaube Direktnachrichten auf dem Server."
            )
        except Exception:
            pass

    except Exception as error:
        print(f"[APPLICATION] Fehler bei {user}: {error}")

    finally:
        active_applications.pop(user_id, None)


async def send_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    await clean_panel(channel)

    embed = base_embed(
        "🧑‍💻 Developer-Bewerbung",
        "Du möchtest dem Developer-Team beitreten?"
    )

    embed.add_field(
        name="Ablauf",
        value=(
            "Klicke auf den Button. "
            "Danach bekommst du die Fragen per DM."
        ),
        inline=False
    )

    embed.add_field(
        name="Wichtig",
        value="Bitte beantworte alle Fragen ehrlich und vollständig.",
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print("===================================")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("===================================")

    if startup_finished:
        return

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print(f"[START] Guild {GUILD_ID} nicht gefunden.")
        return

    # Quiz-Fragen zurücksetzen
    refill_quiz_bag()

    quiz_channel = get_channel(QUIZ_CHANNEL_ID)

    if quiz_channel:
        await clean_bot_messages(quiz_channel)

        try:
            await send_new_quiz(quiz_channel)
        except Exception as error:
            print(f"[QUIZ] Startfehler: {error}")

    await send_nametag_panel()
    await send_support_panel()
    await send_team_panel()
    await send_shift_panel()
    await send_developer_tasks()
    await send_application_panel()

    await update_all_nametags(guild)

    startup_finished = True

    print("[START] Alle Panels wurden geladen.")
    print("[START] Bot vollständig gestartet.")


@bot.event
async def on_member_join(member):

    if member.bot:
        return

    if has_nametag_role(member):
        await apply_nametag(member, force=True)


@bot.event
async def on_member_update(before, after):

    if before.bot:
        return

    before_has_role = has_nametag_role(before)
    after_has_role = has_nametag_role(after)

    if not before_has_role and after_has_role:
        # Rolle neu erhalten -> Nametag wieder aktivieren
        await apply_nametag(after, force=True)

    elif before_has_role and not after_has_role:
        # Rolle entfernt -> alte Opt-Out-Einstellung löschen,
        # damit eine spätere erneute Vergabe wieder funktioniert.
        user_id = str(after.id)

        if user_id in data["nametag_opt_out"]:
            data["nametag_opt_out"].remove(user_id)
            save_data()


@bot.event
async def on_voice_state_update(member, before, after):

    if member.bot:
        return

    joined_support = (
        after.channel is not None
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
    )

    left_support = (
        before.channel is not None
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    )

    if joined_support:

        if not is_support_staff(member):
            await create_support_case(member)

        else:
            await assign_supporters()

    if left_support:

        if str(member.id) in active_support_cases:
            await close_support_case(member)

        else:
            await assign_supporters()


@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.reply(
            "❌ Du hast dafür keine Berechtigung.",
            delete_after=7
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(
            "❌ Es fehlt ein erforderliches Argument.",
            delete_after=7
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.reply(
            "❌ Dieser Befehl kann nur auf dem Server verwendet werden.",
            delete_after=7
        )
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.reply(
            "❌ Du kannst diesen Befehl nicht verwenden.",
            delete_after=7
        )
        return

    print(f"[COMMAND ERROR] {repr(error)}")

    try:
        await ctx.reply(
            "❌ Beim Ausführen des Befehls ist ein Fehler aufgetreten.",
            delete_after=7
        )
    except Exception:
        pass


# ============================================================
# PERSISTENTE VIEWS
# ============================================================

bot.add_view(NametagPanelView())
bot.add_view(SupportView())
bot.add_view(TeamRegistrationView())
bot.add_view(DeveloperShiftView())
bot.add_view(DeveloperTaskView())
bot.add_view(DeveloperApplicationView())


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gefunden. "
            "Lege den Token als Environment Variable DISCORD_TOKEN fest."
        )

    load_data()

    print("[START] Bot wird gestartet...")

    bot.run(DISCORD_TOKEN)
