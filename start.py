import asyncio
import logging
import sqlite3

import openpyxl
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from book import books
from config import API_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()


# Подключение к базе данных SQLite
conn = sqlite3.connect("database.sqlite3")
cursor = conn.cursor()

# Создание таблицы пользователей
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
conn.commit()

# Простая клавиатура для регистрации/входа
start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔑 Войти")],
        [KeyboardButton(text="📝 Регистрация")],
    ],
    resize_keyboard=True,
)

# Основная клавиатура
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Список книг")],
        [KeyboardButton(text="🔍 Найти книгу"), KeyboardButton(text="📖 Взять книгу")],
        [KeyboardButton(text="👤 Личный кабинет"), KeyboardButton(text="🚪 Выход")],
    ],
    resize_keyboard=True,
)


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


# Функция для сохранения данных в Excel
def save_to_excel():
    # Создаем книгу Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Users"

    # Заголовки для таблицы
    ws.append(["User ID", "Name", "Surname", "Password", "Borrowed Books"])

    # Добавляем данные пользователей
    for user_id, data in users.items():
        borrowed_books = ", ".join(data["borrowed_books"])
        ws.append(
            [user_id, data["name"], data["surname"], data["password"], borrowed_books]
        )

    # Сохраняем файл
    wb.save("Excel/users_data.xlsx")


# Функция для отображения списка книг
def get_books_list():
    book_list = "Список книг:\n"
    for title, info in books.items():
        status = (
            "✅ Доступна"
            if info["available"]
            else f"❌ Занята (Взял: {info['borrower']})"
        )
        book_list += f"📖 {title} - {info['author']} ({status})\n"
    return book_list


# Проверка на регистрацию и вход
async def check_registration(message: types.Message):

    # Проверяем, зарегистрирован ли пользователь

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        users[message.from_user.id] = {
            "name": user[1],
            "surname": user[2],
            "password": user[3],
            "borrowed_books": user[4],
        }

    user_id = message.from_user.id
    if user_id not in users:
        await message.answer(
            "⛔ Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь для доступа ко всем функциям.",
            reply_markup=start_kb,
        )
        return False
    return True


@router.message(F.text == "/start")
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    if user_id not in users:
        await message.answer(
            "🔹 Добро пожаловать! Пожалуйста, выберите опцию:\n\n- Вход\n- Регистрация",
            reply_markup=start_kb,
        )
    else:
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

    # Проверяем, существует ли уже пользователь
    if user_id in users:
        await message.answer(
            "⛔ Вы уже зарегистрированы. Используйте вход.", reply_markup=start_kb
        )
        await state.clear()
        return  # Прерываем выполнение функции

    # Получаем сохраненные данные и добавляем пользователя в базу
    user_data = await state.get_data()
    users[user_id] = {
        "name": user_data["name"],
        "surname": user_data["surname"],
        "password": message.text,
        "borrowed_books": [],
    }

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
    user_data = await state.get_data()
    name = user_data["name"]
    surname = user_data["surname"]
    password = message.text

    user = next(
        (u for u in users.values() if u["name"] == name and u["surname"] == surname),
        None,
    )

    if user and user["password"] == password:
        await message.answer(f"✅ Успешный вход, {name}!", reply_markup=menu_kb)
        await state.clear()
    else:
        await message.answer("❌ Неверное имя, фамилия или пароль. Попробуйте ещё раз.")


@router.message(F.text == "👤 Личный кабинет")
async def profile(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return

    user_id = message.from_user.id
    if user_id in users:
        user = users[user_id]
        borrowed_books = (
            ", ".join(user["borrowed_books"])
            if user["borrowed_books"]
            else "Нет взятых книг"
        )
        await message.answer(
            f"👤 Ваш профиль:\n\nИмя: {user['name']}\nФамилия: {user['surname']}\n\nЗарезервированные книги:\n{borrowed_books}",
            reply_markup=menu_kb,
        )


@router.message(F.text == "🚪 Выход")
async def logout(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return

    user_id = message.from_user.id
    if user_id in users:
        await message.answer(
            "Вы вышли из системы. Чтобы вернуться, пожалуйста, выполните вход.",
            reply_markup=start_kb,
        )
        await state.clear()
    else:
        await message.answer("⛔ Вы не вошли в систему. Пожалуйста, выполните вход.")


@router.message(F.text == "📚 Список книг")
async def list_books(message: types.Message):
    book_list = get_books_list()
    await message.answer(book_list)


# Обработчик кнопки "🔍 Найти книгу"
@router.message(F.text == "🔍 Найти книгу")
async def ask_for_book(message: types.Message, state: FSMContext):
    if not await check_registration(message):
        return
    await message.answer("Введите название книги, которую хотите найти:")
    await state.set_state(BookRequest.waiting_for_book_name)


# Обработчик ввода названия книги
@router.message(BookRequest.waiting_for_book_name)
async def find_book(message: types.Message, state: FSMContext):
    book_title = message.text.strip()

    if book_title in books:
        book_info = books[book_title]
        status = (
            "✅ Доступна"
            if book_info["available"]
            else f"❌ Зарезервирована (Резерв: {book_info['borrower']})"
        )
        response = f"📖 {book_title} - {book_info['author']}\nСтатус: {status}"
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

    if title in books and books[title]["available"]:
        books[title]["available"] = False
        user_id = message.from_user.id
        users[user_id]["borrowed_books"].append(title)
        books[title][
            "borrower"
        ] = f"{users[user_id]['name']} {users[user_id]['surname']}"
        await message.answer(
            f"Вы успешно зарезервировали книгу '{title}'. Не забудьте вернуть её вовремя!"
        )
        save_to_excel()  # Сохраняем данные в Excel после изменения
    elif title in books:
        await message.answer("Эта книга уже занята.")
    else:
        await message.answer("Книга не найдена в библиотеке.")

    await state.clear()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    # Запускаем основную функцию main в цикле событий asyncio
    try:
        asyncio.run(main())
        # Обрабатываем прерывание выполнения программы пользователем (Ctrl+C)
    except KeyboardInterrupt:
        print("Exit")
