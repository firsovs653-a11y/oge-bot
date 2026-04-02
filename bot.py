import telebot
import json
import os
import subprocess
import tempfile
from dotenv import load_dotenv
<<<<<<< HEAD
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
=======
>>>>>>> 87f5b5e1b541645bb104ea58f41c8413aa097843

# 1. Загружаем переменные окружения
load_dotenv()

# 2. Получаем токен
TOKEN = os.environ.get('TELEGRAM_TOKEN')

if not TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не задан!")
    exit(1)

# 3. СОЗДАЕМ ОБЪЕКТ БОТА (ВАЖНО: ДО ОБРАБОТЧИКОВ!)
bot = telebot.TeleBot(TOKEN)

# 4. Загружаем задания
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

<<<<<<< HEAD

# 5. Функция запуска кода
=======
>>>>>>> 87f5b5e1b541645bb104ea58f41c8413aa097843
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

<<<<<<< HEAD

# 6. ОБРАБОТЧИКИ КОМАНД (после создания bot)

=======
>>>>>>> 87f5b5e1b541645bb104ea58f41c8413aa097843
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для подготовки к ОГЭ по информатике.\n\n"
        "/tasks — список заданий\n"
        "/task <номер> — взять задание\n"
        "/app — открыть Mini App\n"
        "/help — помощь"
    )

<<<<<<< HEAD

@bot.message_handler(commands=['app'])
def mini_app(message):
    keyboard = InlineKeyboardMarkup()

    # Ссылка на твой Mini App (замени на реальную после деплоя)
    web_app = WebAppInfo(url="https://oge-miniapp.up.railway.app")

    button = InlineKeyboardButton(
        text="🚀 Открыть Mini App",
        web_app=web_app
    )
    keyboard.add(button)

    bot.send_message(
        message.chat.id,
        "📱 Нажми на кнопку, чтобы открыть приложение с заданиями:",
        reply_markup=keyboard
    )


=======
>>>>>>> 87f5b5e1b541645bb104ea58f41c8413aa097843
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "1️⃣ Выбери задание: /tasks\n"
        "2️⃣ Возьми задание: /task 1\n"
        "3️⃣ Напиши код и отправь мне\n"
        "4️⃣ Получи проверку!\n\n"
        "📱 Или открой Mini App: /app"
    )

@bot.message_handler(commands=['tasks'])
def list_tasks(message):
    if not TASKS:
        bot.send_message(message.chat.id, "📚 Пока нет заданий.")
        return
    
    tasks_list = "📚 ДОСТУПНЫЕ ЗАДАНИЯ\n\n"
    for num, task in TASKS.items():
        tasks_list += f"{num}. {task.get('title', 'Без названия')}\n"
    tasks_list += "\nЧтобы взять задание: /task <номер>"
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

<<<<<<< HEAD

# 7. ЗАПУСК БОТА
print("🤖 Бот запущен!")
bot.infinity_polling()
=======
print("🤖 Бот запущен!")
bot.infinity_polling()
>>>>>>> 87f5b5e1b541645bb104ea58f41c8413aa097843
