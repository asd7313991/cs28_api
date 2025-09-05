import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    APP_NAME = os.getenv("APP_NAME", "cs28-api")
    APP_ENV = os.getenv("APP_ENV", "dev")
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    TZ = os.getenv("TZ", "Asia/Shanghai")

    MYSQL_DSN = (
        f"mysql+aiomysql://{os.getenv('MYSQL_USER','root')}:{os.getenv('MYSQL_PASSWORD','123456')}"
        f"@{os.getenv('MYSQL_HOST','127.0.0.1')}:{os.getenv('MYSQL_PORT','3306')}/{os.getenv('MYSQL_DB','cs28')}?charset=utf8mb4"
    )
    REDIS_URL = f"redis://{os.getenv('REDIS_HOST','127.0.0.1')}:{os.getenv('REDIS_PORT','6379')}/{os.getenv('REDIS_DB','0')}"

    JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))
    PASSWORD_SALT = os.getenv("PASSWORD_SALT", "change_me")

    BET_LOCK_AHEAD_SECONDS = int(os.getenv("BET_LOCK_AHEAD_SECONDS", "3"))

    LOTTERY_DEFAULT_CODE = os.getenv("LOTTERY_DEFAULT_CODE", "jnd28")
    LOTTERY_DEFAULT_NAME = os.getenv("LOTTERY_DEFAULT_NAME", "加拿大28")
    LOTTERY_DEFAULT_PERIOD_SECONDS = int(os.getenv("LOTTERY_DEFAULT_PERIOD_SECONDS", "210"))

    COLLECTOR_JND28_URL = os.getenv("COLLECTOR_JND28_URL", "https://cs00.vip/data/last/jnd28.json")
    COLLECTOR_POLL_SECONDS = int(os.getenv("COLLECTOR_POLL_SECONDS", "5"))

settings = Settings()
