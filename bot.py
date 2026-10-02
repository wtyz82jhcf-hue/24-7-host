import os
import json
import random
import asyncio
import re
from datetime import datetime

import discord
from discord.ext import commands


# ============================================================
# KONFIGURATION
# ============================================================

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NICKNAME_CHANNEL_ID = 1555684071911202836

GUILD_ID = 1519481018221072454

NAMETAG_ROLE_ID = 1520102928398942348
QUIZ_COMMAND_ROLE_ID = 1530188150456979526

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"

TOKEN = os.environ.get("DISCORD_TOKEN")


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ============================================================
# DATEN
# ============================================================

nametag_removed_users = set()
quiz_scores = {}

current_quiz = None
current_quiz_message = None

quiz_bag = []
quiz_lock = asyncio.Lock()

startup_finished = False


# ============================================================
# BOT
# ============================================================

class RLPBot(commands.Bot):

    async def setup_hook(self):
        load_data()

        self.add_view(NicknamePanelView())
        self.add_view(DeveloperApplicationView())
        self.add_view(QuizView())


bot = RLPBot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DATEN LADEN / SPEICHERN
# ============================================================

def load_data():
    global nametag_removed_users
    global quiz_scores

    try:
        if not os.path.exists(DATA_FILE):
            return

        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        nametag_removed_users = set(
            int(user_id)
            for user_id in data.get("nametag_removed_users", [])
        )

        quiz_scores = {
            str(user_id): int(score)
            for user_id, score in data.get("quiz_scores", {}).items()
        }

        print("💾 Daten erfolgreich geladen.")

    except Exception as error:
        print(f"❌ Fehler beim Laden der Daten: {error}")


def save_data():
    try:
        data = {
            "nametag_removed_users": list(nametag_removed_users),
            "quiz_scores": quiz_scores
        }

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    except Exception as error:
        print(f"❌ Fehler beim Speichern der Daten: {error}")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


async def safe_delete(message):
    try:
        await message.delete()
        return True

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return False


async def cleanup_messages(channel, title):
    if channel is None or bot.user is None:
        return

    deleted = 0

    try:
        async for message in channel.history(
            limit=None,
            oldest_first=False
        ):
            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]

            if embed.title != title:
                continue

            if await safe_delete(message):
                deleted += 1

            await asyncio.sleep(0.15)

        print(
            f"🧹 {deleted} alte Nachricht(en) mit Titel "
            f"'{title}' gelöscht."
        )

    except discord.Forbidden:
        print(f"❌ Keine Berechtigung zum Löschen in #{channel.name}.")

    except discord.HTTPException as error:
        print(f"❌ Discord-Fehler beim Aufräumen: {error}")

    except Exception as error:
        print(f"❌ Fehler beim Aufräumen: {error}")


# ============================================================
# EMOJI-QUIZ – DATEN
# ============================================================

COUNTRIES = [
    ("🇩🇪", "Deutschland"),
    ("🇫🇷", "Frankreich"),
    ("🇮🇹", "Italien"),
    ("🇪🇸", "Spanien"),
    ("🇵🇹", "Portugal"),
    ("🇳🇱", "Niederlande"),
    ("🇧🇪", "Belgien"),
    ("🇦🇹", "Österreich"),
    ("🇨🇭", "Schweiz"),
    ("🇬🇧", "Vereinigtes Königreich"),
    ("🇮🇪", "Irland"),
    ("🇺🇸", "USA"),
    ("🇨🇦", "Kanada"),
    ("🇧🇷", "Brasilien"),
    ("🇦🇷", "Argentinien"),
    ("🇲🇽", "Mexiko"),
    ("🇯🇵", "Japan"),
    ("🇨🇳", "China"),
    ("🇰🇷", "Südkorea"),
    ("🇮🇳", "Indien"),
    ("🇦🇺", "Australien"),
    ("🇳🇿", "Neuseeland"),
    ("🇿🇦", "Südafrika"),
    ("🇪🇬", "Ägypten"),
    ("🇹🇷", "Türkei"),
    ("🇬🇷", "Griechenland"),
    ("🇳🇴", "Norwegen"),
    ("🇸🇪", "Schweden"),
    ("🇩🇰", "Dänemark"),
    ("🇫🇮", "Finnland"),
    ("🇮🇸", "Island"),
    ("🇵🇱", "Polen"),
    ("🇨🇿", "Tschechien"),
    ("🇭🇺", "Ungarn"),
    ("🇷🇴", "Rumänien"),
    ("🇧🇬", "Bulgarien"),
    ("🇭🇷", "Kroatien"),
    ("🇷🇸", "Serbien"),
    ("🇺🇦", "Ukraine"),
    ("🇬🇪", "Georgien"),
    ("🇮🇱", "Israel"),
    ("🇸🇦", "Saudi-Arabien"),
    ("🇦🇪", "Vereinigte Arabische Emirate"),
    ("🇹🇭", "Thailand"),
    ("🇻🇳", "Vietnam"),
    ("🇸🇬", "Singapur"),
    ("🇮🇩", "Indonesien"),
    ("🇵🇭", "Philippinen"),
    ("🇲🇾", "Malaysia"),
    ("🇲🇦", "Marokko"),
    ("🇰🇪", "Kenia"),
    ("🇳🇬", "Nigeria"),
    ("🇨🇱", "Chile"),
    ("🇨🇴", "Kolumbien"),
    ("🇵🇪", "Peru"),
    ("🇺🇾", "Uruguay"),
    ("🇨🇺", "Kuba"),
    ("🇮🇸", "Island"),
]


