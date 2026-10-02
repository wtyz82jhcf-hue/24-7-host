import os
import json
import random
import asyncio
import re
from datetime import datetime

import discord
from discord.ext import commands


# =========================================================
# KONFIGURATION
# =========================================================

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NICKNAME_CHANNEL_ID = 1555684071911202836

GUILD_ID = 1519481018221072454
NAMETAG_ROLE_ID = 1520102928398942348

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# =========================================================
# DATEN
# =========================================================

nametag_removed_users = set()
quiz_scores = {}

current_quiz = None
current_quiz_message = None

quiz_bag = []
quiz_lock = asyncio.Lock()

startup_finished = False


# =========================================================
# DATEN SPEICHERN / LADEN
# =========================================================

def load_data():
    global nametag_removed_users
    global quiz_scores

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        nametag_removed_users = set(
            str(x) for x in data.get("nametag_removed_users", [])
        )

        quiz_scores = {
            str(k): int(v)
            for k, v in data.get("quiz_scores", {}).items()
        }

    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        nametag_removed_users = set()
        quiz_scores = {}


def save_data():
    data = {
        "nametag_removed_users": list(nametag_removed_users),
        "quiz_scores": quiz_scores
    }

    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def normalize(text):
    return re.sub(r"\s+", " ", text.strip()).lower()


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# =========================================================
#                     EMOJI QUIZ
# =========================================================
# =========================================================

# ---------------------------------------------------------
# BASISDATEN FÜR SEHR VIELE FRAGEN
# ---------------------------------------------------------

COUNTRIES = [
    ("🇩🇪", "Deutschland"),
    ("🇦🇹", "Österreich"),
    ("🇨🇭", "Schweiz"),
    ("🇫🇷", "Frankreich"),
    ("🇮🇹", "Italien"),
    ("🇪🇸", "Spanien"),
    ("🇵🇹", "Portugal"),
    ("🇳🇱", "Niederlande"),
    ("🇧🇪", "Belgien"),
    ("🇱🇺", "Luxemburg"),
    ("🇩🇰", "Dänemark"),
    ("🇸🇪", "Schweden"),
    ("🇳🇴", "Norwegen"),
    ("🇫🇮", "Finnland"),
    ("🇮🇸", "Island"),
    ("🇬🇧", "Vereinigtes Königreich"),
    ("🇮🇪", "Irland"),
    ("🇵🇱", "Polen"),
    ("🇨🇿", "Tschechien"),
    ("🇸🇰", "Slowakei"),
    ("🇭🇺", "Ungarn"),
    ("🇷🇴", "Rumänien"),
    ("🇧🇬", "Bulgarien"),
    ("🇬🇷", "Griechenland"),
    ("🇭🇷", "Kroatien"),
    ("🇸🇮", "Slowenien"),
    ("🇷🇸", "Serbien"),
    ("🇺🇦", "Ukraine"),
    ("🇹🇷", "Türkei"),
    ("🇺🇸", "USA"),
    ("🇨🇦", "Kanada"),
    ("🇲🇽", "Mexiko"),
    ("🇧🇷", "Brasilien"),
    ("🇦🇷", "Argentinien"),
    ("🇨🇱", "Chile"),
    ("🇵🇪", "Peru"),
    ("🇨🇴", "Kolumbien"),
    ("🇺🇾", "Uruguay"),
    ("🇯🇵", "Japan"),
    ("🇨🇳", "China"),
    ("🇰🇷", "Südkorea"),
    ("🇮🇳", "Indien"),
    ("🇮🇩", "Indonesien"),
    ("🇹🇭", "Thailand"),
    ("🇻🇳", "Vietnam"),
    ("🇵🇭", "Philippinen"),
    ("🇦🇺", "Australien"),
    ("🇳🇿", "Neuseeland"),
    ("🇿🇦", "Südafrika"),
    ("🇪🇬", "Ägypten"),
    ("🇲🇦", "Marokko"),
    ("🇹🇳", "Tunesien"),
    ("🇳🇬", "Nigeria"),
    ("🇰🇪", "Kenia"),
    ("🇸🇦", "Saudi-Arabien"),
    ("🇦🇪", "Vereinigte Arabische Emirate"),
    ("🇮🇱", "Israel"),
    ("🇮🇷", "Iran"),
    ("🇮🇶", "Irak"),
    ("🇵🇰", "Pakistan"),
    ("🇧🇩", "Bangladesch"),
    ("🇳🇵", "Nepal"),
    ("🇸🇬", "Singapur"),
    ("🇲🇾", "Malaysia"),
]


