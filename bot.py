import os
import json
import random
import string
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

# DATEN

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

# HILFSFUNKTIONEN

# ============================================================

def now():
return datetime.now(timezone.utc)

def normalize(value):
return " ".join(str(value).strip().lower().split())

def format_datetime(dt):
try:
if isinstance(dt, str):
dt = datetime.fromisoformat(dt)

```
    return dt.astimezone().strftime("%d.%m.%Y %H:%M")
except Exception:
    return "Unbekannt"
```

def format_duration(seconds):
seconds = max(0, int(seconds))

```
minutes, seconds = divmod(seconds, 60)
hours, minutes = divmod(minutes, 60)

if hours:
    return f"{hours} Std. {minutes} Min."

if minutes:
    return f"{minutes} Min. {seconds} Sek."

return f"{seconds} Sek."
```

def generate_case_id():
letters = string.ascii_uppercase

```
return "#S-" + "".join(
    random.choice(letters)
    for _ in range(10)
)
```

def safe_member_name(member):
name = member.display_name

```
while name.startswith(NAMETAG):
    name = name[len(NAMETAG):]

return name.strip()
```

def base_embed(title, description="", color=None):
if color is None:
color = discord.Color.blurple()

```
embed = discord.Embed(
    title=title,
    description=description,
    color=color,
    timestamp=now()
)

embed.set_footer(text="RLP System")

return embed
```

async def safe_delete(message):
try:
await message.delete()
except Exception:
pass

async def clean_bot_panel(channel, title):
if not hasattr(channel, "history"):
return

```
try:
    async for message in channel.history(limit=None):
        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == title
        ):
            await safe_delete(message)
            await asyncio.sleep(0.05)
except Exception as error:
    print(f"[PANEL] Fehler beim Bereinigen: {error}")
```

# ============================================================

# DATENSPEICHER

# ============================================================

def load_data():
global nametag_removed_users
global quiz_scores
global active_team_members
global active_developer_shifts
global developer_tasks

```
if not os.path.exists(DATA_FILE):
    print("[DATA] Keine vorhandene Datenbank gefunden.")
    return

try:
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    nametag_removed_users = {
        int(user_id)
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

    active_team_members = {
        int(user_id)
        for user_id in data.get(
            "active_team_members",
            []
        )
    }

    active_developer_shifts = {
        str(user_id): value
        for user_id, value in data.get(
            "active_developer_shifts",
            {}
        ).items()
    }

    developer_tasks = data.get(
        "developer_tasks",
        []
    )

    print("[DATA] Daten erfolgreich geladen.")

except Exception as error:
    print(f"[DATA] Fehler beim Laden: {error}")
```

def save_data():
try:
data = {
"nametag_removed_users": list(
nametag_removed_users
),
"quiz_scores": quiz_scores,
"active_team_members": list(
active_team_members
),
"active_developer_shifts":
active_developer_shifts,
"developer_tasks":
developer_tasks
}

```
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

except Exception as error:
    print(f"[DATA] Fehler beim Speichern: {error}")
```

# ============================================================

# NAMETAG SYSTEM

# ============================================================

async def set_rlp_nickname(member, force=False):
if not isinstance(member, discord.Member):
return

```
role = member.guild.get_role(NAMETAG_ROLE_ID)

if role is None:
    return

if role not in member.roles:
    return

if (
    member.id in nametag_removed_users
    and not force
):
    return

if force:
    nametag_removed_users.discard(member.id)
    save_data()

clean_name = safe_member_name(member)

nickname = f"{NAMETAG}{clean_name}"

if len(nickname) > 32:
    nickname = nickname[:32]

try:
    if member.nick != nickname:
        await member.edit(
            nick=nickname,
            reason="RLP Nametag System"
        )

except discord.Forbidden:
    print(
        f"[NAMETAG] Keine Rechte für {member}"
    )

except discord.HTTPException as error:
    print(
        f"[NAMETAG] Discord-Fehler: {error}"
    )
```

async def remove_rlp_nickname(member):
clean_name = safe_member_name(member)

```
nametag_removed_users.add(member.id)

save_data()

try:
    await member.edit(
        nick=clean_name,
        reason="RLP Nametag entfernt"
    )

except discord.Forbidden:
    pass

except discord.HTTPException:
    pass
```

async def update_all_rlp_nicknames():
guild = bot.get_guild(GUILD_ID)

```
if guild is None:
    return

role = guild.get_role(NAMETAG_ROLE_ID)

if role is None:
    print(
        "[NAMETAG] RLP-Rolle wurde nicht gefunden."
    )
    return

print(
    f"[NAMETAG] Prüfe {len(role.members)} Mitglieder."
)

for member in role.members:
    await set_rlp_nickname(member)
    await asyncio.sleep(0.05)
```

# ============================================================

# NAMETAG PANEL

# ============================================================

class NicknamePanelView(discord.ui.View):