COLORS = [
    ("🔴", "Rot"),
    ("🔵", "Blau"),
    ("🟢", "Grün"),
    ("🟡", "Gelb"),
    ("🟠", "Orange"),
    ("🟣", "Lila"),
    ("🩷", "Pink"),
    ("🟤", "Braun"),
    ("⚫", "Schwarz"),
    ("⚪", "Weiß"),
    ("🩶", "Grau"),
    ("🟦", "Hellblau"),
]


ANIMALS = [
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
    ("🦆", "Ente"),
    ("🦅", "Adler"),
    ("🦉", "Eule"),
    ("🐺", "Wolf"),
    ("🐗", "Wildschwein"),
    ("🐴", "Pferd"),
    ("🦄", "Einhorn"),
    ("🐝", "Biene"),
    ("🐛", "Raupe"),
    ("🦋", "Schmetterling"),
    ("🐌", "Schnecke"),
    ("🐞", "Marienkäfer"),
    ("🐜", "Ameise"),
    ("🕷️", "Spinne"),
    ("🐢", "Schildkröte"),
    ("🐍", "Schlange"),
    ("🦎", "Eidechse"),
    ("🦖", "Dinosaurier"),
    ("🐙", "Oktopus"),
    ("🦀", "Krabbe"),
    ("🐠", "Fisch"),
    ("🐬", "Delfin"),
    ("🐳", "Wal"),
    ("🦈", "Hai"),
    ("🐊", "Krokodil"),
    ("🦒", "Giraffe"),
    ("🐘", "Elefant"),
]


FOOD = [
    ("🍕", "Pizza"),
    ("🍔", "Burger"),
    ("🍟", "Pommes"),
    ("🌭", "Hotdog"),
    ("🌮", "Taco"),
    ("🌯", "Burrito"),
    ("🍿", "Popcorn"),
    ("🍩", "Donut"),
    ("🍪", "Keks"),
    ("🍰", "Kuchen"),
    ("🎂", "Torte"),
    ("🍫", "Schokolade"),
    ("🍭", "Lolli"),
    ("🍬", "Bonbon"),
    ("🍎", "Apfel"),
    ("🍌", "Banane"),
    ("🍉", "Wassermelone"),
    ("🍇", "Trauben"),
    ("🍓", "Erdbeere"),
    ("🍒", "Kirsche"),
    ("🍑", "Pfirsich"),
    ("🥝", "Kiwi"),
    ("🍍", "Ananas"),
    ("🥭", "Mango"),
    ("🍋", "Zitrone"),
    ("🥕", "Karotte"),
    ("🌽", "Mais"),
    ("🥔", "Kartoffel"),
    ("🍅", "Tomate"),
    ("🥒", "Gurke"),
    ("🍄", "Pilz"),
    ("🍞", "Brot"),
    ("🥨", "Brezel"),
    ("🧀", "Käse"),
    ("🍳", "Ei"),
    ("🍗", "Hähnchen"),
    ("🍝", "Pasta"),
    ("🍣", "Sushi"),
    ("🍜", "Nudeln"),
]


