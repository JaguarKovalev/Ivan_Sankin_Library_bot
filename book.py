books = {
    "Война и мир": {"author": "Лев Толстой", "available": True, "borrower": None},
    "Преступление и наказание": {"author": "Федор Достоевский", "available": True, "borrower": None},
    "Мастер и Маргарита": {"author": "Михаил Булгаков", "available": True, "borrower": None},
    "Анна Каренина": {"author": "Лев Толстой", "available": True, "borrower": None},
    "Отцы и дети": {"author": "Иван Тургенев", "available": True, "borrower": None},
    "Евгений Онегин": {"author": "Александр Пушкин", "available": True, "borrower": None},
    "Герой нашего времени": {"author": "Михаил Лермонтов", "available": True, "borrower": None},
    "Обломов": {"author": "Иван Гончаров", "available": True, "borrower": None},
    "Доктор Живаго": {"author": "Борис Пастернак", "available": True, "borrower": None},
    "Дети Арбата": {"author": "Анатолий Рыбаков", "available": True, "borrower": None},
    "Как закалялась сталь": {"author": "Николай Островский", "available": True, "borrower": None},
    "Белая гвардия": {"author": "Михаил Булгаков", "available": True, "borrower": None},
    "Чапаев": {"author": "Дмитрий Фурманов", "available": True, "borrower": None},
    "Двенадцать стульев": {"author": "Илья Ильф, Евгений Петров", "available": True, "borrower": None},
    "Золотой телёнок": {"author": "Илья Ильф, Евгений Петров", "available": True, "borrower": None},
    "Тихий Дон": {"author": "Михаил Шолохов", "available": True, "borrower": None},
    "Жизнь и судьба": {"author": "Василий Гроссман", "available": True, "borrower": None},
    "Архипелаг ГУЛАГ": {"author": "Александр Солженицын", "available": True, "borrower": None},
    "Записки охотника": {"author": "Иван Тургенев", "available": True, "borrower": None},
    "Собачье сердце": {"author": "Михаил Булгаков", "available": True, "borrower": None},
    "Республика ШКИД": {"author": "Григорий Белых, Алексей Пантелеев", "available": True, "borrower": None},
    "Фауст": {"author": "Иоганн Гёте", "available": True, "borrower": None},
    "Капитанская дочка": {"author": "Александр Пушкин", "available": True, "borrower": None},
    "Накануне": {"author": "Иван Тургенев", "available": True, "borrower": None},
    "По ком звонит колокол": {"author": "Эрнест Хемингуэй", "available": True, "borrower": None},
    "Мёртвые души": {"author": "Николай Гоголь", "available": True, "borrower": None},
    "Записки из подполья": {"author": "Федор Достоевский", "available": True, "borrower": None},
    "Лолита": {"author": "Владимир Набоков", "available": True, "borrower": None},
    "Судьба человека": {"author": "Михаил Шолохов", "available": True, "borrower": None},
    "Остров Крым": {"author": "Василий Аксенов", "available": True, "borrower": None},
    "Пикник на обочине": {"author": "Аркадий и Борис Стругацкие", "available": True, "borrower": None},
    "Чевенгур": {"author": "Андрей Платонов", "available": True, "borrower": None},
    "Котлован": {"author": "Андрей Платонов", "available": True, "borrower": None},
    "Маленький принц": {"author": "Антуан де Сент-Экзюпери", "available": True, "borrower": None},
    "Идиот": {"author": "Федор Достоевский", "available": True, "borrower": None},
    "Невский проспект": {"author": "Николай Гоголь", "available": True, "borrower": None},
    "Чёрный человек": {"author": "Сергей Есенин", "available": True, "borrower": None},
    "Тарас Бульба": {"author": "Николай Гоголь", "available": True, "borrower": None},
    "Алые паруса": {"author": "Александр Грин", "available": True, "borrower": None},
    "Гранатовый браслет": {"author": "Александр Куприн", "available": True, "borrower": None},
    "Олеся": {"author": "Александр Куприн", "available": True, "borrower": None},
    "Портрет Дориана Грея": {"author": "Оскар Уайльд", "available": True, "borrower": None},
    "Старик и море": {"author": "Эрнест Хемингуэй", "available": True, "borrower": None}
}
def update_book_status(title, borrower):
    if title in books:
        books[title]["available"] = borrower is None
        books[title]["borrower"] = borrower

        with open("books.py", "w", encoding="utf-8") as f:
            f.write(f"books = {books}\n")

        return True
    return False