```
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
    if not isinstance(
        interaction.user,
        discord.Member
    ):
        return

    await remove_rlp_nickname(
        interaction.user
    )

    embed = base_embed(
        "🏷️ Nametag entfernt",
        (
            "Dein **RLP Nametag** wurde erfolgreich entfernt.\n\n"
            "Wenn dir die RLP-Rolle später erneut gegeben wird, "
            "wird das Nametag automatisch wieder gesetzt."
        ),
        discord.Color.green()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )
```

async def send_nickname_panel():
channel = bot.get_channel(
NICKNAME_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "🏷️ Nametag-System"
)

embed = base_embed(
    "🏷️ Nametag-System",
    (
        "Hier kannst du dein **RLP Nametag** verwalten.\n\n"
        "🏷️ **Nametag entfernen**\n"
        "Entfernt `RLP ` aus deinem Namen.\n\n"
        "🔄 **Automatisch**\n"
        "Wenn dir die RLP-Rolle später erneut gegeben "
        "wird, wird das Nametag automatisch wieder gesetzt."
    )
)

await channel.send(
    embed=embed,
    view=NicknamePanelView()
)
```

# ============================================================

# QUIZ DATEN

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
("🇺🇦", "Ukraine"),
("🇮🇳", "Indien"),
("🇿🇦", "Südafrika"),
("🇪🇬", "Ägypten"),
("🇲🇦", "Marokko"),
("🇸🇦", "Saudi-Arabien"),
("🇦🇪", "Vereinigte Arabische Emirate"),
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
("🐮", "Kuh"),
("🐷", "Schwein"),
("🐔", "Huhn"),
("🐧", "Pinguin"),
("🐦", "Vogel"),
("🦆", "Ente"),
("🦅", "Adler"),
("🦉", "Eule"),
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

JOBS = [
("👨‍💻", "Developer"),
("👨‍⚕️", "Arzt"),
("👨‍🚒", "Feuerwehrmann"),
("👮", "Polizist"),
("👨‍🏫", "Lehrer"),
("👨‍🍳", "Koch"),
("👨‍🔧", "Mechaniker"),
("👨‍🎨", "Künstler"),
("👨‍✈️", "Pilot"),
("👨‍🌾", "Landwirt"),
("🧑‍💼", "Manager"),
("🧑‍⚖️", "Richter"),
("🕵️", "Detektiv"),
("🧑‍🚀", "Astronaut"),
("🎤", "Sänger"),
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

def unique_category(category):
result = []
seen = set()

```
for emoji, name in category:
    key = normalize(name)

    if key in seen:
        continue

    seen.add(key)
    result.append((emoji, name))

return result
```

def create_quiz(category_name, category, correct):
wrong_pool = [
item
for item in category
if item != correct
]

```
if len(wrong_pool) < 3:
    return None

wrong = random.sample(
    wrong_pool,
    3
)

options = [
    correct,
    *wrong
]

random.shuffle(options)

return {
    "category": category_name,
    "emoji": correct[0],
    "answer": correct[1],
    "options": options,
    "correct_position": options.index(correct)
}
```

def build_quizzes():
quizzes = []

```
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

for category_name, raw_category in categories:
    category = unique_category(raw_category)

    for correct in category:
        quiz = create_quiz(
            category_name,
            category,
            correct
        )

        if quiz is not None:
            quizzes.append(quiz)

return quizzes
```

QUIZZES = build_quizzes()

def refill_quiz_bag():
global quiz_bag

```
quiz_bag = list(
    range(len(QUIZZES))
)

random.shuffle(quiz_bag)
```

# ============================================================

# QUIZ VIEW

# ============================================================

class QuizAnswerButton(discord.ui.Button):

```
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
        or interaction.message.id
        != current_quiz_message.id
    ):
        await interaction.response.send_message(
            "❌ Dieses Quiz ist nicht mehr aktiv.",
            ephemeral=True
        )
        return

    quiz = current_quiz

    if self.position != quiz["correct_position"]:
        await interaction.response.send_message(
            "❌ Falsch! Versuch es weiter.",
            ephemeral=True
        )
        return

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

    current_quiz = None

    embed = base_embed(
        "✅ Richtige Antwort!",
        (
            f"{interaction.user.mention} "
            "hat die richtige Antwort gewählt.\n\n"
            f"**Antwort:** {quiz['answer']}\n"
            "**+1 Punkt**"
        ),
        discord.Color.green()
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )

    await asyncio.sleep(3)

    if interaction.channel:
        await send_new_quiz(
            interaction.channel
        )
```

class QuizHintButton(discord.ui.Button):

```
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
        (
            f"💡 Kategorie: "
            f"**{current_quiz['category']}**"
        ),
        ephemeral=True
    )
```

class QuizSkipButton(discord.ui.Button):

```
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

    quiz = current_quiz
    current_quiz = None

    await interaction.response.edit_message(
        embed=base_embed(
            "⏭️ Quiz übersprungen",
            (
                f"Die richtige Antwort wäre "
                f"**{quiz['answer']}** gewesen."
            ),
            discord.Color.orange()
        ),
        view=None
    )

    await asyncio.sleep(2)

    if interaction.channel:
        await send_new_quiz(
            interaction.channel
        )
