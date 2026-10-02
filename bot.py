import os
import json
import random
import string
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


# ============================================================
#                         KONFIGURATION
# ============================================================

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

# -------------------------
# CHANNELS
# -------------------------

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NICKNAME_CHANNEL_ID = 1555684071911202836

SUPPORT_CHANNEL_ID = 1519788919254679602
TEAM_REGISTER_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1540797414863151155

# Kanal für Support-Abschlussberichte
SUPPORT_LOG_CHANNEL_ID = SUPPORT_CHANNEL_ID


# -------------------------
# ROLES
# -------------------------

NAMETAG_ROLE_ID = 1520102928398942348

# Nur diese Rolle darf !quiz verwenden
QUIZ_COMMAND_ROLE_ID = 1530188150456979526


# -------------------------
# NAMETAG
# -------------------------

NAMETAG = "RLP "


# -------------------------
# DATEI
# -------------------------

DATA_FILE = "bot_data.json"


# ============================================================
#                         INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states


# ============================================================
#                         BOT
# ============================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
#                         DATEN
# ============================================================

nametag_removed_users = set()

quiz_scores = {}

active_support_cases = {}
active_team_members = set()
active_developer_shifts = {}
developer_tasks = []

active_applications = {}

quiz_bag = []
current_quiz = None
current_quiz_message = None

quiz_lock = asyncio.Lock()

startup_finished = False


# ============================================================
#                         HILFSFUNKTIONEN
# ============================================================

def normalize(value):
    return " ".join(str(value).strip().lower().split())


def now():
    return datetime.now(timezone.utc)


def format_datetime(dt):
    return dt.strftime("%d.%m.%Y %H:%M")


def format_duration(seconds):
    seconds = max(0, int(seconds))

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours} Std. {minutes} Min."

    if minutes:
        return f"{minutes} Min. {seconds} Sek."

    return f"{seconds} Sek."


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


def generate_case_id():
    letters = string.ascii_uppercase
    code = "".join(random.choice(letters) for _ in range(10))
    return f"#S-{code}"


# ============================================================
#                         DATENBANK
# ============================================================

def load_data():
    global nametag_removed_users
    global quiz_scores
    global active_team_members
    global active_developer_shifts
    global developer_tasks

    if not os.path.exists(DATA_FILE):
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        nametag_removed_users = set(
            int(x) for x in data.get("nametag_removed_users", [])
        )

        quiz_scores = {
            str(k): int(v)
            for k, v in data.get("quiz_scores", {}).items()
        }

        active_team_members = set(
            int(x) for x in data.get("active_team_members", [])
        )

        active_developer_shifts = {
            str(k): v
            for k, v in data.get("active_developer_shifts", {}).items()
        }

        developer_tasks = data.get("developer_tasks", [])

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")


def save_data():
    try:
        data = {
            "nametag_removed_users": list(nametag_removed_users),
            "quiz_scores": quiz_scores,
            "active_team_members": list(active_team_members),
            "active_developer_shifts": active_developer_shifts,
            "developer_tasks": developer_tasks
        }

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


# ============================================================
#                         EMBED HELPERS
# ============================================================

def base_embed(title, description="", color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=now()
    )

    embed.set_footer(
        text="RLP System"
    )

    return embed


# ============================================================
#                         NAMETAG SYSTEM
# ============================================================

def get_clean_name(member):
    name = member.display_name

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_rlp_nickname(member, force=False):
    if not isinstance(member, discord.Member):
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    if role not in member.roles:
        return

    if member.id in nametag_removed_users and not force:
        return

    if force:
        nametag_removed_users.discard(member.id)
        save_data()

    clean_name = get_clean_name(member)

    nickname = f"{NAMETAG}{clean_name}"

    if len(nickname) > 32:
        nickname = nickname[:32]

    try:
        if member.nick != nickname:
            await member.edit(nick=nickname, reason="RLP Nametag System")

    except discord.Forbidden:
        print(f"[NAMETAG] Keine Rechte für {member}")


async def remove_rlp_nickname(member):
    clean_name = get_clean_name(member)

    nametag_removed_users.add(member.id)
    save_data()

    try:
        await member.edit(
            nick=clean_name,
            reason="RLP Nametag entfernt"
        )
    except discord.Forbidden:
        pass


async def update_all_rlp_nicknames():
    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        return

    role = guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[NAMETAG] Rolle nicht gefunden.")
        return

    for member in role.members:
        await set_rlp_nickname(member)


# ============================================================
#                         NAMETAG PANEL
# ============================================================

class NicknamePanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🏷️",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_remove_nametag"
    )
    async def remove_nametag(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            return

        await remove_rlp_nickname(interaction.user)

        embed = base_embed(
            "🏷️ Nametag entfernt",
            "Dein **RLP Nametag** wurde erfolgreich entfernt.",
            discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_nickname_panel():
    channel = bot.get_channel(NICKNAME_CHANNEL_ID)

    if channel is None:
        return

    async for message in channel.history(limit=None):
        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "🏷️ Nametag-System"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.2)

    embed = base_embed(
        "🏷️ Nametag-System",
        (
            "Hier kannst du dein **RLP Nametag** verwalten.\n\n"
            "Klicke auf **Nametag entfernen**, wenn du das Nametag "
            "nicht mehr verwenden möchtest.\n\n"
            "Wird die entsprechende Rolle später erneut vergeben, "
            "wird das Nametag automatisch wieder gesetzt."
        ),
        discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )


# ============================================================
#                         QUIZ DATEN
# ============================================================

COUNTRIES = [
    ("🇩🇪", "Deutschland"),
    ("🇫🇷", "Frankreich"),
    ("🇮🇹", "Italien"),
    ("🇪🇸", "Spanien"),
    ("🇬🇧", "Vereinigtes Königreich"),
    ("🇺🇸", "USA"),
    ("🇨🇦", "Kanada"),
    ("🇯🇵", "Japan"),
    ("🇰🇷", "Südkorea"),
    ("🇨🇳", "China"),
    ("🇧🇷", "Brasilien"),
    ("🇦🇷", "Argentinien"),
    ("🇲🇽", "Mexiko"),
    ("🇦🇺", "Australien"),
    ("🇳🇿", "Neuseeland"),
    ("🇳🇴", "Norwegen"),
    ("🇸🇪", "Schweden"),
    ("🇫🇮", "Finnland"),
    ("🇩🇰", "Dänemark"),
    ("🇳🇱", "Niederlande"),
    ("🇧🇪", "Belgien"),
    ("🇨🇭", "Schweiz"),
    ("🇦🇹", "Österreich"),
    ("🇵🇱", "Polen"),
    ("🇨🇿", "Tschechien"),
    ("🇬🇷", "Griechenland"),
    ("🇵🇹", "Portugal"),
    ("🇮🇪", "Irland"),
    ("🇮🇸", "Island"),
    ("🇹🇷", "Türkei"),
    ("🇷🇺", "Russland"),
    ("🇺🇦", "Ukraine"),
    ("🇮🇳", "Indien"),
    ("🇿🇦", "Südafrika"),
    ("🇪🇬", "Ägypten"),
    ("🇲🇦", "Marokko"),
    ("🇸🇦", "Saudi-Arabien"),
    ("🇦🇪", "Vereinigte Arabische Emirate"),
    ("🇮🇱", "Israel"),
    ("🇹🇭", "Thailand"),
    ("🇻🇳", "Vietnam"),
    ("🇸🇬", "Singapur"),
    ("🇮🇩", "Indonesien"),
    ("🇵🇭", "Philippinen"),
    ("🇲🇾", "Malaysia"),
    ("🇨🇱", "Chile"),
    ("🇨🇴", "Kolumbien"),
    ("🇵🇪", "Peru"),
    ("🇺🇾", "Uruguay"),
    ("🇨🇺", "Kuba"),
]

COLORS = [
    ("🔴", "Rot"),
    ("🔵", "Blau"),
    ("🟢", "Grün"),
    ("🟡", "Gelb"),
    ("🟠", "Orange"),
    ("🟣", "Lila"),
    ("⚫", "Schwarz"),
    ("⚪", "Weiß"),
    ("🟤", "Braun"),
    ("🩷", "Pink"),
    ("🩵", "Hellblau"),
    ("🩶", "Grau"),
]

ANIMALS = [
    ("🐶", "Hund"),
    ("🐱", "Katze"),
    ("🦁", "Löwe"),
    ("🐯", "Tiger"),
    ("🐻", "Bär"),
    ("🐼", "Panda"),
    ("🐨", "Koala"),
    ("🐵", "Affe"),
    ("🦊", "Fuchs"),
    ("🐺", "Wolf"),
    ("🐸", "Frosch"),
    ("🐰", "Hase"),
    ("🐭", "Maus"),
    ("🐹", "Hamster"),
    ("🐼", "Panda"),
    ("🐮", "Kuh"),
    ("🐷", "Schwein"),
    ("🐸", "Frosch"),
    ("🐵", "Affe"),
    ("🐔", "Huhn"),
    ("🐧", "Pinguin"),
    ("🐦", "Vogel"),
    ("🦆", "Ente"),
    ("🦅", "Adler"),
    ("🦉", "Eule"),
    ("🐺", "Wolf"),
    ("🐗", "Wildschwein"),
    ("🐴", "Pferd"),
    ("🦄", "Einhorn"),
    ("🐝", "Biene"),
    ("🦋", "Schmetterling"),
    ("🐢", "Schildkröte"),
    ("🐍", "Schlange"),
    ("🦎", "Eidechse"),
    ("🐊", "Krokodil"),
    ("🐬", "Delfin"),
    ("🐳", "Wal"),
    ("🦈", "Hai"),
    ("🐙", "Oktopus"),
    ("🦀", "Krabbe"),
]

FOOD = [
    ("🍕", "Pizza"),
    ("🍔", "Burger"),
    ("🍟", "Pommes"),
    ("🌭", "Hotdog"),
    ("🌮", "Taco"),
    ("🌯", "Burrito"),
    ("🍝", "Pasta"),
    ("🍜", "Nudeln"),
    ("🍣", "Sushi"),
    ("🍚", "Reis"),
    ("🍛", "Curry"),
    ("🍱", "Bento"),
    ("🥪", "Sandwich"),
    ("🥗", "Salat"),
    ("🍳", "Ei"),
    ("🥞", "Pfannkuchen"),
    ("🧇", "Waffel"),
    ("🍩", "Donut"),
    ("🍪", "Keks"),
    ("🎂", "Kuchen"),
    ("🍰", "Torte"),
    ("🍫", "Schokolade"),
    ("🍿", "Popcorn"),
    ("🍎", "Apfel"),
    ("🍌", "Banane"),
    ("🍓", "Erdbeere"),
    ("🍉", "Wassermelone"),
    ("🍇", "Trauben"),
    ("🍒", "Kirsche"),
    ("🥝", "Kiwi"),
    ("🥭", "Mango"),
    ("🍍", "Ananas"),
]

DRINKS = [
    ("🥤", "Softdrink"),
    ("🧃", "Saft"),
    ("☕", "Kaffee"),
    ("🍵", "Tee"),
    ("🥛", "Milch"),
    ("🧋", "Bubble Tea"),
    ("🍹", "Cocktail"),
    ("🧊", "Eisgetränk"),
]

VEHICLES = [
    ("🚗", "Auto"),
    ("🚕", "Taxi"),
    ("🚌", "Bus"),
    ("🚓", "Polizeiauto"),
    ("🚑", "Krankenwagen"),
    ("🚒", "Feuerwehr"),
    ("🚚", "LKW"),
    ("🏎️", "Rennwagen"),
    ("🚲", "Fahrrad"),
    ("🏍️", "Motorrad"),
    ("🚜", "Traktor"),
    ("✈️", "Flugzeug"),
    ("🚁", "Helikopter"),
    ("🚀", "Rakete"),
    ("🚢", "Schiff"),
    ("⛵", "Segelboot"),
    ("🚂", "Zug"),
    ("🚇", "U-Bahn"),
]

SPORTS = [
    ("⚽", "Fußball"),
    ("🏀", "Basketball"),
    ("🏈", "American Football"),
    ("⚾", "Baseball"),
    ("🎾", "Tennis"),
    ("🏐", "Volleyball"),
    ("🏉", "Rugby"),
    ("🥊", "Boxen"),
    ("🥋", "Kampfsport"),
    ("🏓", "Tischtennis"),
    ("🏸", "Badminton"),
    ("⛳", "Golf"),
    ("🏹", "Bogenschießen"),
    ("🎳", "Bowling"),
    ("🏊", "Schwimmen"),
    ("🚴", "Radsport"),
    ("⛷️", "Skifahren"),
    ("🏆", "Wettkampf"),
]

NATURE = [
    ("🌳", "Baum"),
    ("🌲", "Nadelbaum"),
    ("🌴", "Palme"),
    ("🌵", "Kaktus"),
    ("🌻", "Sonnenblume"),
    ("🌹", "Rose"),
    ("🌷", "Tulpe"),
    ("🌸", "Blüte"),
    ("🍀", "Klee"),
    ("🌱", "Pflanze"),
    ("🌿", "Kräuter"),
    ("🍁", "Ahornblatt"),
    ("🍂", "Herbstblatt"),
    ("🌊", "Welle"),
    ("🔥", "Feuer"),
    ("❄️", "Schnee"),
    ("☀️", "Sonne"),
    ("🌙", "Mond"),
    ("⭐", "Stern"),
    ("🌈", "Regenbogen"),
]

TECH = [
    ("💻", "Laptop"),
    ("🖥️", "Computer"),
    ("📱", "Smartphone"),
    ("⌨️", "Tastatur"),
    ("🖱️", "Maus"),
    ("🎧", "Kopfhörer"),
    ("📷", "Kamera"),
    ("📺", "Fernseher"),
    ("🎮", "Controller"),
    ("🕹️", "Joystick"),
    ("💾", "Diskette"),
    ("💿", "CD"),
    ("🔋", "Batterie"),
    ("🔌", "Stecker"),
    ("📡", "Antenne"),
    ("🤖", "Roboter"),
]

OBJECTS = [
    ("🔑", "Schlüssel"),
    ("🔒", "Schloss"),
    ("🎒", "Rucksack"),
    ("📚", "Bücher"),
    ("✏️", "Stift"),
    ("📏", "Lineal"),
    ("🕒", "Uhr"),
    ("💡", "Glühbirne"),
    ("🔨", "Hammer"),
    ("🪛", "Schraubenzieher"),
    ("🧹", "Besen"),
    ("🪑", "Stuhl"),
    ("🛏️", "Bett"),
    ("🚪", "Tür"),
    ("🪟", "Fenster"),
    ("🎁", "Geschenk"),
]


def create_quiz(category_name, category):
    correct = random.choice(category)

    wrong_pool = [
        item
        for item in category
        if item != correct
    ]

    wrong = random.sample(
        wrong_pool,
        min(3, len(wrong_pool))
    )

    options = [correct] + wrong
    random.shuffle(options)

    correct_position = options.index(correct)

    return {
        "category": category_name,
        "emoji": correct[0],
        "answer": correct[1],
        "options": options,
        "correct_position": correct_position
    }


def build_quizzes():
    quizzes = []

    categories = [
        ("Länder", COUNTRIES),
        ("Farben", COLORS),
        ("Tiere", ANIMALS),
        ("Essen", FOOD),
        ("Getränke", DRINKS),
        ("Fahrzeuge", VEHICLES),
        ("Sport", SPORTS),
        ("Natur", NATURE),
        ("Technik", TECH),
        ("Gegenstände", OBJECTS),
    ]

    for category_name, category in categories:
        amount = min(len(category), 30)

        for _ in range(amount):
            quizzes.append(
                create_quiz(
                    category_name,
                    category
                )
            )

    return quizzes


QUIZZES = build_quizzes()


# ============================================================
#                         QUIZ FUNKTIONEN
# ============================================================

def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(range(len(QUIZZES)))
    random.shuffle(quiz_bag)


async def send_new_quiz(channel):
    global current_quiz
    global current_quiz_message

    async with quiz_lock:

        if not quiz_bag:
            refill_quiz_bag()

        index = quiz_bag.pop()

        current_quiz = QUIZZES[index]

        quiz = current_quiz

        embed = base_embed(
            "🧩 Emoji-Quiz",
            (
                f"**Kategorie:** {quiz['category']}\n\n"
                f"Welcher Begriff gehört zu diesem Emoji?\n\n"
                f"# {quiz['emoji']}"
            ),
            discord.Color.blurple()
        )

        view = QuizView(quiz)

        message = await channel.send(
            embed=embed,
            view=view
        )

        current_quiz_message = message


class QuizAnswerButton(discord.ui.Button):

    def __init__(self, position, label):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=f"quiz_answer_{position}"
        )

        self.position = position

    async def callback(self, interaction):
        global current_quiz
        global current_quiz_message

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if (
            current_quiz_message is None
            or interaction.message.id != current_quiz_message.id
        ):
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        quiz = current_quiz

        if self.position == quiz["correct_position"]:

            user_id = str(interaction.user.id)

            quiz_scores[user_id] = (
                quiz_scores.get(user_id, 0) + 1
            )

            save_data()

            current_quiz = None

            embed = base_embed(
                "✅ Richtige Antwort!",
                (
                    f"{interaction.user.mention} hat die richtige Antwort "
                    f"gewählt.\n\n"
                    f"**Antwort:** {quiz['answer']}\n"
                    f"**+1 Punkt**"
                ),
                discord.Color.green()
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

            await asyncio.sleep(3)

            if interaction.channel:
                await send_new_quiz(interaction.channel)

        else:
            await interaction.response.send_message(
                "❌ Falsch! Versuch es weiter.",
                ephemeral=True
            )


class QuizHintButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Hinweis",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="quiz_hint_button"
        )

    async def callback(self, interaction):
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"💡 Der gesuchte Begriff gehört zur Kategorie "
            f"**{current_quiz['category']}**.",
            ephemeral=True
        )


class QuizSkipButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="quiz_skip_button"
        )

    async def callback(self, interaction):
        global current_quiz

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )
            return

        current_quiz = None

        await interaction.response.edit_message(
            embed=base_embed(
                "⏭️ Quiz übersprungen",
                "Das Quiz wurde übersprungen.",
                discord.Color.orange()
            ),
            view=None
        )

        await asyncio.sleep(2)

        if interaction.channel:
            await send_new_quiz(interaction.channel)


class QuizView(discord.ui.View):

    def __init__(self, quiz=None):
        super().__init__(timeout=None)

        if quiz is not None:
            for index, option in enumerate(quiz["options"]):
                self.add_item(
                    QuizAnswerButton(
                        index,
                        option[1]
                    )
                )

        self.add_item(QuizHintButton())
        self.add_item(QuizSkipButton())


# ============================================================
#                         QUIZ COMMANDS
# ============================================================

@bot.command(name="quiz")
async def quiz_command(ctx):

    if not isinstance(ctx.author, discord.Member):
        return

    if not any(
        role.id == QUIZ_COMMAND_ROLE_ID
        for role in ctx.author.roles
    ):
        embed = base_embed(
            "🔒 Keine Berechtigung",
            (
                "Du benötigst die entsprechende Team-Rolle, "
                "um `!quiz` zu verwenden."
            ),
            discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            delete_after=5
        )

        return

    await send_new_quiz(ctx.channel)


