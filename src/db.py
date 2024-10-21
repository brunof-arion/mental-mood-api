import aiomysql
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME')
}

db_pool = None

async def init_db_pool():
    global db_pool
    db_pool = await aiomysql.create_pool(**DATABASE_CONFIG)

# async def get_db_pool():
#     return db_pool


async def get_db_pool():
    return await aiomysql.create_pool(**DATABASE_CONFIG)
