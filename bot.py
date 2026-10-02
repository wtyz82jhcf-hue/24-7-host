import os
import random
import re
import asyncio
import discord


# ============================================================
# KANÄLE / ROLLEN
# ============================================================

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

DEVELOPER_ROLE_ID = 1541393345295683634


# ============================================================
# EMOJI-QUIZZE
# ============================================================

QUIZZES = [
    (["🍕", "🧀"], "Pizza"),
    (["🌧️", "🌈"], "Regenbogen"),
    (["🐶", "🦴"], "Hund"),
    (["🐱", "🐭"], "Katze"),
    (["🐰", "🥕"], "Hase"),
    (["🐵", "🍌"], "Affe"),
    (["🐼", "🎋"], "Panda"),
    (["🦁", "🌿"], "Löwe"),
    (["🐯", "🌴"], "Tiger"),
    (["🐘", "🌳"], "Elefant"),
    (["🦒", "🌳"], "Giraffe"),
    (["🐴", "🏇"], "Pferd"),
    (["🐮", "🥛"], "Kuh"),
    (["🐷", "🐖"], "Schwein"),
    (["🐔", "🥚"], "Huhn"),
    (["🐸", "💧"], "Frosch"),
    (["🐢", "🏁"], "Schildkröte"),
    (["🐍", "🌿"], "Schlange"),
    (["🦋", "🌸"], "Schmetterling"),
    (["🐝", "🍯"], "Biene"),
    (["🦊", "🌲"], "Fuchs"),
    (["🐻", "🍯"], "Bär"),
    (["🐺", "🌙"], "Wolf"),
    (["🦉", "🌙"], "Eule"),
    (["🦅", "☁️"], "Adler"),
    (["🐧", "❄️"], "Pinguin"),
    (["🐬", "🌊"], "Delfin"),
    (["🦈", "🌊"], "Hai"),
    (["🐙", "🌊"], "Oktopus"),
    (["🦀", "🏖️"], "Krabbe"),
    (["🐠", "🌊"], "Fisch"),
    (["🍎", "🍏"], "Apfel"),
    (["🍌", "🍎"], "Banane"),
    (["🍓", "🍒"], "Beeren"),
    (["🍉", "☀️"], "Wassermelone"),
    (["🍋", "🥤"], "Limonade"),
    (["🍊", "🍹"], "Orange"),
    (["🍍", "🌴"], "Ananas"),
    (["🥥", "🏝️"], "Kokosnuss"),
    (["🥕", "🐰"], "Karotte"),
    (["🌽", "🌾"], "Mais"),
    (["🍅", "🥗"], "Salat"),
    (["🍔", "🍟"], "Fast Food"),
    (["🌭", "🥤"], "Hotdog"),
    (["🍿", "🎬"], "Kino"),
    (["🍦", "☀️"], "Eis"),
    (["🍩", "☕"], "Donut"),
    (["🍫", "🥛"], "Schokolade"),
    (["🍰", "🧁"], "Kuchen"),
    (["🍪", "🥛"], "Kekse"),
    (["🍝", "🍅"], "Nudeln"),
    (["🍣", "🥢"], "Sushi"),
    (["🌮", "🌶️"], "Taco"),
    (["🎂", "🎁"], "Geburtstag"),
    (["🎈", "🎉"], "Party"),
    (["🎄", "🎁"], "Weihnachten"),
    (["🎃", "👻"], "Halloween"),
    (["😊", "❤️"], "Glück"),
    (["😂", "🤣"], "Lachen"),
    (["😭", "💧"], "Weinen"),
    (["😡", "🔥"], "Wut"),
    (["😎", "🕶️"], "Cool"),
    (["😴", "🛏️"], "Schlafen"),
    (["⏰", "😴"], "Wecker"),
    (["🚿", "🧼"], "Duschen"),
    (["🪥", "😁"], "Zähneputzen"),
    (["🏃", "👟"], "Laufen"),
    (["🏊", "🌊"], "Schwimmen"),
    (["🚴", "🚲"], "Radfahren"),
    (["🏋️", "💪"], "Fitness"),
    (["⚽", "🥅"], "Fußball"),
    (["🏀", "🏆"], "Basketball"),
    (["🏐", "🏆"], "Volleyball"),
    (["🎾", "🏟️"], "Tennis"),
    (["🥊", "🏆"], "Boxen"),
    (["🏎️", "🏁"], "Rennen"),
    (["🥇", "🏆"], "Sieger"),
    (["🎸", "🎤"], "Musik"),
    (["🥁", "🎵"], "Schlagzeug"),
    (["🎹", "🎼"], "Klavier"),
    (["🎨", "🖌️"], "Malen"),
    (["📖", "🔦"], "Lesen"),
    (["✏️", "📓"], "Schreiben"),
    (["🎧", "🎵"], "Musik"),
    (["📺", "🍿"], "Fernsehen"),
    (["🎮", "🕹️"], "Gaming"),
    (["💻", "⌨️"], "Computer"),
    (["📱", "💬"], "Chat"),
    (["📧", "💻"], "E-Mail"),
    (["📞", "📱"], "Anruf"),
    (["🔑", "🚪"], "Schlüssel"),
    (["🔒", "🔑"], "Schloss"),
    (["💰", "🏦"], "Geld"),
    (["💎", "💰"], "Reichtum"),
    (["🎁", "🎀"], "Geschenk"),
    (["🚗", "⛽"], "Auto"),
    (["🚕", "🏙️"], "Taxi"),
    (["🚌", "🚏"], "Bus"),
    (["🚲", "🛣️"], "Fahrrad"),
    (["🏍️", "🛣️"], "Motorrad"),
    (["🚓", "👮"], "Polizei"),
    (["🚑", "🏥"], "Krankenwagen"),
    (["🚒", "🔥"], "Feuerwehr"),
    (["🚁", "🚨"], "Hubschrauber"),
    (["🚢", "⚓"], "Schiff"),
    (["🚆", "🚉"], "Zug"),
    (["✈️", "🧳"], "Flugzeug"),
    (["🚀", "🌕"], "Weltraum"),
    (["🏴‍☠️", "🚢"], "Piraten"),
    (["👑", "🏰"], "König"),
    (["🏰", "⚔️"], "Burg"),
    (["🗺️", "🧳"], "Reise"),
    (["🌍", "✈️"], "Weltreise"),
    (["🏨", "🛏️"], "Hotel"),
    (["🏖️", "☀️"], "Strand"),
    (["🌊", "🐚"], "Meer"),
    (["🏝️", "🌴"], "Insel"),
    (["🏕️", "🔥"], "Camping"),
    (["🏔️", "❄️"], "Berg"),
    (["🏜️", "🐪"], "Wüste"),
    (["🌲", "🏡"], "Wald"),
    (["🌋", "🔥"], "Vulkan"),
    (["🌞", "🌻"], "Sommer"),
    (["❄️", "⛄"], "Winter"),
    (["🍂", "🌳"], "Herbst"),
    (["🌷", "🌸"], "Frühling"),
    (["🌙", "⭐"], "Mond"),
    (["☁️", "💧"], "Regen"),
    (["🌞", "🔥"], "Hitze"),
    (["🌳", "🍎"], "Apfelbaum"),
    (["🌻", "🌞"], "Sonnenblume"),
    (["🌹", "❤️"], "Rose"),
    (["🎓", "📚"], "Abschluss"),
    (["🔬", "🧪"], "Wissenschaft"),
    (["🧑‍🍳", "🍳"], "Kochen"),
    (["🍰", "🧁"], "Backen"),
    (["🧑‍💻", "💻"], "Developer"),
    (["💡", "🧠"], "Idee"),
    (["🎬", "🎟️"], "Film"),
    (["🎨", "🖼️"], "Kunst"),
    (["🎤", "🎙️"], "Sänger"),
    (["🎸", "🥁"], "Band"),
    (["📚", "🏫"], "Schule"),
    (["🎒", "📚"], "Schulranzen"),
    (["📝", "✏️"], "Hausaufgaben"),
    (["📅", "⏰"], "Termin"),
    (["🛒", "🛍️"], "Einkaufen"),
    (["🏠", "🔑"], "Zuhause"),
    (["🛋️", "📺"], "Wohnzimmer"),
    (["🛏️", "🌙"], "Schlafzimmer"),
    (["🚪", "🔔"], "Türklingel"),
    (["📦", "🚚"], "Paket"),
    (["📬", "✉️"], "Brief"),
    (["✉️", "📮"], "Post"),
    (["🔔", "📱"], "Benachrichtigung"),
    (["🎟️", "🎬"], "Kinokarte"),
    (["🎁", "🎉"], "Feier"),
    (["🎊", "🎉"], "Feier"),
]


