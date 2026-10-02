import os
import json
import random
import asyncio
import re
from datetime import datetime, timezone

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

MAX_NICKNAME_LENGTH = 32


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
quiz_answer_lock = asyncio.Lock()

startup_finished = False

active_applications = set()


# =========================================================
# DATEN LADEN
# =========================================================

def load_data():
    global nametag_removed_users
    global quiz_scores

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        nametag_removed_users = {
            str(user_id)
            for user_id in data.get(
                "nametag_removed_users",
                []
            )
        }

        quiz_scores = {
            str(user_id): int(score)
            for user_id, score in data.get(
                "quiz_scores",
                {}
            ).items()
        }

        print(
            f"[DATA] {len(nametag_removed_users)} "
            f"RLP-Ausnahmen geladen."
        )

        print(
            f"[DATA] {len(quiz_scores)} "
            f"Quiz-Spieler geladen."
        )

    except FileNotFoundError:

        nametag_removed_users = set()
        quiz_scores = {}

        print(
            "[DATA] Keine gespeicherten Daten gefunden. "
            "Neue Datei wird erstellt."
        )

    except (json.JSONDecodeError, ValueError) as error:

        nametag_removed_users = set()
        quiz_scores = {}

        print(
            f"[DATA] Fehler beim Laden der Daten: {error}"
        )


# =========================================================
# DATEN SPEICHERN
# =========================================================

def save_data():

    data = {
        "nametag_removed_users": list(
            nametag_removed_users
        ),
        "quiz_scores": quiz_scores
    }

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            f"[DATA] Fehler beim Speichern: {error}"
        )


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def now_utc():
    return datetime.now(timezone.utc)


def normalize(text):
    return re.sub(
        r"\s+",
        " ",
        text.strip()
    ).lower()


async def safe_delete(message):

    if message is None:
        return

    try:
        await message.delete()

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


def get_member_display_name(member):

    return (
        member.display_name
        if member
        else "Unbekannter Benutzer"
    )


# =========================================================
# =========================================================
#                         EMOJI QUIZ
# =========================================================
# =========================================================


# =========================================================
# LÄNDER
# =========================================================

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
    ("🇷🇺", "Russland"),
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
    ("🇩🇿", "Algerien"),
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
    ("🇵🇭", "Philippinen"),
]


# =========================================================
# FARBEN
# =========================================================

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


# =========================================================
# TIERE
# =========================================================

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
    ("🦍", "Gorilla"),
    ("🐆", "Leopard"),
    ("🦌", "Hirsch"),
    ("🐑", "Schaf"),
    ("🐐", "Ziege"),
    ("🐕", "Hund"),
    ("🐈", "Katze"),
]


# =========================================================
# ESSEN
# =========================================================

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
    ("🥪", "Sandwich"),
    ("🌯", "Wrap"),
    ("🥓", "Speck"),
    ("🌽", "Mais"),
]


# =========================================================
# GETRÄNKE
# =========================================================

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


# =========================================================
# FAHRZEUGE
# =========================================================

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
    ("🚀", "Rakete"),
    ("🚂", "Dampflok"),
]


# =========================================================
# SPORT
# =========================================================

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
    ("🏹", "Bogenschießen"),
    ("⛳", "Golf"),
    ("🥌", "Curling"),
]


# =========================================================
# NATUR
# =========================================================

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
    ("🌪️", "Tornado"),
    ("🌌", "Sternenhimmel"),
]


# =========================================================
# TECHNIK
# =========================================================

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
    ("📻", "Radio"),
    ("🎮", "Spielekonsole"),
    ("🛰️", "Satellit"),
]


# =========================================================
# BERUFE
# =========================================================

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
    ("👨‍🎨", "Künstler"),
    ("🧑‍🔬", "Wissenschaftler"),
    ("👨‍🌾", "Landwirt"),
]


# =========================================================
# GEGENSTÄNDE
# =========================================================

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
    ("📦", "Paket"),
    ("🪥", "Zahnbürste"),
    ("🧴", "Flasche"),
    ("🕶️", "Sonnenbrille"),
]


# =========================================================
# QUIZ-ANTWORTEN
# =========================================================

def get_unique_labels(pool):

    result = []
    seen = set()

    for emoji, label in pool:

        if label in seen:
            continue

        seen.add(label)
        result.append(
            (emoji, label)
        )

    return result


def make_options(correct, pool, amount=4):

    unique_pool = get_unique_labels(pool)

    wrong = [
        item
        for item in unique_pool
        if item[1] != correct
    ]

    if len(wrong) < amount - 1:
        return []

    selected_wrong = random.sample(
        wrong,
        amount - 1
    )

    selected = selected_wrong + [
        next(
            item
            for item in unique_pool
            if item[1] == correct
        )
    ]

    random.shuffle(selected)

    return selected


def create_quiz(
    question,
    correct,
    pool,
    hint
):

    options = make_options(
        correct,
        pool
    )

    if len(options) != 4:
        return None

    return {
        "question": question,
        "answers": options,
        "correct": correct,
        "hint": hint
    }


# =========================================================
# QUIZ-POOL ERSTELLEN
# =========================================================