COLORS = [
    ("🔴", "Rot"),
    ("🟠", "Orange"),
    ("🟡", "Gelb"),
    ("🟢", "Grün"),
    ("🔵", "Blau"),
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
    ("🐭", "Maus"),
    ("🐹", "Hamster"),
    ("🐰", "Kaninchen"),
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
    ("🦋", "Schmetterling"),
    ("🐌", "Schnecke"),
    ("🐞", "Marienkäfer"),
    ("🐢", "Schildkröte"),
    ("🐍", "Schlange"),
    ("🦎", "Eidechse"),
    ("🐙", "Oktopus"),
    ("🦀", "Krabbe"),
    ("🐠", "Fisch"),
    ("🐬", "Delfin"),
    ("🐳", "Wal"),
    ("🦈", "Hai"),
    ("🐊", "Krokodil"),
    ("🦒", "Giraffe"),
    ("🐘", "Elefant"),
    ("🦏", "Nashorn"),
    ("🦛", "Nilpferd"),
    ("🐪", "Kamel"),
    ("🦘", "Känguru"),
    ("🦓", "Zebra"),
]


FOOD = [
    ("🍕", "Pizza"),
    ("🍔", "Burger"),
    ("🍟", "Pommes"),
    ("🌭", "Hotdog"),
    ("🌮", "Taco"),
    ("🌯", "Burrito"),
    ("🍝", "Spaghetti"),
    ("🍜", "Nudeln"),
    ("🍣", "Sushi"),
    ("🍚", "Reis"),
    ("🍛", "Curry"),
    ("🥨", "Brezel"),
    ("🍞", "Brot"),
    ("🥐", "Croissant"),
    ("🥖", "Baguette"),
    ("🧀", "Käse"),
    ("🥚", "Ei"),
    ("🍳", "Spiegelei"),
    ("🥞", "Pfannkuchen"),
    ("🧇", "Waffel"),
    ("🍗", "Hähnchen"),
    ("🌭", "Hotdog"),
    ("🥗", "Salat"),
    ("🍎", "Apfel"),
    ("🍌", "Banane"),
    ("🍉", "Wassermelone"),
    ("🍇", "Trauben"),
    ("🍓", "Erdbeere"),
    ("🍒", "Kirschen"),
    ("🍑", "Pfirsich"),
    ("🍍", "Ananas"),
    ("🥝", "Kiwi"),
    ("🥭", "Mango"),
    ("🍋", "Zitrone"),
    ("🍊", "Orange"),
    ("🍫", "Schokolade"),
    ("🍪", "Keks"),
    ("🍩", "Donut"),
    ("🍰", "Kuchen"),
    ("🍦", "Eis"),
    ("🍿", "Popcorn"),
]


DRINKS = [
    ("💧", "Wasser"),
    ("🥛", "Milch"),
    ("🧃", "Saft"),
    ("🥤", "Softdrink"),
    ("☕", "Kaffee"),
    ("🍵", "Tee"),
    ("🧋", "Bubble Tea"),
    ("🍋", "Limonade"),
]


VEHICLES = [
    ("🚗", "Auto"),
    ("🚕", "Taxi"),
    ("🚌", "Bus"),
    ("🚎", "Oberleitungsbus"),
    ("🚓", "Polizeiauto"),
    ("🚑", "Rettungswagen"),
    ("🚒", "Feuerwehrfahrzeug"),
    ("🚚", "LKW"),
    ("🚛", "Sattelzug"),
    ("🏍️", "Motorrad"),
    ("🚲", "Fahrrad"),
    ("🛴", "E-Scooter"),
    ("🚜", "Traktor"),
    ("🚆", "Zug"),
    ("🚇", "U-Bahn"),
    ("🚊", "Straßenbahn"),
    ("✈️", "Flugzeug"),
    ("🚁", "Hubschrauber"),
    ("🚢", "Schiff"),
    ("⛵", "Segelboot"),
]


SPORTS = [
    ("⚽", "Fußball"),
    ("🏀", "Basketball"),
    ("🏈", "American Football"),
    ("⚾", "Baseball"),
    ("🎾", "Tennis"),
    ("🏐", "Volleyball"),
    ("🏉", "Rugby"),
    ("🏓", "Tischtennis"),
    ("🏸", "Badminton"),
    ("🥊", "Boxen"),
    ("🥋", "Kampfsport"),
    ("🏊", "Schwimmen"),
    ("🚴", "Radfahren"),
    ("⛷️", "Skifahren"),
    ("🏂", "Snowboarden"),
    ("🏎️", "Rennsport"),
    ("🏋️", "Gewichtheben"),
    ("🤸", "Turnen"),
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
    ("🌿", "Kräuter"),
    ("🌊", "Welle"),
    ("🏔️", "Berg"),
    ("🌋", "Vulkan"),
    ("🏝️", "Insel"),
    ("🏜️", "Wüste"),
    ("🌈", "Regenbogen"),
    ("☀️", "Sonne"),
    ("🌙", "Mond"),
    ("⭐", "Stern"),
    ("☁️", "Wolke"),
    ("🌧️", "Regen"),
    ("⛈️", "Gewitter"),
    ("❄️", "Schnee"),
    ("🔥", "Feuer"),
]


TECH = [
    ("📱", "Smartphone"),
    ("💻", "Laptop"),
    ("🖥️", "Computer"),
    ("⌨️", "Tastatur"),
    ("🖱️", "Maus"),
    ("🎧", "Kopfhörer"),
    ("📷", "Kamera"),
    ("📺", "Fernseher"),
    ("📡", "Antenne"),
    ("🔋", "Batterie"),
    ("🔌", "Stecker"),
    ("💾", "Datenträger"),
    ("🖨️", "Drucker"),
    ("⌚", "Smartwatch"),
    ("🕹️", "Controller"),
    ("💿", "CD"),
]


