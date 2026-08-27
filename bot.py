import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@eclipsedlf"
REWARD = 0.50
MIN_WITHDRAW = 15.0

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    invited_by INTEGER,
    referrals INTEGER DEFAULT 0
)
""")
db.commit()


def get_user(user_id, username=None):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username or "")
        )
        db.commit()

    return user


async def is_subscribed(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        ],
        [
            InlineKeyboardButton("💸 Вывод", callback_data="withdraw"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username)

    # Реферальная ссылка: /start 123456
    if context.args:
        try:
            inviter_id = int(context.args[0])

            if inviter_id != user.id:
                cursor.execute(
                    "SELECT invited_by FROM users WHERE user_id = ?",
                    (user.id,)
                )
                row = cursor.fetchone()

                if row and row[0] is None:
                    cursor.execute(
                        "UPDATE users SET invited_by = ? WHERE user_id = ?",
                        (inviter_id, user.id)
                    )

                    cursor.execute(
                        "UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id = ?",
                        (REWARD, inviter_id)
                    )

                    db.commit()
        except (ValueError, TypeError):
            pass

    subscribed = await is_subscribed(context, user.id)

    if not subscribed:
        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 Подписаться",
                    url="https://t.me/eclipsedlf"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Проверить подписку",
                    callback_data="check_sub"
                )
            ]
        ]

        await update.message.reply_text(
            "👋 Привет!\n\n"
            "Чтобы пользоваться ботом, сначала подпишись на наш канал.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "💰 Получай 0.50 ⭐ за каждого приглашённого пользователя.",
        reply_markup=main_menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_sub":
        if await is_subscribed(context, user_id):
            await query.edit_message_text(
                "✅ Подписка подтверждена!\n\n"
                "Теперь можешь пользоваться ботом.",
                reply_markup=main_menu()
            )
        else:
            await query.answer(
                "❌ Ты ещё не подписался на канал.",
                show_alert=True
            )

    elif query.data == "balance":
        cursor.execute(
            "SELECT balance, referrals FROM users WHERE user_id = ?",
            (user_id,)
        )
        data = cursor.fetchone()

        balance = data[0] if data else 0
        referrals = data[1] if data else 0

        await query.edit_message_text(
            f"💰 Твой баланс: {balance:.2f} ⭐\n"
            f"👥 Приглашено: {referrals}",
            reply_markup=main_menu()
        )

    elif query.data == "referrals":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"

        await query.edit_message_text(
            "👥 Твоя реферальная ссылка:\n\n"
            f"{link}\n\n"
            "За каждого приглашённого пользователя начисляется 0.50 ⭐.",
            reply_markup=main_menu()
        )

    elif query.data == "withdraw":
        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,)
        )
        data = cursor.fetchone()
        balance = data[0] if data else 0

        if balance < MIN_WITHDRAW:
            await query.edit_message_text(
                f"💸 Минимальная сумма вывода — {MIN_WITHDRAW:.0f} ⭐.\n\n"
                f"Твой баланс: {balance:.2f} ⭐",
                reply_markup=main_menu()
            )
        else:
            await query.edit_message_text(
                "💸 Ты можешь оформить заявку на вывод.\n\n"
                "Функцию автоматической выплаты подключим следующим этапом.",
                reply_markup=main_menu()
            )


def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    run()