DRINKS = [
    ("💧", "Wasser"),
    ("🥤", "Softdrink"),
    ("☕", "Kaffee"),
    ("🍵", "Tee"),
    ("🧃", "Saft"),
    ("🥛", "Milch"),
    ("🧋", "Bubble Tea"),
    ("🧉", "Mate"),
]


VEHICLES = [
    ("🚗", "Auto"),
    ("🚕", "Taxi"),
    ("🚌", "Bus"),
    ("🚓", "Polizeiauto"),
    ("🚑", "Krankenwagen"),
    ("🚒", "Feuerwehr"),
    ("🚐", "Van"),
    ("🚚", "LKW"),
    ("🏎️", "Rennwagen"),
    ("🚓", "Streifenwagen"),
    ("🏍️", "Motorrad"),
    ("🚲", "Fahrrad"),
    ("🛴", "Roller"),
    ("🚂", "Zug"),
    ("🚆", "Schnellzug"),
    ("✈️", "Flugzeug"),
    ("🚁", "Hubschrauber"),
    ("🚢", "Schiff"),
    ("⛵", "Segelboot"),
    ("🚀", "Rakete"),
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
    ("🏒", "Eishockey"),
    ("🏏", "Cricket"),
    ("⛳", "Golf"),
    ("🏹", "Bogenschießen"),
    ("🏊", "Schwimmen"),
    ("🚴", "Radsport"),
    ("🏃", "Leichtathletik"),
]


NATURE = [
    ("🌳", "Baum"),
    ("🌲", "Nadelbaum"),
    ("🌴", "Palme"),
    ("🌵", "Kaktus"),
    ("🌻", "Sonnenblume"),
    ("🌹", "Rose"),
    ("🌷", "Tulpe"),
    ("🌺", "Blume"),
    ("🍀", "Klee"),
    ("🌿", "Kräuter"),
    ("🌊", "Wasser"),
    ("🏔️", "Berg"),
    ("🌋", "Vulkan"),
    ("🏜️", "Wüste"),
    ("🏝️", "Insel"),
    ("🌅", "Sonnenaufgang"),
    ("🌄", "Berglandschaft"),
    ("☀️", "Sonne"),
    ("🌙", "Mond"),
    ("⭐", "Stern"),
    ("🌧️", "Regen"),
    ("❄️", "Schnee"),
    ("🌈", "Regenbogen"),
    ("🌪️", "Tornado"),
]


TECH = [
    ("💻", "Laptop"),
    ("🖥️", "Computer"),
    ("⌨️", "Tastatur"),
    ("🖱️", "Maus"),
    ("📱", "Smartphone"),
    ("📷", "Kamera"),
    ("🎧", "Kopfhörer"),
    ("🎮", "Controller"),
    ("🕹️", "Joystick"),
    ("📺", "Fernseher"),
    ("📡", "Antenne"),
    ("🔋", "Akku"),
    ("🔌", "Stecker"),
    ("💾", "Diskette"),
    ("💿", "CD"),
    ("🤖", "Roboter"),
]


JOBS = [
    ("👨‍⚕️", "Arzt"),
    ("👩‍⚕️", "Ärztin"),
    ("👨‍🏫", "Lehrer"),
    ("👮", "Polizist"),
    ("👨‍🚒", "Feuerwehrmann"),
    ("👨‍🍳", "Koch"),
    ("👨‍💻", "Programmierer"),
    ("👷", "Bauarbeiter"),
    ("👨‍🔧", "Mechaniker"),
    ("👨‍⚖️", "Richter"),
    ("👨‍🎨", "Künstler"),
    ("👨‍✈️", "Pilot"),
    ("🧑‍🌾", "Landwirt"),
    ("🧑‍🚀", "Astronaut"),
    ("🧑‍🔬", "Wissenschaftler"),
]


OBJECTS = [
    ("📚", "Bücher"),
    ("✏️", "Bleistift"),
    ("🖊️", "Stift"),
    ("📏", "Lineal"),
    ("✂️", "Schere"),
    ("🔑", "Schlüssel"),
    ("🔒", "Schloss"),
    ("🎒", "Rucksack"),
    ("🪑", "Stuhl"),
    ("🛏️", "Bett"),
    ("🚪", "Tür"),
    ("🪟", "Fenster"),
    ("🕯️", "Kerze"),
    ("⏰", "Wecker"),
    ("📞", "Telefon"),
    ("💡", "Lampe"),
    ("🧸", "Teddybär"),
    ("☂️", "Regenschirm"),
]


