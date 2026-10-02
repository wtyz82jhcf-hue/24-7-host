import os
import json
import random
import re
import asyncio
import discord
from discord.ext import commands

# =========================================================
# EINSTELLUNGEN
# =========================================================

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NICKNAME_CHANNEL_ID = 1555684071911202836

GUILD_ID = 1519481018221072454
NAMETAG_ROLE_ID = 1520102928398942348

NAMETAG = "RLP "
NAMETAG_DATA_FILE = "nametag_data.json"

# =========================================================
# QUIZ
# =========================================================

QUIZZES = [
    {
        "question": "Wie viele Bundesländer hat Deutschland?",
        "answers": ["16"],
        "emoji": "🇩🇪"
    },
    {
        "question": "Wie heißt die Hauptstadt von Deutschland?",
        "answers": ["Berlin"],
        "emoji": "🏙️"
    },
    {
        "question": "Wie viele Tage hat eine Woche?",
        "answers": ["7", "sieben"],
        "emoji": "📅"
    },
    {
        "question": "Wie viele Kontinente gibt es?",
        "answers": ["7", "sieben"],
        "emoji": "🌍"
    },
    {
        "question": "Wie heißt der größte Planet unseres Sonnensystems?",
        "answers": ["Jupiter"],
        "emoji": "🪐"
    },
    {
        "question": "Wie viel ist 10 + 15?",
        "answers": ["25"],
        "emoji": "➕"
    },
    {
        "question": "Wie viel ist 12 × 5?",
        "answers": ["60"],
        "emoji": "✖️"
    },
    {
        "question": "Welche Farbe entsteht aus Blau und Gelb?",
        "answers": ["grün", "gruen"],
        "emoji": "🎨"
    },
    {
        "question": "Wie heißt der natürliche Satellit der Erde?",
        "answers": ["Mond"],
        "emoji": "🌙"
    },
    {
        "question": "Wie viele Monate hat ein Jahr?",
        "answers": ["12", "zwölf", "zwoelf"],
        "emoji": "📆"
    }
]

DEVELOPER_QUESTIONS = [
    "Wie heißt du?",
    "Wie alt bist du?",
    "Wie lange bist du schon auf Discord?",
    "Welche Programmiersprachen kannst du?",
    "Welche Erfahrungen hast du mit Discord Bots?",
    "Warum möchtest du Developer werden?",
    "Was würdest du als Developer auf dem Server verbessern?",
    "Wie viel Zeit könntest du ungefähr für das Team investieren?",
    "Gibt es noch etwas, das wir über dich wissen sollten?"
]

# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================================================
# GLOBALE VARIABLEN
# =========================================================

current_quiz = None
current_quiz_message = None

quiz_bag = []

quiz_lock = asyncio.Lock()
startup_finished = False

skip_counts = {}
hint_counts = {}

active_applications = set()

# =========================================================
# RLP-DATEN
# =========================================================

nametag_removed_users = set()


