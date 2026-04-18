import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from threading import Thread
from flask import Flask
from bot_data import TRUTHS, DARES, WOULD_YOU_RATHER, ROASTS, FATES


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  DATABASE SETUP  (persistent on Railway disk)
# ─────────────────────────────────────────────
DB_PATH = "/app/scores.db"


def init_db():
    """Create scores table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            user_id   INTEGER PRIMARY KEY,
            name      TEXT,
            truths    INTEGER DEFAULT 0,
            dares     INTEGER DEFAULT 0,
            wyr       INTEGER DEFAULT 0,
            roasts    INTEGER DEFAULT 0,
            fates     INTEGER DEFAULT 0,
            total     INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized at %s", DB_PATH)


def update_score(user, command: str):
    """Increment the relevant counter for a user in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Insert user row if first time
    c.execute('''
        INSERT OR IGNORE INTO scores (user_id, name)
        VALUES (?, ?)
    ''', (user.id, user.first_name))
    # Update name (handles name changes) and bump the column
    c.execute(f'''
        UPDATE scores
        SET name = ?, {command} = {command} + 1, total = total + 1
        WHERE user_id = ?
    ''', (user.first_name, user.id))
    conn.commit()
    conn.close()


def get_score_text(uid: int) -> str:
    """Return a formatted score string for one user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT truths, dares, wyr, roasts, fates, total FROM scores WHERE user_id = ?',
        (uid,)
    )
    row = c.fetchone()
    conn.close()

    if not row or row[5] == 0:
        return "No questions asked yet! Start playing 🎮"

    truths, dares, wyr, roasts, fates, total = row
    return (
        f"🤔 Truths asked : {truths}\n"
        f"💪 Dares asked  : {dares}\n"
        f"🤔💭 WYR asked  : {wyr}\n"
        f"🔥 Roasts asked : {roasts}\n"
        f"🔮 Fates asked  : {fates}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 Total         : {total}"
    )


def get_leaderboard() -> list:
    """Return top 10 users sorted by total questions."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, total FROM scores ORDER BY total DESC LIMIT 10')
    rows = c.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  BOT COMMAND SETUP  (slash-menu in Telegram)
# ─────────────────────────────────────────────
async def post_init(application: Application) -> None:
    """Register commands so they appear when users type '/' in Telegram."""
    await application.bot.set_my_commands([
        BotCommand("start",       "Start the bot 🎭"),
        BotCommand("help",        "Show help message ❓"),
        BotCommand("play",        "Start playing with buttons 🎮"),
        BotCommand("truth",       "Get a truth question 🤔"),
        BotCommand("dare",        "Get a dare challenge 💪"),
        BotCommand("wyr",         "Would you rather 🤔💭"),
        BotCommand("roast",       "Get roasted 🔥"),
        BotCommand("fate",        "Get your fate prediction 🔮"),
        BotCommand("score",       "View your personal scorecard 📊"),
        BotCommand("leaderboard", "See top players 🏆"),
    ])


