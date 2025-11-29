import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

PATH_TO_DB_USERS = "db/users.db"

PATH_TO_DB_TASK = "db/task.db"


