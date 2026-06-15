import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Singleton MySQL connection manager.
    Reads credentials from .env file.
    Usage:
        db = DatabaseConnection()
        conn = db.get_connection()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = None
        return cls._instance

    def get_connection(self):
        """Returns active connection, creates one if not exists."""
        if self._connection is None or not self._connection.is_connected():
            self._connection = self._create_connection()
        return self._connection

    def _create_connection(self):
        """Creates a new MySQL connection from environment variables."""
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
            logger.info("MySQL connection established successfully")
            return conn

        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise

    def close(self):
        """Closes the connection if open."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            logger.info("MySQL connection closed")
            self._connection = None


def get_db():
    """Convenience function — returns active connection."""
    return DatabaseConnection().get_connection()