```

class QuizView(discord.ui.View):

```
def __init__(self, quiz=None):
    super().__init__(
        timeout=None
    )

    if quiz is not None:
        for index, option in enumerate(
            quiz["options"]
        ):
            self.add_item(
                QuizAnswerButton(
                    index,
                    option[1]
                )
            )

    self.add_item(
        QuizHintButton()
    )

    self.add_item(
        QuizSkipButton()
    )
```

async def send_new_quiz(channel):
global current_quiz
global current_quiz_message

```
if channel is None:
    return

async with quiz_lock:
    if not quiz_bag:
        refill_quiz_bag()

    if not quiz_bag:
        return

    index = quiz_bag.pop()

    current_quiz = QUIZZES[index]

    quiz = current_quiz

    embed = base_embed(
        "🧩 Emoji-Quiz",
        (
            f"**Kategorie:** {quiz['category']}\n\n"
            "Welcher Begriff gehört zu diesem Emoji?\n\n"
            f"# {quiz['emoji']}"
        )
    )

    view = QuizView(
        quiz
    )

    message = await channel.send(
        embed=embed,
        view=view
    )

    current_quiz_message = message
```

# ============================================================

# BOT KLASSE

# ============================================================

class RLPBot(commands.Bot):

```
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
```

# ============================================================

# BOT ERSTELLEN

# ============================================================

bot = RLPBot(
command_prefix="!",
intents=intents,
help_command=None
)

# ============================================================

# QUIZ COMMANDS

# ============================================================

@bot.command(name="quiz")
async def quiz_command(ctx):

```
if not isinstance(
    ctx.author,
    discord.Member
):
    return

has_role = any(
    role.id == QUIZ_COMMAND_ROLE_ID
    for role in ctx.author.roles
)

if not has_role:
    await ctx.send(
        embed=base_embed(
            "🔒 Keine Berechtigung",
            (
                "Du benötigst die entsprechende "
                "Rolle, um `!quiz` zu verwenden."
            ),
            discord.Color.red()
        ),
        delete_after=5
    )
    return

if ctx.channel.id != QUIZ_CHANNEL_ID:
    await ctx.send(
        embed=base_embed(
            "📍 Falscher Kanal",
            (
                "Der `!quiz`-Command kann nur "
                "im vorgesehenen Quiz-Kanal "
                "verwendet werden."
            ),
            discord.Color.orange()
        ),
        delete_after=5
    )
    return

await send_new_quiz(
    ctx.channel
)
```

@bot.command(name="punkte")
async def punkte_command(ctx):

```
score = quiz_scores.get(
    str(ctx.author.id),
    0
)

await ctx.send(
    embed=base_embed(
        "📊 Dein Punktestand",
        (
            f"👤 **Spieler:** {ctx.author.mention}\n"
            f"🏆 **Punkte:** `{score}`"
        )
    )
)
```

@bot.command(name="top")
async def top_command(ctx):

```
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
    key=lambda item: item[1],
    reverse=True
)

lines = []

for index, (
    user_id,
    score
) in enumerate(
    sorted_scores[:10],
    start=1
):
    member = None

    if ctx.guild:
        try:
            member = ctx.guild.get_member(
                int(user_id)
            )
        except Exception:
            member = None

    if member:
        name = member.display_name
    else:
        name = f"User {user_id}"

    lines.append(
        f"**{index}.** {name} — `{score} Punkte`"
    )

await ctx.send(
    embed=base_embed(
        "🏆 Top 10",
        "\n".join(lines),
        discord.Color.gold()
    )
)
```

# ============================================================

# SUPPORT SYSTEM

# ============================================================

def is_support_staff(member):
if member.id in active_team_members:
return True

```
if member.guild_permissions.administrator:
    return True

if member.guild_permissions.manage_guild:
    return True

return False
```

async def create_support_case(member):
if member.id in active_support_cases:
return

```
active_support_cases[
    member.id
] = {
    "case_id": generate_case_id(),
    "user_id": member.id,
    "started_at": now().isoformat(),
    "supporter_id": None
}

print(
    f"[SUPPORT] Case für {member} erstellt."
)
```

async def assign_supporter(voice_channel):
if voice_channel is None:
return

```
for user_id, case in list(
    active_support_cases.items()
):
    if case.get("supporter_id"):
        continue

    user_member = voice_channel.guild.get_member(
        user_id
    )

    if user_member is None:
        continue

    if user_member not in voice_channel.members:
        continue

    for member in voice_channel.members:
        if member.id == user_id:
            continue

        if member.bot:
            continue

        if is_support_staff(member):
            case["supporter_id"] = member.id

            print(
                f"[SUPPORT] {member} wurde als "
                f"Supporter für {case['case_id']} gesetzt."
            )

            break