# ============================================================
# QUIZ-HILFSFUNKTIONEN
# ============================================================

def make_options(correct, category):
    names = [name for emoji, name in category if name != correct]

    wrong_answers = random.sample(
        names,
        min(3, len(names))
    )

    options = wrong_answers + [correct]
    random.shuffle(options)

    return options


def create_quiz(question, correct, category, emoji=None, hint=None):
    options = make_options(correct, category)

    return {
        "question": question,
        "correct": correct,
        "options": options,
        "emoji": emoji,
        "hint": hint or "Überlege genau und vergleiche die Antwortmöglichkeiten.",
        "category": "Emoji Quiz"
    }


def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(range(len(QUIZZES)))
    random.shuffle(quiz_bag)

    print(f"🧠 Quiz-Fragen neu gemischt: {len(quiz_bag)} Fragen")


# ============================================================
# QUIZ ERSTELLEN
# ============================================================

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
        ("Berufe", JOBS),
        ("Gegenstände", OBJECTS),
    ]

    for category_name, category in categories:

        for emoji, answer in category:

            quizzes.append(
                create_quiz(
                    f"Welcher Begriff passt zu diesem Emoji? {emoji}",
                    answer,
                    category,
                    emoji,
                    f"Das gesuchte Wort gehört zur Kategorie „{category_name}“."
                )
            )

    # Mathe
    for _ in range(30):
        a = random.randint(2, 20)
        b = random.randint(2, 20)

        operation = random.choice(["+", "-", "*"])

        if operation == "+":
            answer = a + b
            question = f"🧮 Wie viel ist {a} + {b}?"

        elif operation == "-":
            if b > a:
                a, b = b, a

            answer = a - b
            question = f"🧮 Wie viel ist {a} - {b}?"

        else:
            answer = a * b
            question = f"🧮 Wie viel ist {a} × {b}?"

        options = [
            answer,
            answer + random.randint(1, 5),
            max(0, answer - random.randint(1, 5)),
            answer + random.randint(6, 10)
        ]

        options = list(dict.fromkeys(options))

        while len(options) < 4:
            options.append(answer + len(options) + 10)

        random.shuffle(options)

        quizzes.append({
            "question": question,
            "correct": str(answer),
            "options": [str(option) for option in options],
            "emoji": "🧮",
            "hint": "Rechne die Aufgabe Schritt für Schritt.",
            "category": "Mathe"
        })

    # Rätsel
    riddles = [
        (
            "Ich habe vier Beine, kann aber nicht laufen. Was bin ich?",
            "Tisch"
        ),
        (
            "Was wird nass, während es trocknet?",
            "Handtuch"
        ),
        (
            "Ich habe Zähne, kann aber nicht beißen. Was bin ich?",
            "Kamm"
        ),
        (
            "Was hat einen Hals, aber keinen Kopf?",
            "Flasche"
        ),
        (
            "Was hat Hände, kann aber nicht klatschen?",
            "Uhr"
        ),
        (
            "Was kann um die Welt reisen, bleibt aber immer in einer Ecke?",
            "Briefmarke"
        ),
        (
            "Was hat viele Schlüssel, aber öffnet keine Tür?",
            "Klavier"
        ),
        (
            "Was geht hoch, kommt aber niemals wieder herunter?",
            "Alter"
        ),
    ]

    for question, answer in riddles:

        possible = [
            answer,
            "Regenschirm",
            "Fenster",
            "Schuhe"
        ]

        possible = list(dict.fromkeys(possible))

        random.shuffle(possible)

        quizzes.append({
            "question": f"🧩 {question}",
            "correct": answer,
            "options": possible,
            "emoji": "🧩",
            "hint": "Lies das Rätsel genau und denke nicht zu kompliziert.",
            "category": "Rätsel"
        })

    return quizzes


QUIZZES = build_quizzes()


# ============================================================
# QUIZ – NEUE FRAGE
# ============================================================

