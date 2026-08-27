import os
import sqlite3

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL = "@eclipsedlf"
CHANNEL_URL = "https://t.me/eclipsedlf"

# Админ для заявок на вывод
WITHDRAW_ADMIN = "@Eclipsed_consult"

# Награда за реферала
REFERRAL_REWARD = 0.50

# Минимальный вывод
MIN_WITHDRAW = 15.0

# Промокод
PROMO = "44621"
PROMO_REWARD = 10.0
PROMO_LIMIT = 10


# =========================
# DATABASE
# =========================

db = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

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
""", (
    PROMO,
    PROMO_REWARD,
    PROMO_LIMIT
))

db.commit()


# =========================
# ГЛАВНОЕ МЕНЮ
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
# ПОЛЬЗОВАТЕЛЬ
# =========================

def get_user(user_id, username=""):

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
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
            (
                user_id,
                username
            )
        )

        db.commit()

    else:

        cursor.execute(
            """
            UPDATE users
            SET username = ?
            WHERE user_id = ?
            """,
            (
                username,
                user_id
            )
        )

        db.commit()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    return cursor.fetchone()


# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================

async def is_subscribed(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):

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
# НАЧИСЛЕНИЕ РЕФЕРАЛА
# =========================

async def process_referral(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    inviter_id: int
):

    if user_id == inviter_id:
        return False

    # Проверяем, существует ли пригласивший
    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE user_id = ?
        """,
        (inviter_id,)
    )

    inviter = cursor.fetchone()

    if not inviter:
        return False

    # Проверяем, был ли пользователь
    # уже кем-то приглашён
    cursor.execute(
        """
        SELECT invited_by
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    if not row:
        return False

    # Уже был засчитан реферал
    if row[0] is not None:
        return False

    # Проверяем подписку
    subscribed = await is_subscribed(
        context,
        user_id
    )

    if not subscribed:
        return False

    # Привязываем пользователя
    cursor.execute(
        """
        UPDATE users
        SET invited_by = ?,
            subscribed = 1
        WHERE user_id = ?
        AND invited_by IS NULL
        """,
        (
            inviter_id,
            user_id
        )
    )

    if cursor.rowcount != 1:
        db.rollback()
        return False

    # Начисляем награду
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

    # Уведомляем пригласившего
    try:

        await context.bot.send_message(
            chat_id=inviter_id,
            text=(
                "🎉 Новый реферал!\n\n"
                "👤 Пользователь подписался "
                "на канал и активировал бота.\n\n"
                f"⭐ Тебе начислено "
                f"{REFERRAL_REWARD:.2f} Stars."
            )
        )

    except Exception:
        pass

    return True


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    # Если пользователь пришёл по реферальной ссылке,
    # сохраняем пригласившего ДО проверки подписки.
    if context.args:

        try:

            inviter_id = int(
                context.args[0]
            )

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
                        SELECT user_id
                        FROM users
                        WHERE user_id = ?
                        """,
                        (inviter_id,)
                    )

                    inviter_exists = cursor.fetchone()

                    if inviter_exists:

                        # Сохраняем пригласившего,
                        # но награду пока НЕ выдаём
                        cursor.execute(
                            """
                            UPDATE users
                            SET invited_by = ?
                            WHERE user_id = ?
                            AND invited_by IS NULL
                            """,
                            (
                                inviter_id,
                                user.id
                            )
                        )

                        db.commit()

        except (
            ValueError,
            TypeError
        ):
            pass

    # Если не подписан
    if not subscribed:

        await update.message.reply_text(
            "👋 Привет!\n\n"
            "Чтобы пользоваться ботом, "
            "сначала подпишись на канал:\n\n"
            f"{CHANNEL_URL}\n\n"
            "После подписки снова нажми /start.\n\n"
            "⭐ После подтверждения подписки "
            "твой пригласивший получит "
            f"{REFERRAL_REWARD:.2f} Stars.",
            reply_markup=keyboard()
        )

        return

    # =========================
    # ПОЛЬЗОВАТЕЛЬ ПОДПИСАН
    # =========================

    cursor.execute(
        """
        UPDATE users
        SET subscribed = 1
        WHERE user_id = ?
        """,
        (user.id,)
    )

    db.commit()

    # Проверяем реферала
    referral_activated = False

    cursor.execute(
        """
        SELECT invited_by
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cursor.fetchone()

    if row and row[0] is not None:

        inviter_id = row[0]

        # ВАЖНО:
        # здесь нельзя повторно начислять,
        # поэтому сначала проверяем,
        # был ли уже засчитан реферал.
        cursor.execute(
            """
            SELECT referrals
            FROM users
            WHERE user_id = ?
            """,
            (inviter_id,)
        )

        # Проверка через отдельную таблицу
        # referral_rewards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referral_rewards (
                invited_user_id INTEGER PRIMARY KEY,
                inviter_id INTEGER,
                reward REAL
            )
        """)

        db.commit()

        cursor.execute(
            """
            SELECT invited_user_id
            FROM referral_rewards
            WHERE invited_user_id = ?
            """,
            (user.id,)
        )

        already_rewarded = cursor.fetchone()

        if not already_rewarded:

            try:

                cursor.execute(
                    """
                    INSERT INTO referral_rewards
                    (invited_user_id, inviter_id, reward)
                    VALUES (?, ?, ?)
                    """,
                    (
                        user.id,
                        inviter_id,
                        REFERRAL_REWARD
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

                referral_activated = True

                try:

                    await context.bot.send_message(
                        chat_id=inviter_id,
                        text=(
                            "🎉 Новый реферал!\n\n"
                            "👤 Пользователь подписался "
                            "на канал.\n\n"
                            f"⭐ Начислено: "
                            f"{REFERRAL_REWARD:.2f} Stars"
                        )
                    )

                except Exception:
                    pass

            except sqlite3.IntegrityError:

                db.rollback()

    if referral_activated:

        await update.message.reply_text(
            "✅ Подписка подтверждена!\n\n"
            "🎉 Реферальная награда успешно "
            "начислена пригласившему.\n\n"
            "⭐ Приглашай новых пользователей "
            f"и получай {REFERRAL_REWARD:.2f} Stars "
            "за каждого.",
            reply_markup=keyboard()
        )

    else:

        await update.message.reply_text(
            "✅ Подписка подтверждена!\n\n"
            "⭐ Приглашай пользователей и получай "
            f"{REFERRAL_REWARD:.2f} Stars за каждого.",
            reply_markup=keyboard()
        )


# =========================
# БАЛАНС
# =========================

async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return

    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cursor.fetchone()

    balance_value = (
        row[0]
        if row
        else 0.0
    )

    await update.message.reply_text(
        "💰 Твой баланс:\n\n"
        f"⭐ {balance_value:.2f} Stars",
        reply_markup=keyboard()
    )


# =========================
# РЕФЕРАЛЫ
# =========================

async def referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return

    await show_referrals(
        update,
        context
    )


# =========================
# ПОКАЗ РЕФЕРАЛОВ
# =========================

async def show_referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    # Обновляем статус подписки
    subscribed = await is_subscribed(
        context,
        user.id
    )

    if subscribed:

        cursor.execute(
            """
            UPDATE users
            SET subscribed = 1
            WHERE user_id = ?
            """,
            (user.id,)
        )

        db.commit()

    # Получаем статистику
    cursor.execute(
        """
        SELECT referrals, balance
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cursor.fetchone()

    referrals_count = (
        row[0]
        if row
        else 0
    )

    balance_value = (
        row[1]
        if row
        else 0.0
    )

    bot_username = context.bot.username

    referral_link = (
        f"https://t.me/{bot_username}?start={user.id}"
    )

    referral_keyboard = ReplyKeyboardMarkup(
        [
            ["🔄 Обновить"],
            ["⬅️ Главное меню"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
        f"👤 Приглашено: {referrals_count}\n"
        f"⭐ Заработано за рефералов: "
        f"{referrals_count * REFERRAL_REWARD:.2f} ⭐\n"
        f"💰 Текущий баланс: {balance_value:.2f} ⭐\n\n"
        f"💎 За одного приглашённого: "
        f"{REFERRAL_REWARD:.2f} ⭐\n\n"
        "🔗 Твоя реферальная ссылка:\n"
        f"{referral_link}\n\n"
        "📌 Награда начисляется только после "
        "подписки приглашённого на канал "
        "и подтверждения через /start.",
        reply_markup=referral_keyboard
    )


# =========================
# ОБНОВИТЬ РЕФЕРАЛЫ
# =========================

async def refresh_referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return

    # Проверяем всех пользователей,
    # которые пришли по этой реферальной ссылке
    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE invited_by = ?
        """,
        (user.id,)
    )

    invited_users = cursor.fetchall()

    newly_activated = 0

    for row in invited_users:

        invited_user_id = row[0]

        # Проверяем подписку
        subscribed = await is_subscribed(
            context,
            invited_user_id
        )

        if not subscribed:
            continue

        # Проверяем, была ли уже награда
        cursor.execute(
            """
            SELECT invited_user_id
            FROM referral_rewards
            WHERE invited_user_id = ?
            """,
            (invited_user_id,)
        )

        already_rewarded = cursor.fetchone()

        if already_rewarded:
            continue

        try:

            cursor.execute(
                """
                INSERT INTO referral_rewards
                (invited_user_id, inviter_id, reward)
                VALUES (?, ?, ?)
                """,
                (
                    invited_user_id,
                    user.id,
                    REFERRAL_REWARD
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
                    user.id
                )
            )

            db.commit()

            newly_activated += 1

        except sqlite3.IntegrityError:

            db.rollback()

    await show_referrals(
        update,
        context
    )

    if newly_activated > 0:

        await update.message.reply_text(
            f"🎉 Найдено новых подтверждённых "
            f"рефералов: {newly_activated}\n\n"
            f"⭐ Начислено: "
            f"{newly_activated * REFERRAL_REWARD:.2f} Stars"
        )


# =========================
# ВЫВОД
# =========================

async def withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return

    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cursor.fetchone()

    balance_value = (
        row[0]
        if row
        else 0.0
    )

    if balance_value < MIN_WITHDRAW:

        await update.message.reply_text(
            "💰 Твой баланс: "
            f"{balance_value:.2f} ⭐\n\n"
            "❌ Для вывода нужно минимум "
            f"{MIN_WITHDRAW:.0f} ⭐.",
            reply_markup=keyboard()
        )

        return

    context.user_data[
        "waiting_withdraw"
    ] = True

    await update.message.reply_text(
        "💸 ВЫВОД STARS\n\n"
        f"💰 Доступно: {balance_value:.2f} ⭐\n"
        f"📌 Минимум: {MIN_WITHDRAW:.0f} ⭐\n\n"
        "Введи сумму вывода.\n\n"
        "Например: 15 или 25\n\n"
        "Для отмены напиши «Отмена».",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["❌ Отмена"]
            ],
            resize_keyboard=True
        )
    )