# ============================================================
# DEVELOPER-FRAGEN
# ============================================================

DEVELOPER_QUESTIONS = [
    "Welche Erfahrungen hast du bisher mit Discord-Servern und deren Funktionen?",
    "Welche Erfahrungen hast du mit Discord-Bots?",
    "Hast du schon einmal einen Discord-Bot eingerichtet oder verwaltet?",
    "Welche Discord-Bot-Funktionen kennst du und hast du bereits verwendet?",
    "Hast du Erfahrung mit Buttons, Select-Menüs oder Modals?",
    "Hast du schon einmal ein Ticketsystem für Discord erstellt oder verwaltet?",
    "Hast du Erfahrung mit automatisierten Rollen und Reaktionen?",
    "Hast du schon einmal ein Verifizierungs- oder Bewerbungssystem für einen Discord-Server umgesetzt?",
    "Wie würdest du ein professionelles Discord-Bewerbungssystem gestalten?",
]


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ============================================================
# VARIABLEN
# ============================================================

current_quiz = None
current_quiz_message = None

last_result_messages = {}

active_applications = set()

quiz_bag = []

last_quiz_emojis = set()

startup_finished = False

quiz_lock = asyncio.Lock()


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def normalize(text):
    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"[^a-z0-9]+", "", text)


async def safe_delete(message):
    if message is None:
        return

    try:
        await message.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print("❌ Keine Berechtigung zum Löschen.")
    except discord.HTTPException as error:
        print(f"❌ Fehler beim Löschen: {error}")