async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message
    global quiz_bag

    async with quiz_lock:

        if not quiz_bag:
            refill_quiz_bag()

        quiz_index = quiz_bag.pop()
        quiz = QUIZZES[quiz_index]

        current_quiz = quiz

        embed = discord.Embed(
            title="🧠 Emoji Quiz",
            description=(
                f"## {quiz['question']}\n\n"
                "Wähle die richtige Antwort:"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📚 Kategorie",
            value=quiz.get("category", "Allgemein"),
            inline=True
        )

        embed.add_field(
            name="🏆 Punkte",
            value="+1 Punkt",
            inline=True
        )

        embed.set_footer(
            text="RLP • Emoji Quiz"
        )

        view = QuizView(quiz)

        try:
            current_quiz_message = await channel.send(
                embed=embed,
                view=view
            )

        except discord.HTTPException as error:
            print(f"❌ Fehler beim Senden des Quiz: {error}")


# ============================================================
# QUIZ BUTTONS
# ============================================================

class QuizAnswerButton(discord.ui.Button):

    def __init__(self, position, answer):
        super().__init__(
            label=answer,
            style=discord.ButtonStyle.secondary,
            custom_id=f"quiz_answer_{position}"
        )

        self.position = position
        self.answer = answer

    async def callback(self, interaction: discord.Interaction):

        global current_quiz
        global current_quiz_message

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if (
            current_quiz_message is not None
            and interaction.message.id != current_quiz_message.id
        ):
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if normalize(self.answer) != normalize(
            str(current_quiz["correct"])
        ):
            await interaction.response.send_message(
                "❌ Leider falsch. Versuch es weiter!",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        quiz_scores[user_id] = quiz_scores.get(user_id, 0) + 1
        save_data()

        correct_answer = current_quiz["correct"]

        current_quiz = None

        for item in self.view.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(
            content=(
                f"🎉 **{interaction.user.display_name}** "
                f"hat die richtige Antwort gefunden!\n"
                f"✅ Antwort: **{correct_answer}**\n"
                f"🏆 +1 Punkt"
            ),
            view=self.view
        )

        await asyncio.sleep(1.5)

        await send_new_quiz(interaction.channel)


class QuizHintButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="💡 Hinweis",
            style=discord.ButtonStyle.primary,
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
            f"💡 **Hinweis:**\n{current_quiz['hint']}",
            ephemeral=True
        )


class QuizSkipButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="⏭️ Überspringen",
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
            content="⏭️ Quiz wurde übersprungen.",
            view=None
        )

        await asyncio.sleep(0.8)

        await send_new_quiz(interaction.channel)


class QuizView(discord.ui.View):

    def __init__(self, quiz=None):
        super().__init__(timeout=None)

        if quiz is not None:

            for index, answer in enumerate(quiz["options"]):
                self.add_item(
                    QuizAnswerButton(index, answer)
                )

        self.add_item(QuizHintButton())
        self.add_item(QuizSkipButton())


# ============================================================
# QUIZ COMMAND
# ============================================================

@bot.command(name="quiz")
async def quiz_command(ctx):

    if not isinstance(ctx.author, discord.Member):
        return

    # ========================================================
    # NUR DIESE ROLLE DARF !quiz BENUTZEN
    # ========================================================

    has_permission = any(
        role.id == QUIZ_COMMAND_ROLE_ID
        for role in ctx.author.roles
    )

    if not has_permission:

        embed = discord.Embed(
            title="🔒 Keine Berechtigung",
            description=(
                "Du benötigst die entsprechende Team-Rolle, "
                "um den Befehl `!quiz` zu verwenden."
            ),
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            delete_after=5
        )

        return

    await send_new_quiz(ctx.channel)


# ============================================================
# PUNKTE
# ============================================================

@bot.command(name="punkte")
async def points_command(ctx):

    score = quiz_scores.get(
        str(ctx.author.id),
        0
    )

    embed = discord.Embed(
        title="🏆 Deine Quiz-Punkte",
        description=(
            f"{ctx.author.mention}, du hast aktuell "
            f"**{score} Punkt(e)**."
        ),
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed)


# ============================================================
# TOP
# ============================================================

@bot.command(name="top")
async def top_command(ctx):

    if not quiz_scores:
        await ctx.send(
            "🏆 Es gibt noch keine Quiz-Punkte."
        )
        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Emoji-Quiz Rangliste",
        description="Die aktuellen Top-Spieler:",
        color=discord.Color.gold()
    )

    text = ""

    for index, (user_id, score) in enumerate(
        sorted_scores[:10],
        start=1
    ):

        member = ctx.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else f"User {user_id}"
        )

        text += (
            f"**{index}.** {name} — "
            f"🏆 **{score}** Punkte\n"
        )

    embed.add_field(
        name="Rangliste",
        value=text,
        inline=False
    )

    await ctx.send(embed=embed)