# =========================
# ОБРАБОТКА ВЫВОДА
# =========================

async def process_withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = update.message.text.strip()

    if text.lower() in (
        "отмена",
        "cancel",
        "❌ отмена"
    ):

        context.user_data[
            "waiting_withdraw"
        ] = False

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

    if amount <= 0:

        await update.message.reply_text(
            "❌ Некорректная сумма.",
            reply_markup=keyboard()
        )

        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ Минимальная сумма вывода — "
            f"{MIN_WITHDRAW:.0f} ⭐.",
            reply_markup=keyboard()
        )

        return

    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    row = cursor.fetchone()

    balance_value = (
        row[0]
        if row
        else 0.0
    )

    if amount > balance_value:

        await update.message.reply_text(
            "❌ Недостаточно Stars.\n\n"
            f"💰 Твой баланс: "
            f"{balance_value:.2f} ⭐",
            reply_markup=keyboard()
        )

        return

    try:

        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            AND balance >= ?
            """,
            (
                amount,
                user.id,
                amount
            )
        )

        if cursor.rowcount != 1:

            db.rollback()

            await update.message.reply_text(
                "❌ Не удалось создать заявку.",
                reply_markup=keyboard()
            )

            return

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
            "❌ Ошибка при создании заявки.",
            reply_markup=keyboard()
        )

        return

    context.user_data[
        "waiting_withdraw"
    ] = False

    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )

    # Отправляем заявку админу
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

        # Возвращаем Stars
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


# =========================
# ПРОМОКОД
# =========================

async def promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    get_user(
        user.id,
        user.username or ""
    )

    if not await is_subscribed(
        context,
        user.id
    ):

        await update.message.reply_text(
            "❌ Сначала подпишись на @eclipsedlf.",
            reply_markup=keyboard()
        )

        return

    context.user_data[
        "waiting_promo"
    ] = True

    await update.message.reply_text(
        "🎁 Введи промокод сообщением ниже.\n\n"
        "Например: 44621\n\n"
        "Для отмены напиши «Отмена».",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["❌ Отмена"]
            ],
            resize_keyboard=True
        )
    )


# =========================
# ОБРАБОТКА ПРОМОКОДА
# =========================

async def process_promo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = update.message.text.strip()

    if text.lower() in (
        "отмена",
        "cancel",
        "❌ отмена"
    ):

        context.user_data[
            "waiting_promo"
        ] = False

        await update.message.reply_text(
            "❌ Ввод промокода отменён.",
            reply_markup=keyboard()
        )

        return

    promo_code = text

    cursor.execute(
        """
        SELECT reward, max_uses, uses
        FROM promos
        WHERE promo = ?
        """,
        (promo_code,)
    )

    promo_row = cursor.fetchone()

    if not promo_row:

        await update.message.reply_text(
            "❌ Промокод не найден.",
            reply_markup=keyboard()
        )

        return

    reward, max_uses, uses = promo_row

    if uses >= max_uses:

        context.user_data[
            "waiting_promo"
        ] = False

        await update.message.reply_text(
            "❌ Лимит активаций промокода "
            "уже закончился.",
            reply_markup=keyboard()
        )

        return

    cursor.execute(
        """
        SELECT 1
        FROM promo_uses
        WHERE user_id = ?
        AND promo = ?
        """,
        (
            user.id,
            promo_code
        )
    )

    already_used = cursor.fetchone()

    if already_used:

        context.user_data[
            "waiting_promo"
        ] = False

        await update.message.reply_text(
            "❌ Ты уже использовал этот промокод.",
            reply_markup=keyboard()
        )

        return

    try:

        cursor.execute(
            """
            INSERT INTO promo_uses
            (user_id, promo)
            VALUES (?, ?)
            """,
            (
                user.id,
                promo_code
            )
        )

        cursor.execute(
            """
            UPDATE promos
            SET uses = uses + 1
            WHERE promo = ?
            AND uses < max_uses
            """,
            (promo_code,)
        )

        if cursor.rowcount != 1:

            db.rollback()

            await update.message.reply_text(
                "❌ Промокод больше недоступен.",
                reply_markup=keyboard()
            )

            return

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

        db.commit()

    except Exception:

        db.rollback()

        await update.message.reply_text(
            "❌ Ошибка активации промокода.",
            reply_markup=keyboard()
        )

        return

    context.user_data[
        "waiting_promo"
    ] = False

    await update.message.reply_text(
        "🎉 Промокод активирован!\n\n"
        f"⭐ Начислено: {reward:.2f} Stars",
        reply_markup=keyboard()
    )


# =========================
# КАНАЛ
# =========================

async def channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📢 Наш канал:\n\n"
        f"{CHANNEL_URL}",
        reply_markup=keyboard()
    )


# =========================
# ГЛАВНЫЙ ROUTER
# =========================

async def message_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    # Ввод промокода
    if context.user_data.get(
        "waiting_promo"
    ):

        await process_promo(
            update,
            context
        )

        return

    # Ввод суммы вывода
    if context.user_data.get(
        "waiting_withdraw"
    ):

        await process_withdraw(
            update,
            context
        )

        return

    # Баланс
    if text == "💰 Баланс":

        await balance(
            update,
            context
        )

        return

    # Рефералы
    if text == "👥 Рефералы":

        await referrals(
            update,
            context
        )

        return

    # Обновить рефералы
    if text == "🔄 Обновить":

        await refresh_referrals(
            update,
            context
        )

        return

    # Главное меню
    if text == "⬅️ Главное меню":

        await update.message.reply_text(
            "🏠 Главное меню",
            reply_markup=keyboard()
        )

        return

    # Вывод
    if text == "💸 Вывод":

        await withdraw(
            update,
            context
        )

        return

    # Промокод
    if text == "🎁 Промокод":

        await promo(
            update,
            context
        )

        return

    # Канал
    if text == "📢 Канал":

        await channel(
            update,
            context
        )

        return

    # Неизвестный текст
    await update.message.reply_text(
        "👇 Используй кнопки меню.",
        reply_markup=keyboard()
    )


# =========================
# ЗАПУСК
# =========================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "❌ BOT_TOKEN не найден.\n\n"
            "Добавь токен бота в переменные окружения."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_router
        )
    )

    print("🤖 Бот запущен!")

    application.run_polling()


# =========================
# START
# =========================

if __name__ == "__main__":
    main()