JOBS = [
    ("👮", "Polizist"),
    ("👨‍🚒", "Feuerwehrmann"),
    ("👨‍⚕️", "Arzt"),
    ("👩‍⚕️", "Ärztin"),
    ("👨‍🏫", "Lehrer"),
    ("👩‍🏫", "Lehrerin"),
    ("👨‍🍳", "Koch"),
    ("👩‍🍳", "Köchin"),
    ("👨‍🔧", "Mechaniker"),
    ("👷", "Bauarbeiter"),
    ("👨‍💻", "Programmierer"),
    ("🧑‍✈️", "Pilot"),
    ("🧑‍🚀", "Astronaut"),
    ("🕵️", "Detektiv"),
    ("👨‍⚖️", "Richter"),
]


OBJECTS = [
    ("🔑", "Schlüssel"),
    ("🔒", "Schloss"),
    ("📚", "Bücher"),
    ("✏️", "Bleistift"),
    ("📝", "Notiz"),
    ("📅", "Kalender"),
    ("⏰", "Wecker"),
    ("🎒", "Rucksack"),
    ("👟", "Schuhe"),
    ("👕", "T-Shirt"),
    ("🧢", "Mütze"),
    ("☂️", "Regenschirm"),
    ("🔦", "Taschenlampe"),
    ("🪑", "Stuhl"),
    ("🛏️", "Bett"),
    ("🚪", "Tür"),
    ("🪟", "Fenster"),
    ("🧹", "Besen"),
]


# ---------------------------------------------------------
# HILFSFUNKTION FÜR ANTWORTEN
# ---------------------------------------------------------

def make_options(correct, pool, amount=4):
    values = [x[1] for x in pool if x[1] != correct]

    random.shuffle(values)

    selected = values[:amount - 1]
    selected.append(correct)

    random.shuffle(selected)

    return selected


def emoji_from_name(name, pool):
    for emoji, label in pool:
        if label == name:
            return emoji
    return "❓"


def create_quiz(question, correct, pool, hint):
    options = make_options(correct, pool)

    option_emojis = [
        emoji_from_name(option, pool)
        for option in options
    ]

    return {
        "question": question,
        "answers": [
            (option_emojis[i], options[i])
            for i in range(4)
        ],
        "correct": correct,
        "hint": hint
    }


# ---------------------------------------------------------
# SEHR GROSSER QUIZ-POOL
# ---------------------------------------------------------