@bot.command(name="punkte")
async def punkte_command(ctx):

    score = quiz_scores.get(
        str(ctx.author.id),
        0
    )

    embed = base_embed(
        "📊 Deine Punkte",
        (
            f"👤 **Spieler:** {ctx.author.mention}\n"
            f"🏆 **Punkte:** `{score}`"
        ),
        discord.Color.blurple()
    )

    await ctx.send(embed=embed)


@bot.command(name="top")
async def top_command(ctx):

    if not quiz_scores:
        await ctx.send(
            embed=base_embed(
                "🏆 Rangliste",
                "Aktuell wurden noch keine Punkte gesammelt."
            )
        )
        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    lines = []

    for index, (user_id, score) in enumerate(
        sorted_scores[:10],
        start=1
    ):
        member = ctx.guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"**{index}.** {name} — `{score} Punkte`"
        )

    embed = base_embed(
        "🏆 Top 10",
        "\n".join(lines),
        discord.Color.gold()
    )

    await ctx.send(embed=embed)


# ============================================================
#                         SUPPORT SYSTEM
# ============================================================

async def create_support_case(member):
    if member.id in active_support_cases:
        return

    case_id = generate_case_id()

    active_support_cases[member.id] = {
        "case_id": case_id,
        "user_id": member.id,
        "started_at": now(),
        "supporter_id": None
    }


