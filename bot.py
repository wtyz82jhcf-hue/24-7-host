import os
import json
import random
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.environ.get("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NICKNAME_CHANNEL_ID = 1555684071911202836

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715

# NEUER SCHICHT-PANEL-CHANNEL
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648

# NAMETAG-ROLLE
NAMETAG_ROLE_ID = 1520102928398942348

# SCHICHT-BERECHTIGUNG
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904

# AKTIVE SCHICHT-ROLLE
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"

PANEL_MARKER = "RLP_PANEL:"


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATEN
# =========================================================

DEFAULT_DATA = {
    "nametag_opt_out": [],
    "quiz_scores": {},
    "developer_shifts": {},
    "developer_tasks": {},
    "developer_task_counter": 0,
    "license_plates": {},
    "support_case_counter": 0
}

data = {}

startup_finished = False

quiz_cleanup_task = None
quiz_message_id = None
current_quiz = None
quiz_lock = asyncio.Lock()


# =========================================================
# DATEN LADEN / SPEICHERN
# =========================================================

def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as error:
        print(f"[DATA] Speicherfehler: {error}")


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )

        if isinstance(loaded, dict):
            for key in data:
                if key in loaded:
                    data[key] = loaded[key]

    except Exception as error:
        print(f"[DATA] Ladefehler: {error}")

        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )

        save_data()


load_data()


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    guild = get_guild()

    if guild is None:
        return None

    return guild.get_channel(channel_id)


def get_role(role_id):
    guild = get_guild()

    if guild is None:
        return None

    return guild.get_role(role_id)


def has_role(member, role_id):
    return any(
        role.id == role_id
        for role in member.roles
    )


def now_text():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%d.%m.%Y %H:%M:%S UTC"
    )


def panel_marker(message):
    if not message.embeds:
        return None

    embed = message.embeds[0]

    if not embed.footer:
        return None

    footer = embed.footer.text or ""

    if footer.startswith(PANEL_MARKER):
        return footer

    return None


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(
            *args,
            **kwargs
        )

    except discord.Forbidden:
        print(
            f"[DISCORD] Keine Berechtigung in {getattr(channel, 'id', '?')}"
        )

    except discord.HTTPException as error:
        print(
            f"[DISCORD] Sendefehler: {error}"
        )

    return None


# =========================================================
# NAMETAG
# =========================================================

def clean_nametag(name):
    """
    Entfernt ALLE führenden RLP-Präfixe.
    Dadurch kann niemals entstehen:

    RLP RLP Max
    RLP RLP RLP Max
    """

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name


def make_nametag(name):
    """
    Erst alle vorhandenen RLP-Präfixe entfernen,
    danach genau EINEN setzen.
    """

    clean_name = clean_nametag(name)

    return NAMETAG + clean_name


async def update_member_nametag(member):
    """
    Wichtig:
    Diese Funktion gibt KEINE Rolle.

    Sie arbeitet ausschließlich mit der bereits
    vorhandenen Nametag-Rolle.
    """

    if member.bot:
        return

    role = member.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        print(
            f"[NAMETAG] Rolle {NAMETAG_ROLE_ID} nicht gefunden."
        )
        return

    has_nametag_role = role in member.roles

    current_name = member.nick or member.name

    if has_nametag_role:
        new_name = make_nametag(
            current_name
        )

        if new_name == current_name:
            return

        if len(new_name) > 32:
            new_name = new_name[:32]

        try:
            await member.edit(
                nick=new_name,
                reason="RLP Nametag"
            )

            print(
                f"[NAMETAG] Aktualisiert: {member} -> {new_name}"
            )

        except discord.Forbidden:
            print(
                f"[NAMETAG] Keine Berechtigung für {member}"
            )

        except discord.HTTPException as error:
            print(
                f"[NAMETAG] Fehler: {error}"
            )

    else:
        # Nametag-Rolle NICHT vorhanden:
        # RLP vom Namen entfernen.
        new_name = clean_nametag(
            current_name
        )

        if new_name == current_name:
            return

        try:
            await member.edit(
                nick=new_name if new_name else None,
                reason="RLP Nametag Reset"
            )

            print(
                f"[NAMETAG] Reset: {member} -> {new_name}"
            )

        except discord.Forbidden:
            print(
                f"[NAMETAG] Keine Berechtigung beim Reset: {member}"
            )

        except discord.HTTPException as error:
            print(
                f"[NAMETAG] Reset-Fehler: {error}"
            )


