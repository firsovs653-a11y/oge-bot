import telebot
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime

# ========== НАСТРОЙКИ ==========
# Токен берем из переменных окружения (так безопаснее)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

if not TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не задан!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# Хранилище: какой пользователь какое задание решает
user_current_task = {}


# Загружаем задания из JSON
def load_tasks():
    try:
        with open('tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        print(f"✅ Загружено заданий: {len(tasks)}")
        return tasks
    except FileNotFoundError:
        print("⚠️ Файл tasks.json не найден, создаю пустую базу")
        return {}
    except Exception as e:
        print(f"❌ Ошибка загрузки заданий: {e}")
        return {}


TASKS = load_tasks()


# ========== ФУНКЦИЯ ЗАПУСКА КОДА ==========
def run_python_code(code, input_data):
    """Запускает код Python и возвращает вывод"""
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name

        # Запускаем код
        process = subprocess.run(
            ['python3', temp_file],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=5,
            encoding='utf-8'
        )

        # Удаляем временный файл
        os.unlink(temp_file)

        if process.returncode == 0:
            return process.stdout.strip(), None
        else:
            return None, process.stderr.strip()

    except subprocess.TimeoutExpired:
        return None, "⏰ Время выполнения превышено (5 сек)"
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"


# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для подготовки к ОГЭ по информатике.\n\n"
        "📚 Я умею проверять твои решения задач на Python.\n\n"
        "📋 Команды:\n"
        "/tasks — список заданий\n"
        "/task <номер> — взять задание\n"
        "/help — помощь\n\n"
        "Как работать:\n"
        "1. Выбери задание: /task 1\n"
        "2. Напиши код в любом редакторе\n"
        "3. Отправь код мне — я проверю автоматически!"
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📖 ПОМОЩЬ\n\n"
        "1️⃣ Выбери задание: /tasks\n"
        "2️⃣ Возьми задание: /task 1\n"
        "3️⃣ Напиши код на Python\n"
        "4️⃣ Отправь код в этот чат\n"
        "5️⃣ Получи проверку!\n\n"
        "💡 Подсказка: /hint (если есть)\n"
        "❓ Вопросы? Пиши, помогу!"
    )


@bot.message_handler(commands=['tasks'])
def list_tasks(message):
    if not TASKS:
        bot.send_message(message.chat.id, "📚 Пока нет заданий. Скоро добавлю!")
        return

    tasks_list = "📚 ДОСТУПНЫЕ ЗАДАНИЯ\n\n"
    for num, task in TASKS.items():
        tasks_list += f"{num}. {task.get('title', 'Без названия')}\n"
    tasks_list += "\nЧтобы взять задание: /task <номер>\nПример: /task 1"
    bot.send_message(message.chat.id, tasks_list)


@bot.message_handler(commands=['task'])
def get_task(message):
    # Получаем номер задания из команды
    try:
        task_num = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажи номер задания. Пример: /task 1")
        return

    if not TASKS:
        bot.reply_to(message, "📚 Пока нет заданий. Скоро добавлю!")
        return

    if task_num not in TASKS:
        bot.reply_to(message, f"❌ Задания №{task_num} нет.\nСписок: /tasks")
        return

    task = TASKS[task_num]

    # Запоминаем задание для пользователя
    user_current_task[message.chat.id] = task_num

    # Формируем ответ
    response = f"📝 ЗАДАНИЕ {task_num}: {task.get('title', 'Без названия')}\n\n"
    response += f"{task['description']}\n\n"

    if task.get('test_input'):
        response += f"📥 Пример ввода:\n{task['test_input']}\n\n"

    if task.get('expected_output'):
        response += f"📤 Ожидаемый вывод:\n{task['expected_output']}\n\n"

    response += "✏️ Напиши код на Python и отправь его мне!\n"

    if task.get('hint'):
        response += f"💡 Если нужна подсказка: /hint"

    bot.send_message(message.chat.id, response)


@bot.message_handler(commands=['hint'])
def get_hint(message):
    user_id = message.chat.id
    task_num = user_current_task.get(user_id)

    if not task_num:
        bot.reply_to(message, "❌ Сначала выбери задание: /task 1")
        return

    if task_num not in TASKS:
        bot.reply_to(message, "❌ Задание не найдено")
        return

    task = TASKS[task_num]
    hint = task.get('hint', '💡 Подсказка: попробуй разбить задачу на маленькие шаги.')

    bot.send_message(
        user_id,
        f"💡 ПОДСКАЗКА к заданию {task_num}:\n\n{hint}"
    )


# ========== ОСНОВНАЯ ЛОГИКА ПРОВЕРКИ ==========
@bot.message_handler(func=lambda message: True)
def handle_code(message):
    user_id = message.chat.id
    code = message.text

    # Проверяем, есть ли активное задание
    task_num = user_current_task.get(user_id)

    if not task_num:
        bot.reply_to(
            message,
            "❌ Сначала выбери задание: /task 1\n\n"
            "Список заданий: /tasks"
        )
        return

    if task_num not in TASKS:
        bot.reply_to(message, "❌ Задание не найдено. Выбери новое: /tasks")
        user_current_task.pop(user_id, None)
        return

    task = TASKS[task_num]

    # Сообщаем о начале проверки
    status_msg = bot.send_message(user_id, "🔍 Проверяю код... ⏳")

    # Проверяем наличие тестов
    if not task.get('test_input') or not task.get('expected_output'):
        bot.edit_message_text(
            "❌ Для этого задания пока нет тестов. Попробуй другое задание: /tasks",
            chat_id=user_id,
            message_id=status_msg.message_id
        )
        return

    # Запускаем код
    actual_output, error = run_python_code(code, task['test_input'])

    if error:
        response = f"❌ ОШИБКА ВЫПОЛНЕНИЯ\n\n{error}\n\n"
        response += "💡 Проверь синтаксис и попробуй снова!"
        bot.edit_message_text(
            response,
            chat_id=user_id,
            message_id=status_msg.message_id
        )
        return

    # Сравниваем вывод
    actual_normalized = actual_output.strip()
    expected_normalized = task['expected_output'].strip()

    if actual_normalized == expected_normalized:
        response = f"✅ ПРАВИЛЬНО!\n\n"
        response += f"Твой вывод:\n{actual_output}\n\n"
        response += "🎉 Отлично! Хочешь следующее задание?\n"
        response += f"📋 /tasks — список всех заданий"

        bot.edit_message_text(
            response,
            chat_id=user_id,
            message_id=status_msg.message_id
        )
    else:
        response = f"❌ НЕПРАВИЛЬНО\n\n"
        response += f"Твой вывод:\n{actual_output}\n\n"
        response += f"Ожидалось:\n{expected_normalized}\n\n"
        response += "💡 Попробуй:\n"
        response += f"• /hint — посмотреть подсказку\n"
        response += "• Исправить код и отправить снова"

        bot.edit_message_text(
            response,
            chat_id=user_id,
            message_id=status_msg.message_id
        )


# ========== ЗАПУСК ==========
print("=" * 50)
print("🤖 Бот для подготовки к ОГЭ по информатике")
print(f"📚 Загружено заданий: {len(TASKS)}")
print("=" * 50)
print("✅ Бот запущен и готов к работе!")
print("=" * 50)

bot.infinity_polling()