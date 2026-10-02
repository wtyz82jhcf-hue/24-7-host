```python
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

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181
NICKNAME_CHANNEL_ID = 1555684071911202836

NAMETAG_ROLE_ID = 1520102928398942348

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ============================================================
# BOT
# ============================================================

class RLPBot(commands.Bot):

    async def setup_hook(self):
        load_data()

        # Persistente Views
        self.add_view(QuizView())
        self.add_view(NicknamePanelView())
        self.add_view(DeveloperApplicationView())

        print("[SYSTEM] Persistente Buttons geladen.")


bot = RLPBot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DATEN
# ============================================================

nametag_removed_users = set()
quiz_scores = {}

current_quiz = None
current_quiz_message = None
quiz_answered = False
quiz_lock = asyncio.Lock()

startup_finished = False


# ============================================================
# QUIZ FRAGEN
# ============================================================

QUIZZES = [

    {
        "question": "Welche Stadt ist die Hauptstadt von Deutschland?",
        "emoji": "🇩🇪",
        "answers": [
            ("🇩🇪", "Berlin"),
            ("🍺", "München"),
            ("🏰", "Hamburg"),
            ("🌊", "Köln")
        ],
        "correct": "🇩🇪",
        "hint": "Die Hauptstadt liegt im Nordosten Deutschlands."
    },

    {
        "question": "Welcher Planet ist der größte in unserem Sonnensystem?",
        "emoji": "🪐",
        "answers": [
            ("🪐", "Jupiter"),
            ("🔴", "Mars"),
            ("🌍", "Erde"),
            ("☀️", "Sonne")
        ],
        "correct": "🪐",
        "hint": "Dieser Planet ist ein Gasriese."
    },

    {
        "question": "Wie viele Bundesländer hat Deutschland?",
        "emoji": "🏛️",
        "answers": [
            ("1️⃣", "16"),
            ("2️⃣", "12"),
            ("3️⃣", "14"),
            ("4️⃣", "18")
        ],
        "correct": "1️⃣",
        "hint": "Es sind mehr als 15."
    },

    {
        "question": "Welches Tier wird oft als König der Tiere bezeichnet?",
        "emoji": "🦁",
        "answers": [
            ("🦁", "Löwe"),
            ("🐯", "Tiger"),
            ("🐺", "Wolf"),
            ("🐻", "Bär")
        ],
        "correct": "🦁",
        "hint": "Er wird häufig mit einer großen Mähne dargestellt."
    },

    {
        "question": "Wie viele Tage hat eine normale Woche?",
        "emoji": "📅",
        "answers": [
            ("7️⃣", "7"),
            ("5️⃣", "5"),
            ("6️⃣", "6"),
            ("8️⃣", "8")
        ],
        "correct": "7️⃣",
        "hint": "Montag bis Sonntag."
    },

    {
        "question": "Welche Farbe entsteht aus Blau und Gelb?",
        "emoji": "🎨",
        "answers": [
            ("🟢", "Grün"),
            ("🟣", "Lila"),
            ("🟠", "Orange"),
            ("🔴", "Rot")
        ],
        "correct": "🟢",
        "hint": "Die Farbe findet man häufig in der Natur."
    },

    {
        "question": "Wie heißt der natürliche Satellit der Erde?",
        "emoji": "🌙",
        "answers": [
            ("🌙", "Mond"),
            ("☀️", "Sonne"),
            ("⭐", "Stern"),
            ("🪐", "Saturn")
        ],
        "correct": "🌙",
        "hint": "Man kann ihn besonders gut nachts sehen."
    },

    {
        "question": "Wie viel ist 12 × 5?",
        "emoji": "🧮",
        "answers": [
            ("6️⃣0️⃣", "60"),
            ("5️⃣0️⃣", "50"),
            ("7️⃣0️⃣", "70"),
            ("8️⃣0️⃣", "80")
        ],
        "correct": "6️⃣0️⃣",
        "hint": "12 mal 5 ergibt dasselbe wie 6 mal 10."
    },

    {
        "question": "Welches Land hat die Form eines Stiefels?",
        "emoji": "👢",
        "answers": [
            ("🇮🇹", "Italien"),
            ("🇪🇸", "Spanien"),
            ("🇫🇷", "Frankreich"),
            ("🇵🇹", "Portugal")
        ],
        "correct": "🇮🇹",
        "hint": "Das Land liegt südlich der Alpen."
    },

    {
        "question": "Welches Element hat das chemische Symbol O?",
        "emoji": "⚗️",
        "answers": [
            ("💨", "Sauerstoff"),
            ("💧", "Wasserstoff"),
            ("🔥", "Kohlenstoff"),
            ("🪨", "Eisen")
        ],
        "correct": "💨",
        "hint": "Wir brauchen dieses Element zum Atmen."
    },

    {
        "question": "Wie viele Monate hat ein Jahr?",
        "emoji": "📆",
        "answers": [
            ("1️⃣2️⃣", "12"),
            ("1️⃣0️⃣", "10"),
            ("1️⃣1️⃣", "11"),
            ("1️⃣3️⃣", "13")
        ],
        "correct": "1️⃣2️⃣",
        "hint": "Januar bis Dezember."
    },

    {
        "question": "Welcher Ozean ist der größte?",
        "emoji": "🌊",
        "answers": [
            ("🌊", "Pazifischer Ozean"),
            ("🌊", "Atlantischer Ozean"),
            ("🌊", "Indischer Ozean"),
            ("🌊", "Arktischer Ozean")
        ],
        "correct": "🌊",
        "hint": "Er liegt zwischen Asien/Australien und Amerika."
    },

]


# ============================================================
# DEVELOPER FRAGEN
# ============================================================

DEVELOPER_QUESTIONS = [

    "Wie heißt du?",

    "Wie alt bist du?",

    "Wie lange bist du bereits auf Discord?",

    "Welche Programmiersprachen kannst du?",

    "Welche Erfahrungen hast du mit Discord Bots?",

    "Warum möchtest du Developer werden?",

    "Was würdest du auf dem Server verbessern?",

    "Wie viel Zeit könntest du ungefähr für das Team investieren?",

    "Gibt es noch etwas, das wir über dich wissen sollten?"

]


# ============================================================
# DATEN SPEICHERN
# ============================================================

def load_data():

    global nametag_removed_users
    global quiz_scores

    if not os.path.exists(DATA_FILE):

        nametag_removed_users = set()
        quiz_scores = {}

        save_data()
        return

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        nametag_removed_users = {
            int(user_id)
            for user_id in data.get("nametag_removed_users", [])
        }

        quiz_scores = {
            int(user_id): int(score)
            for user_id, score in data.get("quiz_scores", {}).items()
        }

        print("[DATA] Daten erfolgreich geladen.")

    except Exception as error:

        print(f"[DATA] Fehler beim Laden: {error}")

        nametag_removed_users = set()
        quiz_scores = {}


def save_data():

    try:

        data = {
            "nametag_removed_users": list(nametag_removed_users),
            "quiz_scores": {
                str(user_id): score
                for user_id, score in quiz_scores.items()
            }
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
# NICKNAME / RLP
# ============================================================

def get_clean_name(member: discord.Member):

    name = member.nick or member.name

    # Alle RLP-Präfixe entfernen
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_rlp_nickname(member: discord.Member, force=False):

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        print("[RLP] RLP-Rolle nicht gefunden.")
        return

    # Benutzer hat RLP über das Panel entfernt
    if member.id in nametag_removed_users and not force:
        return

    # Wenn RLP neu vergeben wurde:
    if force:

        if member.id in nametag_removed_users:

            nametag_removed_users.discard(member.id)
            save_data()

    # Rolle muss vorhanden sein
    if role not in member.roles:
        return

    clean_name = get_clean_name(member)

    if not clean_name:
        clean_name = member.name

    new_nickname = f"{NAMETAG}{clean_name}"

    # Discord erlaubt maximal 32 Zeichen
    new_nickname = new_nickname[:32]

    if member.nick == new_nickname:
        return

    try:

        await member.edit(
            nick=new_nickname,
            reason="RLP Nametag automatisch gesetzt"
        )

        print(
            f"[RLP] {member.name} -> {new_nickname}"
        )

    except discord.Forbidden:

        print(
            f"[RLP] Keine Berechtigung für {member}"
        )

    except discord.HTTPException as error:

        print(
            f"[RLP] Discord-Fehler bei {member}: {error}"
        )


async def remove_rlp_nickname(member: discord.Member):

    clean_name = get_clean_name(member)

    # dauerhaft merken
    nametag_removed_users.add(member.id)
    save_data()

    try:

        if not clean_name:

            await member.edit(
                nick=None,
                reason="RLP über Nickname-Panel entfernt"
            )

        else:

            await member.edit(
                nick=clean_name[:32],
                reason="RLP über Nickname-Panel entfernt"
            )

        print(
            f"[RLP] Entfernt bei {member}"
        )

    except discord.Forbidden:

        print(
            f"[RLP] Keine Berechtigung für {member}"
        )

        raise

    except discord.HTTPException as error:

        print(
            f"[RLP] Fehler: {error}"
        )

        raise


async def update_all_rlp_nicknames():

    guild = bot.get_guild(GUILD_ID)

    if guild is None:

        print("[RLP] Server nicht gefunden.")
        return

    role = guild.get_role(NAMETAG_ROLE_ID)

    if role is None:

        print("[RLP] RLP-Rolle nicht gefunden.")
        return

    print(
        f"[RLP] Prüfe {len(role.members)} Mitglieder..."
    )

    for member in role.members:

        try:

            await set_rlp_nickname(
                member,
                force=False
            )

            await asyncio.sleep(0.15)

        except Exception as error:

            print(
                f"[RLP] Fehler bei {member}: {error}"
            )

    print("[RLP] Alle Nicknames überprüft.")


# ============================================================
# NICKNAME PANEL
# ============================================================

class NicknamePanelView(discord.ui.View):

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
                "❌ Diese Funktion funktioniert nur auf dem Server.",
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

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            await remove_rlp_nickname(member)

            await interaction.followup.send(
                "✅ **RLP wurde entfernt.**\n\n"
                "Dein Name bleibt auch nach einem Bot-Neustart "
                "ohne `RLP `.\n\n"
                "Wenn dir die RLP-Rolle später **neu gegeben** wird, "
                "wird `RLP ` wieder automatisch hinzugefügt.",
                ephemeral=True
            )

        except Exception:

            await interaction.followup.send(
                "❌ Ich konnte deinen Nickname nicht ändern. "
                "Der Bot benötigt die Berechtigung "
                "**Nickname verwalten** und seine Rolle muss "
                "über deiner Rolle liegen.",
                ephemeral=True
            )


async def cleanup_panel_messages(
    channel,
    title
):

    try:

        deleted = 0

        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].title == title:

                try:

                    await message.delete()
                    deleted += 1

                except discord.HTTPException:
                    pass

        print(
            f"[PANEL] {deleted} alte '{title}' Panels gelöscht."
        )

    except Exception as error:

        print(
            f"[PANEL] Cleanup-Fehler: {error}"
        )


async def send_nickname_panel():

    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:

        print(
            "[RLP] Nickname-Kanal nicht gefunden."
        )

        return

    await cleanup_panel_messages(
        channel,
        "🏷️ Nickname ändern"
    )

    embed = discord.Embed(
        title="🏷️ Nickname ändern",
        description=(
            "**RLP vor deinem Namen entfernen?**\n\n"
            "Klicke auf den Button unten.\n\n"
            "❌ **RLP entfernen**\n"
            "Entfernt `RLP ` vor deinem Namen.\n\n"
            "🔄 Wenn du die **RLP-Rolle später neu bekommst**, "
            "wird `RLP ` automatisch wieder gesetzt."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Nickname System"
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )

    print("[RLP] Nickname-Panel gesendet.")


# ============================================================
# QUIZ
# ============================================================

def normalize(text):

    text = text.lower().strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def choose_quiz():

    return random.choice(QUIZZES)


def create_quiz_embed(quiz):

    embed = discord.Embed(
        title=f"{quiz['emoji']} Emoji Quiz",
        description=(
            f"## {quiz['question']}\n\n"
            "Wähle die richtige Antwort über die Buttons unten.\n\n"
            "💡 Du kannst auch einen **Hinweis** benutzen."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🏆 Belohnung",
        value="**+1 Punkt**",
        inline=True
    )

    embed.add_field(
        name="💡 Hinweis",
        value="Über den Hinweis-Button verfügbar.",
        inline=True
    )

    embed.set_footer(
        text="Emoji Quiz • Viel Erfolg!"
    )

    return embed


class QuizAnswerButton(
    discord.ui.Button
):

    def __init__(
        self,
        emoji,
        label,
        correct,
        position
    ):

        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=label,
            custom_id=f"quiz_answer_{position}"
        )

        self.answer_emoji = emoji
        self.correct = correct

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        global current_quiz
        global current_quiz_message
        global quiz_answered

        if current_quiz is None:

            await interaction.response.send_message(
                "❌ Gerade läuft kein Quiz.",
                ephemeral=True
            )

            return

        async with quiz_lock:

            if quiz_answered:

                await interaction.response.send_message(
                    "⏳ Diese Frage wurde bereits beantwortet.",
                    ephemeral=True
                )

                return

            if self.correct:

                quiz_answered = True

                user_id = interaction.user.id

                quiz_scores[user_id] = (
                    quiz_scores.get(user_id, 0) + 1
                )

                save_data()

                score = quiz_scores[user_id]

                await interaction.response.send_message(
                    f"🎉 **Richtig!**\n\n"
                    f"Du bekommst **+1 Punkt**.\n"
                    f"🏆 Dein Punktestand: **{score}**",
                    ephemeral=True
                )

                if current_quiz_message:

                    await safe_delete(
                        current_quiz_message
                    )

                await asyncio.sleep(1.5)

                await send_new_quiz(
                    interaction.channel
                )

            else:

                await interaction.response.send_message(
                    "❌ Leider falsch! Versuch es nochmal.",
                    ephemeral=True
                )


class QuizView(discord.ui.View):

    def __init__(
        self,
        quiz=None
    ):

        super().__init__(
            timeout=None
        )

        if quiz is not None:

            for index, answer in enumerate(
                quiz["answers"]
            ):

                emoji, label = answer

                self.add_item(
                    QuizAnswerButton(
                        emoji=emoji,
                        label=label,
                        correct=(
                            emoji == quiz["correct"]
                        ),
                        position=index
                    )
                )

            self.add_item(
                QuizHintButton()
            )

            self.add_item(
                QuizSkipButton()
            )


class QuizHintButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Hinweis",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="quiz_hint_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if current_quiz is None:

            await interaction.response.send_message(
                "❌ Kein Quiz aktiv.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"💡 **Hinweis:**\n{current_quiz['hint']}",
            ephemeral=True
        )


class QuizSkipButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="quiz_skip_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        global current_quiz_message
        global quiz_answered

        async with quiz_lock:

            if quiz_answered:

                await interaction.response.send_message(
                    "⏳ Diese Frage wurde bereits beantwortet.",
                    ephemeral=True
                )

                return

            quiz_answered = True

            await interaction.response.send_message(
                "⏭️ Frage übersprungen!",
                ephemeral=True
            )

            if current_quiz_message:

                await safe_delete(
                    current_quiz_message
                )

            await asyncio.sleep(1)

            await send_new_quiz(
                interaction.channel
            )


async def send_new_quiz(channel):

    global current_quiz
    global current_quiz_message
    global quiz_answered

    current_quiz = choose_quiz()
    quiz_answered = False

    embed = create_quiz_embed(
        current_quiz
    )

    view = QuizView(
        current_quiz
    )

    current_quiz_message = await channel.send(
        embed=embed,
        view=view
    )

    print(
        "[QUIZ] Neue Frage gesendet."
    )


async def safe_delete(message):

    try:

        await message.delete()

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):

        pass


# ============================================================
# DEVELOPER BEWERBUNG
# ============================================================

active_applications = set()


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

        user = interaction.user

        if user.id in active_applications:

            await interaction.response.send_message(
                "❌ Du hast bereits eine laufende Bewerbung.",
                ephemeral=True
            )

            return

        active_applications.add(
            user.id
        )

        await interaction.response.send_message(
            "📩 **Bewerbung gestartet!**\n"
            "Ich schicke dir jetzt eine DM.",
            ephemeral=True
        )

        try:

            await run_developer_application(
                user
            )

        except discord.Forbidden:

            active_applications.discard(
                user.id
            )

            await interaction.followup.send(
                "❌ Ich konnte dir keine DM schicken.\n\n"
                "Bitte aktiviere deine Direktnachrichten "
                "für diesen Server.",
                ephemeral=True
            )

        except Exception as error:

            active_applications.discard(
                user.id
            )

            print(
                f"[BEWERBUNG] Fehler: {error}"
            )

            await interaction.followup.send(
                "❌ Bei der Bewerbung ist ein Fehler aufgetreten.",
                ephemeral=True
            )


async def run_developer_application(user):

    try:

        dm = await user.create_dm()

        await dm.send(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛠️ **DEVELOPER-BEWERBUNG**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Beantworte bitte jede Frage einzeln.\n"
            "Du hast pro Frage **5 Minuten** Zeit.\n\n"
            "Viel Erfolg! 🚀"
        )

        answers = []

        for number, question in enumerate(
            DEVELOPER_QUESTIONS,
            start=1
        ):

            await dm.send(
                f"### Frage {number}/{len(DEVELOPER_QUESTIONS)}\n"
                f"**{question}**"
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

                answer_message = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=check
                )

            except asyncio.TimeoutError:

                await dm.send(
                    "⌛ **Zeit abgelaufen.**\n"
                    "Deine Bewerbung wurde beendet."
                )

                return

            answers.append(
                answer_message.content
            )

        await dm.send(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ **BEWERBUNG ABGESCHICKT**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Danke! Deine Bewerbung wurde an das Team "
            "weitergeleitet."
        )

        await send_application_review(
            user,
            answers
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
            "[BEWERBUNG] Review-Kanal nicht gefunden."
        )

        return

    embed = discord.Embed(
        title="🛠️ Neue Developer-Bewerbung",
        description=(
            f"**Bewerber:** {user.mention}\n"
            f"**User-ID:** `{user.id}`"
        ),
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    for index, answer in enumerate(
        answers
    ):

        question = DEVELOPER_QUESTIONS[index]

        if len(answer) > 1024:

            answer = (
                answer[:1021]
                + "..."
            )

        embed.add_field(
            name=f"{index + 1}. {question}",
            value=answer or "*Keine Antwort*",
            inline=False
        )

    embed.set_footer(
        text="Developer Bewerbung • RLP"
    )

    await channel.send(
        embed=embed
    )

    print(
        f"[BEWERBUNG] Bewerbung von {user} gesendet."
    )


async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:

        print(
            "[BEWERBUNG] Bewerbungskanal nicht gefunden."
        )

        return

    await cleanup_panel_messages(
        channel,
        "🛠️ Developer Bewerbung"
    )

    embed = discord.Embed(
        title="🛠️ Developer Bewerbung",
        description=(
            "## Du möchtest Developer werden?\n\n"
            "Dann bewirb dich ganz einfach über den Button "
            "unten.\n\n"
            "📩 Die Bewerbung findet **per DM** statt.\n"
            "📝 Du bekommst mehrere Fragen.\n"
            "⏱️ Pro Frage hast du 5 Minuten.\n"
            "📋 Anschließend wird die Bewerbung an das Team "
            "gesendet.\n\n"
            "**Viel Erfolg! 🚀**"
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text="RLP Developer Team"
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )

    print(
        "[BEWERBUNG] Bewerbungspanel gesendet."
    )


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 Eingeloggt als: {bot.user}")
    print(f"🆔 Bot-ID: {bot.user.id}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if startup_finished:

        print(
            "[SYSTEM] Reconnect erkannt."
        )

        return

    startup_finished = True

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        print(
            "❌ Server nicht gefunden!"
        )

        return

    print(
        f"✅ Server gefunden: {guild.name}"
    )

    # --------------------------------------------------------
    # RLP
    # --------------------------------------------------------

    try:

        await update_all_rlp_nicknames()

    except Exception as error:

        print(
            f"[RLP] Startup-Fehler: {error}"
        )

    # --------------------------------------------------------
    # QUIZ
    # --------------------------------------------------------

    try:

        quiz_channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if quiz_channel:

            await send_new_quiz(
                quiz_channel
            )

        else:

            print(
                "[QUIZ] Kanal nicht gefunden."
            )

    except Exception as error:

        print(
            f"[QUIZ] Startup-Fehler: {error}"
        )

    # --------------------------------------------------------
    # NICKNAME PANEL
    # --------------------------------------------------------

    try:

        await send_nickname_panel()

    except Exception as error:

        print(
            f"[RLP PANEL] Fehler: {error}"
        )

    # --------------------------------------------------------
    # DEVELOPER PANEL
    # --------------------------------------------------------

    try:

        await send_application_panel()

    except Exception as error:

        print(
            f"[BEWERBUNG PANEL] Fehler: {error}"
        )

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ BOT VOLLSTÄNDIG GESTARTET")
    print("🎯 Quiz: AKTIV")
    print("🏷️ RLP: AKTIV")
    print("🛠️ Bewerbungen: AKTIV")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


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

    before_has_role = (
        role in before.roles
    )

    after_has_role = (
        role in after.roles
    )

    # RLP-Rolle wurde gerade neu vergeben
    if not before_has_role and after_has_role:

        print(
            f"[RLP] Rolle neu vergeben an {after}."
        )

        nametag_removed_users.discard(
            after.id
        )

        save_data()

        await set_rlp_nickname(
            after,
            force=True
        )


# ============================================================
# COMMANDS
# ============================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def quiz(ctx):

    if ctx.channel.id != QUIZ_CHANNEL_ID:

        await ctx.send(
            "❌ Dieser Command funktioniert nur im Quiz-Kanal.",
            delete_after=5
        )

        return

    await send_new_quiz(
        ctx.channel
    )


@bot.command()
async def punkte(ctx):

    score = quiz_scores.get(
        ctx.author.id,
        0
    )

    embed = discord.Embed(
        title="🏆 Deine Quiz-Punkte",
        description=(
            f"{ctx.author.mention}\n\n"
            f"Du hast **{score} Punkt"
            f"{'e' if score != 1 else ''}**."
        ),
        color=discord.Color.gold()
    )

    await ctx.send(
        embed=embed,
        delete_after=10
    )


@bot.command()
async def top(ctx):

    if not quiz_scores:

        await ctx.send(
            "🏆 Noch keine Punkte vorhanden.",
            delete_after=10
        )

        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    lines = []

    for position, (user_id, score) in enumerate(
        sorted_scores,
        start=1
    ):

        member = ctx.guild.get_member(
            user_id
        )

        if member:

            name = member.display_name

        else:

            name = f"User {user_id}"

        lines.append(
            f"**{position}.** {name} — 🏆 **{score}**"
        )

    embed = discord.Embed(
        title="🏆 Quiz Rangliste",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await ctx.send(
        embed=embed,
        delete_after=20
    )


# ============================================================
# ERROR HANDLER
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

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ Dafür hast du keine Berechtigung.",
            delete_after=5
        )

        return

    print(
        f"[COMMAND ERROR] {error}"
    )


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.environ.get(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN wurde nicht gefunden!"
    )


# ============================================================
# START
# ============================================================

print("🚀 Starte RLP Bot...")

bot.run(TOKEN)
```