# =========================================================
# NAMETAG PANEL
# =========================================================

class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Nametag prüfen / aktualisieren",
        emoji="🏷️",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_nametag_refresh"
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await update_member_nametag(
            interaction.user
        )

        role = interaction.guild.get_role(
            NAMETAG_ROLE_ID
        )

        if role and role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ Dein RLP-Nametag wurde aktualisiert.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ Du hast die Nametag-Rolle aktuell nicht.",
                ephemeral=True
            )


def create_nametag_embed():
    embed = discord.Embed(
        title="🏷️ RLP Nametag-System",
        description=(
            "Die Nametag-Rolle steuert dein RLP-Nametag.\n\n"
            f"Wenn du die Rolle `{NAMETAG_ROLE_ID}` besitzt, "
            f"wird automatisch **{NAMETAG}** vor deinen Namen gesetzt.\n\n"
            "Wenn die Rolle entfernt wird, wird das Nametag "
            "beim nächsten Update wieder entfernt.\n\n"
            "**Wichtig:** Das System vergibt diese Rolle nicht selbst."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=PANEL_MARKER + "nametag"
    )

    return embed


# =========================================================
# KENNZEICHEN
# =========================================================

def normalize_plate(plate):
    plate = plate.upper().strip()

    parts = plate.split()

    return " ".join(parts)


def split_plate(plate):
    """
    Beispiele:

    RLP 01
    -> prefix = RLP
    -> number = 01

    RY ZE 01
    -> prefix = RY ZE
    -> number = 01
    """

    parts = normalize_plate(
        plate
    ).split()

    if len(parts) < 2:
        return None, None

    number = parts[-1]

    prefix = " ".join(
        parts[:-1]
    )

    if not prefix:
        return None, None

    # Die Nummer muss wirklich numerisch sein.
    if not number.isdigit():
        return None, None

    return prefix, number


def get_user_plate(user_id):
    entry = data[
        "license_plates"
    ].get(
        str(user_id)
    )

    if not isinstance(entry, dict):
        return None

    return entry.get("plate")


def find_plate_number(
    number,
    ignore_user_id=None
):
    """
    Prüft ausschließlich die Nummer.

    RLP 01
    RY 01
    RY ZE 01

    sind somit alle dieselbe Nummer 01.
    """

    for user_id, entry in data[
        "license_plates"
    ].items():

        if (
            ignore_user_id is not None
            and str(user_id) == str(ignore_user_id)
        ):
            continue

        if not isinstance(entry, dict):
            continue

        saved_plate = entry.get(
            "plate"
        )

        if not saved_plate:
            continue

        _, saved_number = split_plate(
            saved_plate
        )

        if saved_number == number:
            return user_id, saved_plate

    return None, None


def get_all_plates():
    result = []

    for user_id, entry in data[
        "license_plates"
    ].items():

        if not isinstance(entry, dict):
            continue

        plate = entry.get(
            "plate"
        )

        if not plate:
            continue

        result.append(
            (
                int(user_id),
                plate
            )
        )

    result.sort(
        key=lambda item: item[1]
    )

    return result


# =========================================================
# KENNZEICHEN MODAL
# =========================================================

class PlateModal(
    discord.ui.Modal,
    title="Kennzeichen registrieren"
):

    plate_input = discord.ui.TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        min_length=2,
        max_length=20,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        user_id = str(
            interaction.user.id
        )

        existing = get_user_plate(
            user_id
        )

        if existing:
            await interaction.response.send_message(
                (
                    f"❌ Du hast bereits **{existing}** registriert.\n"
                    "Entferne dein aktuelles Kennzeichen zuerst."
                ),
                ephemeral=True
            )
            return

        plate = normalize_plate(
            self.plate_input.value
        )

        prefix, number = split_plate(
            plate
        )

        if prefix is None or number is None:
            await interaction.response.send_message(
                (
                    "❌ Ungültiges Kennzeichen.\n\n"
                    "Beispiele:\n"
                    "`RLP 01`\n"
                    "`RLP 02`\n"
                    "`RLP 03`\n\n"
                    "Die letzte Angabe muss eine Zahl sein."
                ),
                ephemeral=True
            )
            return

        existing_user, existing_plate = find_plate_number(
            number
        )

        if existing_user is not None:
            await interaction.response.send_message(
                (
                    f"❌ Die Nummer **{number}** ist bereits vergeben.\n\n"
                    f"Bereits registriert als: **{existing_plate}**\n\n"
                    "Der Präfix darf sich ändern, die Nummer "
                    "muss trotzdem serverweit einmalig bleiben."
                ),
                ephemeral=True
            )
            return

        data[
            "license_plates"
        ][user_id] = {
            "plate": plate,
            "registered_at": now_text()
        }

        save_data()

        await interaction.response.send_message(
            f"✅ **{plate}** wurde erfolgreich registriert.",
            ephemeral=True
        )

        await update_license_plate_panel()


# =========================================================
# KENNZEICHEN LÖSCHEN
# =========================================================

class PlateDeleteView(
    discord.ui.View
):

    def __init__(
        self,
        user_id
    ):
        super().__init__(
            timeout=60
        )

        self.user_id = str(
            user_id
        )

    @discord.ui.button(
        label="Ja, entfernen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if str(
            interaction.user.id
        ) != self.user_id:
            await interaction.response.send_message(
                "❌ Diese Bestätigung gehört nicht zu dir.",
                ephemeral=True
            )
            return

        plate = get_user_plate(
            self.user_id
        )

        if not plate:
            await interaction.response.edit_message(
                content="❌ Kein Kennzeichen gefunden.",
                view=None
            )
            return

        del data[
            "license_plates"
        ][self.user_id]

        save_data()

        await interaction.response.edit_message(
            content=(
                f"✅ **{plate}** wurde entfernt.\n"
                "Die Nummer ist jetzt wieder frei."
            ),
            view=None
        )

        await update_license_plate_panel()

    @discord.ui.button(
        label="Abbrechen",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if str(
            interaction.user.id
        ) != self.user_id:
            await interaction.response.send_message(
                "❌ Diese Bestätigung gehört nicht zu dir.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="Abgebrochen.",
            view=None
        )


# =========================================================
# KENNZEICHEN VIEW
# =========================================================

class PlateView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Kennzeichen registrieren",
        emoji="🚘",
        style=discord.ButtonStyle.success,
        custom_id="rlp_plate_register"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            PlateModal()
        )

    @discord.ui.button(
        label="Mein Kennzeichen entfernen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_plate_remove"
    )
    async def remove(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        plate = get_user_plate(
            interaction.user.id
        )

        if not plate:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            (
                f"Möchtest du **{plate}** wirklich entfernen?\n"
                "Die Nummer wird danach wieder freigegeben."
            ),
            view=PlateDeleteView(
                interaction.user.id
            ),
            ephemeral=True
        )


def create_license_plate_embed():
    embed = discord.Embed(
        title="🚘 RLP Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen verwalten.\n\n"
            "### Regeln\n"
            "• Jeder Benutzer darf **1 Kennzeichen** besitzen.\n"
            "• Die **Nummer** muss serverweit einmalig sein.\n"
            "• Der Präfix darf mehrfach vorkommen.\n\n"
            "**Beispiel:**\n"
            "✅ `RLP 01`\n"
            "❌ `RY ZE 01` wenn `RLP 01` bereits vergeben ist\n"
            "✅ `RLP 02`\n"
            "✅ `RLP 03`\n\n"
            "Wenn ein Kennzeichen gelöscht wird, wird seine Nummer "
            "wieder freigegeben."
        ),
        color=discord.Color.dark_blue()
    )

    plates = get_all_plates()

    if plates:
        lines = []

        guild = get_guild()

        for user_id, plate in plates:
            member = guild.get_member(
                user_id
            ) if guild else None

            name = (
                member.display_name
                if member
                else f"User {user_id}"
            )

            lines.append(
                f"🚘 **{plate}** — {name}"
            )

        text = "\n".join(
            lines
        )

        if len(text) > 3900:
            text = text[:3890] + "\n..."

        embed.add_field(
            name="Registrierte Kennzeichen",
            value=text,
            inline=False
        )

    else:
        embed.add_field(
            name="Registrierte Kennzeichen",
            value="Noch keine Kennzeichen registriert.",
            inline=False
        )

    embed.set_footer(
        text=PANEL_MARKER + "license"
    )

    return embed