def build_quizzes():

    quizzes = []

    # -----------------------------------------------------
    # Kategorien
    # -----------------------------------------------------

    category_data = [
        (
            COUNTRIES,
            "🌍 Welche Flagge gehört zu **{answer}**?",
            "Schau dir die Flaggenfarben und das Muster genau an."
        ),
        (
            COLORS,
            "🎨 Welche Farbe wird durch {emoji} dargestellt?",
            "Überlege, welche Farbe das Emoji zeigt."
        ),
        (
            ANIMALS,
            "🐾 Welches Tier wird durch {emoji} dargestellt?",
            "Achte auf die typische Darstellung des Tieres."
        ),
        (
            FOOD,
            "🍽️ Was wird durch {emoji} dargestellt?",
            "Überlege, welches Essen das Emoji zeigt."
        ),
        (
            DRINKS,
            "🥤 Welches Getränk wird durch {emoji} dargestellt?",
            "Achte auf die Form des Getränkesymbols."
        ),
        (
            VEHICLES,
            "🚗 Welches Fahrzeug wird durch {emoji} dargestellt?",
            "Überlege, welches Verkehrsmittel du siehst."
        ),
        (
            SPORTS,
            "🏆 Welche Sportart wird durch {emoji} dargestellt?",
            "Achte auf das Sportgerät oder die Bewegung."
        ),
        (
            NATURE,
            "🌿 Was wird durch {emoji} dargestellt?",
            "Überlege, was du in der Natur findest."
        ),
        (
            TECH,
            "💻 Welches technische Gerät wird durch {emoji} dargestellt?",
            "Achte auf das Gerät oder technische Zubehör."
        ),
        (
            JOBS,
            "👤 Welcher Beruf wird durch {emoji} dargestellt?",
            "Überlege, welcher Beruf zu dem Emoji passt."
        ),
        (
            OBJECTS,
            "🔎 Welcher Gegenstand wird durch {emoji} dargestellt?",
            "Erkenne den Gegenstand anhand seiner Darstellung."
        ),
    ]

    # -----------------------------------------------------
    # Standard-Fragen
    # -----------------------------------------------------

    for category, template, hint in category_data:

        for emoji, answer in category:

            question = template.format(
                emoji=emoji,
                answer=answer
            )

            quiz = create_quiz(
                question,
                answer,
                category,
                hint
            )

            if quiz:
                quizzes.append(quiz)

    # -----------------------------------------------------
    # Mehrere alternative Fragestellungen
    # -----------------------------------------------------

    templates = [
        "🔎 Welches Emoji passt zu **{answer}**?",
        "🧠 Welches Symbol steht für **{answer}**?",
        "🎯 Welches Emoji beschreibt **{answer}**?",
        "❓ Welches dieser Emojis gehört zu **{answer}**?",
        "🧐 Erkennst du **{answer}** anhand des passenden Emojis?",
        "🎲 Finde das Emoji für **{answer}**!",
        "✨ Welches Symbol gehört zu **{answer}**?",
        "🏆 Wähle das richtige Emoji für **{answer}**.",
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

        unique_category = get_unique_labels(
            category
        )

        for emoji, answer in unique_category:

            for template in templates:

                quiz = create_quiz(
                    template.format(
                        answer=answer
                    ),
                    answer,
                    unique_category,
                    "Vergleiche alle vier Emojis miteinander."
                )

                if quiz:
                    quizzes.append(quiz)

    # -----------------------------------------------------
    # Emoji-Kombinationen
    # -----------------------------------------------------

    combination_quizzes = [
        (
            "🇩🇪🍺",
            "Deutschland",
            [
                "Deutschland",
                "Frankreich",
                "Italien",
                "Spanien"
            ]
        ),
        (
            "🇮🇹🍕",
            "Italien",
            [
                "Italien",
                "Japan",
                "Mexiko",
                "Griechenland"
            ]
        ),
        (
            "🇯🇵🍣",
            "Japan",
            [
                "Japan",
                "China",
                "Südkorea",
                "Thailand"
            ]
        ),
        (
            "🇲🇽🌮",
            "Mexiko",
            [
                "Mexiko",
                "Brasilien",
                "Spanien",
                "Portugal"
            ]
        ),
        (
            "🇺🇸🍔",
            "USA",
            [
                "USA",
                "Kanada",
                "Australien",
                "Mexiko"
            ]
        ),
        (
            "🇫🇷🥐",
            "Frankreich",
            [
                "Frankreich",
                "Belgien",
                "Deutschland",
                "Schweiz"
            ]
        ),
        (
            "🇪🇸💃",
            "Spanien",
            [
                "Spanien",
                "Portugal",
                "Italien",
                "Brasilien"
            ]
        ),
        (
            "🇬🇧☕",
            "Vereinigtes Königreich",
            [
                "Vereinigtes Königreich",
                "Irland",
                "USA",
                "Kanada"
            ]
        ),
        (
            "🇦🇺🦘",
            "Australien",
            [
                "Australien",
                "Neuseeland",
                "Südafrika",
                "Indonesien"
            ]
        ),
        (
            "🇪🇬🐪",
            "Ägypten",
            [
                "Ägypten",
                "Marokko",
                "Tunesien",
                "Saudi-Arabien"
            ]
        ),
        (
            "🇨🇳🐼",
            "China",
            [
                "China",
                "Japan",
                "Südkorea",
                "Vietnam"
            ]
        ),
        (
            "🇮🇪🍀",
            "Irland",
            [
                "Irland",
                "Island",
                "Schottland",
                "Kanada"
            ]
        ),
        (
            "🇬🇷🏛️",
            "Griechenland",
            [
                "Griechenland",
                "Italien",
                "Türkei",
                "Spanien"
            ]
        ),
        (
            "🇨🇦🍁",
            "Kanada",
            [
                "Kanada",
                "USA",
                "Australien",
                "Neuseeland"
            ]
        ),
    ]

    for emoji_text, correct, options in combination_quizzes:

        answers = []

        for country in options:

            flag = next(
                (
                    emoji
                    for emoji, name in COUNTRIES
                    if name == country
                ),
                "🌍"
            )

            answers.append(
                (flag, country)
            )

        quizzes.append(
            {
                "question": (
                    f"🧩 Welche Verbindung passt "
                    f"am besten zu:\n\n"
                    f"**{emoji_text}**"
                ),
                "answers": answers,
                "correct": correct,
                "hint": (
                    "Die Emojis geben dir gemeinsam "
                    "einen Hinweis auf das gesuchte Land."
                )
            }
        )

    # -----------------------------------------------------
    # Rechenfragen
    # -----------------------------------------------------

    math_quizzes = [
        ("🍎 + 🍎", "2", ["1", "2", "3", "4"]),
        ("🍎🍎 + 🍎", "3", ["2", "3", "4", "5"]),
        ("⭐⭐ + ⭐⭐", "4", ["2", "3", "4", "5"]),
        ("🐶🐶🐶 - 🐶", "2", ["1", "2", "3", "4"]),
        ("🍕🍕🍕 + 🍕", "4", ["2", "3", "4", "5"]),
        ("🚗🚗 - 🚗", "1", ["0", "1", "2", "3"]),
        ("⚽⚽⚽⚽ - ⚽⚽", "2", ["1", "2", "3", "4"]),
        ("🍎🍎🍎 + 🍎🍎", "5", ["3", "4", "5", "6"]),
        ("⭐ + ⭐⭐", "3", ["2", "3", "4", "5"]),
        ("🐱🐱🐱🐱 ÷ 🐱🐱", "2", ["1", "2", "3", "4"]),
        ("🍕🍕 + 🍕🍕🍕", "5", ["3", "4", "5", "6"]),
        ("⭐⭐⭐⭐ - ⭐", "3", ["2", "3", "4", "5"]),
        ("🐶🐶 + 🐱🐱", "4", ["2", "3", "4", "5"]),
        ("🍎🍎🍎🍎 - 🍎🍎", "2", ["1", "2", "3", "4"]),
    ]

    for expression, correct, options in math_quizzes:

        answers = [
            ("🔢", option)
            for option in options
        ]

        quizzes.append(
            {
                "question": (
                    "🔢 **Emoji-Rechnen**\n\n"
                    f"Wie viel ergibt:\n"
                    f"**{expression}**"
                ),
                "answers": answers,
                "correct": correct,
                "hint": (
                    "Zähle die Symbole und rechne "
                    "Schritt für Schritt."
                )
            }
        )

    # -----------------------------------------------------
    # Rätsel
    # -----------------------------------------------------

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
        ("🥨🇩🇪", "Deutschland"),
        ("🥐🗼🇫🇷", "Frankreich"),
        ("🦘🇦🇺", "Australien"),
        ("🍀🇮🇪", "Irland"),
        ("🗽🇺🇸", "USA"),
        ("🐼🇨🇳", "China"),
        ("🦁🇿🇦", "Südafrika"),
        ("🐪🏜️", "Wüste"),
        ("🌊🏖️", "Strand"),
        ("🌋🔥", "Vulkan"),
        ("🌈☀️🌧️", "Regenbogen"),
        ("🌙🛏️", "Nacht"),
        ("🎄🎁", "Weihnachten"),
        ("🎃👻", "Halloween"),
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
        "Strand",
        "Vulkan",
        "Regenbogen",
        "Weihnachten",
        "Halloween",
    ]

    for emoji_text, correct in riddles:

        available = [
            answer
            for answer in riddle_options
            if answer != correct
        ]

        selected = random.sample(
            available,
            3
        )

        answers = [
            ("❓", answer)
            for answer in selected
        ]

        answers.append(
            ("✅", correct)
        )

        random.shuffle(answers)

        quizzes.append(
            {
                "question": (
                    "🧩 **Emoji-Rätsel**\n\n"
                    f"{emoji_text}\n\n"
                    "Was könnten diese Emojis bedeuten?"
                ),
                "answers": answers,
                "correct": correct,
                "hint": (
                    "Versuche die Emojis als "
                    "gemeinsamen Hinweis zu verstehen."
                )
            }
        )

    # -----------------------------------------------------
    # Alltag
    # -----------------------------------------------------

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
        ("🧹🏠", "Putzen"),
        ("🍽️🧼", "Abwaschen"),
        ("📱⏰", "Wecker"),
        ("🛒🥦", "Einkaufen"),
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
        "Putzen",
        "Abwaschen",
        "Wecker",
    ]

    for emoji_text, correct in everyday:

        others = [
            answer
            for answer in everyday_options
            if answer != correct
        ]

        selected = random.sample(
            others,
            3
        )

        answers = [
            ("❓", answer)
            for answer in selected
        ]

        answers.append(
            ("✅", correct)
        )

        random.shuffle(answers)

        quizzes.append(
            {
                "question": (
                    "🏠 **Alltagsrätsel**\n\n"
                    f"{emoji_text}\n\n"
                    "Was beschreibt diese Kombination?"
                ),
                "answers": answers,
                "correct": correct,
                "hint": (
                    "Überlege, welche Handlung oder "
                    "Situation dargestellt wird."
                )
            }
        )

    # -----------------------------------------------------
    # Finale Bereinigung
    # -----------------------------------------------------

    valid_quizzes = []

    for quiz in quizzes:

        if (
            quiz
            and len(quiz.get("answers", [])) == 4
            and quiz.get("correct")
            and quiz["correct"] in [
                answer
                for _, answer in quiz["answers"]
            ]
        ):
            valid_quizzes.append(quiz)

    random.shuffle(valid_quizzes)

    return valid_quizzes


