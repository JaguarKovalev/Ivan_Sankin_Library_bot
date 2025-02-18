import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import API_TOKEN

# Если вы хотите за один раз загрузить книги из book.py в БД:
# from book import books as initial_books

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

##############################################################################
# БЛОК РАБОТЫ С БАЗОЙ ДАННЫХ
##############################################################################

# Подключаемся к базе
conn = sqlite3.connect("database.sqlite3")
cursor = conn.cursor()

# Создаём таблицу пользователей (если не существует)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        surname TEXT,
        password TEXT,
        borrowed_books TEXT
    )
"""
)

# Создаём таблицу книг (если не существует)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        author TEXT,
        available BOOLEAN,
        borrower TEXT
    )
"""
)

conn.commit()


def init_books_in_db():
    """
    Пример функции, которая единовременно загружает книги в таблицу `books`,
    если они там ещё не записаны. Можно вызвать её один раз при старте бота.
    Предполагается, что у вас есть словарь initial_books в book.py.
    Или вы можете прописать книги прямо здесь в виде словаря.
    """
    # from book import books as initial_books
    initial_books = {
        "Война и мир": {"author": "Лев Толстой", "available": True, "borrower": None},
        "Преступление и наказание": {
            "author": "Федор Достоевский",
            "available": True,
            "borrower": None,
        },
        "Мастер и Маргарита": {
            "author": "Михаил Булгаков",
            "available": True,
            "borrower": None,
        },
        # ... Добавьте остальные при необходимости ...
    }

    # Проверяем, есть ли уже какие-то записи в таблице books
    cursor.execute("SELECT COUNT(*) FROM books")
    count = cursor.fetchone()[0]
    if count == 0:
        # Если записей нет, загружаем initial_books
        for title, info in initial_books.items():
            cursor.execute(
                "INSERT INTO books (title, author, available, borrower) VALUES (?, ?, ?, ?)",
                (title, info["author"], info["available"], info["borrower"]),
            )
        conn.commit()


# Если нужно один раз заполнить таблицу книг, снимите комментарий:
# init_books_in_db()


##############################################################################
# FSM Состояния
##############################################################################


class LoginState(StatesGroup):
    waiting_for_name = State()
    waiting_for_surname = State()
    waiting_for_password = State()


class RegisterState(StatesGroup):
    waiting_for_name = State()
    waiting_for_surname = State()
    waiting_for_password = State()


class BookRequest(StatesGroup):
    waiting_for_book_name = State()


##############################################################################
# КЛАВИАТУРЫ
##############################################################################

start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔑 Войти")],
        [KeyboardButton(text="📝 Регистрация")],
    ],
    resize_keyboard=True,
)

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Список книг")],
        [KeyboardButton(text="🔍 Найти книгу"), KeyboardButton(text="📖 Взять книгу")],
        [KeyboardButton(text="👤 Личный кабинет"), KeyboardButton(text="🚪 Выход")],
    ],
    resize_keyboard=True,
)


##############################################################################
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
##############################################################################


def get_user_data(user_id: int):
    """
    Получаем запись пользователя из БД.
    Возвращает dict или None, если пользователя нет.
    """
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        # row: (user_id, name, surname, password, borrowed_books)
        return {
            "user_id": row[0],
            "name": row[1],
            "surname": row[2],
            "password": row[3],
            "borrowed_books": row[4],  # CSV-строка или None
        }
    return None