# =========================================================
# SCHICHTSYSTEM
# =========================================================

class ShiftView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Schicht starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="rlp_shift_start"
    )
    async def start(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            await interaction.response.send_message(
                "❌ Nur auf dem Server möglich.",
                ephemeral=True
            )
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Schicht-Berechtigung.",
                ephemeral=True
            )
            return

        user_id = str(
            member.id
        )

        if user_id in data[
            "developer_shifts"
        ]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        data[
            "developer_shifts"
        ][user_id] = {
            "started_at": now_text()
        }

        save_data()

        # NUR HIER wird die aktive Schicht-Rolle vergeben.
        active_role = member.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is not None:
            if active_role not in member.roles:
                try:
                    await member.add_roles(
                        active_role,
                        reason="RLP Schicht gestartet"
                    )

                except discord.Forbidden:
                    await interaction.response.send_message(
                        "❌ Der Bot kann die Schicht-Rolle nicht vergeben. "
                        "Prüfe die Rollen-Hierarchie.",
                        ephemeral=True
                    )
                    return

                except discord.HTTPException as error:
                    print(
                        f"[SHIFT] Rollenfehler: {error}"
                    )

        await send_shift_log(
            member,
            "🟢 Schicht gestartet"
        )

        await interaction.response.send_message(
            "🟢 Deine Schicht wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="rlp_shift_end"
    )
    async def end(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):
            await interaction.response.send_message(
                "❌ Nur auf dem Server möglich.",
                ephemeral=True
            )
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Schicht-Berechtigung.",
                ephemeral=True
            )
            return

        user_id = str(
            member.id
        )

        shift = data[
            "developer_shifts"
        ].get(
            user_id
        )

        if not shift:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        started_at = shift.get(
            "started_at"
        )

        del data[
            "developer_shifts"
        ][user_id]

        save_data()

        # NUR HIER wird die aktive Schicht-Rolle entfernt.
        active_role = member.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is not None:
            if active_role in member.roles:
                try:
                    await member.remove_roles(
                        active_role,
                        reason="RLP Schicht beendet"
                    )

                except discord.HTTPException as error:
                    print(
                        f"[SHIFT] Entfernungsfehler: {error}"
                    )

        await send_shift_log(
            member,
            "🔴 Schicht beendet",
            started_at
        )

        await interaction.response.send_message(
            "🔴 Deine Schicht wurde beendet.",
            ephemeral=True
        )