async def finish_support_case(member, supporter=None):

    case = active_support_cases.pop(member.id, None)

    if case is None:
        return

    ended_at = now()
    duration = (
        ended_at - case["started_at"]
    ).total_seconds()

    supporter_id = (
        supporter.id
        if supporter
        else case.get("supporter_id")
    )

    supporter_text = "Nicht festgestellt"

    if supporter_id:
        supporter_member = member.guild.get_member(
            supporter_id
        )

        if supporter_member:
            supporter_text = supporter_member.mention

    channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛡️ Support-Fall beendet",
        description=(
            f"{member.mention} wurde erfolgreich supportet."
        ),
        color=discord.Color.green(),
        timestamp=ended_at
    )

    embed.add_field(
        name="🆔 CaseID",
        value=f"`{case['case_id']}`",
        inline=True
    )

    embed.add_field(
        name="👤 Nutzer",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="🛠️ Supporter",
        value=supporter_text,
        inline=True
    )

    embed.add_field(
        name="🕐 Erstellt am",
        value=format_datetime(case["started_at"]),
        inline=True
    )

    embed.add_field(
        name="⏱️ Dauer",
        value=format_duration(duration),
        inline=True
    )

    embed.add_field(
        name="🔒 Status",
        value="Erfolgreich beendet",
        inline=True
    )

    embed.set_footer(
        text="RLP Support System"
    )

    await channel.send(embed=embed)