def build_quizzes():

    quizzes = []

    # =====================================================
    # LÄNDER
    # =====================================================

    for emoji, country in COUNTRIES:
        quizzes.append(
            create_quiz(
                f"🌍 Welche Flagge gehört zu **{country}**?",
                country,
                COUNTRIES,
                "Schau dir die Farben und das Muster der Flagge genau an."
            )
        )

    # =====================================================
    # FARBEN
    # =====================================================

    for emoji, color in COLORS:
        quizzes.append(
            {
                "question": f"🎨 Welche Farbe wird durch {emoji} dargestellt?",
                "answers": [
                    (e, c)
                    for e, c in random.sample(COLORS, 4)
                ],
                "correct": color,
                "hint": "Überlege, welche Farbe das Emoji normalerweise darstellt."
            }
        )

    # =====================================================
    # TIERE
    # =====================================================

    for emoji, animal in ANIMALS:
        quizzes.append(
            {
                "question": f"🐾 Welches Tier wird durch {emoji} dargestellt?",
                "answers": [
                    (e, a)
                    for e, a in random.sample(ANIMALS, 4)
                ],
                "correct": animal,
                "hint": "Erkenne das Tier anhand seiner typischen Darstellung."
            }
        )

    # =====================================================
    # ESSEN
    # =====================================================

    for emoji, food in FOOD:
        quizzes.append(
            {
                "question": f"🍽️ Was wird durch {emoji} dargestellt?",
                "answers": [
                    (e, f)
                    for e, f in random.sample(FOOD, 4)
                ],
                "correct": food,
                "hint": "Überlege, welches Essen dieses Emoji zeigt."
            }
        )

    # =====================================================
    # GETRÄNKE
    # =====================================================

    for emoji, drink in DRINKS:
        quizzes.append(
            {
                "question": f"🥤 Welches Getränk wird durch {emoji} dargestellt?",
                "answers": [
                    (e, d)
                    for e, d in random.sample(DRINKS, 4)
                ],
                "correct": drink,
                "hint": "Achte auf die Form und das typische Getränkesymbol."
            }
        )

    # =====================================================
    # FAHRZEUGE
    # =====================================================

    for emoji, vehicle in VEHICLES:
        quizzes.append(
            {
                "question": f"🚗 Welches Fahrzeug wird durch {emoji} dargestellt?",
                "answers": [
                    (e, v)
                    for e, v in random.sample(VEHICLES, 4)
                ],
                "correct": vehicle,
                "hint": "Überlege, welches Verkehrsmittel das Emoji zeigt."
            }
        )

    # =====================================================
    # SPORT
    # =====================================================

    for emoji, sport in SPORTS:
        quizzes.append(
            {
                "question": f"🏆 Welche Sportart wird durch {emoji} dargestellt?",
                "answers": [
                    (e, s)
                    for e, s in random.sample(SPORTS, 4)
                ],
                "correct": sport,
                "hint": "Achte auf das Sportgerät oder die Bewegung."
            }
        )

    # =====================================================
    # NATUR
    # =====================================================

    for emoji, nature in NATURE:
        quizzes.append(
            {
                "question": f"🌿 Was wird durch {emoji} dargestellt?",
                "answers": [
                    (e, n)
                    for e, n in random.sample(NATURE, 4)
                ],
                "correct": nature,
                "hint": "Überlege, was du normalerweise in der Natur findest."
            }
        )

    # =====================================================
    # TECHNIK
    # =====================================================

    for emoji, tech in TECH:
        quizzes.append(
            {
                "question": f"💻 Was wird durch {emoji} dargestellt?",
                "answers": [
                    (e, t)
                    for e, t in random.sample(TECH, 4)
                ],
                "correct": tech,
                "hint": "Achte auf das technische Gerät oder Zubehör."
            }
        )

    # =====================================================
    # BERUFE
    # =====================================================

    for emoji, job in JOBS:
        quizzes.append(
            {
                "question": f"👤 Welcher Beruf wird durch {emoji} dargestellt?",
                "answers": [
                    (e, j)
                    for e, j in random.sample(JOBS, 4)
                ],
                "correct": job,
                "hint": "Überlege, welche Tätigkeit zu der Person passt."
            }
        )

    # =====================================================
    # GEGENSTÄNDE
    # =====================================================

    for emoji, obj in OBJECTS:
        quizzes.append(
            {
                "question": f"🔎 Was wird durch {emoji} dargestellt?",
                "answers": [
                    (e, o)
                    for e, o in random.sample(OBJECTS, 4)
                ],
                "correct": obj,
                "hint": "Erkenne den Gegenstand anhand seiner Form."
            }
        )

    # =====================================================
    # EMOJI-KOMBINATIONEN
    # =====================================================

    combination_quizzes = [
        (
            "🇩🇪🍺",
            "Deutschland",
            ["Deutschland", "Frankreich", "Italien", "Spanien"]
        ),
        (
            "🇮🇹🍕",
            "Italien",
            ["Italien", "Japan", "Mexiko", "Griechenland"]
        ),
        (
            "🇯🇵🍣",
            "Japan",
            ["Japan", "China", "Südkorea", "Thailand"]
        ),
        (
            "🇲🇽🌮",
            "Mexiko",
            ["Mexiko", "Brasilien", "Spanien", "Portugal"]
        ),
        (
            "🇺🇸🍔",
            "USA",
            ["USA", "Kanada", "Australien", "Mexiko"]
        ),
        (
            "🇫🇷🥐",
            "Frankreich",
            ["Frankreich", "Belgien", "Deutschland", "Schweiz"]
        ),
        (
            "🇪🇸💃",
            "Spanien",
            ["Spanien", "Portugal", "Italien", "Brasilien"]
        ),
        (
            "🇬🇧☕",
            "Vereinigtes Königreich",
            ["Vereinigtes Königreich", "Irland", "USA", "Kanada"]
        ),
        (
            "🇦🇺🦘",
            "Australien",
            ["Australien", "Neuseeland", "Südafrika", "Indonesien"]
        ),
        (
            "🇪🇬🐪",
            "Ägypten",
            ["Ägypten", "Marokko", "Tunesien", "Saudi-Arabien"]
        ),
    ]

    for emojis, correct, options in combination_quizzes:
        answers = []

        for country in options:
            flag = next(
                (e for e, c in COUNTRIES if c == country),
                "🌍"
            )
            answers.append((flag, country))

        quizzes.append(
            {
                "question": f"🧩 Welche Verbindung passt am besten zu {emojis}?",
                "answers": answers,
                "correct": correct,
                "hint": "Die Emojis geben dir einen Hinweis auf das gesuchte Land."
            }
        )

    # =====================================================
    # ZAHLEN / EMOJI-RECHNEN
    # =====================================================

    math_quizzes = [
        ("🍎 + 🍎", "2", ["1", "2", "3", "4"]),
        ("🍎🍎 + 🍎", "3", ["2", "3", "4", "5"]),
        ("⭐⭐ + ⭐⭐", "4", ["2", "3", "4", "5"]),
        ("🐶🐶🐶 - 🐶", "2", ["1", "2", "3", "4"]),
        ("🍕🍕🍕 + 🍕", "4", ["2", "3", "4", "5"]),
        ("🚗🚗 - 🚗", "1", ["0", "1", "2", "3"]),
        ("⚽⚽⚽⚽ - ⚽⚽", "2", ["1", "2", "3", "4"]),
        ("🍎🍎🍎 + 🍎🍎", "5", ["3", "4", "5", "6"]),
        ("⭐ × ⭐⭐⭐", "3", ["2", "3", "4", "6"]),
        ("🐱🐱🐱🐱 ÷ 🐱🐱", "2", ["1", "2", "3", "4"]),
    ]

    for expression, correct, options in math_quizzes:
        quizzes.append(
            {
                "question": f"🔢 Wie viele Symbole ergeben zusammen: {expression}?",
                "answers": [
                    ("🔢", option)
                    for option in options
                ],
                "correct": correct,
                "hint": "Zähle die Emojis und rechne Schritt für Schritt."
            }
        )

    # =====================================================
    # EMOJI-RÄTSEL
    # =====================================================

    riddles = [
        ("🌧️☂️", "Regen"),
        ("☀️🏖️", "Sommer"),
        ("❄️⛄", "Winter"),
        ("🌸🌷", "Frühling"),
        ("🍂🍁", "Herbst"),
        ("🌙⭐", "Nacht"),
        ("☀️🌅", "Morgen"),
        ("🍕🍝🇮🇹", "Italien"),
        ("🍣🍚🇯🇵", "Japan"),
        ("🌮🌯🇲🇽", "Mexiko"),
        ("🥨🍺🇩🇪", "Deutschland"),
        ("🥐🗼🇫🇷", "Frankreich"),
        ("🦘🇦🇺", "Australien"),
        ("🍀🇮🇪", "Irland"),
        ("🗼🇫🇷", "Frankreich"),
        ("🗽🇺🇸", "USA"),
        ("🏰🇩🇪", "Deutschland"),
        ("🐼🇨🇳", "China"),
        ("🦁🇿🇦", "Südafrika"),
        ("🐪🏜️", "Wüste"),
    ]

    riddle_options = [
        "Deutschland",
        "Frankreich",
        "Italien",
        "Japan",
        "Mexiko",
        "Australien",
        "China",
        "USA",
        "Irland",
        "Sommer",
        "Winter",
        "Frühling",
        "Herbst",
        "Regen",
        "Nacht",
        "Morgen",
        "Wüste",
        "Südafrika",
    ]

    for emoji_text, correct in riddles:
        available = [
            x for x in riddle_options
            if x != correct
        ]

        selected = random.sample(
            available,
            min(3, len(available))
        )

        answers = [
            ("❓", x)
            for x in selected
        ]

        answers.append(("✅", correct))
        random.shuffle(answers)

        quizzes.append(
            {
                "question": f"🧠 Was könnten diese Emojis bedeuten?\n\n{emoji_text}",
                "answers": answers,
                "correct": correct,
                "hint": "Versuche die einzelnen Emojis als gemeinsamen Hinweis zu verstehen."
            }
        )

    # =====================================================
    # ALLTAG
    # =====================================================

    everyday = [
        ("🛏️", "Schlafen"),
        ("🍳☕", "Frühstück"),
        ("🎒🏫", "Schule"),
        ("💼🏢", "Arbeit"),
        ("🛒🏪", "Einkaufen"),
        ("🏠🛋️", "Zuhause"),
        ("🚿🧼", "Duschen"),
        ("🪥😁", "Zähneputzen"),
        ("📚✏️", "Lernen"),
        ("📱💬", "Chatten"),
        ("🎮🕹️", "Gaming"),
        ("🎬🍿", "Kino"),
        ("🏋️💪", "Training"),
        ("⚽🏟️", "Fußballspiel"),
        ("✈️🧳", "Reise"),
        ("🚗⛽", "Tanken"),
    ]

    everyday_options = [
        "Schlafen",
        "Frühstück",
        "Schule",
        "Arbeit",
        "Einkaufen",
        "Zuhause",
        "Duschen",
        "Zähneputzen",
        "Lernen",
        "Chatten",
        "Gaming",
        "Kino",
        "Training",
        "Fußballspiel",
        "Reise",
        "Tanken",
    ]

    for emoji_text, correct in everyday:
        others = [
            x for x in everyday_options
            if x != correct
        ]

        selected = random.sample(others, 3)

        answers = [
            ("❓", x)
            for x in selected
        ]

        answers.append(("✅", correct))
        random.shuffle(answers)

        quizzes.append(
            {
                "question": f"🏠 Was beschreibt diese Emoji-Kombination?\n\n{emoji_text}",
                "answers": answers,
                "correct": correct,
                "hint": "Überlege, welche gemeinsame Handlung oder Situation die Emojis darstellen."
            }
        )

    # =====================================================
    # MEHRFACH-VARIATIONEN
    # =====================================================

    # Dadurch entstehen zusätzliche Fragen zu den gleichen
    # Themen, aber mit anderer Fragestellung und Antwortlage.

    question_templates = [
        "🔎 Welches Emoji passt zu **{answer}**?",
        "🧠 Welches Symbol steht für **{answer}**?",
        "🎯 Welches Emoji beschreibt **{answer}**?",
        "❓ Welches dieser Emojis gehört zu **{answer}**?",
    ]

    all_categories = [
        COUNTRIES,
        COLORS,
        ANIMALS,
        FOOD,
        DRINKS,
        VEHICLES,
        SPORTS,
        NATURE,
        TECH,
        JOBS,
        OBJECTS,
    ]

    for category in all_categories:

        for emoji, answer in category:

            for template in question_templates:

                wrong = [
                    item
                    for item in category
                    if item[1] != answer
                ]

                if len(wrong) < 3:
                    continue

                selected_wrong = random.sample(wrong, 3)

                choices = selected_wrong + [(emoji, answer)]
                random.shuffle(choices)

                quizzes.append(
                    {
                        "question": template.format(answer=answer),
                        "answers": choices,
                        "correct": answer,
                        "hint": "Vergleiche die vier Emojis und suche das Symbol, das wirklich passt."
                    }
                )

    return quizzes