async def delete_previous_result(user, channel):
    old_message = last_result_messages.get(user.id)

    if old_message:
        await safe_delete(old_message)
        last_result_messages.pop(user.id, None)


# ============================================================
# QUIZ
# ============================================================

def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(range(len(QUIZZES)))
    random.shuffle(quiz_bag)


def get_next_quiz():
    global quiz_bag
    global last_quiz_emojis

    if not quiz_bag:
        refill_quiz_bag()

    for position, index in enumerate(quiz_bag):
        emojis = set(QUIZZES[index][0])

        if not emojis & last_quiz_emojis:
            quiz_bag.pop(position)
            last_quiz_emojis = emojis
            return QUIZZES[index]

    index = quiz_bag.pop(0)
    last_quiz_emojis = set(QUIZZES[index][0])

    return QUIZZES[index]


def create_quiz_embed(emojis):
    embed = discord.Embed(
        title="🎯 Emoji-Quiz",
        description=(
            "**Was bedeutet diese Emoji-Kombination?**\n\n"
            f"# {' '.join(emojis)}\n\n"
            "💬 Schreibe deine Antwort in den Chat!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text="Viel Glück! 🍀")

    return embed


async def send_new_quiz():
    global current_quiz
    global current_quiz_message

    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        print("❌ Quiz-Kanal wurde nicht gefunden.")
        return

    current_quiz = get_next_quiz()

    embed = create_quiz_embed(current_quiz[0])

    current_quiz_message = await channel.send(embed=embed)

    print(f"✅ Neues Quiz: {current_quiz[1]}")


async def cleanup_old_quizzes(channel):
    try:
        async for message in channel.history(limit=100):
            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].title == "🎯 Emoji-Quiz":
                await safe_delete(message)

    except discord.Forbidden:
        print("❌ Keine Berechtigung zum Lesen des Verlaufs.")


# ============================================================
# ABLEHNEN
# ============================================================

class RejectApplicationModal(
    discord.ui.Modal,
    title="Bewerbung ablehnen"
):

    reason = discord.ui.TextInput(
        label="Grund für die Ablehnung",
        placeholder="Bitte schreibe den Grund...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=1,
        max_length=1000
    )

    def __init__(self, user):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction):
        reason = self.reason.value.strip()

        try:
            await self.user.send(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ **DEVELOPER-BEWERBUNG**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Leider wurde deine Developer-Bewerbung "
                "**abgelehnt**.\n\n"
                "📝 **Grund:**\n"
                f"{reason}\n\n"
                "Vielen Dank trotzdem für dein Interesse!\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            "🔴 Die Bewerbung wurde abgelehnt.",
            ephemeral=True
        )

        for child in self.view.children:
            child.disabled = True

        try:
            await interaction.message.edit(view=self.view)
        except discord.HTTPException:
            pass


# ============================================================
# ANNEHMEN / ABLEHNEN
# ============================================================