def create_user(user_id: int, name: str, surname: str, password: str):
    """
    Создаём нового пользователя в таблице users.
    borrowed_books по умолчанию будет пустой строкой.
    """
    cursor.execute(
        """
        INSERT INTO users (user_id, name, surname, password, borrowed_books)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, name, surname, password, ""),
    )
    conn.commit()


def update_user_borrowed_books(user_id: int, new_borrowed_books: str):
    """
    Обновляем CSV-строку с перечнем взятых книг у пользователя в таблице.
    """
    cursor.execute(
        "UPDATE users SET borrowed_books = ? WHERE user_id = ?",
        (new_borrowed_books, user_id),
    )
    conn.commit()


def get_books_list() -> str:
    """
    Возвращаем список всех книг из БД в виде строки для отправки пользователю.
    """
    cursor.execute("SELECT title, author, available, borrower FROM books")
    rows = cursor.fetchall()

    if not rows:
        return "❌ В базе данных нет ни одной книги."

    book_list = "Список книг:\n"
    for title, author, available, borrower in rows:
        if available:
            status = "✅ Доступна"
        else:
            status = f"❌ Занята (Взял: {borrower})"
        book_list += f"📖 {title} - {author} ({status})\n"
    return book_list


def find_book_in_db(title: str):
    """
    Ищем книгу по названию. Возвращаем кортеж (title, author, available, borrower) или None.
    """
    cursor.execute(
        "SELECT title, author, available, borrower FROM books WHERE title = ?",
        (title,),
    )
    return cursor.fetchone()


def set_book_borrowed(title: str, borrower: str):
    """
    Установить, что книга взята пользователем (available=False, borrower=...).
    """
    cursor.execute(
        "UPDATE books SET available = ?, borrower = ? WHERE title = ?",
        (False, borrower, title),
    )
    conn.commit()


def set_book_returned(title: str):
    """
    Установить, что книга возвращена (available=True, borrower=None).
    """
    cursor.execute(
        "UPDATE books SET available = ?, borrower = NULL WHERE title = ?",
        (True, title),
    )
    conn.commit()


async def check_registration(message: types.Message) -> bool:
    """
    Проверка, зарегистрирован ли пользователь. Если нет, отправляем сообщение и возвращаем False.
    """
    user_id = message.from_user.id
    user = get_user_data(user_id)
    if not user:
        await message.answer(
            "⛔ Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь для доступа ко всем функциям.",
            reply_markup=start_kb,
        )
        return False
    return True


##############################################################################
# ХЕНДЛЕРЫ /start, Регистрация, Вход
##############################################################################


@router.message(F.text == "/start")
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user_data(user_id)

    # Если пользователя нет, предлагаем регистрацию или вход
    if not user:
        await message.answer(
            "🔹 Добро пожаловать! Пожалуйста, выберите опцию:\n\n- Вход\n- Регистрация",
            reply_markup=start_kb,
        )
    else:
        # Пользователь есть – просим пароль
        await message.answer("🔑 Введите ваш пароль для входа:", reply_markup=start_kb)
        await state.set_state(LoginState.waiting_for_password)


@router.message(F.text == "📝 Регистрация")
async def start_registration(message: types.Message, state: FSMContext):
    await message.answer("🔹 Давайте зарегистрируемся! Введите ваше имя:")
    await state.set_state(RegisterState.waiting_for_name)


@router.message(F.text == "🔑 Войти")
async def start_login(message: types.Message, state: FSMContext):
    await message.answer("🔑 Введите ваше имя:")
    await state.set_state(LoginState.waiting_for_name)


@router.message(RegisterState.waiting_for_name)
async def register_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(RegisterState.waiting_for_surname)


@router.message(RegisterState.waiting_for_surname)
async def register_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Придумайте пароль:")
    await state.set_state(RegisterState.waiting_for_password)


@router.message(RegisterState.waiting_for_password)
async def register_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, есть ли уже такая запись
    if get_user_data(user_id):
        await message.answer(
            "⛔ Вы уже зарегистрированы. Используйте вход.", reply_markup=start_kb
        )
        await state.clear()
        return

    # Сохраняем пользователя в БД
    user_data = await state.get_data()
    create_user(
        user_id=user_id,
        name=user_data["name"],
        surname=user_data["surname"],
        password=message.text,
    )

    await message.answer(
        "✅ Регистрация завершена! Добро пожаловать.", reply_markup=menu_kb
    )
    await state.clear()


@router.message(LoginState.waiting_for_name)
async def login_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(LoginState.waiting_for_surname)


@router.message(LoginState.waiting_for_surname)
async def login_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Введите ваш пароль:")
    await state.set_state(LoginState.waiting_for_password)


@router.message(LoginState.waiting_for_password)
async def check_password(message: types.Message, state: FSMContext):
    user_data_state = await state.get_data()
    name = user_data_state["name"]
    surname = user_data_state["surname"]
    password_input = message.text

    # Попробуем найти пользователя по имени и фамилии
    cursor.execute(
        """
        SELECT user_id, password FROM users
        WHERE name = ? AND surname = ?
        """,
        (name, surname),
    )
    row = cursor.fetchone()

    if row:
        user_id_db = row[0]
        password_db = row[1]
        if password_db == password_input:
            await message.answer(f"✅ Успешный вход, {name}!", reply_markup=menu_kb)
            await state.clear()
            return
    await message.answer("❌ Неверное имя, фамилия или пароль. Попробуйте ещё раз.")


##############################################################################
# ЛИЧНЫЙ КАБИНЕТ / ВЫХОД
##############################################################################


@router.message(F.text == "👤 Личный кабинет")
async def profile(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return

    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        borrowed_books_csv = user_data["borrowed_books"]
        if borrowed_books_csv:
            borrowed_list = borrowed_books_csv.split(",")
            borrowed_books_str = ", ".join(borrowed_list)
        else:
            borrowed_books_str = "Нет взятых книг"

        await message.answer(
            f"👤 Ваш профиль:\n\nИмя: {user_data['name']}\n"
            f"Фамилия: {user_data['surname']}\n\n"
            f"Зарезервированные книги:\n{borrowed_books_str}",
            reply_markup=menu_kb,
        )


@router.message(F.text == "🚪 Выход")
async def logout(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return

    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        await message.answer(
            "Вы вышли из системы. Чтобы вернуться, пожалуйста, выполните вход.",
            reply_markup=start_kb,
        )
        await state.clear()
    else:
        await message.answer("⛔ Вы не вошли в систему. Пожалуйста, выполните вход.")


##############################################################################
# КНИГИ: СПИСОК / ПОИСК / ВЗЯТЬ
##############################################################################


@router.message(F.text == "📚 Список книг")
async def list_books_handler(message: types.Message):
    book_list = get_books_list()
    await message.answer(book_list)


@router.message(F.text == "🔍 Найти книгу")
async def ask_for_book(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return
    await message.answer("Введите название книги, которую хотите найти:")
    await state.set_state(BookRequest.waiting_for_book_name)


@router.message(BookRequest.waiting_for_book_name)
async def find_book(message: types.Message, state: FSMContext):
    book_title = message.text.strip()
    row = find_book_in_db(book_title)

    if row:
        title, author, available, borrower = row
        status = (
            "✅ Доступна" if available else f"❌ Зарезервирована (Резерв: {borrower})"
        )
        response = f"📖 {title} - {author}\nСтатус: {status}"
    else:
        response = "❌ Книга не найдена в библиотеке."

    await message.answer(response)
    await state.clear()


@router.message(F.text == "📖 Взять книгу")
async def borrow_book_request(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return
    await message.answer("Введите название книги, которую хотите зарезервировать:")
    await state.set_state(BookRequest.waiting_for_book_name)


@router.message(BookRequest.waiting_for_book_name)
async def borrow_book(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return

    title = message.text.strip()
    row = find_book_in_db(title)
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    if not row:
        await message.answer("Книга не найдена в библиотеке.")
        await state.clear()
        return

    # row = (title, author, available, borrower)
    _, _, available, borrower = row

    if available:
        # Обновляем книгу
        borrower_str = f"{user_data['name']} {user_data['surname']}"
        set_book_borrowed(title, borrower_str)

        # Обновляем список книг пользователя (CSV)
        borrowed_csv = user_data["borrowed_books"] or ""
        borrowed_list = borrowed_csv.split(",") if borrowed_csv else []
        borrowed_list = [x for x in borrowed_list if x]  # На случай пустой строки
        borrowed_list.append(title)
        new_borrowed_csv = ",".join(borrowed_list)
        update_user_borrowed_books(user_id, new_borrowed_csv)

        await message.answer(
            f"Вы успешно зарезервировали книгу «{title}». Не забудьте вернуть её вовремя!"
        )
    else:
        await message.answer("Эта книга уже занята.")

    await state.clear()


##############################################################################
# Запуск бота
##############################################################################


async def main():
    dp.include_router(router)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