def create_shift_embed():
    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            "### Schichtsystem\n\n"
            "🟢 **Schicht starten**\n"
            "Startet deine Schicht und gibt dir die aktive "
            "Schicht-Rolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Schicht und entfernt die aktive "
            "Schicht-Rolle.\n\n"
            "### Voraussetzung\n"
            f"Du brauchst die Berechtigungsrolle "
            f"`{SHIFT_PERMISSION_ROLE_ID}`."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=PANEL_MARKER + "shift"
    )

    return embed


async def send_shift_log(
    member,
    action,
    started_at=None
):
    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title=action,
        color=discord.Color.blurple(),
        timestamp=datetime.now(
            timezone.utc
        )
    )

    embed.add_field(
        name="Benutzer",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=False
    )

    if started_at:
        embed.add_field(
            name="Beginn",
            value=started_at,
            inline=False
        )

    embed.set_footer(
        text="RLP Schicht-Log"
    )

    await safe_send(
        channel,
        embed=embed
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(
    discord.ui.Modal,
    title="RLP Bewerbung"
):

    name_input = discord.ui.TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=100,
        required=True
    )

    age_input = discord.ui.TextInput(
        label="Alter",
        placeholder="Dein Alter",
        max_length=3,
        required=True
    )

    text_input = discord.ui.TextInput(
        label="Bewerbung",
        placeholder="Schreibe deine Bewerbung...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        channel = get_channel(
            REVIEW_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blurple(),
            timestamp=datetime.now(
                timezone.utc
            )
        )

        embed.add_field(
            name="Discord",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="Bewerbung",
            value=self.text_input.value,
            inline=False
        )

        await safe_send(
            channel,
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde eingereicht.",
            ephemeral=True
        )