QUIZZES = build_quizzes()


# =========================================================
# QUIZ-BAG
# =========================================================

def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(range(len(QUIZZES)))
    random.shuffle(quiz_bag)

    print(f"[QUIZ] Neuer Fragen-Pool: {len(quiz_bag)} Fragen")


def get_next_quiz():
    global quiz_bag

    if not quiz_bag:
        refill_quiz_bag()

    index = quiz_bag.pop()
    return QUIZZES[index]


# =========================================================
# QUIZ EMBED
# =========================================================

def create_quiz_embed(quiz):
    embed = discord.Embed(
        title="🧠 Emoji Quiz",
        description=(
            f"### {quiz['question']}\n\n"
            "Wähle die richtige Antwort:"
        ),
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )

    for emoji, answer in quiz["answers"]:
        embed.add_field(
            name=f"{emoji} {answer}",
            value="\u200b",
            inline=True
        )

    embed.set_footer(
        text="💡 Nutze den Hinweis, wenn du nicht weiterkommst."
    )

    return embed


# =========================================================
# QUIZ BUTTONS
# =========================================================

class QuizAnswerButton(discord.ui.Button):

    def __init__(self, position, emoji, label):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=label,
            custom_id=f"quiz_answer_{position}"
        )

        self.position = position

    async def callback(self, interaction: discord.Interaction):

        global current_quiz
        global current_quiz_message

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if interaction.message.id != getattr(
            current_quiz_message,
            "id",
            None
        ):
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        answer = current_quiz["answers"][self.position][1]

        if answer == current_quiz["correct"]:

            user_id = str(interaction.user.id)

            quiz_scores[user_id] = (
                quiz_scores.get(user_id, 0) + 1
            )

            save_data()

            await interaction.response.send_message(
                f"✅ Richtig! **+1 Punkt**\n"
                f"🏆 Du hast jetzt **{quiz_scores[user_id]} Punkte**.",
                ephemeral=True
            )

            channel = interaction.channel

            old_message = current_quiz_message

            current_quiz = None
            current_quiz_message = None

            await safe_delete(old_message)

            await asyncio.sleep(1)

            if channel:
                await send_new_quiz(channel)

        else:

            await interaction.response.send_message(
                "❌ Leider falsch! Versuch es weiter. 😄",
                ephemeral=True
            )


class QuizHintButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji="💡",
            label="Hinweis",
            custom_id="quiz_hint_button"
        )

    async def callback(self, interaction: discord.Interaction):

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
            style=discord.ButtonStyle.danger,
            emoji="⏭️",
            label="Überspringen",
            custom_id="quiz_skip_button"
        )

    async def callback(self, interaction: discord.Interaction):

        global current_quiz
        global current_quiz_message

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )
            return

        channel = interaction.channel
        old_message = current_quiz_message

        current_quiz = None
        current_quiz_message = None

        await interaction.response.send_message(
            "⏭️ Quiz übersprungen!",
            ephemeral=True
        )

        await safe_delete(old_message)

        await asyncio.sleep(1)

        if channel:
            await send_new_quiz(channel)


class QuizView(discord.ui.View):

    def __init__(self, quiz=None):
        super().__init__(timeout=None)

        if quiz is not None:

            for position, (emoji, label) in enumerate(
                quiz["answers"]
            ):
                self.add_item(
                    QuizAnswerButton(
                        position,
                        emoji,
                        label
                    )
                )

        self.add_item(QuizHintButton())
        self.add_item(QuizSkipButton())


# =========================================================
# NEUES QUIZ SENDEN
# =========================================================

async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message

    async with quiz_lock:

        quiz = get_next_quiz()

        current_quiz = quiz

        embed = create_quiz_embed(quiz)

        view = QuizView(quiz)

        try:
            message = await channel.send(
                embed=embed,
                view=view
            )

            current_quiz_message = message

        except Exception as e:
            print(f"[QUIZ] Fehler beim Senden: {e}")


# =========================================================
# QUIZ COMMANDS
# =========================================================

@bot.command(name="quiz")
@commands.has_permissions(manage_messages=True)
async def quiz_command(ctx):

    await send_new_quiz(ctx.channel)


