import os
import sqlite3

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL = "@eclipsedlf"
CHANNEL_URL = "https://t.me/eclipsedlf"

REWARD = 0.50
MIN_WITHDRAW = 15.0

PROMO = "15kleeps"
PROMO_REWARD = 15.0
PROMO_LIMIT = 10


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


cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_uses (
    user_id INTEGER PRIMARY KEY,
    promo TEXT NOT NULL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS promos (
    promo TEXT PRIMARY KEY,
    reward REAL,
    max_uses INTEGER,
    uses INTEGER DEFAULT 0
)
""")


cursor.execute("""
INSERT OR IGNORE INTO promos
(promo, reward, max_uses, uses)
VALUES (?, ?, ?, 0)
""", (PROMO, PROMO_REWARD, PROMO_LIMIT))


db.commit()


def get_user(user_id, username=""):
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        db.commit()


def keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💰 Баланс", "👥 Рефералы"],
            ["💸 Вывод", "📢 Канал"],
        ],
        resize_keyboard=True
    )


async def is_subscribed(context, user_id):
    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    get_user(user.id, user.username or "")

    # Реферальная система
    if context.args:

        try:
            inviter_id = int(context.args[0])

            if inviter_id != user.id:

                cursor.execute(
                    """
                    SELECT invited_by
                    FROM users
                    WHERE user_id = ?
                    """,
                    (user.id,)
                )

                row = cursor.fetchone()

                if row and row[0] is None:

                    cursor.execute(
                        """
                        UPDATE users
                        SET invited_by = ?
                        WHERE user_id = ?
                        """,
                        (inviter_id, user.id)
                    )

                    cursor.execute(
                        """
                        UPDATE users
                        SET balance = balance + ?,
                            referrals = referrals + 1
                        WHERE user_id = ?
                        """,
                        (REWARD, inviter_id)
                    )

                    db.commit()

        except (ValueError, TypeError):
            pass


    if not await is_subscribed(context, user.id):

        await update.message.reply_text(
            "👋 Привет!\n\n"
            "Чтобы пользоваться ботом, сначала подпишись "
            "на канал @eclipsedlf.\n\n"
            "После подписки снова нажми /start.",
            reply_markup=keyboard()
        )

        return


    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "⭐ Приглашай пользователей и получай "
        "0.50 Stars за каждого.\n\n"
        "🎁 Также можешь активировать промокоды.",
        reply_markup=keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    get_user(user.id, user.username or "")


    if not await is_subscribed(context, user.id):

        await update.message.reply_text(
            "❌ Сначала подпишись на канал @eclipsedlf.",
            reply_markup=keyboard()
        )

        return


    # ПРОМОКОД
    if text.lower() == PROMO.lower():

        cursor.execute(
            """
            SELECT user_id
            FROM promo_uses
            WHERE user_id = ?
            """,
            (user.id,)
        )

        if cursor.fetchone():

            await update.message.reply_text(
                "❌ Ты уже активировал этот промокод.",
                reply_markup=keyboard()
            )

            return


        cursor.execute(
            """
            SELECT reward, max_uses, uses
            FROM promos
            WHERE promo = ?
            """,
            (PROMO,)
        )

        promo_data = cursor.fetchone()


        if not promo_data:

            await update.message.reply_text(
                "❌ Промокод не найден.",
                reply_markup=keyboard()
            )

            return


        reward, max_uses, uses = promo_data


        if uses >= max_uses:

            await update.message.reply_text(
                "❌ Все активации этого промокода уже закончились.",
                reply_markup=keyboard()
            )

            return


        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (reward, user.id)
        )


        cursor.execute(
            """
            INSERT INTO promo_uses
            (user_id, promo)
            VALUES (?, ?)
            """,
            (user.id, PROMO)
        )


        cursor.execute(
            """
            UPDATE promos
            SET uses = uses + 1
            WHERE promo = ?
            """,
            (PROMO,)
        )


        db.commit()


        remaining = max_uses - uses - 1


        await update.message.reply_text(
            "🎉 Промокод активирован!\n\n"
            f"⭐ Начислено: {reward:.0f} Stars\n"
            f"🔥 Осталось активаций: {remaining}",
            reply_markup=keyboard()
        )

        return


    # БАЛАНС
    if text == "💰 Баланс":

        cursor.execute(
            """
            SELECT balance, referrals
            FROM users
            WHERE user_id = ?
            """,
            (user.id,)
        )

        data = cursor.fetchone()

        balance = data[0] if data else 0
        referrals = data[1] if data else 0


        await update.message.reply_text(
            f"💰 Баланс: {balance:.2f} ⭐\n"
            f"👥 Рефералов: {referrals}",
            reply_markup=keyboard()
        )

        return


    # РЕФЕРАЛЫ
    if text == "👥 Рефералы":

        bot = await context.bot.get_me()

        referral_link = (
            f"https://t.me/{bot.username}?start={user.id}"
        )


        await update.message.reply_text(
            "👥 Твоя реферальная ссылка:\n\n"
            f"{referral_link}\n\n"
            f"⭐ За одного приглашённого: {REWARD:.2f} Stars",
            reply_markup=keyboard()
        )

        return


    # ВЫВОД
    if text == "💸 Вывод":

        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user.id,)
        )

        data = cursor.fetchone()

        balance = data[0] if data else 0


        if balance < MIN_WITHDRAW:

            await update.message.reply_text(
                f"💸 Минимальный вывод: {MIN_WITHDRAW:.0f} ⭐\n\n"
                f"Твой баланс: {balance:.2f} ⭐",
                reply_markup=keyboard()
            )

        else:

            await update.message.reply_text(
                "💸 У тебя достаточно Stars для вывода.\n\n"
                "Систему заявок на вывод подключим следующим этапом.",
                reply_markup=keyboard()
            )

        return


    # КАНАЛ
    if text == "📢 Канал":

        await update.message.reply_text(
            f"📢 Наш канал:\n{CHANNEL_URL}",
            reply_markup=keyboard()
        )

        return


def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в GitHub Secrets"
        )


    app = Application.builder().token(BOT_TOKEN).build()


    app.add_handler(
        CommandHandler("start", start)
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )


    print("Bot started!")

    app.run_polling()


if __name__ == "__main__":
    main()