QUIZZES = build_quizzes()


# =========================================================
# QUIZ-BAG
# =========================================================

def refill_quiz_bag():

    global quiz_bag

    quiz_bag = list(
        range(len(QUIZZES))
    )

    random.shuffle(
        quiz_bag
    )

    print(
        f"[QUIZ] Neuer Fragen-Pool: "
        f"{len(quiz_bag)} Fragen"
    )


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
        title="🧠  EMOJI QUIZ",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"### {quiz['question']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Wähle die richtige Antwort!**\n"
            "💡 Du kannst jederzeit einen Hinweis anfordern."
        ),
        color=discord.Color.blurple(),
        timestamp=now_utc()
    )

    for position, (emoji, answer) in enumerate(
        quiz["answers"],
        start=1
    ):

        embed.add_field(
            name=f"{position}. {emoji} {answer}",
            value="Klicke auf den passenden Button 👇",
            inline=True
        )

    embed.set_footer(
        text="🏆 Für jede richtige Antwort erhältst du 1 Punkt."
    )

    return embed


# =========================================================
# QUIZ BUTTON – ANTWORT
# =========================================================

class QuizAnswerButton(discord.ui.Button):

    def __init__(
        self,
        position,
        emoji,
        label
    ):

        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=label,
            custom_id=f"quiz_answer_{position}"
        )

        self.position = position

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        global current_quiz
        global current_quiz_message

        async with quiz_answer_lock:

            if current_quiz is None:

                await interaction.response.send_message(
                    "❌ Dieses Quiz ist bereits beendet.",
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

            answer = current_quiz[
                "answers"
            ][self.position][1]

            # ---------------------------------------------
            # RICHTIG
            # ---------------------------------------------

            if answer == current_quiz["correct"]:

                user_id = str(
                    interaction.user.id
                )

                quiz_scores[user_id] = (
                    quiz_scores.get(
                        user_id,
                        0
                    ) + 1
                )

                save_data()

                score = quiz_scores[user_id]

                old_message = current_quiz_message
                channel = interaction.channel

                current_quiz = None
                current_quiz_message = None

                await interaction.response.send_message(
                    (
                        "🎉 **RICHTIG!**\n\n"
                        "🏆 **+1 Punkt**\n"
                        f"📊 Dein Punktestand: **{score} Punkte**"
                    ),
                    ephemeral=True
                )

                await safe_delete(
                    old_message
                )

                await asyncio.sleep(1)

                if channel:

                    await send_new_quiz(
                        channel
                    )

            # ---------------------------------------------
            # FALSCH
            # ---------------------------------------------

            else:

                await interaction.response.send_message(
                    (
                        "❌ **Leider falsch!**\n"
                        "😄 Versuch es weiter!"
                    ),
                    ephemeral=True
                )


# =========================================================
# QUIZ BUTTON – HINWEIS
# =========================================================

class QuizHintButton(discord.ui.Button):

    def __init__(self):

        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji="💡",
            label="Hinweis",
            custom_id="quiz_hint_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if current_quiz is None:

            await interaction.response.send_message(
                "❌ Aktuell ist kein Quiz aktiv.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            (
                "💡 **Hinweis**\n\n"
                f"{current_quiz['hint']}"
            ),
            ephemeral=True
        )