class ApplicationView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bewerben",
        emoji="📨",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_application"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ApplicationModal()
        )


def create_application_embed():
    embed = discord.Embed(
        title="📨 RLP Bewerbung",
        description=(
            "Du möchtest dich bei RLP bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=PANEL_MARKER + "application"
    )

    return embed


# =========================================================
# TASK SYSTEM
# =========================================================

class TaskModal(
    discord.ui.Modal,
    title="Neue Entwickler-Aufgabe"
):

    task_input = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibung...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        data[
            "developer_task_counter"
        ] += 1

        task_id = data[
            "developer_task_counter"
        ]

        data[
            "developer_tasks"
        ][str(task_id)] = {
            "task": self.task_input.value,
            "created_by": interaction.user.id,
            "created_at": now_text(),
            "completed": False
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Aufgabe #{task_id} erstellt.",
            ephemeral=True
        )

        await update_task_panel()


class TaskView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="rlp_task_create"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TaskModal()
        )


def create_task_embed():
    embed = discord.Embed(
        title="📝 Entwickler-Aufgaben",
        description="Verwaltung der aktuellen Entwickler-Aufgaben.",
        color=discord.Color.blurple()
    )

    tasks = data.get(
        "developer_tasks",
        {}
    )

    active = [
        (task_id, task)
        for task_id, task in tasks.items()
        if not task.get(
            "completed",
            False
        )
    ]

    if not active:
        embed.add_field(
            name="Offene Aufgaben",
            value="Keine offenen Aufgaben.",
            inline=False
        )

    else:
        lines = []

        for task_id, task in active[:20]:
            lines.append(
                f"**#{task_id}** — {task.get('task', 'Keine Beschreibung')}"
            )

        embed.add_field(
            name="Offene Aufgaben",
            value="\n".join(lines),
            inline=False
        )

    embed.set_footer(
        text=PANEL_MARKER + "tasks"
    )

    return embed


# =========================================================
# PANEL SYSTEM
# =========================================================

async def upsert_panel(
    channel_id,
    embed,
    view
):
    channel = get_channel(
        channel_id
    )

    if channel is None:
        print(
            f"[PANEL] Channel {channel_id} nicht gefunden."
        )
        return

    marker = panel_marker_from_embed(
        embed
    )

    if not marker:
        return

    existing = None

    try:
        async for message in channel.history(
            limit=200
        ):
            if not message.author.bot:
                continue

            if panel_marker(message) == marker:
                existing = message
                break

    except discord.HTTPException as error:
        print(
            f"[PANEL] Fehler: {error}"
        )

    if existing:
        try:
            await existing.edit(
                embed=embed,
                view=view
            )
            return

        except discord.HTTPException:
            pass

    await safe_send(
        channel,
        embed=embed,
        view=view
    )