```

async def finish_support_case(member):
case = active_support_cases.pop(
member.id,
None
)

```
if case is None:
    return

ended_at = now()

try:
    started_at = datetime.fromisoformat(
        case["started_at"]
    )
except Exception:
    started_at = ended_at

duration = (
    ended_at - started_at
).total_seconds()

supporter_id = case.get(
    "supporter_id"
)

supporter_text = "Nicht festgestellt"

if supporter_id:
    supporter_member = member.guild.get_member(
        int(supporter_id)
    )

    if supporter_member:
        supporter_text = supporter_member.mention

channel = bot.get_channel(
    SUPPORT_LOG_CHANNEL_ID
)

if not isinstance(
    channel,
    discord.TextChannel
):
    print(
        "[SUPPORT] Support-Log-Kanal nicht gefunden."
    )
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
    value=format_datetime(started_at),
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

await channel.send(
    embed=embed
)

print(
    f"[SUPPORT] Case {case['case_id']} abgeschlossen."
)
```

class SupportView(discord.ui.View):

```
def __init__(self):
    super().__init__(
        timeout=None
    )

@discord.ui.button(
    label="Support-Informationen",
    emoji="🎫",
    style=discord.ButtonStyle.primary,
    custom_id="support_info"
)
async def support_info(
    self,
    interaction,
    button
):
    embed = base_embed(
        "🎫 Support-System",
        (
            "Willkommen im offiziellen Support-System.\n\n"
            "📞 **Support starten**\n"
            "Betritt den vorgesehenen Support-Call.\n\n"
            "🆔 **CaseID**\n"
            "Für deinen Fall wird automatisch eine eindeutige "
            "CaseID erstellt.\n\n"
            "🛠️ **Supporter**\n"
            "Ein eingetragener Teamler oder berechtigter "
            "Supporter wird automatisch erfasst.\n\n"
            "⏱️ **Dauer**\n"
            "Die Zeit im Support-Call wird automatisch gemessen.\n\n"
            "📋 **Abschluss**\n"
            "Beim Verlassen wird ein Abschlussbericht erstellt."
        )
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )
```

async def send_support_panel():
channel = bot.get_channel(
SUPPORT_LOG_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "🎫 Support-System"
)

embed = base_embed(
    "🎫 Support-System",
    (
        "Willkommen im offiziellen Support-System.\n\n"
        "📞 **Support starten**\n"
        "Betritt den Support-Call:\n"
        f"<#{SUPPORT_VOICE_CHANNEL_ID}>\n\n"
        "🆔 **Automatische CaseID**\n"
        "Jeder Support-Fall erhält eine eindeutige CaseID.\n\n"
        "🛠️ **Supporter-Erkennung**\n"
        "Eingetragene Teamler und berechtigte Teammitglieder "
        "werden automatisch erkannt.\n\n"
        "⏱️ **Automatische Dauer**\n"
        "Die Supportdauer wird automatisch erfasst.\n\n"
        "📋 **Abschlussbericht**\n"
        "Nach dem Verlassen wird ein professioneller "
        "Abschlussbericht erstellt."
    )
)

await channel.send(
    embed=embed,
    view=SupportView()
)
```

# ============================================================

# TEAMLER REGISTRIERUNG

# ============================================================

class TeamRegistrationView(discord.ui.View):

```
def __init__(self):
    super().__init__(
        timeout=None
    )

@discord.ui.button(
    label="Eintragen",
    emoji="🟢",
    style=discord.ButtonStyle.success,
    custom_id="team_register"
)
async def register(
    self,
    interaction,
    button
):
    active_team_members.add(
        interaction.user.id
    )

    save_data()

    await interaction.response.send_message(
        embed=base_embed(
            "🟢 Eingetragen",
            (
                "Du bist jetzt als verfügbarer "
                "Teamler eingetragen.\n\n"
                "Du kannst nun automatisch als "
                "Supporter erkannt werden."
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
    interaction,
    button
):
    active_team_members.discard(
        interaction.user.id
    )

    save_data()

    await interaction.response.send_message(
        embed=base_embed(
            "🔴 Ausgetragen",
            (
                "Du wurdest erfolgreich "
                "ausgetragen."
            ),
            discord.Color.red()
        ),
        ephemeral=True
    )

@discord.ui.button(
    label="Team anzeigen",
    emoji="👥",
    style=discord.ButtonStyle.secondary,
    custom_id="team_list"
)
async def list_team(
    self,
    interaction,
    button
):
    guild = interaction.guild

    if guild is None:
        return

    members = []

    for user_id in active_team_members:
        member = guild.get_member(
            user_id
        )

        if member:
            members.append(
                f"🟢 {member.mention}"
            )

    if not members:
        description = (
            "Aktuell ist kein Teamler "
            "als verfügbar eingetragen."
        )
    else:
        description = "\n".join(
            members[:25]
        )

    await interaction.response.send_message(
        embed=base_embed(
            "👥 Verfügbare Teamler",
            description
        ),
        ephemeral=True
    )
```

