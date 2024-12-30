import os
from dotenv import load_dotenv

# Загрузка данных из .env файла
load_dotenv()

# Получение параметров подключения к базе данных
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

# Получение секрета для JWT
SECRET_KEY = os.environ.get("SECRET_KEY")