def panel_marker_from_embed(embed):
    if not embed.footer:
        return None

    text = embed.footer.text or ""

    if text.startswith(PANEL_MARKER):
        return text

    return None


async def clean_panels():
    channel_ids = [
        APPLICATION_CHANNEL_ID,
        NICKNAME_CHANNEL_ID,
        DEVELOPER_TASK_CHANNEL_ID,
        DEVELOPER_SHIFT_CHANNEL_ID
    ]

    for channel_id in set(
        channel_ids
    ):
        channel = get_channel(
            channel_id
        )

        if channel is None:
            continue

        try:
            async for message in channel.history(
                limit=200
            ):
                if not message.author.bot:
                    continue

                if panel_marker(message):
                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

        except discord.HTTPException as error:
            print(
                f"[PANEL] Cleanup-Fehler: {error}"
            )


async def send_all_panels():
    await upsert_panel(
        NICKNAME_CHANNEL_ID,
        create_nametag_embed(),
        NametagView()
    )

    await upsert_panel(
        NICKNAME_CHANNEL_ID,
        create_license_plate_embed(),
        PlateView()
    )

    await upsert_panel(
        APPLICATION_CHANNEL_ID,
        create_application_embed(),
        ApplicationView()
    )

    await upsert_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        create_task_embed(),
        TaskView()
    )

    await upsert_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        create_shift_embed(),
        ShiftView()
    )


async def update_license_plate_panel():
    await upsert_panel(
        NICKNAME_CHANNEL_ID,
        create_license_plate_embed(),
        PlateView()
    )


async def update_task_panel():
    await upsert_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        create_task_embed(),
        TaskView()
    )


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_POOL = [
    {
        "emoji": "🚗⛽",
        "answer": "Tanken",
        "options": [
            "Tanken",
            "Parken",
            "Waschen",
            "Reparieren"
        ]
    },
    {
        "emoji": "🚓🚨",
        "answer": "Polizei",
        "options": [
            "Polizei",
            "Feuerwehr",
            "Taxi",
            "Werkstatt"
        ]
    },
    {
        "emoji": "🚒🔥",
        "answer": "Feuerwehr",
        "options": [
            "Polizei",
            "Feuerwehr",
            "Rettungsdienst",
            "Werkstatt"
        ]
    },
    {
        "emoji": "🚑🏥",
        "answer": "Rettungsdienst",
        "options": [
            "Taxi",
            "Rettungsdienst",
            "Polizei",
            "Werkstatt"
        ]
    },
    {
        "emoji": "🔧🚗",
        "answer": "Werkstatt",
        "options": [
            "Werkstatt",
            "Tankstelle",
            "Polizei",
            "Parkplatz"
        ]
    },
    {
        "emoji": "🅿️🚗",
        "answer": "Parken",
        "options": [
            "Tanken",
            "Parken",
            "Waschen",
            "Fahren"
        ]
    },
    {
        "emoji": "🚦🔴",
        "answer": "Rote Ampel",
        "options": [
            "Grüne Ampel",
            "Rote Ampel",
            "Baustelle",
            "Stoppschild"
        ]
    },
    {
        "emoji": "🛑🚗",
        "answer": "Stoppschild",
        "options": [
            "Stoppschild",
            "Vorfahrt",
            "Kreisverkehr",
            "Ampel"
        ]
    },
    {
        "emoji": "🔄🚘",
        "answer": "Kreisverkehr",
        "options": [
            "Kreisverkehr",
            "Autobahn",
            "Parkplatz",
            "Tankstelle"
        ]
    },
    {
        "emoji": "🚘💨",
        "answer": "Schnell fahren",
        "options": [
            "Schnell fahren",
            "Parken",
            "Tanken",
            "Waschen"
        ]
    }
]