class ApplicationDecisionView(discord.ui.View):

    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(
        label="Annehm",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="application_accept"
    )
    async def accept(self, interaction, button):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Server konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        role = guild.get_role(DEVELOPER_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Die Developer-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        member = guild.get_member(self.user.id)

        if member is None:
            try:
                member = await guild.fetch_member(self.user.id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "❌ Der Bewerber ist nicht mehr auf dem Server.",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "❌ Der Bewerber konnte nicht gefunden werden.",
                    ephemeral=True
                )
                return

        try:
            await member.add_roles(
                role,
                reason=f"Developer-Bewerbung angenommen von {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Developer-Rolle nicht vergeben.\n\n"
                "Prüfe bitte, ob der Bot **Rollen verwalten** darf "
                "und ob seine Bot-Rolle über der Developer-Rolle steht.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:
            print(f"❌ Rollenfehler: {error}")

            await interaction.response.send_message(
                "❌ Beim Vergeben der Rolle ist ein Fehler aufgetreten.",
                ephemeral=True
            )
            return

        try:
            await self.user.send(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "✅ **DEVELOPER-BEWERBUNG**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Herzlichen Glückwunsch! 🎉\n\n"
                "Deine Developer-Bewerbung wurde "
                "**angenommen**.\n\n"
                "Dir wurde die Developer-Rolle zugewiesen.\n\n"
                "Willkommen im Team! 👨‍💻\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            f"🟢 Bewerbung angenommen!\n"
            f"✅ {member.mention} hat {role.mention} erhalten.",
            ephemeral=True
        )

        for child in self.children:
            child.disabled = True

        try:
            await interaction.message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(
        label="Ablehn",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="application_reject"
    )
    async def reject(self, interaction, button):

        await interaction.response.send_modal(
            RejectApplicationModal(self.user)
        )


# ============================================================
# BEWERBEN BUTTON
# ============================================================

class DeveloperApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        emoji="👨‍💻",
        style=discord.ButtonStyle.primary,
        custom_id="developer_application_button"
    )
    async def apply(self, interaction, button):

        user = interaction.user

        if user.id in active_applications:
            await interaction.response.send_message(
                "⏳ Deine Bewerbung läuft bereits.",
                ephemeral=True
            )
            return

        active_applications.add(user.id)

        try:
            try:
                await user.send(
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "👨‍💻 **DEVELOPER-BEWERBUNG**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Vielen Dank für dein Interesse! ❤️\n\n"
                    "📋 **Ablauf**\n\n"
                    "• 9 Fragen\n"
                    "• Eine Frage nach der anderen\n"
                    "• Antworte direkt auf jede Frage\n"
                    "• Schreibe `abbrechen` zum Beenden\n\n"
                    "🍀 Viel Erfolg!\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich kann dir keine DM schicken.\n\n"
                    "Bitte aktiviere deine Direktnachrichten "
                    "für diesen Server.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                "✅ Deine Developer-Bewerbung wurde per DM gestartet.",
                ephemeral=True
            )

            await start_developer_application(user)

        finally:
            active_applications.discard(user.id)


# ============================================================
# BEWERBUNG
# ============================================================

async def start_developer_application(user):

    answers = []

    def check(message):
        return (
            message.author.id == user.id
            and isinstance(message.channel, discord.DMChannel)
        )

    for number, question in enumerate(
        DEVELOPER_QUESTIONS,
        start=1
    ):

        embed = discord.Embed(
            title="👨‍💻 Developer-Bewerbung",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name=f"📋 Frage {number}/9",
            value=question,
            inline=False
        )

        embed.add_field(
            name="✏️ Deine Antwort",
            value="Schreibe deine Antwort als nächste Nachricht.",
            inline=False
        )

        embed.set_footer(
            text="Schreibe „abbrechen“, wenn du die Bewerbung beenden möchtest."
        )

        await user.send(embed=embed)

        try:
            answer_message = await bot.wait_for(
                "message",
                timeout=900,
                check=check
            )

        except asyncio.TimeoutError:
            await user.send(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⏰ **BEWERBUNG BEENDET**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Du hast zu lange nicht geantwortet."
            )
            return

        answer = answer_message.content.strip()

        if normalize(answer) == "abbrechen":
            await user.send(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ **BEWERBUNG ABGEBROCHEN**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Deine Bewerbung wurde abgebrochen."
            )
            return

        answers.append(answer)

        await user.send(
            "✅ **Antwort gespeichert!**\n"
            "➡️ Weiter zur nächsten Frage..."
        )

    await user.send(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ **BEWERBUNG ABGESCHLOSSEN**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Vielen Dank für deine Bewerbung! ❤️\n\n"
        "Deine Antworten wurden erfolgreich "
        "an das Developer-Team übermittelt.\n\n"
        "⏳ Deine Bewerbung wird nun geprüft."
    )

    await send_application_to_team(user, answers)


# ============================================================
# BEWERBUNG AN TEAM
# ============================================================

async def send_application_to_team(user, answers):

    channel = bot.get_channel(REVIEW_CHANNEL_ID)

    if channel is None:
        print("❌ Review-Kanal wurde nicht gefunden.")
        return

    embed = discord.Embed(
        title="👨‍💻 Neue Developer-Bewerbung",
        description=(
            f"**Bewerber:** {user.mention}\n"
            f"**Benutzer:** {user}\n"
            f"**User-ID:** `{user.id}`"
        ),
        color=discord.Color.blurple()
    )

    for number, answer in enumerate(answers, start=1):

        question = DEVELOPER_QUESTIONS[number - 1]

        value = (
            f"**{question}**\n\n"
            f"{answer}"
        )

        if len(value) > 1024:
            value = value[:1021] + "..."

        embed.add_field(
            name=f"Frage {number}",
            value=value,
            inline=False
        )

    embed.set_footer(
        text="Developer Bewerbungssystem"
    )

    await channel.send(
        embed=embed,
        view=ApplicationDecisionView(user)
    )

    print(
        f"✅ Bewerbung von {user} wurde an das Team gesendet."
    )


# ============================================================
# BEWERBUNGS-PANEL
# ============================================================

async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        print("❌ Bewerbungskanal wurde nicht gefunden.")
        return

    try:
        async for message in channel.history(limit=100):

            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].title == "👨‍💻 Developer Bewerbung":
                print("✅ Developer-Panel existiert bereits.")
                return

    except discord.Forbidden:
        print("❌ Keine Berechtigung für den Bewerbungskanal.")
        return

    embed = discord.Embed(
        title="👨‍💻 Developer Bewerbung",
        description=(
            "**Du möchtest unser Developer-Team unterstützen?**\n\n"
            "Klicke unten auf **Bewerben**, um deine Bewerbung "
            "zu starten.\n\n"
            "📩 Die Bewerbung läuft anschließend über deine DMs."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Developer Bewerbungssystem"
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )

    print("✅ Developer-Panel erstellt.")


# ============================================================
# BOT
# ============================================================

class QuizBot(discord.Client):

    async def setup_hook(self):
        self.add_view(
            DeveloperApplicationView()
        )


bot = QuizBot(
    intents=intents
)


# ============================================================
# BOT ONLINE
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print(f"✅ Bot ist online als {bot.user}")

    if startup_finished:
        return

    startup_finished = True

    quiz_channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel:
        await cleanup_old_quizzes(
            quiz_channel
        )

        await send_new_quiz()

    else:
        print("❌ Quiz-Kanal nicht gefunden.")

    await send_application_panel()


# ============================================================
# NACHRICHTEN
# ============================================================

@bot.event
async def on_message(message):

    global current_quiz
    global current_quiz_message

    if message.author == bot.user:
        return

    if message.channel.id != QUIZ_CHANNEL_ID:
        return

    if current_quiz is None:
        return

    answer = normalize(
        message.content
    )

    correct_answer = normalize(
        current_quiz[1]
    )

    user = message.author

    if answer == correct_answer:

        async with quiz_lock:

            if current_quiz is None:
                return

            await delete_previous_result(
                user,
                message.channel
            )

            result_message = await message.channel.send(
                f"✅ {user.mention} Richtig!"
            )

            last_result_messages[
                user.id
            ] = result_message

            old_quiz_message = current_quiz_message

            current_quiz = None
            current_quiz_message = None

            await safe_delete(
                old_quiz_message
            )

            await send_new_quiz()

        return

    await delete_previous_result(
        user,
        message.channel
    )

    result_message = await message.channel.send(
        f"❌ {user.mention} Leider falsch! "
        "Nächster Versuch!"
    )

    last_result_messages[
        user.id
    ] = result_message


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.environ.get(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN wurde nicht gefunden."
    )


# ============================================================
# START
# ============================================================

bot.run(TOKEN)
