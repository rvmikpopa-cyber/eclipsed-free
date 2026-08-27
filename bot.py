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

# Администратор, которому приходят заявки
WITHDRAW_ADMIN = "@Eclipsed_consult"

REFERRAL_REWARD = 0.50
MIN_WITHDRAW = 15.0

PROMO = "44621"
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
    user_id INTEGER,
    promo TEXT NOT NULL,
    PRIMARY KEY (user_id, promo)
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
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    amount REAL,
    status TEXT DEFAULT 'pending'
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

    else:
        cursor.execute(
            """
            UPDATE users
            SET username = ?
            WHERE user_id = ?
            """,
            (username, user_id)
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

    subscribed = await is_subscribed(
        context,
        user.id
    )

    if not subscribed:

        await update.message.reply_text(
            "👋 Привет!\n\n"
            "Чтобы пользоваться ботом, "
            "подпишись на канал @eclipsedlf.\n\n"
            "После подписки снова нажми /start.",
            reply_markup=keyboard()
        )

        return

    # =========================
    # REFERRAL
    # =========================

    if context.args:

        try:
            inviter_id = int(context.args[0])

            if inviter_id != user.id:

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
# MESSAGES
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

    # Проверяем подписку
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
    # WITHDRAW INPUT
    # =========================

    if context.user_data.get("waiting_withdraw"):

        # Отмена
        if text.lower() in ("отмена", "cancel", "❌ отмена"):

            context.user_data["waiting_withdraw"] = False

            await update.message.reply_text(
                "❌ Вывод отменён.",
                reply_markup=keyboard()
            )

            return

        try:
            amount = float(
                text.replace(",", ".")
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Введи только число.\n\n"
                "Например: 15 или 25",
                reply_markup=keyboard()
            )

            return

        # Проверяем положительное число
        if amount <= 0:

            await update.message.reply_text(
                "❌ Некорректная сумма.",
                reply_markup=keyboard()
            )

            return

        # Проверяем минимум
        if amount < MIN_WITHDRAW:

            await update.message.reply_text(
                "❌ Минимальная сумма вывода — 15 ⭐.",
                reply_markup=keyboard()
            )

            return

        # Получаем баланс
        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user.id,)
        )

        row = cursor.fetchone()

        balance = row[0] if row else 0.0

        # Проверяем баланс
        if amount > balance:

            await update.message.reply_text(
                f"❌ Недостаточно Stars.\n\n"
                f"💰 Твой баланс: {balance:.2f} ⭐",
                reply_markup=keyboard()
            )

            return

        # =========================
        # СОЗДАЁМ ЗАЯВКУ
        # =========================

        try:

            # Списываем Stars
            cursor.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE user_id = ?
                """,
                (
                    amount,
                    user.id
                )
            )

            # Создаём заявку
            cursor.execute(
                """
                INSERT INTO withdrawals
                (user_id, username, amount, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (
                    user.id,
                    user.username or "",
                    amount
                )
            )

            withdrawal_id = cursor.lastrowid

            db.commit()

        except Exception:

            db.rollback()

            await update.message.reply_text(
                "❌ Ошибка при создании заявки. "
                "Попробуй ещё раз.",
                reply_markup=keyboard()
            )

            return

        context.user_data["waiting_withdraw"] = False

        username = (
            f"@{user.username}"
            if user.username
            else "нет username"
        )

        # =========================
        # ОТПРАВКА АДМИНУ
        # =========================

        try:

            await context.bot.send_message(
                chat_id=WITHDRAW_ADMIN,
                text=(
                    "💸 НОВАЯ ЗАЯВКА НА ВЫВОД\n\n"
                    f"👤 Пользователь: {username}\n"
                    f"🆔 ID: {user.id}\n"
                    f"⭐ Сумма: {amount:.2f} Stars\n"
                    f"📋 Заявка №{withdrawal_id}\n"
                    "⏳ Статус: ожидает выплаты"
                )
            )

        except Exception:

            # Если админу не удалось отправить заявку,
            # возвращаем Stars пользователю

            cursor.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE user_id = ?
                """,
                (
                    amount,
                    user.id
                )
            )

            cursor.execute(
                """
                DELETE FROM withdrawals
                WHERE id = ?
                """,
                (withdrawal_id,)
            )

            db.commit()

            await update.message.reply_text(
                "❌ Не удалось отправить заявку админу.\n\n"
                "⭐ Stars возвращены на баланс.",
                reply_markup=keyboard()
            )

            return

        await update.message.reply_text(
            "✅ Заявка на вывод создана!\n\n"
            f"⭐ Сумма: {amount:.2f}\n"
            f"📋 Заявка №{withdrawal_id}\n\n"
            "⏳ Ожидай обработки.",
            reply_markup=keyboard()
        )

        return

    # =========================
    # BALANCE
