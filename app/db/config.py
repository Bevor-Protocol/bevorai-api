import os

from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("POSTGRES_USER")
db_pswd = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
db_host = os.getenv("POSTGRES_HOST", "postgres")

TORTOISE_ORM = {
    "connections": {
        "default": f"postgres://{db_user}:{db_pswd}@{db_host}:5432/{db_name}"
    },
    "apps": {
        "models": {
            "models": ["app.db.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