# ─────────────────────────────────────────────
#  CORE COMMANDS
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat_type = update.effective_chat.type

    if chat_type == "private":
        welcome_message = (
            f"🎭 Welcome {user.mention_html()}!\n\n"
            "I'm your Truth or Dare bot with extra fun features!\n\n"
            "<b>Commands:</b>\n"
            "🎮 /play - Start playing with buttons\n"
            "🤔 /truth - Get a truth question\n"
            "💪 /dare - Get a dare challenge\n"
            "🤔💭 /wyr - Would you rather\n"
            "🔥 /roast - Get roasted\n"
            "🔮 /fate - Your fate prediction\n"
            "📊 /score - View your scorecard\n"
            "🏆 /leaderboard - See top players\n"
            "❓ /help - Show help message\n\n"
            "💡 <b>Tip:</b> Add me to a group chat to play with friends!\n\n"
            "Let's have some fun! 🎉"
        )
        await update.message.reply_html(welcome_message)
    else:
        welcome_message = (
            f"🎭 Hello everyone! I'm the Truth or Dare bot!\n\n"
            "<b>How to play:</b>\n"
            "• Type /truth for a truth question\n"
            "• Type /dare for a dare challenge\n"
            "• Type /wyr for would you rather\n"
            "• Type /roast to get roasted\n"
            "• Type /fate for your fate prediction\n"
            "• Type /score to see your scorecard\n"
            "• Type /leaderboard to see top players\n"
            "• Type /help for more info\n\n"
            "Ready to have some fun? 🎉"
        )
        await update.message.reply_html(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    chat_type = update.effective_chat.type

    if chat_type == "private":
        help_text = (
            "🎮 <b>How to Play (Private Chat):</b>\n\n"
            "<b>Button Mode:</b>\n"
            "🎮 /play - Start with interactive buttons\n\n"
            "<b>Direct Commands:</b>\n"
            "🤔 /truth - Get a random truth question\n"
            "💪 /dare - Get a random dare challenge\n"
            "🤔💭 /wyr - Would you rather question\n"
            "🔥 /roast - Get roasted by the bot\n"
            "🔮 /fate - Get your fate prediction\n\n"
            "<b>Scorecard:</b>\n"
            "📊 /score - View your personal scorecard\n"
            "🏆 /leaderboard - See the top players\n\n"
            "❓ /help - Show this help message\n\n"
            "💡 <b>Tip:</b> Use /play for easy button navigation!\n\n"
            "Enjoy! 🎉"
        )
    else:
        help_text = (
            "🎮 <b>How to Play (Group Chat):</b>\n\n"
            "<b>Commands:</b>\n"
            "🤔 /truth - Get a random truth question\n"
            "💪 /dare - Get a random dare challenge\n"
            "🤔💭 /wyr - Would you rather question\n"
            "🔥 /roast - Get roasted by the bot\n"
            "🔮 /fate - Get your fate prediction\n\n"
            "<b>Scorecard:</b>\n"
            "📊 /score - View your personal scorecard\n"
            "🏆 /leaderboard - See the top players\n\n"
            "❓ /help - Show this help message\n\n"
            "<b>Group Play:</b>\n"
            "• Take turns and have fun!\n"
            "• Be honest and brave! 💪\n\n"
            "Enjoy! 🎉"
        )

    await update.message.reply_html(help_text)


async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show game buttons - only works in private chat."""
    chat_type = update.effective_chat.type

    if chat_type != "private":
        await update.message.reply_text(
            "🎮 Button mode only works in private chat!\n\n"
            "In groups, use commands directly:\n"
            "/truth, /dare, /wyr, /roast, /fate"
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("🤔 Truth", callback_data="truth"),
            InlineKeyboardButton("💪 Dare", callback_data="dare"),
        ],
        [InlineKeyboardButton("🤔💭 Would You Rather", callback_data="wyr")],
        [
            InlineKeyboardButton("🔥 Roast Me", callback_data="roast"),
            InlineKeyboardButton("🔮 My Fate", callback_data="fate"),
        ],
        [InlineKeyboardButton("📊 My Score", callback_data="score")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎭 <b>Choose Your Game!</b>\n\nPick what you want to play:",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
#  GAME COMMANDS
# ─────────────────────────────────────────────
async def truth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_score(user, "truths")
    truth = random.choice(TRUTHS)
    await update.message.reply_html(
        f"🤔 <b>TRUTH for {user.mention_html()}:</b>\n\n{truth}\n\n"
    )


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_score(user, "dares")
    dare = random.choice(DARES)
    await update.message.reply_html(
        f"💪 <b>DARE for {user.mention_html()}:</b>\n\n{dare}\n\n"
    )


async def wyr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_score(user, "wyr")
    wyr = random.choice(WOULD_YOU_RATHER)
    await update.message.reply_html(
        f"🤔💭 <b>WOULD YOU RATHER for {user.mention_html()}:</b>\n\n{wyr}\n\n"
    )


async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_score(user, "roasts")
    roast = random.choice(ROASTS)
    await update.message.reply_html(
        f"🔥 <b>ROAST for {user.mention_html()}:</b>\n\n{roast}\n\n"
    )


async def fate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_score(user, "fates")
    fate = random.choice(FATES)
    await update.message.reply_html(
        f"🔮 <b>FATE PREDICTION for {user.mention_html()}:</b>\n\n{fate}\n\n"
    )


# ─────────────────────────────────────────────
#  SCORECARD COMMANDS
# ─────────────────────────────────────────────
async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show personal scorecard."""
    user = update.effective_user
    score_text = get_score_text(user.id)
    await update.message.reply_html(
        f"📊 <b>Scorecard for {user.mention_html()}:</b>\n\n{score_text}"
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top 10 players leaderboard."""
    rows = get_leaderboard()

    if not rows:
        await update.message.reply_text("No scores yet! Start playing first 🎮")
        return

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [
        f"{medals[i]} <b>{name}</b> — {total} questions"
        for i, (name, total) in enumerate(rows)
    ]

    await update.message.reply_html(
        f"🏆 <b>LEADERBOARD — Top Players</b>\n\n"
        + "\n".join(lines)
        + "\n\n📊 Use /score to see your own stats!"
    )


# ─────────────────────────────────────────────
#  BUTTON CALLBACKS
# ─────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses — sends a NEW message each time."""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # Keyboard shown after every result
    keyboard = [
        [
            InlineKeyboardButton("🤔 Truth", callback_data="truth"),
            InlineKeyboardButton("💪 Dare", callback_data="dare"),
        ],
        [InlineKeyboardButton("🤔💭 Would You Rather", callback_data="wyr")],
        [
            InlineKeyboardButton("🔥 Roast Me", callback_data="roast"),
            InlineKeyboardButton("🔮 My Fate", callback_data="fate"),
        ],
        [InlineKeyboardButton("📊 My Score", callback_data="score")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == "truth":
        update_score(user, "truths")
        message = f"🤔 <b>TRUTH:</b>\n\n{random.choice(TRUTHS)}\n\n"

    elif query.data == "dare":
        update_score(user, "dares")
        message = f"💪 <b>DARE:</b>\n\n{random.choice(DARES)}\n\n"

    elif query.data == "wyr":
        update_score(user, "wyr")
        message = f"🤔💭 <b>WOULD YOU RATHER:</b>\n\n{random.choice(WOULD_YOU_RATHER)}\n\n"

    elif query.data == "roast":
        update_score(user, "roasts")
        message = f"🔥 <b>ROAST:</b>\n\n{random.choice(ROASTS)}\n\n"

    elif query.data == "fate":
        update_score(user, "fates")
        message = f"🔮 <b>FATE PREDICTION:</b>\n\n{random.choice(FATES)}\n\n"

    elif query.data == "score":
        score_text = get_score_text(user.id)
        await query.message.reply_html(
            f"📊 <b>Scorecard for {user.mention_html()}:</b>\n\n{score_text}\n\n",
            reply_markup=reply_markup
        )
        return

    else:
        message = "Something went wrong! Try again."

    await query.message.reply_html(message, reply_markup=reply_markup)


# ─────────────────────────────────────────────
#  FLASK  (keep-alive ping endpoint)
# ─────────────────────────────────────────────
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "✅ Truth or Dare Bot is running!"


@flask_app.route("/health")
def health():
    return "OK"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main() -> None:
    """Start the bot."""
    TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")

    if TOKEN == "YOUR_TOKEN_HERE":
        print("⚠️  WARNING: Please set your bot token!")
        print("For local testing, replace 'YOUR_TOKEN_HERE' in the code.")
        print("For Railway, set the BOT_TOKEN environment variable.")
        return

    # Initialize persistent SQLite database
    init_db()

    # Build application
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Game commands
    application.add_handler(CommandHandler("start",       start))
    application.add_handler(CommandHandler("help",        help_command))
    application.add_handler(CommandHandler("play",        play_command))
    application.add_handler(CommandHandler("truth",       truth_command))
    application.add_handler(CommandHandler("dare",        dare_command))
    application.add_handler(CommandHandler("wyr",         wyr_command))
    application.add_handler(CommandHandler("roast",       roast_command))
    application.add_handler(CommandHandler("fate",        fate_command))

    # Scorecard commands
    application.add_handler(CommandHandler("score",       score_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # Button callbacks
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start Flask keep-alive in background thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("✅ Bot is running... Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