# ============================================================
#                         TEAMLER SYSTEM
# ============================================================

class TeamRegistrationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Eintragen",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="team_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        active_team_members.add(interaction.user.id)
        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🟢 Eingetragen",
                (
                    "Du wurdest erfolgreich als verfügbarer "
                    "Teamler eingetragen."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Austragen",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="team_unregister"
    )
    async def unregister(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        active_team_members.discard(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🔴 Ausgetragen",
                "Du wurdest erfolgreich ausgetragen.",
                discord.Color.red()
            ),
            ephemeral=True
        )


async def send_team_registration_panel():

    channel = bot.get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if channel is None:
        return

    async for message in channel.history(limit=None):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "👥 Teamler-System"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.2)

    embed = base_embed(
        "👥 Teamler-System",
        (
            "Über dieses System könnt ihr euren aktuellen "
            "Team-Status verwalten.\n\n"
            "🟢 **Eintragen**\n"
            "Du bist aktuell verfügbar.\n\n"
            "🔴 **Austragen**\n"
            "Du bist aktuell nicht verfügbar."
        ),
        discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=TeamRegistrationView()
    )


# ============================================================
#                         DEVELOPER SCHICHT
# ============================================================

class DeveloperShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="developer_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        if user_id in active_developer_shifts:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Developer-Schicht.",
                ephemeral=True
            )
            return

        active_developer_shifts[user_id] = {
            "started_at": now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🟢 Schicht gestartet",
                (
                    f"{interaction.user.mention}, deine "
                    "Developer-Schicht wurde gestartet."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="developer_shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = str(interaction.user.id)

        shift = active_developer_shifts.get(
            user_id
        )

        if not shift:
            await interaction.response.send_message(
                "⚠️ Du hast aktuell keine aktive Schicht.",
                ephemeral=True
            )
            return

        started_at = datetime.fromisoformat(
            shift["started_at"]
        )

        duration = (
            now() - started_at
        ).total_seconds()

        del active_developer_shifts[user_id]

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🔴 Schicht beendet",
                (
                    f"{interaction.user.mention}\n\n"
                    f"⏱️ **Schichtdauer:** "
                    f"{format_duration(duration)}"
                ),
                discord.Color.red()
            ),
            ephemeral=True
        )


async def send_developer_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    async for message in channel.history(limit=None):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "💻 Developer-Schichtsystem"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.2)

    embed = base_embed(
        "💻 Developer-Schichtsystem",
        (
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Startet deine Arbeitszeit.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Arbeitszeit und zeigt die Dauer an."
        ),
        discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# ============================================================
#                         DEVELOPER AUFGABEN
# ============================================================

class DeveloperTaskModal(discord.ui.Modal, title="Neue Developer-Aufgabe"):

    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        task_id = len(developer_tasks) + 1

        developer_tasks.append({
            "id": task_id,
            "text": str(self.task),
            "creator_id": interaction.user.id,
            "completed": False,
            "claimed_by": None
        })

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "📋 Aufgabe erstellt",
                (
                    f"**Aufgabe #{task_id}** wurde erfolgreich "
                    "erstellt."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

        await send_developer_tasks()


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.success,
        custom_id="developer_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


async def send_developer_tasks():

    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    async for message in channel.history(limit=None):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "💻 Developer-Aufgaben"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.15)

    embed = base_embed(
        "💻 Developer-Aufgaben",
        "Hier findet ihr die aktuellen Developer-Aufgaben.",
        discord.Color.blurple()
    )

    if not developer_tasks:
        embed.add_field(
            name="📋 Keine Aufgaben",
            value="Aktuell sind keine Aufgaben vorhanden.",
            inline=False
        )

    else:

        for task in developer_tasks[-15:]:

            status = (
                "✅ Erledigt"
                if task["completed"]
                else "🟡 Offen"
            )

            claimed = (
                f"<@{task['claimed_by']}>"
                if task.get("claimed_by")
                else "Niemand"
            )

            embed.add_field(
                name=f"#{task['id']} • {status}",
                value=(
                    f"{task['text']}\n"
                    f"👤 Bearbeiter: {claimed}"
                ),
                inline=False
            )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


@bot.command(name="devtask")
@commands.has_permissions(administrator=True)
async def devtask_command(ctx, *, task: str):

    task_id = len(developer_tasks) + 1

    developer_tasks.append({
        "id": task_id,
        "text": task,
        "creator_id": ctx.author.id,
        "completed": False,
        "claimed_by": None
    })

    save_data()

    await send_developer_tasks()

    await ctx.message.delete()


@bot.command(name="devdone")
@commands.has_permissions(administrator=True)
async def devdone_command(ctx, task_id: int):

    for task in developer_tasks:

        if task["id"] == task_id:

            task["completed"] = True

            save_data()

            await send_developer_tasks()

            await ctx.send(
                f"✅ Developer-Aufgabe **#{task_id}** wurde abgeschlossen.",
                delete_after=5
            )

            return

    await ctx.send(
        "❌ Diese Aufgabe wurde nicht gefunden.",
        delete_after=5
    )


# ============================================================
#                         DEVELOPER BEWERBUNG
# ============================================================

DEVELOPER_QUESTIONS = [
    "Wie lange bist du bereits auf Discord aktiv?",
    "Welche Erfahrungen hast du mit Discord Bots?",
    "Welche Programmiersprachen beherrschst du?",
    "Wie viel Zeit kannst du pro Woche investieren?",
    "Warum möchtest du Developer werden?",
    "Welche Projekte hast du bereits umgesetzt?"
]


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id in active_applications:
            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Bewerbung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📨 Ich habe dir eine DM für die Bewerbung geschickt.",
            ephemeral=True
        )

        try:
            await run_developer_application(
                interaction.user
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ Ich konnte dir keine DM schicken. "
                "Bitte aktiviere deine Direktnachrichten.",
                ephemeral=True
            )