@bot.command(name="punkte")
async def points_command(ctx):

    points = quiz_scores.get(
        str(ctx.author.id),
        0
    )

    await ctx.send(
        f"🏆 {ctx.author.mention}, du hast "
        f"**{points} Punkte**."
    )


@bot.command(name="top")
async def top_command(ctx):

    if not quiz_scores:
        await ctx.send(
            "🏆 Noch niemand hat Punkte gesammelt."
        )
        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 **Emoji-Quiz Rangliste**\n\n"

    for position, (user_id, score) in enumerate(
        sorted_scores,
        start=1
    ):
        user = ctx.guild.get_member(int(user_id))

        if user:
            name = user.display_name
        else:
            name = f"User {user_id}"

        text += (
            f"**{position}.** {name} — "
            f"**{score} Punkte**\n"
        )

    await ctx.send(text)


# =========================================================
# RLP NAMETAGS
# =========================================================

def get_clean_name(member):

    name = member.nick or member.name

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_rlp_nickname(member, force=False):

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    if role not in member.roles:
        return

    user_id = str(member.id)

    if (
        user_id in nametag_removed_users
        and not force
    ):
        return

    if force:
        nametag_removed_users.discard(user_id)
        save_data()

    clean_name = get_clean_name(member)

    nickname = f"{NAMETAG}{clean_name}"

    nickname = nickname[:32]

    if member.nick == nickname:
        return

    try:
        await member.edit(
            nick=nickname,
            reason="RLP Nametag"
        )

    except discord.Forbidden:
        print(
            f"[RLP] Keine Berechtigung für {member}"
        )

    except discord.HTTPException as e:
        print(
            f"[RLP] Discord Fehler bei {member}: {e}"
        )


async def remove_rlp_nickname(member):

    user_id = str(member.id)

    clean_name = get_clean_name(member)

    try:
        await member.edit(
            nick=clean_name[:32],
            reason="RLP vom Benutzer entfernt"
        )

        nametag_removed_users.add(user_id)
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

    role = guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[RLP] Rolle nicht gefunden.")
        return

    print(
        f"[RLP] Aktualisiere {len(role.members)} Mitglieder..."
    )

    for member in role.members:
        await set_rlp_nickname(member)

    print("[RLP] Nametags aktualisiert.")


# =========================================================
# NAMETAG PANEL
# =========================================================

class NicknamePanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="RLP entfernen",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_remove_button"
    )
    async def remove_rlp(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied nicht gefunden.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            NAMETAG_ROLE_ID
        )

        if role is None or role not in member.roles:
            await interaction.response.send_message(
                "❌ Du hast die RLP-Rolle nicht.",
                ephemeral=True
            )
            return

        success = await remove_rlp_nickname(member)

        if success:

            await interaction.response.send_message(
                "✅ Dein RLP wurde entfernt.\n"
                "Dein Name bleibt auch nach einem Bot-Neustart "
                "ohne RLP.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Ich konnte deinen Nicknamen nicht ändern. "
                "Bitte prüfe die Bot-Berechtigungen.",
                ephemeral=True
            )


# =========================================================
# DEVELOPER BEWERBUNG
# =========================================================

DEVELOPER_QUESTIONS = [
    "Wie alt bist du?",
    "Wie lange programmierst du schon?",
    "Welche Programmiersprachen kannst du?",
    "Welche Erfahrungen hast du mit Discord Bots?",
    "Welche Erfahrungen hast du mit Python?",
    "Warum möchtest du Developer werden?",
    "Wie würdest du einen Fehler im Bot suchen?",
    "Wie würdest du mit einem anderen Teammitglied zusammenarbeiten?",
    "Warum sollten wir dich als Developer nehmen?"
]


active_applications = set()


class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        emoji="🛠️",
        style=discord.ButtonStyle.success,
        custom_id="developer_apply_button"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user_id = interaction.user.id

        if user_id in active_applications:
            await interaction.response.send_message(
                "❌ Du hast bereits eine laufende Bewerbung.",
                ephemeral=True
            )
            return

        active_applications.add(user_id)

        await interaction.response.send_message(
            "📩 Ich habe dir eine DM geschickt. "
            "Beantworte dort die Fragen.",
            ephemeral=True
        )

        asyncio.create_task(
            run_developer_application(
                interaction.user
            )
        )


async def run_developer_application(user):

    try:

        await user.send(
            "🛠️ **Developer Bewerbung**\n\n"
            "Wir starten jetzt deine Bewerbung.\n"
            "Bitte beantworte jede Frage einzeln."
        )

        answers = []

        for number, question in enumerate(
            DEVELOPER_QUESTIONS,
            start=1
        ):

            await user.send(
                f"**Frage {number}/{len(DEVELOPER_QUESTIONS)}**\n"
                f"{question}"
            )

            def check(message):
                return (
                    message.author.id == user.id
                    and isinstance(
                        message.channel,
                        discord.DMChannel
                    )
                )

            try:

                message = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=check
                )

            except asyncio.TimeoutError:

                await user.send(
                    "⏰ Bewerbung abgebrochen, "
                    "weil du zu lange nicht geantwortet hast."
                )

                return

            answers.append(message.content)

        await user.send(
            "✅ Deine Bewerbung wurde vollständig "
            "aufgenommen und an das Team weitergeleitet."
        )

        await send_application_review(
            user,
            answers
        )

    except discord.Forbidden:

        print(
            f"[APPLICATION] Keine DM-Berechtigung für {user}"
        )

    finally:

        active_applications.discard(user.id)


