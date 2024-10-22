import aiomysql
import os
from utils import get_secret
from dotenv import load_dotenv

# Load environment variables from .env file

load_dotenv()

secret_name = os.getenv("SECRET_NAME")
region_name = os.getenv("REGION_NAME")

secret_value = get_secret(secret_name, region_name)

DATABASE_CONFIG = {
    'host': secret_value.get('DB_HOST'),
    'port': int(secret_value.get('DB_PORT')),
    'user': secret_value.get('DB_USER'),
    'password': secret_value.get('DB_PASSWORD'),
    'db': secret_value.get('DB_NAME')
}

db_pool = None

async def init_db_pool():
    global db_pool
    db_pool = await aiomysql.create_pool(**DATABASE_CONFIG)

# async def get_db_pool():
#     return db_pool


async def get_db_pool():
    return await aiomysql.create_pool(**DATABASE_CONFIG)
