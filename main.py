import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import logging
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64
from dotenv import load_dotenv
import pytz  # Новая библиотека для работы с часовыми поясами

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_logs.txt'),
        logging.StreamHandler()
    ]
)

# Настройка intents
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

TRACKED_USERS = [
    "David Perres",
    "Billy Gale",
    "Edvin",
    "Richie Kawasaki",
    "Aron",
    "Isaac Yates",
    "Angel",
    "Virgil",
    "Colby Tailer",
    "Oliver Lux",
    "Jurek",
    "Damian Kowalski",
    "Van Simmons",
    "Oscar Upton",
    "Andi_Landi",
    "Nikitich",
    "Adam Merch",
    "Mason Norville",
    "Yohan Paxton",
    "Yuri Torres",
    "Travis Stone",
    "Martin Santos",
    "Isaiah Miller",
    "Dan Hudson",
    "Iker Huxley"
]

# Настройка Google Sheets из переменных окружения
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Получение переменных окружения
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_JSON_BASE64 = os.getenv('SERVICE_ACCOUNT_JSON_BASE64')

# Настройка часового пояса (GMT+2)
TIMEZONE = pytz.timezone('Europe/Kiev')  # или 'Europe/Bucharest'

# Проверка переменных окружения
print(f"DISCORD_TOKEN: {'✅' if DISCORD_TOKEN else '❌'}")
print(f"SPREADSHEET_ID: {'✅' if SPREADSHEET_ID else '❌'}")
print(f"SERVICE_ACCOUNT_JSON_BASE64: {'✅' if SERVICE_ACCOUNT_JSON_BASE64 else '❌'}")
print(f"TRACKED_USERS LENGTH: {len(TRACKED_USERS)}")

# Инициализация Google Sheets
def init_sheets():
    try:
        if not SERVICE_ACCOUNT_JSON_BASE64:
            raise ValueError("SERVICE_ACCOUNT_JSON_BASE64 не найден в переменных окружения")

        # Декодируем Base64 и парсим JSON
        service_account_json = base64.b64decode(SERVICE_ACCOUNT_JSON_BASE64).decode('utf-8')
        service_account_info = json.loads(service_account_json)

        # Создаем credentials из декодированного JSON
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet('BackLog')
        return worksheet
    except Exception as e:
        logging.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def get_utc_plus_2_time():
    """Получает текущее время в UTC+2"""
    utc_now = datetime.utcnow()
    utc_plus_2 = pytz.utc.localize(utc_now).astimezone(TIMEZONE)
    return utc_plus_2

def is_user_tracked(member):
    """Проверяет, нужно ли отслеживать этого пользователя"""
    # Проверяем по display_name и username
    display_name = member.display_name
    username = member.name

    # Проверяем точное совпадение
    if display_name in TRACKED_USERS or username in TRACKED_USERS:
        return True

    # Проверяем частичное совпадение (на случай если есть различия в регистре или пробелах)
    for tracked_user in TRACKED_USERS:
        if (tracked_user.lower().strip() == display_name.lower().strip() or
            tracked_user.lower().strip() == username.lower().strip()):
            return True

    return False

@bot.event
async def on_ready():
    print(f'{bot.user} подключен к Discord!')
    logging.info(f'Бот {bot.user} запущен')

    # Проверка подключения к Google Sheets
    worksheet = init_sheets()
    if worksheet:
        print("✅ Подключение к Google Sheets успешно")
    else:
        print("❌ Ошибка подключения к Google Sheets")

@bot.event
async def on_voice_state_update(member, before, after):
    """Обработчик изменений голосового состояния пользователя"""

    # Проверяем, нужно ли отслеживать этого пользователя
    if not is_user_tracked(member):
        return

    # Пользователь присоединился к голосовому каналу
    if before.channel is None and after.channel is not None:
        log_voice_event(member, "LogIn", after.channel.name)

    # Пользователь покинул голосовой канал
    elif before.channel is not None and after.channel is None:
        log_voice_event(member, "LogOut", before.channel.name)

def log_voice_event(member, event_type, channel_name):
    """Запись события в Google Sheets и локальный лог"""

    # Получаем время в UTC+2
    current_time = get_utc_plus_2_time()
    date_str = current_time.strftime('%Y-%m-%d')
    time_str = current_time.strftime('%H:%M:%S')
    name = member.display_name
    username = member.name

    # Локальное логирование
    log_message = f"🎤 {name} ({username}) {event_type} канал '{channel_name}' в {time_str} (UTC+2)"
    print(log_message)
    logging.info(log_message)

    # Запись в Google Sheets
    try:
        worksheet = init_sheets()
        if worksheet:
            # Добавляем новую строку
            row_data = [date_str, name, time_str if event_type == "LogIn" else "",
                       time_str if event_type == "LogOut" else "", channel_name]
            worksheet.append_row(row_data)
            print(f"✅ Данные записаны в Google Sheets: {row_data}")
        else:
            print("❌ Не удалось подключиться к Google Sheets")
    except Exception as e:
        logging.error(f"Ошибка записи в Google Sheets: {e}")
        print(f"❌ Ошибка записи в Google Sheets: {e}")

# Запуск бота
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