async def send_application_review(user, answers):

    channel = bot.get_channel(
        REVIEW_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Neue Developer Bewerbung",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    embed.set_author(
        name=str(user),
        icon_url=user.display_avatar.url
    )

    for number, answer in enumerate(
        answers,
        start=1
    ):

        embed.add_field(
            name=f"Frage {number}",
            value=answer[:1024],
            inline=False
        )

    await channel.send(
        embed=embed
    )


async def cleanup_panel_messages(
    channel,
    title
):

    if channel is None:
        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author.id == bot.user.id
                and message.embeds
                and message.embeds[0].title == title
            ):

                await safe_delete(message)

    except Exception as e:
        print(
            f"[PANEL] Cleanup Fehler: {e}"
        )


async def send_nickname_panel():

    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:
        return

    await cleanup_panel_messages(
        channel,
        "🏷️ Nickname ändern"
    )

    embed = discord.Embed(
        title="🏷️ Nickname ändern",
        description=(
            "### 🪪 Nametag-System\n\n"
            "Du hast die Möglichkeit, dein **RLP** "
            "vor deinem Namen zu entfernen.\n\n"
            "🏷️ **Aktuell:** `RLP DeinName`\n\n"
            "Wenn du auf **RLP entfernen** klickst, "
            "wird dein Name ohne RLP gespeichert.\n\n"
            "🔄 Auch nach einem Bot-Neustart bleibt "
            "deine Auswahl erhalten.\n\n"
            "⚠️ Wenn dir die RLP-Rolle später **neu gegeben** "
            "wird, wird RLP wieder automatisch gesetzt."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )


async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    await cleanup_panel_messages(
        channel,
        "🛠️ Developer Bewerbung"
    )

    embed = discord.Embed(
        title="🛠️ Developer Bewerbung",
        description=(
            "Du möchtest unser Development-Team unterstützen?\n\n"
            "Klicke auf den Button unten und starte "
            "deine Bewerbung.\n\n"
            "📩 Die Bewerbung findet per DM statt.\n"
            "⏱️ Für jede Frage hast du 5 Minuten Zeit."
        ),
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# =========================================================
# BOT KLASSE
# =========================================================

class RLPBot(commands.Bot):

    async def setup_hook(self):

        load_data()

        self.add_view(
            NicknamePanelView()
        )

        self.add_view(
            DeveloperApplicationView()
        )

        # Für die persistenten Quiz-Buttons
        self.add_view(
            QuizView()
        )


# =========================================================
# BOT ERSTELLEN
# =========================================================

bot = RLPBot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global startup_finished

    print(
        f"✅ Bot online als {bot.user}"
    )

    if startup_finished:
        return

    startup_finished = True

    refill_quiz_bag()

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        print("[BOT] Server nicht gefunden.")
        return

    # -----------------------------------------------------
    # RLP NAMETAGS
    # -----------------------------------------------------

    await update_all_rlp_nicknames()

    # -----------------------------------------------------
    # QUIZ
    # -----------------------------------------------------

    quiz_channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel:

        # Alte Bot-Quiznachrichten entfernen
        try:

            async for message in quiz_channel.history(
                limit=100
            ):

                if (
                    message.author.id == bot.user.id
                    and message.embeds
                    and message.embeds[0].title == "🧠 Emoji Quiz"
                ):
                    await safe_delete(message)

        except Exception as e:

            print(
                f"[QUIZ] Cleanup Fehler: {e}"
            )

        await send_new_quiz(
            quiz_channel
        )

    # -----------------------------------------------------
    # PANELS
    # -----------------------------------------------------

    await send_nickname_panel()

    await send_application_panel()

    print(
        f"🧠 Emoji Quiz geladen: {len(QUIZZES)} Fragen"
    )


# =========================================================
# MITGLIED BEITRITT
# =========================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    await set_rlp_nickname(
        member,
        force=True
    )


# =========================================================
# RLP ROLLE WIRD VERGEBEN
# =========================================================

@bot.event
async def on_member_update(before, after):

    before_role = (
        before.guild.get_role(
            NAMETAG_ROLE_ID
        )
    )

    if before_role is None:
        return

    had_role_before = (
        before_role in before.roles
    )

    has_role_now = (
        before_role in after.roles
    )

    # Rolle wurde neu gegeben
    if not had_role_before and has_role_now:

        await set_rlp_nickname(
            after,
            force=True
        )


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    await bot.process_commands(message)


# =========================================================
# COMMAND FEHLER
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

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ Dafür hast du keine Berechtigung."
        )

        return

    print(
        f"[COMMAND ERROR] {error}"
    )


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.environ.get(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


# =========================================================
# START
# =========================================================

bot.run(TOKEN)
