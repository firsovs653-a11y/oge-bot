import telebot
import json
import os
import subprocess
import tempfile
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

load_dotenv()

TOKEN = os.environ.get('TELEGRAM_TOKEN')

if not TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не задан!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

user_current_task = {}


def load_tasks():
    try:
        with open('tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        print(f"✅ Загружено заданий: {len(tasks)}")
        return tasks
    except:
        return {}


TASKS = load_tasks()


def run_python_code(code, input_data):
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name

        process = subprocess.run(
            ['python3', temp_file],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=5,
            encoding='utf-8'
        )

        os.unlink(temp_file)

        if process.returncode == 0:
            return process.stdout.strip(), None
        else:
            return None, process.stderr.strip()

    except subprocess.TimeoutExpired:
        return None, "⏰ Время выполнения превышено (5 сек)"
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"


@bot.message_handler(commands=['start'])
def start(message):
    # Временно для локального тестирования
    # Потом замени на реальный URL от Railway
    webapp_url = "oge-miniapp-production.up.railway.app"  # Локальный Mini App

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        text="📱 Открыть Mini App",
        web_app=WebAppInfo(url=webapp_url)
    ))

    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для подготовки к ОГЭ по информатике.\n\n"
        "📱 Нажми на кнопку ниже, чтобы открыть Mini App с заданиями!\n\n"
        "Или используй команды:\n"
        "/tasks — список заданий\n"
        "/task <номер> — взять задание\n"
        "/help — помощь",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "1️⃣ Выбери задание: /tasks\n"
        "2️⃣ Возьми задание: /task 1\n"
        "3️⃣ Напиши код и отправь мне\n"
        "4️⃣ Получи проверку!\n\n"
        "📱 Или нажми на кнопку 'Открыть Mini App' для удобного интерфейса!"
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
    user_current_task[message.chat.id] = task_num

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
        response += f"📋 /tasks — список всех заданий\n"
        response += "📱 Или открой Mini App для удобного интерфейса!"

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
        response += "• Исправить код и отправить снова\n"
        response += "• Открыть Mini App для удобного интерфейса"

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