def create_quiz_embed(
    question
):
    embed = discord.Embed(
        title="🧠 RLP Emoji Quiz",
        description=(
            "Errate den Begriff anhand der Emojis.\n\n"
            f"## {question['emoji']}\n\n"
            "Wähle anschließend die passende Antwort."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Emoji Quiz"
    )

    return embed


class QuizView(
    discord.ui.View
):

    def __init__(
        self,
        question
    ):
        super().__init__(
            timeout=30
        )

        options = question[
            "options"
        ]

        for index, option in enumerate(
            options
        ):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rlp_quiz_{index}"
            )

            async def callback(
                interaction,
                selected=option
            ):
                await answer_quiz(
                    interaction,
                    selected,
                    question
                )

            button.callback = callback

            self.add_item(
                button
            )


async def answer_quiz(
    interaction,
    selected,
    question
):
    global quiz_message_id
    global current_quiz

    async with quiz_lock:

        if current_quiz is None:
            await interaction.response.send_message(
                "⚠️ Dieses Quiz ist bereits beendet.",
                ephemeral=True
            )
            return

        if selected != question["answer"]:
            await interaction.response.send_message(
                "❌ Falsch! Versuch es bei der nächsten Frage.",
                ephemeral=True
            )
            return

        user_id = str(
            interaction.user.id
        )

        data[
            "quiz_scores"
        ][user_id] = (
            data[
                "quiz_scores"
            ].get(
                user_id,
                0
            ) + 1
        )

        save_data()

        quiz_message_id = None
        current_quiz = None

        await interaction.response.send_message(
            "✅ Richtig! +1 Punkt.",
            ephemeral=True
        )

        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass

    await asyncio.sleep(1)

    await send_new_quiz()


async def send_new_quiz():
    global quiz_message_id
    global current_quiz

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    async with quiz_lock:

        question = random.choice(
            QUIZ_POOL
        )

        current_quiz = question

        try:
            message = await channel.send(
                embed=create_quiz_embed(
                    question
                ),
                view=QuizView(
                    question
                )
            )

            quiz_message_id = message.id

        except discord.HTTPException as error:
            print(
                f"[QUIZ] Fehler: {error}"
            )

            current_quiz = None
            quiz_message_id = None


async def clear_quiz_channel():
    global quiz_message_id
    global current_quiz

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    quiz_message_id = None
    current_quiz = None

    try:
        async for message in channel.history(
            limit=None
        ):
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    except discord.HTTPException as error:
        print(
            f"[QUIZ] Cleanup-Fehler: {error}"
        )


async def quiz_cleanup_loop():
    global quiz_message_id

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:
            channel = get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel:

                active_id = quiz_message_id

                async for message in channel.history(
                    limit=None
                ):
                    if (
                        active_id is not None
                        and message.id == active_id
                    ):
                        continue

                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

        except Exception as error:
            print(
                f"[QUIZ CLEANUP] {error}"
            )

        await asyncio.sleep(5)


# =========================================================
# SUPPORT VOICE
# =========================================================