# =========================================================
# QUIZ BUTTON – ÜBERSPRINGEN
# =========================================================

class QuizSkipButton(discord.ui.Button):

    def __init__(self):

        super().__init__(
            style=discord.ButtonStyle.danger,
            emoji="⏭️",
            label="Überspringen",
            custom_id="quiz_skip_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        global current_quiz
        global current_quiz_message

        async with quiz_answer_lock:

            if current_quiz is None:

                await interaction.response.send_message(
                    "❌ Aktuell ist kein Quiz aktiv.",
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

            channel = interaction.channel
            old_message = current_quiz_message

            current_quiz = None
            current_quiz_message = None

            await interaction.response.send_message(
                "⏭️ **Quiz übersprungen!**",
                ephemeral=True
            )

            await safe_delete(
                old_message
            )

            await asyncio.sleep(1)

            if channel:

                await send_new_quiz(
                    channel
                )


# =========================================================
# QUIZ VIEW
# =========================================================

class QuizView(discord.ui.View):

    def __init__(
        self,
        quiz=None
    ):

        super().__init__(
            timeout=None
        )

        if quiz is not None:

            for position, (
                emoji,
                label
            ) in enumerate(
                quiz["answers"]
            ):

                self.add_item(
                    QuizAnswerButton(
                        position,
                        emoji,
                        label
                    )
                )

        self.add_item(
            QuizHintButton()
        )

        self.add_item(
            QuizSkipButton()
        )


# =========================================================
# NEUES QUIZ SENDEN
# =========================================================

async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message

    if channel is None:
        return

    async with quiz_lock:

        quiz = get_next_quiz()

        current_quiz = quiz

        embed = create_quiz_embed(
            quiz
        )

        view = QuizView(
            quiz
        )

        try:

            message = await channel.send(
                embed=embed,
                view=view
            )

            current_quiz_message = message

        except discord.Forbidden:

            print(
                "[QUIZ] Keine Berechtigung, "
                "im Quiz-Kanal zu senden."
            )

            current_quiz = None
            current_quiz_message = None

        except discord.HTTPException as error:

            print(
                f"[QUIZ] Discord-Fehler: {error}"
            )

            current_quiz = None
            current_quiz_message = None


# =========================================================
# BOT KLASSE
# =========================================================

class RLPBot(commands.Bot):

    async def setup_hook(self):

        print(
            "[BOT] Lade gespeicherte Daten..."
        )

        load_data()

        # Persistent Nickname Panel
        self.add_view(
            NicknamePanelView()
        )

        # Persistent Developer Panel
        self.add_view(
            DeveloperApplicationView()
        )

        print(
            "[BOT] Persistent Views geladen."
        )


# =========================================================
# BOT ERSTELLEN
# =========================================================

bot = RLPBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# QUIZ COMMANDS
# =========================================================

@bot.command(
    name="quiz"
)
@commands.has_permissions(
    manage_messages=True
)
async def quiz_command(ctx):

    embed = discord.Embed(
        title="🧠 Neues Emoji Quiz",
        description=(
            "🎯 Ein neues Quiz wurde gestartet!\n\n"
            "Viel Erfolg an alle Teilnehmer. 🍀"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )

    await send_new_quiz(
        ctx.channel
    )


@bot.command(
    name="punkte"
)
async def points_command(ctx):

    points = quiz_scores.get(
        str(ctx.author.id),
        0
    )

    embed = discord.Embed(
        title="🏆 Dein Quiz-Punktestand",
        description=(
            f"👤 Spieler: {ctx.author.mention}\n\n"
            f"⭐ Punkte: **{points}**"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="🧠 Spiele weiter, um mehr Punkte zu sammeln!"
    )

    await ctx.send(
        embed=embed
    )


@bot.command(
    name="top"
)
async def top_command(ctx):

    if not quiz_scores:

        embed = discord.Embed(
            title="🏆 Emoji Quiz Rangliste",
            description=(
                "📭 Aktuell hat noch niemand "
                "Punkte gesammelt."
            ),
            color=discord.Color.gold()
        )

        await ctx.send(
            embed=embed
        )

        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    lines = []

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for position, (
        user_id,
        score
    ) in enumerate(
        sorted_scores,
        start=1
    ):

        try:

            member = ctx.guild.get_member(
                int(user_id)
            )

        except ValueError:

            member = None

        if member:

            name = member.display_name

        else:

            name = f"User {user_id}"

        if position <= 3:

            prefix = medals[
                position - 1
            ]

        else:

            prefix = f"**{position}.**"

        lines.append(
            f"{prefix} **{name}** — ⭐ **{score} Punkte**"
        )

    embed = discord.Embed(
        title="🏆 Emoji Quiz Rangliste",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(lines)
            + "\n━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="🎯 Die Rangliste zeigt die besten 10 Spieler."
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# HELP COMMAND
# =========================================================

@bot.command(
    name="help"
)
async def help_command(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot – Hilfe",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Hier findest du alle verfügbaren Befehle.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🧠 Quiz",
        value=(
            "`!quiz` — Neues Quiz starten\n"
            "`!punkte` — Eigenen Punktestand anzeigen\n"
            "`!top` — Top 10 anzeigen"
        ),
        inline=False
    )

    embed.add_field(
        name="🏷️ Nametag",
        value=(
            "Dein **RLP** wird automatisch vor deinen "
            "Namen gesetzt, wenn du die entsprechende "
            "Rolle besitzt."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Developer",
        value=(
            "Die Bewerbung wird über das "
            "Developer-Panel gestartet."
        ),
        inline=False
    )

    embed.set_footer(
        text="🤖 RLP Bot"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# RLP NAMETAGS
# =========================================================

def get_clean_name(member):

    name = member.nick or member.name

    while name.startswith(
        NAMETAG
    ):

        name = name[
            len(NAMETAG):
        ]

    return name.strip()


def create_rlp_nickname(member):

    clean_name = get_clean_name(
        member
    )

    available_length = (
        MAX_NICKNAME_LENGTH
        - len(NAMETAG)
    )

    clean_name = clean_name[
        :available_length
    ]

    return (
        f"{NAMETAG}{clean_name}"
    )


async def set_rlp_nickname(
    member,
    force=False
):

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    role = member.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    if role not in member.roles:
        return

    user_id = str(
        member.id
    )

    # Benutzer hat RLP bewusst entfernt
    if (
        user_id in nametag_removed_users
        and not force
    ):
        return

    # Bei erneuter Vergabe der Rolle
    # wird die Ausnahme gelöscht.
    if force:

        nametag_removed_users.discard(
            user_id
        )

        save_data()

    nickname = create_rlp_nickname(
        member
    )

    if member.nick == nickname:
        return

    try:

        await member.edit(
            nick=nickname,
            reason="RLP Nametag automatisch gesetzt"
        )

        print(
            f"[RLP] Nametag gesetzt: "
            f"{member} -> {nickname}"
        )

    except discord.Forbidden:

        print(
            f"[RLP] Keine Berechtigung für {member}"
        )

    except discord.HTTPException as error:

        print(
            f"[RLP] Discord-Fehler bei {member}: "
            f"{error}"
        )


async def remove_rlp_nickname(member):

    user_id = str(
        member.id
    )

    clean_name = get_clean_name(
        member
    )

    try:

        await member.edit(
            nick=clean_name[:32],
            reason="RLP vom Benutzer entfernt"
        )

        nametag_removed_users.add(
            user_id
        )

        save_data()

        print(
            f"[RLP] RLP entfernt: {member}"
        )

        return True

    except discord.Forbidden:

        print(
            f"[RLP] Keine Berechtigung für {member}"
        )

        return False

    except discord.HTTPException as error:

        print(
            f"[RLP] Fehler beim Entfernen: {error}"
        )

        return False


async def update_all_rlp_nicknames():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        print(
            "[RLP] Server nicht gefunden."
        )

        return

    role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:

        print(
            "[RLP] RLP-Rolle nicht gefunden."
        )

        return

    print(
        f"[RLP] Prüfe {len(role.members)} Mitglieder..."
    )

    for member in role.members:

        await set_rlp_nickname(
            member
        )

        await asyncio.sleep(
            0.15
        )

    print(
        "[RLP] Nametags aktualisiert."
    )


# =========================================================
# NAMETAG PANEL
# =========================================================

class NicknamePanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

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

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Dieser Button funktioniert nur auf dem Server.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            NAMETAG_ROLE_ID
        )

        if (
            role is None
            or role not in member.roles
        ):

            await interaction.response.send_message(
                (
                    "❌ Du besitzt die erforderliche "
                    "RLP-Rolle nicht."
                ),
                ephemeral=True
            )

            return

        success = await remove_rlp_nickname(
            member
        )

        if success:

            embed = discord.Embed(
                title="✅ RLP entfernt",
                description=(
                    "Dein RLP-Nametag wurde erfolgreich entfernt.\n\n"
                    "🏷️ Dein Name bleibt ohne `RLP `.\n"
                    "🔄 Diese Einstellung bleibt auch nach "
                    "einem Bot-Neustart bestehen.\n\n"
                    "♻️ Wenn dir die RLP-Rolle später erneut "
                    "gegeben wird, wird `RLP ` wieder automatisch "
                    "hinzugefügt."
                ),
                color=discord.Color.green()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        else:

            embed = discord.Embed(
                title="❌ Änderung fehlgeschlagen",
                description=(
                    "Ich konnte deinen Nicknamen nicht ändern.\n\n"
                    "Bitte stelle sicher, dass der Bot die "
                    "Berechtigung **Nicknames verwalten** besitzt "
                    "und seine Rolle über deiner Rolle steht."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
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


class DeveloperApplicationView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

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
                (
                    "⏳ Du hast bereits eine laufende "
                    "Developer-Bewerbung."
                ),
                ephemeral=True
            )

            return

        active_applications.add(
            user_id
        )

        embed = discord.Embed(
            title="📩 Bewerbung gestartet",
            description=(
                "Deine Developer-Bewerbung wurde gestartet.\n\n"
                "📬 Ich habe dir eine **DM** geschickt.\n"
                "📝 Beantworte dort die Fragen nacheinander.\n"
                "⏱️ Für jede Frage hast du **5 Minuten** Zeit."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        asyncio.create_task(
            run_developer_application(
                interaction.user
            )
        )


async def run_developer_application(
    user
):

    try:

        await user.send(
            embed=discord.Embed(
                title="🛠️ Developer Bewerbung",
                description=(
                    "Willkommen bei deiner Developer-Bewerbung!\n\n"
                    f"Ich stelle dir insgesamt "
                    f"**{len(DEVELOPER_QUESTIONS)} Fragen**.\n\n"
                    "📝 Bitte beantworte jede Frage einzeln.\n"
                    "⏱️ Für jede Frage hast du 5 Minuten Zeit."
                ),
                color=discord.Color.blurple()
            )
        )

        answers = []

        for number, question in enumerate(
            DEVELOPER_QUESTIONS,
            start=1
        ):

            embed = discord.Embed(
                title=(
                    f"📝 Frage {number}/"
                    f"{len(DEVELOPER_QUESTIONS)}"
                ),
                description=question,
                color=discord.Color.blurple()
            )

            embed.set_footer(
                text="⏱️ Du hast 5 Minuten Zeit zu antworten."
            )

            await user.send(
                embed=embed
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
                    embed=discord.Embed(
                        title="⏰ Bewerbung abgebrochen",
                        description=(
                            "Du hast zu lange nicht geantwortet.\n\n"
                            "Wenn du dich erneut bewerben möchtest, "
                            "kannst du den Button im Developer-Panel "
                            "erneut verwenden."
                        ),
                        color=discord.Color.orange()
                    )
                )

                return

            answers.append(
                message.content
            )

        await user.send(
            embed=discord.Embed(
                title="✅ Bewerbung abgeschickt",
                description=(
                    "Vielen Dank!\n\n"
                    "Deine Developer-Bewerbung wurde "
                    "vollständig aufgenommen und an das "
                    "Team weitergeleitet. 📬\n\n"
                    "Das Team wird deine Bewerbung prüfen."
                ),
                color=discord.Color.green()
            )
        )

        await send_application_review(
            user,
            answers
        )

    except discord.Forbidden:

        print(
            f"[APPLICATION] Keine DM-Berechtigung für {user}"
        )

    except discord.HTTPException as error:

        print(
            f"[APPLICATION] Discord-Fehler bei {user}: "
            f"{error}"
        )

    finally:

        active_applications.discard(
            user.id
        )


async def send_application_review(
    user,
    answers
):

    channel = bot.get_channel(
        REVIEW_CHANNEL_ID
    )

    if channel is None:

        print(
            "[APPLICATION] Review-Kanal nicht gefunden."
        )

        return

    embed = discord.Embed(
        title="🛠️ Neue Developer Bewerbung",
        description=(
            f"👤 Bewerber: **{user}**\n"
            f"🆔 ID: `{user.id}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.green(),
        timestamp=now_utc()
    )

    embed.set_author(
        name=str(user),
        icon_url=user.display_avatar.url
    )

    for number, answer in enumerate(
        answers,
        start=1
    ):

        clean_answer = (
            answer.strip()
            if answer.strip()
            else "Keine Antwort"
        )

        embed.add_field(
            name=f"📝 Frage {number}",
            value=clean_answer[:1024],
            inline=False
        )

    embed.set_footer(
        text="🛠️ Developer Bewerbungs-System"
    )

    try:

        await channel.send(
            embed=embed
        )

    except discord.Forbidden:

        print(
            "[APPLICATION] Keine Berechtigung "
            "im Review-Kanal."
        )

    except discord.HTTPException as error:

        print(
            f"[APPLICATION] Fehler beim Senden: {error}"
        )


# =========================================================
# PANEL CLEANUP
# =========================================================

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
                bot.user
                and message.author.id == bot.user.id
                and message.embeds
                and message.embeds[0].title == title
            ):

                await safe_delete(
                    message
                )

    except discord.Forbidden:

        print(
            f"[PANEL] Keine Berechtigung für "
            f"{channel}."
        )

    except discord.HTTPException as error:

        print(
            f"[PANEL] Discord-Fehler: {error}"
        )

    except Exception as error:

        print(
            f"[PANEL] Cleanup-Fehler: {error}"
        )


# =========================================================
# NAMETAG PANEL SENDEN
# =========================================================

async def send_nickname_panel():

    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:

        print(
            "[PANEL] Nickname-Kanal nicht gefunden."
        )

        return

    await cleanup_panel_messages(
        channel,
        "🏷️ Nickname-System"
    )

    embed = discord.Embed(
        title="🏷️ Nickname-System",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "### 🪪 RLP Nametag\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Wenn du die **RLP-Rolle** besitzt, wird "
            "automatisch folgendes vor deinen Namen gesetzt:\n\n"
            "🏷️ `RLP DeinName`\n\n"
            "### ❌ RLP entfernen\n"
            "Klicke auf den Button unten, wenn du das "
            "RLP vor deinem Namen entfernen möchtest.\n\n"
            "🔒 Deine Auswahl wird gespeichert und bleibt "
            "auch nach einem Bot-Neustart bestehen.\n\n"
            "### ♻️ RLP erneut erhalten\n"
            "Wenn dir die RLP-Rolle später **neu gegeben** "
            "wird, wird `RLP ` automatisch wieder gesetzt."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ℹ️ Wichtig",
        value=(
            "Der Bot verwendet ausschließlich "
            f"`{NAMETAG}` als Nametag."
        ),
        inline=False
    )

    embed.set_footer(
        text="🏷️ RLP Nametag-System"
    )

    try:

        await channel.send(
            embed=embed,
            view=NicknamePanelView()
        )

        print(
            "[PANEL] Nickname-Panel gesendet."
        )

    except discord.Forbidden:

        print(
            "[PANEL] Keine Berechtigung "
            "im Nickname-Kanal."
        )

    except discord.HTTPException as error:

        print(
            f"[PANEL] Fehler beim Senden: {error}"
        )


# =========================================================
# DEVELOPER PANEL SENDEN
# =========================================================

async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:

        print(
            "[PANEL] Bewerbungs-Kanal nicht gefunden."
        )

        return

    await cleanup_panel_messages(
        channel,
        "🛠️ Developer Bewerbung"
    )

    embed = discord.Embed(
        title="🛠️ Developer Bewerbung",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "### 💻 Werde Teil des Development-Teams\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Du interessierst dich für Programmierung "
            "und möchtest unser Team unterstützen?\n\n"
            "Dann kannst du dich über den Button unten "
            "als **Developer** bewerben.\n\n"
            "### 📩 Ablauf\n"
            "1️⃣ Klicke auf **Developer bewerben**\n"
            "2️⃣ Du bekommst eine DM vom Bot\n"
            "3️⃣ Beantworte die Fragen einzeln\n"
            "4️⃣ Die Bewerbung wird an das Team gesendet\n\n"
            "⏱️ Für jede Frage hast du **5 Minuten** Zeit."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="📋 Bewerbung",
        value=(
            f"**{len(DEVELOPER_QUESTIONS)} Fragen** "
            "warten auf dich."
        ),
        inline=True
    )

    embed.add_field(
        name="📬 Kontakt",
        value=(
            "Die Bewerbung findet vollständig "
            "über deine DMs statt."
        ),
        inline=True
    )

    embed.set_footer(
        text="🛠️ Development Team"
    )

    try:

        await channel.send(
            embed=embed,
            view=DeveloperApplicationView()
        )

        print(
            "[PANEL] Developer-Panel gesendet."
        )

    except discord.Forbidden:

        print(
            "[PANEL] Keine Berechtigung "
            "im Bewerbungs-Kanal."
        )

    except discord.HTTPException as error:

        print(
            f"[PANEL] Fehler beim Senden: {error}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    global startup_finished

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        f"🤖 Bot online als {bot.user}"
    )

    print(
        f"🆔 Bot-ID: {bot.user.id}"
    )

    print(
        f"🌐 Server: {len(bot.guilds)}"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    if startup_finished:

        print(
            "[BOT] Startup bereits abgeschlossen."
        )

        return

    try:

        guild = bot.get_guild(
            GUILD_ID
        )

        if guild is None:

            print(
                "❌ [BOT] Server nicht gefunden."
            )

            return

        # -------------------------------------------------
        # QUIZ BAG
        # -------------------------------------------------

        refill_quiz_bag()

        # -------------------------------------------------
        # RLP NAMETAGS
        # -------------------------------------------------

        await update_all_rlp_nicknames()

        # -------------------------------------------------
        # QUIZ KANAL
        # -------------------------------------------------

        quiz_channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if quiz_channel:

            try:

                async for message in quiz_channel.history(
                    limit=100
                ):

                    if (
                        bot.user
                        and message.author.id == bot.user.id
                        and message.embeds
                        and message.embeds[0].title
                        == "🧠  EMOJI QUIZ"
                    ):

                        await safe_delete(
                            message
                        )

            except Exception as error:

                print(
                    f"[QUIZ] Cleanup-Fehler: {error}"
                )

            await send_new_quiz(
                quiz_channel
            )

        else:

            print(
                "⚠️ [QUIZ] Quiz-Kanal nicht gefunden."
            )

        # -------------------------------------------------
        # PANELS
        # -------------------------------------------------

        await send_nickname_panel()

        await send_application_panel()

        startup_finished = True

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "✅ RLP BOT ERFOLGREICH GESTARTET"
        )

        print(
            f"🧠 {len(QUIZZES)} Quiz-Fragen geladen"
        )

        print(
            "🏷️ RLP Nametag-System aktiv"
        )

        print(
            "🛠️ Developer-System aktiv"
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    except Exception as error:

        print(
            "❌ [STARTUP] Fehler:"
        )

        print(
            repr(error)
        )


# =========================================================
# MEMBER JOIN
# =========================================================

@bot.event
async def on_member_join(
    member
):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(
        2
    )

    await set_rlp_nickname(
        member,
        force=True
    )


# =========================================================
# RLP ROLLE WIRD VERGEBEN / ENTFERNT
# =========================================================

@bot.event
async def on_member_update(
    before,
    after
):

    if after.guild.id != GUILD_ID:
        return

    role = after.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    had_role_before = (
        role in before.roles
    )

    has_role_now = (
        role in after.roles
    )

    # -----------------------------------------------------
    # RLP ROLLE NEU VERGEBEN
    # -----------------------------------------------------

    if (
        not had_role_before
        and has_role_now
    ):

        print(
            f"[RLP] Rolle neu vergeben an {after}"
        )

        await set_rlp_nickname(
            after,
            force=True
        )

    # -----------------------------------------------------
    # RLP ROLLE ENTFERNT
    # -----------------------------------------------------

    if (
        had_role_before
        and not has_role_now
    ):

        print(
            f"[RLP] Rolle entfernt bei {after}"
        )


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    await bot.process_commands(
        message
    )


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

        embed = discord.Embed(
            title="❌ Keine Berechtigung",
            description=(
                "Du besitzt nicht die erforderliche "
                "Berechtigung für diesen Befehl."
            ),
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        embed = discord.Embed(
            title="❌ Fehlendes Argument",
            description=(
                "Für diesen Befehl fehlen benötigte "
                "Angaben."
            ),
            color=discord.Color.orange()
        )

        await ctx.send(
            embed=embed
        )

        return

    print(
        f"[COMMAND ERROR] {repr(error)}"
    )


# =========================================================
# TOKEN
# =========================================================

TOKEN = os.environ.get(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN wurde nicht gefunden. "
        "Bitte überprüfe dein GitHub-Secret."
    )


# =========================================================
# BOT STARTEN
# =========================================================

print(
    "🚀 Starte RLP Bot..."
)

bot.run(
    TOKEN
)