async def run_developer_application(user):

    active_applications[user.id] = True

    answers = []

    try:

        await user.send(
            embed=base_embed(
                "💻 Developer-Bewerbung",
                (
                    "Willkommen bei der Developer-Bewerbung.\n\n"
                    "Beantworte bitte die folgenden Fragen "
                    "nacheinander."
                )
            )
        )

        for index, question in enumerate(
            DEVELOPER_QUESTIONS,
            start=1
        ):

            await user.send(
                embed=base_embed(
                    f"Frage {index}/{len(DEVELOPER_QUESTIONS)}",
                    question
                )
            )

            def check(message):
                return (
                    message.author.id == user.id
                    and isinstance(message.channel, discord.DMChannel)
                )

            try:

                message = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=check
                )

            except asyncio.TimeoutError:

                await user.send(
                    embed=base_embed(
                        "⏰ Bewerbung abgebrochen",
                        "Die Bewerbung wurde wegen Zeitüberschreitung beendet.",
                        discord.Color.red()
                    )
                )

                return

            answers.append(
                (question, message.content)
            )

        await send_application_review(
            user,
            answers
        )

        await user.send(
            embed=base_embed(
                "✅ Bewerbung eingereicht",
                (
                    "Deine Developer-Bewerbung wurde erfolgreich "
                    "an das zuständige Team weitergeleitet."
                ),
                discord.Color.green()
            )
        )

    finally:

        active_applications.pop(
            user.id,
            None
        )


async def send_application_review(user, answers):

    channel = bot.get_channel(
        REVIEW_CHANNEL_ID
    )

    if channel is None:
        return

    embed = base_embed(
        "💻 Neue Developer-Bewerbung",
        (
            f"**Bewerber:** {user.mention}\n"
            f"**User-ID:** `{user.id}`"
        ),
        discord.Color.blurple()
    )

    for index, (question, answer) in enumerate(
        answers,
        start=1
    ):

        embed.add_field(
            name=f"{index}. {question}",
            value=answer[:1024],
            inline=False
        )

    await channel.send(
        embed=embed
    )


