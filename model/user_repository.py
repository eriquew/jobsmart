import logging
import yaml
from typing import List, Optional
from mysql.connector import Error

from model.database.db_connection import get_db

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Handles all database operations for users.
    Manages user profiles stored as YAML in MySQL.
    """

    def create_user(self, name: str, email: str = None,
                    location: str = None,
                    profile_yaml: dict = None) -> Optional[int]:
        """
        Creates a new user.
        Returns the new user_id or None on error.
        """
        sql = """
            INSERT INTO users (name, email, location, profile_yaml)
            VALUES (%s, %s, %s, %s)
        """
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            yaml_str = yaml.dump(profile_yaml,
                                 allow_unicode=True) if profile_yaml else None
            cursor.execute(sql, (name, email, location, yaml_str))
            conn.commit()
            user_id = cursor.lastrowid
            cursor.close()
            logger.info(f"Created user: {name} (id={user_id})")
            return user_id
        except Error as e:
            logger.error(f"Error creating user '{name}': {e}")
            return None

    def get_all_users(self) -> List[dict]:
        """Returns all users — used by sidebar selector."""
        sql = "SELECT id, name, email, location FROM users ORDER BY name"
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql)
            users  = cursor.fetchall()
            cursor.close()
            return users
        except Error as e:
            logger.error(f"Error fetching users: {e}")
            return []

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Returns full user record including profile_yaml."""
        sql = "SELECT * FROM users WHERE id = %s"
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, (user_id,))
            user   = cursor.fetchone()
            cursor.close()
            return user
        except Error as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def get_profile(self, user_id: int) -> Optional[dict]:
        """
        Returns parsed profile dict for a user.
        Reads from DB first, falls back to config/profile.yaml
        for user_id=1 (Wilson — default user).
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        if user.get("profile_yaml"):
            try:
                return yaml.safe_load(user["profile_yaml"])
            except yaml.YAMLError as e:
                logger.error(f"Error parsing profile YAML for user {user_id}: {e}")

        # Fallback to file for default user
        if user_id == 1:
            try:
                with open("config/profile.yaml", "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.error("config/profile.yaml not found")

        return None

    def update_profile(self, user_id: int, profile: dict) -> bool:
        """Updates user profile YAML in DB."""
        sql = "UPDATE users SET profile_yaml = %s WHERE id = %s"
        try:
            conn     = get_db()
            cursor   = conn.cursor(buffered=True)
            yaml_str = yaml.dump(profile, allow_unicode=True)
            cursor.execute(sql, (yaml_str, user_id))
            conn.commit()
            cursor.close()
            logger.info(f"Updated profile for user {user_id}")
            return True
        except Error as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """Deletes a user and all their scores and tracking."""
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            cursor.execute(
                "DELETE FROM job_scores WHERE user_id = %s", (user_id,)
            )
            cursor.execute(
                "DELETE FROM job_tracking WHERE user_id = %s", (user_id,)
            )
            cursor.execute(
                "DELETE FROM users WHERE id = %s", (user_id,)
            )
            conn.commit()
            cursor.close()
            logger.info(f"Deleted user {user_id}")
            return True
        except Error as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    def user_exists(self, name: str) -> bool:
        """Checks if a user with this name already exists."""
        sql = "SELECT id FROM users WHERE name = %s LIMIT 1"
        try:
            conn   = get_db()
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql, (name,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Error as e:
            logger.error(f"Error checking user exists: {e}")
            return False