async def send_support_voice_log(
    member,
    action
):
    channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🎧 Support Voice",
        color=discord.Color.blurple(),
        timestamp=datetime.now(
            timezone.utc
        )
    )

    embed.add_field(
        name="Benutzer",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="Aktion",
        value=action,
        inline=False
    )

    await safe_send(
        channel,
        embed=embed
    )


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    global startup_finished
    global quiz_cleanup_task

    print(
        f"[BOT] Online als {bot.user}"
    )

    guild = get_guild()

    if guild is None:
        print(
            "[BOT] Server nicht gefunden."
        )
        return

    if startup_finished:
        return

    startup_finished = True

    # Persistente Buttons.
    bot.add_view(
        NametagView()
    )

    bot.add_view(
        PlateView()
    )

    bot.add_view(
        ShiftView()
    )

    bot.add_view(
        TaskView()
    )

    bot.add_view(
        ApplicationView()
    )

    # =====================================================
    # WICHTIG:
    # HIER WIRD KEINE ROLLE VERGEBEN.
    #
    # Die Nametag-Rolle wird NICHT automatisch verteilt.
    # Wir prüfen lediglich Mitglieder, die die Rolle
    # BEREITS besitzen.
    # =====================================================

    for member in guild.members:

        if member.bot:
            continue

        # Nametag nur anhand der bereits vorhandenen Rolle.
        await update_member_nametag(
            member
        )

    # =====================================================
    # SCHICHTEN
    #
    # Nur bereits gespeicherte aktive Schichten
    # bekommen ihre aktive Schicht-Rolle zurück.
    #
    # Es wird NICHT jeder mit Berechtigungsrolle
    # automatisch in eine Schicht gesetzt.
    # =====================================================

    active_role = guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if active_role:

        for user_id in list(
            data[
                "developer_shifts"
            ].keys()
        ):

            member = guild.get_member(
                int(user_id)
            )

            if member is None:
                continue

            if active_role not in member.roles:

                try:
                    await member.add_roles(
                        active_role,
                        reason="RLP aktive Schicht wiederherstellen"
                    )

                except discord.HTTPException as error:
                    print(
                        f"[SHIFT] Wiederherstellung: {error}"
                    )

    # =====================================================
    # PANELS
    # =====================================================

    await clean_panels()

    await send_all_panels()

    # =====================================================
    # QUIZ
    # =====================================================

    await clear_quiz_channel()

    await send_new_quiz()

    if (
        quiz_cleanup_task is None
        or quiz_cleanup_task.done()
    ):
        quiz_cleanup_task = asyncio.create_task(
            quiz_cleanup_loop()
        )

    print(
        "[BOT] Alle Systeme gestartet."
    )


@bot.event
async def on_member_join(
    member
):
    if member.guild.id != GUILD_ID:
        return

    if member.bot:
        return

    # KEINE Rolle vergeben.
    #
    # Nur wenn der User die Nametag-Rolle bereits besitzt,
    # wird das Nametag verarbeitet.
    await update_member_nametag(
        member
    )


@bot.event
async def on_member_update(
    before,
    after
):
    if after.guild.id != GUILD_ID:
        return

    if before.roles == after.roles:
        return

    nametag_role = after.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if nametag_role is None:
        return

    before_has = nametag_role in before.roles
    after_has = nametag_role in after.roles

    if before_has != after_has:
        await update_member_nametag(
            after
        )


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):
    if member.bot:
        return

    joined = (
        after.channel is not None
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
    )

    left = (
        before.channel is not None
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
    )

    if joined and not left:
        await send_support_voice_log(
            member,
            "🟢 Support-Voice betreten"
        )

    elif left and not joined:
        await send_support_voice_log(
            member,
            "🔴 Support-Voice verlassen"
        )


@bot.event
async def on_message(
    message
):
    if message.author.bot:
        return

    if message.guild is None:
        await bot.process_commands(
            message
        )
        return

    if message.guild.id != GUILD_ID:
        await bot.process_commands(
            message
        )
        return

    await bot.process_commands(
        message
    )


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
async def ping(
    ctx
):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def quizscore(
    ctx
):
    score = data[
        "quiz_scores"
    ].get(
        str(ctx.author.id),
        0
    )

    await ctx.send(
        f"🧠 {ctx.author.mention}, dein Score: **{score}**"
    )


@bot.command()
async def kennzeichen(
    ctx
):
    plate = get_user_plate(
        ctx.author.id
    )

    if plate:
        await ctx.send(
            f"🚘 Dein Kennzeichen: **{plate}**"
        )
    else:
        await ctx.send(
            "🚘 Du hast kein Kennzeichen registriert."
        )


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
