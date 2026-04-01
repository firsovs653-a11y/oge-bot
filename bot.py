import telebot
import json
import os
import subprocess
import tempfile
from dotenv import load_dotenv
from flask import Flask, request
import threading
import time

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
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для подготовки к ОГЭ по информатике.\n\n"
        "/tasks — список заданий\n"
        "/task <номер> — взять задание\n"
        "/help — помощь"
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "1️⃣ Выбери задание: /tasks\n"
        "2️⃣ Возьми задание: /task 1\n"
        "3️⃣ Напиши код и отправь мне\n"
        "4️⃣ Получи проверку!"
    )


@bot.message_handler(commands=['tasks'])
def list_tasks(message):
    if not TASKS:
        bot.send_message(message.chat.id, "📚 Пока нет заданий.")
        return

    tasks_list = "📚 ДОСТУПНЫЕ ЗАДАНИЯ\n\n"
    for num, task in TASKS.items():
        tasks_list += f"{num}. {task.get('title', 'Без названия')}\n"
    bot.send_message(message.chat.id, tasks_list)


@bot.message_handler(commands=['task'])
def get_task(message):
    try:
        task_num = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "❌ Укажи номер задания. Пример: /task 1")
        return

    if task_num not in TASKS:
        bot.reply_to(message, f"❌ Задания №{task_num} нет.")
        return

    task = TASKS[task_num]
    user_current_task[message.chat.id] = task_num

    response = f"📝 ЗАДАНИЕ {task_num}: {task.get('title')}\n\n"
    response += f"{task['description']}\n\n"
    response += f"📥 Пример ввода:\n{task['test_input']}\n\n"
    response += f"📤 Ожидаемый вывод:\n{task['expected_output']}\n\n"
    response += "✏️ Напиши код и отправь мне!"

    bot.send_message(message.chat.id, response)


@bot.message_handler(commands=['hint'])
def get_hint(message):
    user_id = message.chat.id
    task_num = user_current_task.get(user_id)

    if not task_num:
        bot.reply_to(message, "❌ Сначала выбери задание: /task 1")
        return

    task = TASKS.get(task_num, {})
    hint = task.get('hint', '💡 Попробуй разбить задачу на маленькие шаги.')
    bot.send_message(user_id, f"💡 ПОДСКАЗКА:\n\n{hint}")


@bot.message_handler(func=lambda message: True)
def handle_code(message):
    user_id = message.chat.id
    code = message.text
    task_num = user_current_task.get(user_id)

    if not task_num:
        bot.reply_to(message, "❌ Сначала выбери задание: /task 1")
        return

    task = TASKS.get(task_num)
    if not task:
        bot.reply_to(message, "❌ Задание не найдено")
        return

    status_msg = bot.send_message(user_id, "🔍 Проверяю код... ⏳")

    actual_output, error = run_python_code(code, task['test_input'])

    if error:
        response = f"❌ ОШИБКА\n\n{error}"
    elif actual_output.strip() == task['expected_output'].strip():
        response = f"✅ ПРАВИЛЬНО!\n\nТвой вывод:\n{actual_output}\n\n🎉 Отлично!"
    else:
        response = f"❌ НЕПРАВИЛЬНО\n\nТвой вывод:\n{actual_output}\n\nОжидалось:\n{task['expected_output']}"

    bot.edit_message_text(response, user_id, status_msg.message_id)


# ========== ДЛЯ RENDER WEB SERVICE ==========
app = Flask(__name__)


@app.route('/')
def index():
    return "🤖 Бот для подготовки к ОГЭ по информатике работает!"


@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200


def run_flask():
    app.run(host='0.0.0.0', port=10000)


# Запускаем Flask в отдельном потоке
threading.Thread(target=run_flask).start()

# Удаляем старый webhook и устанавливаем новый
time.sleep(2)
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url='https://oge-bot.onrender.com/webhook')

print("🤖 Бот запущен на Render Web Service!")