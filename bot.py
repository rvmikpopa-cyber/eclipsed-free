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

REFERRAL_REWARD = 0.50
MIN_WITHDRAW = 15.0

# Секретный промокод
PROMO = "15kleeps"
PROMO_REWARD = 10.0
PROMO_LIMIT = 10


# =========================
# DATABASE
# =========================

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    invited_by INTEGER,
    referrals INTEGER DEFAULT 0,
    subscribed INTEGER DEFAULT 0
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


# =========================
# MENU
# =========================

def keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💰 Баланс", "👥 Рефералы"],
            ["💸 Вывод", "🎁 Промокод"],
            ["📢 Канал"]
        ],
        resize_keyboard=True
    )


# =========================
# USER
# =========================

def get_user(user_id, username=""):
    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        cursor.execute(
            """
            INSERT INTO users
            (user_id, username)
            VALUES (?, ?)
            """,
            (user_id, username)
        )
        db.commit()

    return user


# =========================
# SUBSCRIPTION
# =========================

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


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    # Проверяем подписку
    subscribed = await is_subscribed(
        context,
        user.id
    )

    if not subscribed:

        await update.message.reply_text(
            "👋 Привет!\n\n"
            "Для использования бота подпишись "
            "на канал @eclipsedlf.\n\n"
            "После подписки снова нажми /start.",
            reply_markup=keyboard()
        )

        return

    # =========================
    # REFERRAL PROTECTION
    # =========================

    if context.args:

        try:
            inviter_id = int(context.args[0])

            # Нельзя пригласить самого себя
            if inviter_id != user.id:

                # Проверяем, существует ли пригласивший
                cursor.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id = ?
                    """,
                    (inviter_id,)
                )

                inviter_exists = cursor.fetchone()

                if inviter_exists:

                    # Проверяем, был ли пользователь
                    # уже привязан к другому пригласившему
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
                            SET invited_by = ?,
                                subscribed = 1
                            WHERE user_id = ?
                            """,
                            (
                                inviter_id,
                                user.id
                            )
                        )

                        # Начисляем только один раз
                        cursor.execute(
                            """
                            UPDATE users
                            SET balance = balance + ?,
                                referrals = referrals + 1
                            WHERE user_id = ?
                            """,
                            (
                                REFERRAL_REWARD,
                                inviter_id
                            )
                        )

                        db.commit()

        except (ValueError, TypeError):
            pass

    cursor.execute(
        """
        UPDATE users
        SET subscribed = 1
        WHERE user_id = ?
        """,
        (user.id,)
    )

    db.commit()

    await update.message.reply_text(
        "✅ Подписка подтверждена!\n\n"
        "⭐ Приглашай пользователей и получай "
        "0.50 Stars за каждого.",
        reply_markup=keyboard()
    )


# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user
    text = update.message.text.strip()

    get_user(
        user.id,
        user.username or ""
    )

    # Проверка подписки
    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return


    # =========================
    # BALANCE
    # =========================

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


    # =========================
    # REFERRALS
    # =========================

    if text == "👥 Рефералы":

        bot = await context.bot.get_me()

        referral_link = (
            f"https://t.me/"
            f"{bot.username}"
            f"?start={user.id}"
        )

        await update.message.reply_text(
            "👥 Твоя реферальная ссылка:\n\n"
            f"{referral_link}\n\n"
            "⭐ За одного приглашённого: "
            "0.50 Stars",
            reply_markup=keyboard()
        )

        return


    # =========================
    # PROMO BUTTON
    # =========================

    if text == "🎁 Промокод":

        await update.message.reply_text(
            "🎁 Введи промокод сообщением.",
            reply_markup=keyboard()
        )

        return


    # =========================
    # SECRET PROMO
    # =========================

    if text.lower() == PROMO.lower():

        # Проверяем, использовал ли пользователь
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
                "❌ Ты уже использовал этот промокод.",
                reply_markup=keyboard()
            )

            return


        # Получаем данные промокода
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
                "❌ Промокод недоступен.",
                reply_markup=keyboard()
            )

            return


        reward, max_uses, uses = promo_data


        # Проверяем лимит
        if uses >= max_uses:

            await update.message.reply_text(
                "❌ Промокод больше недоступен.",
                reply_markup=keyboard()
            )

            return


        # Начисляем 10 Stars
        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                reward,
                user.id
            )
        )


        # Записываем активацию
        cursor.execute(
            """
            INSERT INTO promo_uses
            (user_id, promo)
            VALUES (?, ?)
            """,
            (
                user.id,
                PROMO
            )
        )


        # Увеличиваем количество использований
        cursor.execute(
            """
            UPDATE promos
            SET uses = uses + 1
            WHERE promo = ?
            """,
            (PROMO,)
        )

        db.commit()


        # Не показываем название промокода
        # и количество оставшихся активаций
        await update.message.reply_text(
            "🎉 Промокод активирован!\n\n"
            "⭐ Получено: 10 Stars",
            reply_markup=keyboard()
        )

        return


    # =========================
    # WITHDRAW
    # =========================

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
                "💸 Минимальный вывод: "
                "15 ⭐\n\n"
                f"💰 Твой баланс: "
                f"{balance:.2f} ⭐",
                reply_markup=keyboard()
            )

        else:

            await update.message.reply_text(
                "💸 У тебя достаточно Stars "
                "для оформления вывода.\n\n"
                "⚙️ Система заявок на вывод "
                "будет подключена следующим этапом.",
                reply_markup=keyboard()
            )

        return


    # =========================
    # CHANNEL
    # =========================

    if text == "📢 Канал":

        await update.message.reply_text(
            "📢 Наш Telegram-канал:\n"
            f"{CHANNEL_URL}",
            reply_markup=keyboard()
        )

        return


# =========================
# RUN
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в GitHub Secrets"
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
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