def load_nametag_data():
    global nametag_removed_users

    try:
        if not os.path.exists(NAMETAG_DATA_FILE):
            nametag_removed_users = set()
            return

        with open(NAMETAG_DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        nametag_removed_users = {
            int(user_id)
            for user_id in data.get("removed_users", [])
        }

    except Exception as error:
        print(f"[RLP] Fehler beim Laden: {error}")
        nametag_removed_users = set()


def save_nametag_data():
    try:
        data = {
            "removed_users": list(nametag_removed_users)
        }

        with open(NAMETAG_DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    except Exception as error:
        print(f"[RLP] Fehler beim Speichern: {error}")


def get_base_name(member: discord.Member):
    """
    Entfernt alle vorhandenen RLP-Präfixe.
    Beispiel:
    RLP Max -> Max
    RLP RLP Max -> Max
    RLP RLP RLP Max -> Max
    """

    name = member.display_name

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_nametag(member: discord.Member, force=False):
    """
    Setzt exakt einen 'RLP ' Präfix.

    force=True:
    - wird beim Join / neu vergebenen Role verwendet
    - entfernt einen vorherigen Opt-Out
    """

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[RLP] Rolle wurde nicht gefunden.")
        return

    # User hat RLP über das Panel entfernt
    if member.id in nametag_removed_users and not force:
        return

    # Bei force wird ein alter Opt-Out aufgehoben
    if force:
        if member.id in nametag_removed_users:
            nametag_removed_users.discard(member.id)
            save_nametag_data()

    # Nur Mitglieder mit der Rolle bekommen RLP
    if role not in member.roles:
        return

    base_name = get_base_name(member)

    # Discord-Nickname darf maximal 32 Zeichen haben
    new_nickname = f"{NAMETAG}{base_name}"
    new_nickname = new_nickname[:32]

    if member.nick == new_nickname:
        return

    try:
        await member.edit(
            nick=new_nickname,
            reason="RLP Nametag"
        )

        print(f"[RLP] Nickname gesetzt: {member} -> {new_nickname}")

    except discord.Forbidden:
        print(f"[RLP] Keine Berechtigung für {member}.")

    except discord.HTTPException as error:
        print(f"[RLP] Discord-Fehler bei {member}: {error}")


async def remove_nametag(member: discord.Member):
    """
    Entfernt RLP dauerhaft über das Panel.
    """

    base_name = get_base_name(member)

    # Opt-Out speichern
    nametag_removed_users.add(member.id)
    save_nametag_data()

    try:
        # Wenn kein Nickname vorhanden ist, gibt es nichts zu ändern
        if member.nick is None:
            return

        # Discord: None setzt den Nickname auf den Accountnamen zurück.
        # Falls der Accountname selbst mit RLP beginnt, entfernen wir
        # das RLP nicht aus dem Accountnamen, sondern setzen den Nickname
        # auf den bereinigten Namen.
        if base_name:
            await member.edit(
                nick=base_name[:32],
                reason="RLP über Nickname-Panel entfernt"
            )
        else:
            await member.edit(
                nick=None,
                reason="RLP über Nickname-Panel entfernt"
            )

        print(f"[RLP] RLP entfernt: {member}")

    except discord.Forbidden:
        print(f"[RLP] Keine Berechtigung, RLP bei {member} zu entfernen.")

    except discord.HTTPException as error:
        print(f"[RLP] Discord-Fehler beim Entfernen: {error}")


async def update_all_nametags():
    """
    Wird beim Bot-Start ausgeführt.
    Alle Mitglieder mit RLP-Rolle bekommen genau ein RLP.
    Opt-Out-Mitglieder bleiben ohne RLP.
    """

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("[RLP] Server nicht gefunden.")
        return

    role = guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[RLP] RLP-Rolle nicht gefunden.")
        return

    print(f"[RLP] Prüfe {len(role.members)} Mitglieder...")

    for member in role.members:
        try:
            await set_nametag(member, force=False)
        except Exception as error:
            print(f"[RLP] Fehler bei {member}: {error}")

    print("[RLP] Nametags überprüft.")


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


async def safe_delete(message):
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass


# =========================================================
# NICKNAME PANEL
# =========================================================

class NicknamePanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="RLP entfernen",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="nickname_remove_rlp"
    )
    async def remove_rlp(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Das funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        await remove_nametag(member)

        await interaction.followup.send(
            "✅ Dein RLP-Nametag wurde entfernt.\n"
            "Er bleibt auch nach einem Bot-Neustart entfernt.\n\n"
            "Wenn dir die RLP-Rolle später neu gegeben wird, "
            "wird RLP wieder automatisch gesetzt.",
            ephemeral=True
        )


async def send_nickname_panel():
    channel = bot.get_channel(NICKNAME_CHANNEL_ID)

    if channel is None:
        print("[RLP] Nickname-Kanal nicht gefunden.")
        return

    embed = discord.Embed(
        title="Nickname ändern!",
        description=(
            "Du möchtest das **RLP** vor deinem Namen entfernen?\n\n"
            "Klicke einfach auf **RLP entfernen**.\n\n"
            "Wenn du die RLP-Rolle später neu bekommst, "
            "wird `RLP ` automatisch wieder vor deinen Namen gesetzt."
        ),
        color=discord.Color.blue()
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )

    print("[RLP] Nickname-Panel gesendet.")


# =========================================================
# QUIZ
# =========================================================

def get_next_quiz():

    global quiz_bag

    if not quiz_bag:
        quiz_bag = list(range(len(QUIZZES)))
        random.shuffle(quiz_bag)

    index = quiz_bag.pop()

    return QUIZZES[index]


def create_quiz_embed(quiz):

    embed = discord.Embed(
        title="🎯 Quiz",
        description=f"**{quiz['question']}**",
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Antworte direkt auf diese Nachricht."
    )

    return embed


async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message

    current_quiz = get_next_quiz()

    embed = create_quiz_embed(current_quiz)

    view = QuizView()

    current_quiz_message = await channel.send(
        embed=embed,
        view=view
    )

    print("[QUIZ] Neues Quiz gesendet.")


class QuizView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Überspringen",
        style=discord.ButtonStyle.secondary,
        emoji="⏭️",
        custom_id="quiz_skip"
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        channel = interaction.channel

        if channel is None:
            return

        user_id = interaction.user.id

        skip_counts[user_id] = skip_counts.get(user_id, 0) + 1

        await interaction.response.send_message(
            "⏭️ Quiz übersprungen.",
            ephemeral=True
        )

        global current_quiz_message

        if current_quiz_message:
            await safe_delete(current_quiz_message)

        await send_new_quiz(channel)

    @discord.ui.button(
        label="Hinweis",
        style=discord.ButtonStyle.primary,
        emoji="💡",
        custom_id="quiz_hint"
    )
    async def hint(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Gerade läuft kein Quiz.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        hint_counts[user_id] = hint_counts.get(user_id, 0) + 1

        answers = current_quiz["answers"]

        first_letter = answers[0][0]

        await interaction.response.send_message(
            f"💡 Hinweis: Die Antwort beginnt mit **{first_letter.upper()}**.",
            ephemeral=True
        )


# =========================================================
# DEVELOPER-BEWERBUNG
# =========================================================

class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer bewerben",
        style=discord.ButtonStyle.success,
        emoji="🛠️",
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Du kannst dich nur über den Server bewerben.",
                ephemeral=True
            )
            return

        if interaction.user.id in active_applications:
            await interaction.response.send_message(
                "❌ Du hast bereits eine Bewerbung laufen.",
                ephemeral=True
            )
            return

        active_applications.add(interaction.user.id)

        await interaction.response.send_message(
            "📩 Ich habe dir eine DM geschickt. Beantworte dort die Fragen.",
            ephemeral=True
        )

        try:
            await run_application(interaction.user)
        except discord.Forbidden:
            active_applications.discard(interaction.user.id)

            try:
                await interaction.followup.send(
                    "❌ Ich konnte dir keine DM schicken. "
                    "Bitte aktiviere deine Direktnachrichten.",
                    ephemeral=True
                )
            except discord.HTTPException:
                pass

        except Exception as error:
            active_applications.discard(interaction.user.id)
            print(f"[BEWERBUNG] Fehler: {error}")


async def run_application(user):

    try:
        dm = await user.create_dm()

        await dm.send(
            "🛠️ **Developer-Bewerbung**\n\n"
            "Beantworte bitte alle Fragen nacheinander."
        )

        answers = []

        for number, question in enumerate(DEVELOPER_QUESTIONS, start=1):

            await dm.send(
                f"**Frage {number}/{len(DEVELOPER_QUESTIONS)}**\n"
                f"{question}"
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

                await dm.send(
                    "⌛ Deine Bewerbung wurde wegen Inaktivität beendet."
                )

                active_applications.discard(user.id)
                return

            answers.append(message.content)

        await dm.send(
            "✅ Danke! Deine Bewerbung wurde abgeschickt."
        )

        await send_application_to_review(user, answers)

    finally:
        active_applications.discard(user.id)


async def send_application_to_review(user, answers):

    channel = bot.get_channel(REVIEW_CHANNEL_ID)

    if channel is None:
        print("[BEWERBUNG] Review-Kanal nicht gefunden.")
        return

    embed = discord.Embed(
        title="🛠️ Neue Developer-Bewerbung",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Bewerber",
        value=f"{user.mention}\n`{user.id}`",
        inline=False
    )

    for index, answer in enumerate(answers):
        question = DEVELOPER_QUESTIONS[index]

        if len(answer) > 1024:
            answer = answer[:1021] + "..."

        embed.add_field(
            name=question,
            value=answer,
            inline=False
        )

    embed.set_footer(
        text="Developer-Bewerbung"
    )

    await channel.send(embed=embed)


async def send_application_panel():

    channel = bot.get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        print("[BEWERBUNG] Bewerbungskanal nicht gefunden.")
        return

    embed = discord.Embed(
        title="🛠️ Developer gesucht!",
        description=(
            "Du möchtest den Server als Developer unterstützen?\n\n"
            "Klicke auf den Button und beantworte die Fragen "
            "in deinen DMs."
        ),
        color=discord.Color.green()
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )

    print("[BEWERBUNG] Bewerbungspanel gesendet.")


# =========================================================
# BOT
# =========================================================

class QuizBot(commands.Bot):

    async def setup_hook(self):

        load_nametag_data()

        # Persistent Views
        self.add_view(QuizView())
        self.add_view(NicknamePanelView())
        self.add_view(DeveloperApplicationView())

        print("[BOT] Persistent Views geladen.")


# =========================================================
# BOT EVENTS
# =========================================================

@bot.event
async def on_ready():

    global startup_finished

    if startup_finished:
        return

    startup_finished = True

    print("===================================")
    print(f"Bot online als: {bot.user}")
    print("===================================")

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print("[BOT] Server nicht gefunden.")
        return

    print(f"[BOT] Server: {guild.name}")

    # RLP aktualisieren
    try:
        await update_all_nametags()
    except Exception as error:
        print(f"[RLP] Startup-Fehler: {error}")

    # Quiz
    try:
        quiz_channel = bot.get_channel(QUIZ_CHANNEL_ID)

        if quiz_channel:
            await send_new_quiz(quiz_channel)

    except Exception as error:
        print(f"[QUIZ] Startup-Fehler: {error}")

    # Nickname Panel
    try:
        await send_nickname_panel()
    except Exception as error:
        print(f"[NICKNAME] Startup-Fehler: {error}")

    # Developer Panel
    try:
        await send_application_panel()
    except Exception as error:
        print(f"[BEWERBUNG] Startup-Fehler: {error}")

    print("===================================")
    print("Bot vollständig gestartet.")
    print("===================================")


@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    # Beim Serverbeitritt wird RLP gesetzt,
    # sofern die Rolle vorhanden ist.
    await set_nametag(member, force=True)


@bot.event
async def on_member_update(before, after):

    if after.guild.id != GUILD_ID:
        return

    role = after.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    before_has_role = role in before.roles
    after_has_role = role in after.roles

    # RLP-Rolle wurde NEU vergeben
    if not before_has_role and after_has_role:

        print(f"[RLP] RLP-Rolle neu vergeben an {after}.")

        # Alten Opt-Out löschen
        nametag_removed_users.discard(after.id)
        save_nametag_data()

        # RLP setzen
        await set_nametag(after, force=True)


# =========================================================
# NACHRICHTEN / QUIZ-ANTWORTEN
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Commands weiterhin verarbeiten
    await bot.process_commands(message)

    # Nur Quiz-Kanal
    if message.channel.id != QUIZ_CHANNEL_ID:
        return

    if current_quiz is None:
        return

    user_answer = normalize(message.content)

    correct = False

    for answer in current_quiz["answers"]:

        if user_answer == normalize(answer):
            correct = True
            break

    if not correct:
        return

    global current_quiz_message

    try:
        await message.reply(
            f"✅ **Richtig!** Glückwunsch {message.author.mention}!"
        )
    except discord.HTTPException:
        pass

    if current_quiz_message:
        await safe_delete(current_quiz_message)

    await asyncio.sleep(1)

    await send_new_quiz(message.channel)


# =========================================================
# START
# =========================================================

TOKEN = os.environ.get("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden. "
        "Setze deinen Discord Bot Token als Umgebungsvariable."
    )

bot = QuizBot(
    command_prefix="!",
    intents=intents
)

bot.run(TOKEN)
