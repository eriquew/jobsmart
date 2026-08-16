import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


def get_db():
    """
    Returns a fresh MySQL connection.
    Creates a new connection each time — thread safe.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME", "jobsmart"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            consume_results=True
        )
        return conn
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        raise


class DatabaseConnection:
    """
    Kept for backward compatibility with code that imports DatabaseConnection.
    All new code should use get_db() directly.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self):
        return get_db()

    def close(self):
        pass