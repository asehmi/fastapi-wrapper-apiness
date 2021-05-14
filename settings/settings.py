# django environ
import environ
# system environ
from os import environ as osenv
import os
from dotenv import load_dotenv, find_dotenv

# ======== GLOBAL SETTINGS ========

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.getcwd()

print(f'>>> CWD: {BASE_DIR} <<<')

# ======== GENERAL ENVIRONMENT VARS ========

env = environ.Env(
    DEBUG=(bool, False),
    ENVIRONMENT=(str, None),
    ENABLE_FILE_LOGGERS=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

DEBUG = env('DEBUG')
ENVIRONMENT = env('ENVIRONMENT')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

DATA_PATH = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(BASE_DIR, 'sql_db')

# ======== SECRET ENVIRONMENT VARS ========

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

# API General

API_HOST = osenv.get('API_HOST', 'localhost')
API_PORT = int(osenv.get('API_PORT', '8000'))
API_BASE_URL = osenv.get('API_BASE_URL', 'http://localhost:8000')
CORS_ALLOW_ORIGINS = osenv.get('CORS_ALLOW_ORIGINS', '').split(',')