# ============================================================
# NAMETAG
# ============================================================

def get_clean_name(member):

    name = member.display_name

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_rlp_nickname(member, force=False):

    if not isinstance(member, discord.Member):
        return

    has_role = any(
        role.id == NAMETAG_ROLE_ID
        for role in member.roles
    )

    if not has_role:
        return

    if (
        member.id in nametag_removed_users
        and not force
    ):
        return

    if force:
        nametag_removed_users.discard(member.id)
        save_data()

    clean_name = get_clean_name(member)

    new_nickname = f"{NAMETAG}{clean_name}"

    if len(new_nickname) > 32:
        new_nickname = new_nickname[:32]

    if member.nick == new_nickname:
        return

    try:
        await member.edit(
            nick=new_nickname,
            reason="Automatisches RLP-Nametag"
        )

    except discord.Forbidden:
        print(
            f"❌ Keine Berechtigung für {member}"
        )

    except discord.HTTPException as error:
        print(
            f"❌ Fehler beim Nametag von {member}: {error}"
        )


async def remove_rlp_nickname(member):

    clean_name = get_clean_name(member)

    try:
        await member.edit(
            nick=clean_name,
            reason="RLP-Nametag vom Benutzer entfernt"
        )

        nametag_removed_users.add(member.id)
        save_data()

        return True

    except discord.Forbidden:
        return False

    except discord.HTTPException:
        return False


async def update_all_rlp_nicknames():

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        return

    role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    print(
        f"🏷️ Aktualisiere {len(role.members)} RLP-Nametags..."
    )

    for member in role.members:
        await set_rlp_nickname(member)

        await asyncio.sleep(0.1)


# ============================================================
# NAMETAG PANEL
# ============================================================

class NicknamePanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🏷️",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_remove_button"
    )
    async def remove_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        success = await remove_rlp_nickname(
            interaction.user
        )

        if success:

            embed = discord.Embed(
                title="✅ Nametag entfernt",
                description=(
                    "Dein **RLP-Nametag** wurde entfernt.\n\n"
                    "Es bleibt auch nach einem Bot-Neustart entfernt."
                ),
                color=discord.Color.green()
            )

        else:

            embed = discord.Embed(
                title="❌ Fehler",
                description=(
                    "Das Nametag konnte nicht entfernt werden."
                ),
                color=discord.Color.red()
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_nickname_panel():

    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:
        print("❌ Nametag-Channel nicht gefunden.")
        return

    await cleanup_messages(
        channel,
        "🏷️ Nickname ändern"
    )

    embed = discord.Embed(
        title="🏷️ Nickname ändern",
        description=(
            "Hier kannst du dein **RLP-Nametag** entfernen.\n\n"
            "### 🏷️ Nametag\n"
            "Mit der entsprechenden RLP-Rolle wird automatisch "
            f"`{NAMETAG}` vor deinen Namen gesetzt.\n\n"
            "### 🗑️ Entfernen\n"
            "Klicke auf den Button, wenn du das Nametag "
            "nicht mehr möchtest."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP • Nametag-System"
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )


# ============================================================
# DEVELOPER-BEWERBUNG
# ============================================================

DEVELOPER_QUESTIONS = [
    "Wie alt bist du?",
    "Wie lange bist du bereits auf dem Server?",
    "Warum möchtest du Developer werden?",
    "Welche Erfahrungen hast du mit Discord-Bots oder Programmierung?",
    "Welche Programmiersprachen beherrschst du?",
    "Welche Ideen hast du für den Server?",
    "Wie viel Zeit kannst du ungefähr für das Team aufbringen?",
]


active_applications = {}


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        emoji="🛠️",
        style=discord.ButtonStyle.success,
        custom_id="developer_apply_button"
    )
    async def apply_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id in active_applications:

            await interaction.response.send_message(
                "⏳ Du hast bereits eine laufende Bewerbung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "📩 Ich habe dir eine DM geschickt.",
            ephemeral=True
        )

        asyncio.create_task(
            run_developer_application(
                interaction.user
            )
        )


async def run_developer_application(user):

    active_applications[user.id] = True

    try:

        try:
            dm = await user.create_dm()

        except discord.Forbidden:

            active_applications.pop(
                user.id,
                None
            )

            return

        await dm.send(
            "🛠️ **Developer-Bewerbung**\n\n"
            "Danke für dein Interesse!\n"
            "Beantworte bitte die folgenden Fragen.\n\n"
            "Du hast pro Frage **5 Minuten** Zeit."
        )

        answers = []

        for question in DEVELOPER_QUESTIONS:

            await dm.send(
                f"**Frage {len(answers) + 1}/{len(DEVELOPER_QUESTIONS)}**\n"
                f"{question}"
            )

            def check(message):

                return (
                    message.author.id == user.id
                    and message.channel.id == dm.id
                )

            try:

                answer = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=check
                )

            except asyncio.TimeoutError:

                await dm.send(
                    "⏰ Deine Bewerbung wurde wegen "
                    "Zeitüberschreitung beendet."
                )

                return

            answers.append(answer.content)

        await dm.send(
            "✅ Deine Bewerbung wurde erfolgreich "
            "an das Developer-Team weitergeleitet."
        )

        await send_application_review(
            user,
            answers
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

    embed = discord.Embed(
        title="🛠️ Neue Developer-Bewerbung",
        description=(
            f"**Bewerber:** {user.mention}\n"
            f"**User:** {user}"
        ),
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    for index, (question, answer) in enumerate(
        zip(DEVELOPER_QUESTIONS, answers),
        start=1
    ):

        embed.add_field(
            name=f"{index}. {question}",
            value=answer[:1024],
            inline=False
        )

    embed.set_footer(
        text="RLP • Developer-Bewerbung"
    )

    await channel.send(
        embed=embed
    )


async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        print("❌ Bewerbungs-Channel nicht gefunden.")
        return

    await cleanup_messages(
        channel,
        "🛠️ Developer Bewerbung"
    )

    embed = discord.Embed(
        title="🛠️ Developer Bewerbung",
        description=(
            "## 💻 Developer gesucht?\n\n"
            "Du möchtest Teil unseres Developer-Teams werden?\n"
            "Dann kannst du dich direkt über den Button bewerben.\n\n"
            "### 📋 Ablauf\n"
            "1. Bewerbung starten\n"
            "2. Fragen per DM beantworten\n"
            "3. Bewerbung wird an das Team weitergeleitet\n"
            "4. Das Developer-Team überprüft deine Bewerbung\n\n"
            "⏱️ **Pro Frage hast du 5 Minuten Zeit.**"
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text="RLP • Developer-Team"
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
# MEMBER EVENTS
# ============================================================

@bot.event
async def on_member_join(member):

    await set_rlp_nickname(
        member,
        force=True
    )


@bot.event
async def on_member_update(before, after):

    before_roles = {
        role.id
        for role in before.roles
    }

    after_roles = {
        role.id
        for role in after.roles
    }

    role_was_added = (
        NAMETAG_ROLE_ID in after_roles
        and NAMETAG_ROLE_ID not in before_roles
    )

    if role_was_added:

        await set_rlp_nickname(
            after,
            force=True
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    if startup_finished:
        return

    print("=" * 50)
    print(f"🤖 Bot online: {bot.user}")
    print("=" * 50)

    try:

        refill_quiz_bag()

        guild = bot.get_guild(
            GUILD_ID
        )

        if guild is None:

            print(
                f"❌ Guild {GUILD_ID} wurde nicht gefunden."
            )

            return

        # RLP-Nametags aktualisieren
        await update_all_rlp_nicknames()

        # Altes Quiz bereinigen
        quiz_channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if quiz_channel is not None:

            await cleanup_messages(
                quiz_channel,
                "🧠 Emoji Quiz"
            )

            await send_new_quiz(
                quiz_channel
            )

        # Nametag Panel
        await send_nickname_panel()

        # Developer Panel
        await send_application_panel()

        startup_finished = True

        print(
            f"🧠 {len(QUIZZES)} Quiz-Fragen verfügbar."
        )

        print("✅ Startup vollständig abgeschlossen.")

    except Exception as error:

        print(
            f"❌ Fehler beim Startup: {error}"
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
        commands.MissingPermissions
    ):

        embed = discord.Embed(
            title="🔒 Keine Berechtigung",
            description=(
                "Du hast keine Berechtigung für diesen Befehl."
            ),
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            delete_after=5
        )

        return

    print(
        f"❌ Command-Fehler: {error}"
    )


# ============================================================
# MESSAGE
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    await bot.process_commands(message)


# ============================================================
# START
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN wurde nicht gefunden!"
    )


bot.run(TOKEN)