async def send_team_registration_panel():
channel = bot.get_channel(
TEAM_REGISTER_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "👥 Teamler-System"
)

embed = base_embed(
    "👥 Teamler-System",
    (
        "Hier kannst du deinen Team-Status selbst verwalten.\n\n"
        "🟢 **Eintragen**\n"
        "Du bist aktuell verfügbar.\n\n"
        "🔴 **Austragen**\n"
        "Du bist aktuell nicht verfügbar.\n\n"
        "👥 **Team anzeigen**\n"
        "Zeigt die aktuell eingetragenen Teamler.\n\n"
        "Teamler, die eingetragen sind, können vom "
        "Support-System automatisch als Supporter erkannt werden."
    )
)

await channel.send(
    embed=embed,
    view=TeamRegistrationView()
)
```

# ============================================================

# DEVELOPER SCHICHT

# ============================================================

class DeveloperShiftView(discord.ui.View):

```
def __init__(self):
    super().__init__(
        timeout=None
    )

@discord.ui.button(
    label="Schicht starten",
    emoji="🟢",
    style=discord.ButtonStyle.success,
    custom_id="developer_shift_start"
)
async def start_shift(
    self,
    interaction,
    button
):
    user_id = str(
        interaction.user.id
    )

    if user_id in active_developer_shifts:
        await interaction.response.send_message(
            "⚠️ Du hast bereits eine aktive Developer-Schicht.",
            ephemeral=True
        )
        return

    active_developer_shifts[
        user_id
    ] = {
        "started_at": now().isoformat()
    }

    save_data()

    await interaction.response.send_message(
        embed=base_embed(
            "🟢 Schicht gestartet",
            (
                f"{interaction.user.mention}\n\n"
                "Deine Developer-Schicht wurde "
                "erfolgreich gestartet."
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
    interaction,
    button
):
    user_id = str(
        interaction.user.id
    )

    shift = active_developer_shifts.get(
        user_id
    )

    if not shift:
        await interaction.response.send_message(
            "⚠️ Du hast aktuell keine aktive Schicht.",
            ephemeral=True
        )
        return

    try:
        started_at = datetime.fromisoformat(
            shift["started_at"]
        )
    except Exception:
        started_at = now()

    duration = (
        now() - started_at
    ).total_seconds()

    del active_developer_shifts[
        user_id
    ]

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
```

async def send_developer_shift_panel():
channel = bot.get_channel(
DEVELOPER_SHIFT_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "💻 Developer-Schichtsystem"
)

embed = base_embed(
    "💻 Developer-Schichtsystem",
    (
        "Verwalte hier deine Developer-Schicht.\n\n"
        "🟢 **Schicht starten**\n"
        "Startet deine Arbeitszeit.\n\n"
        "🔴 **Schicht beenden**\n"
        "Beendet deine Arbeitszeit und zeigt die Dauer an."
    )
)

await channel.send(
    embed=embed,
    view=DeveloperShiftView()
)
```

# ============================================================

# DEVELOPER AUFGABEN

# ============================================================

def get_next_task_id():
if not developer_tasks:
return 1

```
ids = []

for task in developer_tasks:
    try:
        ids.append(
            int(task.get("id", 0))
        )
    except Exception:
        pass

return max(ids, default=0) + 1
```

def find_task(task_id):
for task in developer_tasks:
try:
if int(task.get("id", 0)) == task_id:
return task
except Exception:
continue

```
return None
```

class DeveloperTaskModal(
discord.ui.Modal,
title="Neue Developer-Aufgabe"
):

```
task = discord.ui.TextInput(
    label="Aufgabe",
    placeholder="Beschreibe die Aufgabe...",
    style=discord.TextStyle.paragraph,
    max_length=1000,
    required=True
)

async def on_submit(self, interaction):
    task_id = get_next_task_id()

    developer_tasks.append(
        {
            "id": task_id,
            "text": str(self.task),
            "creator_id": interaction.user.id,
            "completed": False,
            "claimed_by": None,
            "created_at": now().isoformat()
        }
    )

    save_data()

    await interaction.response.send_message(
        embed=base_embed(
            "📋 Aufgabe erstellt",
            (
                f"**Aufgabe #{task_id}** wurde "
                "erfolgreich erstellt."
            ),
            discord.Color.green()
        ),
        ephemeral=True
    )

    await send_developer_tasks()
```

class DeveloperTaskView(discord.ui.View):

```
def __init__(self):
    super().__init__(
        timeout=None
    )

@discord.ui.button(
    label="Aufgabe erstellen",
    emoji="➕",
    style=discord.ButtonStyle.success,
    custom_id="developer_task_create"
)
async def create_task(
    self,
    interaction,
    button
):
    await interaction.response.send_modal(
        DeveloperTaskModal()
    )

@discord.ui.button(
    label="Hilfe",
    emoji="❓",
    style=discord.ButtonStyle.secondary,
    custom_id="developer_task_help"
)
async def task_help(
    self,
    interaction,
    button
):
    await interaction.response.send_message(
        embed=base_embed(
            "💻 Developer-Aufgaben",
            (
                "➕ Aufgabe erstellen — Button verwenden\n\n"
                "📌 `!devclaim <ID>` — Aufgabe übernehmen\n\n"
                "✅ `!devdone <ID>` — Aufgabe abschließen\n\n"
                "🗑️ `!devdelete <ID>` — Aufgabe löschen "
                "(Administrator)"
            )
        ),
        ephemeral=True
    )
```

async def send_developer_tasks():
channel = bot.get_channel(
DEVELOPER_TASK_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "💻 Developer-Aufgaben"
)

embed = base_embed(
    "💻 Developer-Aufgaben",
    (
        "Hier werden die aktuellen Developer-Aufgaben "
        "übersichtlich verwaltet.\n\n"
        "➕ **Aufgabe erstellen** — Button\n"
        "📌 `!devclaim <ID>` — Aufgabe übernehmen\n"
        "✅ `!devdone <ID>` — Aufgabe abschließen\n"
        "🗑️ `!devdelete <ID>` — Aufgabe löschen"
    )
)

open_tasks = [
    task
    for task in developer_tasks
    if not task.get("completed", False)
]

completed_tasks = [
    task
    for task in developer_tasks
    if task.get("completed", False)
]

if not developer_tasks:
    embed.add_field(
        name="📋 Keine Aufgaben",
        value=(
            "Aktuell sind keine Developer-Aufgaben vorhanden."
        ),
        inline=False
    )

else:
    for task in developer_tasks[-15:]:
        if task.get("completed"):
            status = "✅ Erledigt"
        elif task.get("claimed_by"):
            status = "🟡 In Bearbeitung"
        else:
            status = "⚪ Offen"

        claimed_by = task.get(
            "claimed_by"
        )

        if claimed_by:
            claimed = f"<@{claimed_by}>"
        else:
            claimed = "Niemand"

        text = str(
            task.get(
                "text",
                "Keine Beschreibung"
            )
        )

        embed.add_field(
            name=f"#{task.get('id')} • {status}",
            value=(
                f"{text}\n"
                f"👤 Bearbeiter: {claimed}"
            )[:1024],
            inline=False
        )

embed.add_field(
    name="📊 Übersicht",
    value=(
        f"⚪ Offen: `{len(open_tasks)}`\n"
        f"✅ Erledigt: `{len(completed_tasks)}`"
    ),
    inline=False
)

await channel.send(
    embed=embed,
    view=DeveloperTaskView()
)
```

@bot.command(name="devtask")
@commands.has_permissions(manage_guild=True)
async def devtask_command(
ctx,
*,
task: str
):
task = task.strip()

```
if not task:
    await ctx.send(
        "❌ Bitte gib eine Aufgabe an.",
        delete_after=5
    )
    return

task_id = get_next_task_id()

developer_tasks.append(
    {
        "id": task_id,
        "text": task,
        "creator_id": ctx.author.id,
        "completed": False,
        "claimed_by": None,
        "created_at": now().isoformat()
    }
)

save_data()

await send_developer_tasks()

await ctx.send(
    embed=base_embed(
        "📋 Aufgabe erstellt",
        (
            f"**Aufgabe #{task_id}** wurde erstellt."
        ),
        discord.Color.green()
    ),
    delete_after=5
)

await safe_delete(ctx.message)
```

@bot.command(name="devclaim")
async def devclaim_command(
ctx,
task_id: int
):
task = find_task(task_id)

```
if task is None:
    await ctx.send(
        "❌ Diese Aufgabe wurde nicht gefunden.",
        delete_after=5
    )
    return

if task.get("completed"):
    await ctx.send(
        "⚠️ Diese Aufgabe ist bereits abgeschlossen.",
        delete_after=5
    )
    return

if task.get("claimed_by"):
    await ctx.send(
        (
            "⚠️ Diese Aufgabe wird bereits von "
            f"<@{task['claimed_by']}> bearbeitet."
        ),
        delete_after=5
    )
    return

task["claimed_by"] = ctx.author.id

save_data()

await send_developer_tasks()

await ctx.send(
    embed=base_embed(
        "📌 Aufgabe übernommen",
        (
            f"{ctx.author.mention} hat "
            f"**Aufgabe #{task_id}** übernommen."
        ),
        discord.Color.blurple()
    ),
    delete_after=5
)

await safe_delete(ctx.message)
```

@bot.command(name="devdone")
async def devdone_command(
ctx,
task_id: int
):
task = find_task(task_id)

```
if task is None:
    await ctx.send(
        "❌ Diese Aufgabe wurde nicht gefunden.",
        delete_after=5
    )
    return

if task.get("completed"):
    await ctx.send(
        "⚠️ Diese Aufgabe ist bereits abgeschlossen.",
        delete_after=5
    )
    return

claimed_by = task.get(
    "claimed_by"
)

if (
    not ctx.author.guild_permissions.manage_guild
    and claimed_by != ctx.author.id
):
    await ctx.send(
        (
            "🔒 Du kannst diese Aufgabe nicht "
            "abschließen. Übernimm sie zuerst."
        ),
        delete_after=5
    )
    return

task["completed"] = True

save_data()

await send_developer_tasks()

await ctx.send(
    embed=base_embed(
        "✅ Aufgabe abgeschlossen",
        (
            f"**Aufgabe #{task_id}** wurde von "
            f"{ctx.author.mention} abgeschlossen."
        ),
        discord.Color.green()
    ),
    delete_after=5
)

await safe_delete(ctx.message)
```

@bot.command(name="devdelete")
@commands.has_permissions(manage_guild=True)
async def devdelete_command(
ctx,
task_id: int
):
task = find_task(task_id)

```
if task is None:
    await ctx.send(
        "❌ Diese Aufgabe wurde nicht gefunden.",
        delete_after=5
    )
    return

developer_tasks.remove(task)

save_data()

await send_developer_tasks()

await ctx.send(
    embed=base_embed(
        "🗑️ Aufgabe gelöscht",
        f"**Aufgabe #{task_id}** wurde gelöscht.",
        discord.Color.red()
    ),
    delete_after=5
)

await safe_delete(ctx.message)
```

# ============================================================

# DEVELOPER BEWERBUNG

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

```
def __init__(self):
    super().__init__(
        timeout=None
    )

@discord.ui.button(
    label="Developer bewerben",
    emoji="💻",
    style=discord.ButtonStyle.primary,
    custom_id="developer_apply"
)
async def apply(
    self,
    interaction,
    button
):
    if interaction.user.id in active_applications:
        await interaction.response.send_message(
            "⚠️ Du hast bereits eine aktive Bewerbung.",
            ephemeral=True
        )
        return

    try:
        await interaction.response.send_message(
            "📨 Ich habe dir eine DM für die Bewerbung geschickt.",
            ephemeral=True
        )

        await run_developer_application(
            interaction.user
        )

    except discord.Forbidden:
        try:
            await interaction.followup.send(
                (
                    "❌ Ich konnte dir keine DM schicken.\n"
                    "Bitte aktiviere deine Direktnachrichten "
                    "für diesen Server."
                ),
                ephemeral=True
            )
        except Exception:
            pass
```

async def run_developer_application(user):
active_applications[
user.id
] = True

```
answers = []

try:
    await user.send(
        embed=base_embed(
            "💻 Developer-Bewerbung",
            (
                "Willkommen bei der Developer-Bewerbung.\n\n"
                "Beantworte bitte alle Fragen nacheinander.\n"
                "Für jede Antwort hast du 5 Minuten Zeit."
            )
        )
    )

    for index, question in enumerate(
        DEVELOPER_QUESTIONS,
        start=1
    ):
        await user.send(
            embed=base_embed(
                (
                    f"Frage {index}/"
                    f"{len(DEVELOPER_QUESTIONS)}"
                ),
                question
            )
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
                embed=base_embed(
                    "⏰ Bewerbung abgebrochen",
                    (
                        "Die Bewerbung wurde wegen "
                        "Zeitüberschreitung beendet."
                    ),
                    discord.Color.red()
                )
            )
            return

        answer = message.content.strip()

        if not answer:
            answer = "Keine Antwort"

        answers.append(
            (
                question,
                answer[:1000]
            )
        )

    await send_application_review(
        user,
        answers
    )

    await user.send(
        embed=base_embed(
            "✅ Bewerbung eingereicht",
            (
                "Deine Developer-Bewerbung wurde "
                "erfolgreich an das zuständige Team "
                "weitergeleitet."
            ),
            discord.Color.green()
        )
    )

except discord.Forbidden:
    print(
        f"[BEWERBUNG] DMs für {user} nicht verfügbar."
    )

except Exception as error:
    print(
        f"[BEWERBUNG] Fehler bei {user}: {error}"
    )

finally:
    active_applications.pop(
        user.id,
        None
    )
```

async def send_application_review(
user,
answers
):
channel = bot.get_channel(
REVIEW_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    print(
        "[BEWERBUNG] Review-Kanal nicht gefunden."
    )
    return

embed = base_embed(
    "💻 Neue Developer-Bewerbung",
    (
        f"**Bewerber:** {user.mention}\n"
        f"**User-ID:** `{user.id}`"
    )
)

for index, (
    question,
    answer
) in enumerate(
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
```

async def send_application_panel():
channel = bot.get_channel(
APPLICATION_CHANNEL_ID
)

```
if not isinstance(
    channel,
    discord.TextChannel
):
    return

await clean_bot_panel(
    channel,
    "💻 Developer-Bewerbung"
)

embed = base_embed(
    "💻 Developer-Bewerbung",
    (
        "Du möchtest unser Developer-Team unterstützen?\n\n"
        "Klicke auf **Developer bewerben** und fülle "
        "die Bewerbung per DM aus.\n\n"
        "Bitte beantworte alle Fragen ehrlich und ausführlich."
    )
)

await channel.send(
    embed=embed,
    view=DeveloperApplicationView()
)
```

# ============================================================

# EVENTS

# ============================================================

@bot.event
async def on_ready():
global startup_finished

```
print(
    f"✅ Bot online als {bot.user} ({bot.user.id})"
)

if startup_finished:
    return

guild = bot.get_guild(
    GUILD_ID
)

if guild is None:
    print(
        f"❌ Server {GUILD_ID} wurde nicht gefunden."
    )
    return

try:
    refill_quiz_bag()

    print("[START] Nametags werden geprüft...")
    await update_all_rlp_nicknames()

    quiz_channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if isinstance(
        quiz_channel,
        discord.TextChannel
    ):
        print("[START] Quiz-Kanal wird vorbereitet...")

        async for message in quiz_channel.history(
            limit=None
        ):
            if message.author == bot.user:
                await safe_delete(message)

        await send_new_quiz(
            quiz_channel
        )

    print("[START] Panels werden geladen...")

    await send_nickname_panel()
    await send_application_panel()
    await send_team_registration_panel()
    await send_developer_shift_panel()
    await send_developer_tasks()
    await send_support_panel()

    startup_finished = True

    print(
        "=========================================="
    )
    print(
        "✅ RLP BOT ERFOLGREICH GESTARTET"
    )
    print(
        f"🧩 Quiz-Fragen: {len(QUIZZES)}"
    )
    print(
        f"🎫 Support-Voice: {SUPPORT_VOICE_CHANNEL_ID}"
    )
    print(
        "=========================================="
    )

except Exception as error:
    startup_finished = False

    print(
        f"❌ FEHLER BEIM STARTUP: {error}"
    )
```

@bot.event
async def on_member_join(member):
if member.guild.id != GUILD_ID:
return

```
await asyncio.sleep(2)

await set_rlp_nickname(
    member,
    force=True
)
```

@bot.event
async def on_member_update(
before,
after
):
if before.guild.id != GUILD_ID:
return

```
before_has_role = any(
    role.id == NAMETAG_ROLE_ID
    for role in before.roles
)

after_has_role = any(
    role.id == NAMETAG_ROLE_ID
    for role in after.roles
)

if (
    not before_has_role
    and after_has_role
):
    await set_rlp_nickname(
        after,
        force=True
    )

if (
    before_has_role
    and not after_has_role
):
    if after.id in nametag_removed_users:
        nametag_removed_users.discard(
            after.id
        )

        save_data()
```

@bot.event
async def on_voice_state_update(
member,
before,
after
):
if member.guild.id != GUILD_ID:
return

```
joined_support = (
    after.channel is not None
    and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
)

left_support = (
    before.channel is not None
    and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
)

# ========================================================
# SUPPORT BETRETEN
# ========================================================

if joined_support:

    # Teamler / berechtigtes Teammitglied
    # wird nicht als normaler Support-Nutzer angelegt.
    if is_support_staff(member):
        await assign_supporter(
            after.channel
        )

    else:
        await create_support_case(
            member
        )

        await assign_supporter(
            after.channel
        )

# ========================================================
# SUPPORT VERLASSEN
# ========================================================

if left_support:

    # Wenn der Nutzer mit aktivem Case geht:
    if member.id in active_support_cases:
        await finish_support_case(
            member
        )

    # Wenn ein Supporter geht:
    # Der Case bleibt offen.
    # Falls ein anderer Teamler im Call ist,
    # wird dieser übernommen.
    if after.channel is not None:
        await assign_supporter(
            after.channel
        )
```

# ============================================================

# COMMAND FEHLER

# ============================================================

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

```
if isinstance(
    error,
    commands.MissingPermissions
):
    await ctx.send(
        embed=base_embed(
            "🔒 Keine Berechtigung",
            (
                "Du hast keine Berechtigung "
                "für diesen Command."
            ),
            discord.Color.red()
        ),
        delete_after=5
    )
    return

if isinstance(
    error,
    commands.MissingRequiredArgument
):
    await ctx.send(
        embed=base_embed(
            "❌ Fehlende Eingabe",
            (
                "Für diesen Command fehlt "
                "eine benötigte Eingabe."
            ),
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
    f"[COMMAND ERROR] {repr(error)}"
)
```

# ============================================================

# MESSAGE EVENT

# ============================================================

@bot.event
async def on_message(message):
if message.author.bot:
return

```
await bot.process_commands(
    message
)
```

# ============================================================

# START

# ============================================================

if not DISCORD_TOKEN:
raise RuntimeError(
"DISCORD_TOKEN wurde nicht gefunden. "
"Bitte prüfe dein GitHub-Secret bzw. deine Umgebungsvariable."
)

bot.run(
DISCORD_TOKEN
)