async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    async for message in channel.history(limit=None):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "💻 Developer-Bewerbung"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.2)

    embed = base_embed(
        "💻 Developer-Bewerbung",
        (
            "Du möchtest unser Developer-Team unterstützen?\n\n"
            "Klicke auf **Developer bewerben** und fülle "
            "die Bewerbung per DM aus.\n\n"
            "Bitte beantworte alle Fragen ehrlich und ausführlich."
        ),
        discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
#                         SUPPORT PANEL
# ============================================================

class SupportView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Support-Informationen",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="support_info"
    )
    async def support_info(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = base_embed(
            "🎫 Support-System",
            (
                "Du befindest dich im Support-Bereich.\n\n"
                "Sobald ein Support-Fall gestartet wird, "
                "wird automatisch eine **CaseID** erstellt "
                "und die Dauer erfasst.\n\n"
                "Beim Verlassen des Support-Calls wird der "
                "Support-Fall automatisch abgeschlossen."
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_support_panel():

    channel = bot.get_channel(
        SUPPORT_CHANNEL_ID
    )

    if channel is None:
        return

    # Nur Textnachrichten mit unserem Panel entfernen.
    # Falls der Kanal ein Voice-Channel ist, endet die Funktion hier.
    if not hasattr(channel, "history"):
        return

    async for message in channel.history(limit=None):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == "🎫 Support-System"
        ):
            await safe_delete(message)
            await asyncio.sleep(0.2)

    embed = base_embed(
        "🎫 Support-System",
        (
            "Willkommen im offiziellen Support-Bereich.\n\n"
            "Betritt den Support-Call, um Unterstützung "
            "von unserem Team zu erhalten.\n\n"
            "Beim Start wird automatisch eine **CaseID** "
            "erstellt.\n"
            "Beim Verlassen wird der Fall automatisch "
            "mit Nutzer, Supporter und Dauer dokumentiert."
        ),
        discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=SupportView()
    )


# ============================================================
#                         EVENTS
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print(
        f"✅ Bot online als {bot.user} "
        f"({bot.user.id})"
    )

    if startup_finished:
        return

    load_data()

    refill_quiz_bag()

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("❌ Guild nicht gefunden.")
        return

    try:

        await update_all_rlp_nicknames()

        # Quiz-Channel bereinigen
        quiz_channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if quiz_channel:
            async for message in quiz_channel.history(
                limit=None
            ):
                if message.author == bot.user:
                    await safe_delete(message)
                    await asyncio.sleep(0.1)

            await send_new_quiz(
                quiz_channel
            )

        await send_nickname_panel()
        await send_application_panel()
        await send_team_registration_panel()
        await send_developer_shift_panel()
        await send_developer_tasks()

        # Support-Panel nur senden, wenn es ein Textkanal ist.
        support_channel = bot.get_channel(
            SUPPORT_CHANNEL_ID
        )

        if isinstance(
            support_channel,
            discord.TextChannel
        ):
            await send_support_panel()

        startup_finished = True

        print(
            f"✅ System vollständig geladen."
        )

        print(
            f"🧩 Quiz-Fragen: {len(QUIZZES)}"
        )

    except Exception as error:

        print(
            f"❌ Fehler beim Startup: {error}"
        )


@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    await set_rlp_nickname(
        member,
        force=True
    )


@bot.event
async def on_member_update(before, after):

    if before.guild.id != GUILD_ID:
        return

    role_before = any(
        role.id == NAMETAG_ROLE_ID
        for role in before.roles
    )

    role_after = any(
        role.id == NAMETAG_ROLE_ID
        for role in after.roles
    )

    if not role_before and role_after:

        await set_rlp_nickname(
            after,
            force=True
        )


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if member.guild.id != GUILD_ID:
        return

    # Support-Call betreten
    if (
        after.channel
        and after.channel.id == SUPPORT_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_CHANNEL_ID
        )
    ):

        await create_support_case(member)

    # Support-Call verlassen
    if (
        before.channel
        and before.channel.id == SUPPORT_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_CHANNEL_ID
        )
    ):

        await finish_support_case(member)


# ============================================================
#                         COMMAND ERROR
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
        commands.MissingPermissions
    ):

        await ctx.send(
            embed=base_embed(
                "🔒 Keine Berechtigung",
                "Du hast keine Berechtigung für diesen Command.",
                discord.Color.red()
            ),
            delete_after=5
        )

        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            embed=base_embed(
                "❌ Ungültige Eingabe",
                "Bitte überprüfe deine Eingabe.",
                discord.Color.red()
            ),
            delete_after=5
        )

        return

    print(
        f"[COMMAND ERROR] {error}"
    )


# ============================================================
#                         MESSAGE EVENTS
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    await bot.process_commands(message)


# ============================================================
#                         PERSISTENTE VIEWS
# ============================================================

class RLPBot(commands.Bot):

    async def setup_hook(self):

        load_data()

        self.add_view(
            NicknamePanelView()
        )

        self.add_view(
            DeveloperApplicationView()
        )

        self.add_view(
            TeamRegistrationView()
        )

        self.add_view(
            DeveloperShiftView()
        )

        self.add_view(
            DeveloperTaskView()
        )

        self.add_view(
            SupportView()
        )

        self.add_view(
            QuizView()
        )


# ============================================================
#                         BOT NEU INITIALISIEREN
# ============================================================

bot = RLPBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
#                         TOKEN
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(DISCORD_TOKEN)
