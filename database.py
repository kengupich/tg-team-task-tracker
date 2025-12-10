"""
Database module for Team Task Management Bot.
Handles all database operations including creating tasks, managing users,
and tracking performance metrics.
"""
import sqlite3
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "task_management.db"

def init_db():
    """Initialize database tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create groups table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        admin_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users(user_id)
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        group_id INTEGER,
        registered INTEGER DEFAULT 0,  -- 0 = not registered, 1 = registered via password
        banned INTEGER DEFAULT 0,  -- 0 = not banned, 1 = banned
        deleted INTEGER DEFAULT 0,  -- 0 = active, 1 = deleted (hidden from lists)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(group_id)
    )
    ''')
    
    # Create tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        description TEXT NOT NULL,
        group_id INTEGER NOT NULL,
        assigned_to_list TEXT,  -- JSON list of user IDs
        has_media INTEGER DEFAULT 0,  -- 1 if task has media attachments
        status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, cancelled
        created_by INTEGER,  -- admin ID who created the task
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(group_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')
    
    # Create task_media table to store attachments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_media (
        media_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        file_id TEXT NOT NULL,  -- Telegram file_id
        file_type TEXT NOT NULL,  -- 'photo' or 'video'
        file_name TEXT,
        file_size INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    )
    ''')
    
    # Create task_history table for logging changes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        action TEXT NOT NULL,  -- 'created', 'updated', 'deleted', 'status_changed'
        old_value TEXT,
        new_value TEXT,
        changed_by INTEGER,  -- admin_id or user_id
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (changed_by) REFERENCES users(user_id)
    )
    ''')
    
    # Create registration_requests table for pending user approvals
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registration_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        username TEXT,
        status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_by INTEGER,  -- admin_id who approved/rejected
        reviewed_at TIMESTAMP
    )
    ''')
    
    # Create group_admins table for many-to-many relationship between groups and admins
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        admin_id INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
        FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE(group_id, admin_id)
    )
    ''')
    
    # Create user_groups table for many-to-many relationship between users and groups
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
        UNIQUE(user_id, group_id)
    )
    ''')
    
    # Add deleted column to users table if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN deleted INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def add_user(user_id, name):
    """
    Add a new user to the database.
    
    Args:
        user_id (int): Telegram user ID of the user
        name (str): Name of the user
        
    Returns:
        bool: True if user was added, False if user already exists
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            # user already exists
            conn.close()
            return False
        
        cursor.execute(
            "INSERT INTO users (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added user {name} (ID: {user_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        conn.close()
        return False

def remove_user(user_id):
    """
    Remove a user from the database.
    
    Args:
        user_id (int): Telegram user ID of the user
        
    Returns:
        bool: True if user was removed, False if user doesn't exist
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            # user doesn't exist
            conn.close()
            return False
        
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Removed user with ID: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        conn.close()
        return False

def get_all_users():
    """
    Get all registered users (excluding deleted users, including banned status).
    
    Returns:
        list: List of dictionaries containing user information
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, name, group_id, banned FROM users WHERE deleted = 0 ORDER BY name")
        users = [{"user_id": row[0], "name": row[1], "group_id": row[2], "banned": row[3]} for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        conn.close()
        return []


def get_users_without_group():
    """Get all users without any group assigned (using user_groups table)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Get users who are NOT in user_groups table and NOT deleted
        cursor.execute("""
            SELECT u.user_id, u.name 
            FROM users u
            WHERE u.deleted = 0
            AND u.user_id NOT IN (SELECT DISTINCT user_id FROM user_groups)
            ORDER BY u.name
        """)
        users = [{"user_id": row[0], "name": row[1]} for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users without group: {e}")
        conn.close()
        return []

def get_user_by_id(user_id):
    """
    Get user information by ID (including banned status).
    
    Args:
        user_id (int): Telegram user ID of the user
        
    Returns:
        dict: user information or None if not found
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, name, banned FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"user_id": row[0], "name": row[1], "banned": row[2]}
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        conn.close()
        return None

def user_exists(user_id):
    """
    Check if a user exists in the database.
    
    Args:
        user_id (int): Telegram user ID of the user
        
    Returns:
        bool: True if user exists, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        conn.close()
        return False

def create_task(date, time, description):
    """
    Create a new task.
    
    Args:
        date (str): Date of the task (YYYY-MM-DD)
        time (str): Time of the task (HH:MM)
        description (str): Description of the task
        
    Returns:
        int: ID of the created task, or None if creation failed
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tasks (date, time, description) VALUES (?, ?, ?)",
            (date, time, description)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Created task with ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        conn.close()
        return None

def get_task_by_id(task_id):
    """
    Get task information by ID.
    
    Args:
        task_id (int): ID of the task
        
    Returns:
        dict: Task information or None if not found
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable row factory for dictionary access
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT task_id, date, time, description, assigned_to FROM tasks WHERE task_id = ?", 
            (task_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        conn.close()
        return None

""" def update_task_status(task_id, user_id, response):
    #Update task status when a user accepts or declines.
    
    #Args:
        #task_id (int): ID of the task
        #user_id (int): Telegram user ID of the user
        #response (str): 'accepted' or 'declined'
        
    #Returns:
        #bool: True if update was successful, False otherwise
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if task exists
        cursor.execute("SELECT task_id, assigned_to FROM tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return False
        
        # Check if task is already assigned
        if task[1] is not None and response == "accepted":
            conn.close()
            return False
        
        cursor.execute(
            "UPDATE tasks SET assigned_to = ? WHERE task_id = ?",
            (user_id, task_id)
        )
    
        conn.commit()
        conn.close()
        logger.info(f"user {user_id} {response} task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        conn.rollback()
        conn.close()
        return False """

def get_all_tasks():
    """
    Get all tasks.
    
    Returns:
        list: List of dictionaries containing task information
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable row factory for dictionary access
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT t.task_id, t.date, t.time, t.description, t.assigned_to, u.name as user_name "
            "FROM tasks t LEFT JOIN users u ON t.assigned_to = u.user_id "
            "ORDER BY t.created_at DESC"
        )
        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            if task["user_name"]:
                task["assigned_to_name"] = task["user_name"]
            tasks.append(task)
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        conn.close()
        return []

""" def get_user_stats(user_id):

    #Get performance statistics for a user.
    
   # Args:
        #user_id (int): Telegram user ID of the user
        
    #Returns:
        #dict: Dictionary containing performance statistics

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Get accepted tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM user_responses WHERE user_id = ? AND response = 'accepted'",
            (user_id,)
        )
        accepted = cursor.fetchone()[0]
        
        # Get declined tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM user_responses WHERE user_id = ? AND response = 'declined'",
            (user_id,)
        )
        declined = cursor.fetchone()[0]
        
        # Calculate acceptance rate
        total = accepted + declined
        acceptance_rate = 0
        if total > 0:
            acceptance_rate = round((accepted / total) * 100)
        
        conn.close()
        return {
            "accepted": accepted,
            "declined": declined,
            "total": total,
            "acceptance_rate": acceptance_rate
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        conn.close()
        return {
            "accepted": 0,
            "declined": 0,
            "total": 0,
            "acceptance_rate": 0
        }
 """

# ============================================================================
# Group Management Functions
# ============================================================================

def create_group(name, admin_id = None):
    """
    Create a new group with an administrator.
    
    Args:
        name (str): Name of the group
        admin_id (int): Telegram user ID of the group admin (must be existing user)
        
    Returns:
        int: ID of the created group, or None if creation failed
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        if admin_id is None:
            cursor.execute(
                "INSERT INTO groups (name) VALUES (?)",
                (name,)
            )
        else:
            cursor.execute(
                "INSERT INTO groups (name, admin_id) VALUES (?, ?)",
                (name, admin_id)
            )

        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Created group '{name}' (ID: {group_id})")
        return group_id
    except sqlite3.IntegrityError as e:
        logger.error(f"Error creating group (likely duplicate name): {e}")
        conn.close()
        return None
    except Exception as e:
        logger.exception(f"Error creating group: {e}")
        conn.close()
        return None
    

def get_group(group_id):
    """Get group information by ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT group_id, name, admin_id FROM groups WHERE group_id = ?", (group_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"group_id": row[0], "name": row[1], "admin_id": row[2]}
        return None
    except Exception as e:
        logger.error(f"Error getting group: {e}")
        conn.close()
        return None


def get_all_groups():
    """Get all groups."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT group_id, name, admin_id FROM groups ORDER BY name"
        )
        groups = [{"group_id": row[0], "name": row[1], "admin_id": row[2]} for row in cursor.fetchall()]
        conn.close()
        return groups
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        conn.close()
        return []


def update_group_admin(group_id, new_admin_id):
    """
    Change the administrator of a group.
    
    Args:
        group_id (int): ID of the group
        new_admin_id (int): Telegram user ID of new admin (must be existing user)
        
    Returns:
        bool: True if update was successful
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if new admin exists as a user (users table uses column 'user_id')
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (new_admin_id,))
        if not cursor.fetchone():
            logger.error(f"New admin user {new_admin_id} does not exist")
            conn.close()
            return False
        
        cursor.execute(
            "UPDATE groups SET admin_id = ? WHERE group_id = ?",
            (new_admin_id, group_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated group {group_id} admin to {new_admin_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating group admin: {e}")
        conn.close()
        return False


# ============================================================================
# GROUP ADMINS FUNCTIONS (Many-to-Many)
# ============================================================================

def add_group_admin(group_id, admin_id):
    """
    Add an admin to a group. Supports multiple admins per group.
    
    Args:
        group_id (int): ID of the group
        admin_id (int): Telegram user ID of admin
        
    Returns:
        bool: True if admin was added successfully
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (admin_id,))
        if not cursor.fetchone():
            logger.error(f"User {admin_id} does not exist")
            conn.close()
            return False
        
        # Check if group exists
        cursor.execute("SELECT group_id FROM groups WHERE group_id = ?", (group_id,))
        if not cursor.fetchone():
            logger.error(f"Group {group_id} does not exist")
            conn.close()
            return False
        
        # Add to group_admins (will fail if already exists due to UNIQUE constraint)
        cursor.execute(
            "INSERT OR IGNORE INTO group_admins (group_id, admin_id) VALUES (?, ?)",
            (group_id, admin_id)
        )
        
        # Also update legacy admin_id field in groups table for backward compatibility
        cursor.execute("SELECT admin_id FROM groups WHERE group_id = ?", (group_id,))
        current_admin = cursor.fetchone()[0]
        if current_admin is None:
            cursor.execute("UPDATE groups SET admin_id = ? WHERE group_id = ?", (admin_id, group_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Added admin {admin_id} to group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding group admin: {e}")
        conn.close()
        return False


def remove_group_admin(group_id, admin_id):
    """
    Remove an admin from a group.
    
    Args:
        group_id (int): ID of the group
        admin_id (int): Telegram user ID of admin
        
    Returns:
        bool: True if admin was removed successfully
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM group_admins WHERE group_id = ? AND admin_id = ?",
            (group_id, admin_id)
        )
        
        # Update legacy admin_id if this was the primary admin
        cursor.execute("SELECT admin_id FROM groups WHERE group_id = ? AND admin_id = ?", (group_id, admin_id))
        if cursor.fetchone():
            # Find another admin to set as primary, or set to NULL
            cursor.execute("SELECT admin_id FROM group_admins WHERE group_id = ? LIMIT 1", (group_id,))
            new_primary = cursor.fetchone()
            new_admin_id = new_primary[0] if new_primary else None
            cursor.execute("UPDATE groups SET admin_id = ? WHERE group_id = ?", (new_admin_id, group_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Removed admin {admin_id} from group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing group admin: {e}")
        conn.close()
        return False


def get_group_admins(group_id):
    """
    Get all admins for a specific group.
    
    Args:
        group_id (int): ID of the group
        
    Returns:
        list: List of user IDs who are admins of this group
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT admin_id FROM group_admins WHERE group_id = ?",
            (group_id,)
        )
        admins = [row[0] for row in cursor.fetchall()]
        conn.close()
        return admins
    except Exception as e:
        logger.error(f"Error getting group admins: {e}")
        conn.close()
        return []


def get_admin_groups(admin_id):
    """
    Get all groups where user is an admin.
    
    Args:
        admin_id (int): Telegram user ID of admin
        
    Returns:
        list: List of group dictionaries
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT g.group_id, g.name, g.admin_id
            FROM groups g
            INNER JOIN group_admins ga ON g.group_id = ga.group_id
            WHERE ga.admin_id = ?
            ORDER BY g.name
        ''', (admin_id,))
        
        groups = []
        for row in cursor.fetchall():
            groups.append({
                "group_id": row[0],
                "name": row[1],
                "admin_id": row[2]
            })
        
        conn.close()
        return groups
    except Exception as e:
        logger.error(f"Error getting admin groups: {e}")
        conn.close()
        return []


def is_group_admin(user_id, group_id=None):
    """
    Check if user is a group admin.
    
    Args:
        user_id (int): Telegram user ID
        group_id (int, optional): Specific group ID to check. If None, checks if admin of any group.
        
    Returns:
        bool: True if user is an admin
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        if group_id is None:
            # Check if admin of any group
            cursor.execute("SELECT COUNT(*) FROM group_admins WHERE admin_id = ?", (user_id,))
        else:
            # Check if admin of specific group
            cursor.execute(
                "SELECT COUNT(*) FROM group_admins WHERE admin_id = ? AND group_id = ?",
                (user_id, group_id)
            )
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking group admin: {e}")
        conn.close()
        return False


def get_group_by_admin_id(admin_id):
    """
    Get first group where user is admin (for backward compatibility).
    Use get_admin_groups() for all groups.
    """
    groups = get_admin_groups(admin_id)
    return groups[0] if groups else None


def update_group_name(group_id, new_name):
    """
    Update the name of a group.
    
    Args:
        group_id (int): ID of the group
        new_name (str): New name for the group
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE groups SET name = ? WHERE group_id = ?",
            (new_name, group_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated group {group_id} name to '{new_name}'")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Error updating group name (likely duplicate): {e}")
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Error updating group name: {e}")
        conn.close()
        return False


def delete_task(task_id):
    """
    Delete a task and all its associated media files.
    
    Args:
        task_id (int): ID of the task to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # First, delete all media files associated with this task
        cursor.execute(
            "DELETE FROM task_media WHERE task_id = ?",
            (task_id,)
        )
        
        # Delete the task
        cursor.execute(
            "DELETE FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_deleted > 0:
            logger.info(f"Deleted task {task_id} and its media files")
            return True
        else:
            logger.warning(f"Task {task_id} not found")
            return False
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        conn.close()
        return False


def delete_group(group_id):
    """
    Delete a group and unassign all users from it.
    Also cancels all tasks associated with the group.
    
    Args:
        group_id (int): ID of the group to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # First, unassign all users from this group
        cursor.execute(
            "UPDATE users SET group_id = NULL WHERE group_id = ?",
            (group_id,)
        )
        
        # Cancel all tasks associated with this group
        cursor.execute(
            "UPDATE tasks SET status = 'cancelled' WHERE group_id = ?",
            (group_id,)
        )
        
        # Delete the group
        cursor.execute(
            "DELETE FROM groups WHERE group_id = ?",
            (group_id,)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Deleted group {group_id} and cancelled its tasks")
        return True
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        conn.close()
        return False


def add_user_to_group(user_id, name, group_id):
    """
    Add a user to a group.
    
    Args:
        user_id (int): Telegram user ID
        name (str): name
        group_id (int): ID of the group
        
    Returns:
        bool: True if added, False if user already exists or group doesn't exist
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if group exists
        cursor.execute("SELECT group_id FROM groups WHERE group_id = ?", (group_id,))
        if not cursor.fetchone():
            logger.error(f"Group {group_id} does not exist")
            conn.close()
            return False
        
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            logger.warning(f"user {user_id} already exists")
            conn.close()
            return False
        
        cursor.execute(
            "INSERT INTO users (user_id, name, group_id) VALUES (?, ?, ?)",
            (user_id, name, group_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added user {name} (ID: {user_id}) to group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding user to group: {e}")
        conn.close()
        return False


def get_group_users(group_id):
    """Get all users in a group (from user_groups many-to-many table)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Get users assigned to this group via user_groups table
        cursor.execute(
            "SELECT u.user_id, u.name FROM users u INNER JOIN user_groups ug ON u.user_id = ug.user_id WHERE ug.group_id = ?",
            (group_id,)
        )
        users_rows = cursor.fetchall()

        # Get admins for this group from group_admins (may include users without group_id set)
        cursor.execute(
            "SELECT u.user_id, u.name FROM users u INNER JOIN group_admins ga ON u.user_id = ga.admin_id WHERE ga.group_id = ?",
            (group_id,)
        )
        admin_rows = cursor.fetchall()

        # Merge and deduplicate by user_id
        combined = {}
        for row in users_rows + admin_rows:
            uid, name = row[0], row[1]
            combined[uid] = name

        # Build sorted list by name
        users = [{"user_id": uid, "name": combined[uid]} for uid in combined]
        users.sort(key=lambda x: (x.get('name') or '').lower())
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting group users: {e}")
        conn.close()
        return []


def register_user(user_id, name):
    """
    Register a new user (self-registration via password).
    user is created without a group.
    
    Args:
        user_id (int): Telegram user ID
        name (str): name/first name
        
    Returns:
        bool: True if registered, False if already exists
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            logger.warning(f"user {user_id} already exists")
            conn.close()
            return False
        
        # Create new user without group
        cursor.execute(
            "INSERT INTO users (user_id, name, group_id, registered) VALUES (?, ?, NULL, 1)",
            (user_id, name)
        )
        conn.commit()
        conn.close()
        logger.info(f"Registered new user {name} (ID: {user_id})")
        return True
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        conn.close()
        return False


def is_user_registered(user_id):
    """Check if a user has registered (via password)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT registered FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] == 1 if row else False
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
        conn.close()
        return False


def has_user_group(user_id):
    """Check if user is assigned to any group (using user_groups table)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM user_groups WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking user groups: {e}")
        conn.close()
        return False


def add_user_to_group(user_id, group_id):
    """Add a user to a group (many-to-many relationship)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO user_groups (user_id, group_id) VALUES (?, ?)",
            (user_id, group_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added user {user_id} to group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding user to group: {e}")
        conn.close()
        return False


def remove_user_from_group(user_id, group_id):
    """Remove a user from a group (many-to-many relationship)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM user_groups WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Removed user {user_id} from group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing user from group: {e}")
        conn.close()
        return False


def get_user_groups(user_id):
    """Get all groups a user belongs to."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT g.group_id, g.name FROM groups g INNER JOIN user_groups ug ON g.group_id = ug.group_id WHERE ug.user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        groups = [{"group_id": row[0], "name": row[1]} for row in rows]
        conn.close()
        return groups
    except Exception as e:
        logger.error(f"Error getting user groups: {e}")
        conn.close()
        return []


def get_users_for_task_assignment(creator_id, creator_is_super_admin, creator_is_group_admin, creator_admin_groups=None):
    """Get users available for task assignment based on creator's role.
    
    Args:
        creator_id: ID of user creating the task
        creator_is_super_admin: True if creator is super admin
        creator_is_group_admin: True if creator is group admin
        creator_admin_groups: List of group_ids where creator is admin (if applicable)
        
    Returns:
        List of users available for assignment
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        if creator_is_super_admin:
            # Super admin can assign to anyone
            cursor.execute("SELECT user_id, name, group_id FROM users WHERE banned = 0 ORDER BY name")
        elif creator_is_group_admin and creator_admin_groups:
            # Group admin can assign to users in their managed groups + themselves
            group_ids_str = ','.join(str(gid) for gid in creator_admin_groups)
            query = f"""
                SELECT DISTINCT u.user_id, u.name, u.group_id 
                FROM users u
                LEFT JOIN user_groups ug ON u.user_id = ug.user_id
                WHERE u.banned = 0 AND (
                    ug.group_id IN ({group_ids_str})
                    OR u.user_id = ?
                )
                ORDER BY u.name
            """
            cursor.execute(query, (creator_id,))
        else:
            # Regular worker can assign to users in their own groups + admins of those groups
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.name, u.group_id
                FROM users u
                WHERE u.banned = 0 AND (
                    u.user_id IN (
                        SELECT ug.user_id FROM user_groups ug
                        WHERE ug.group_id IN (
                            SELECT ug2.group_id FROM user_groups ug2 WHERE ug2.user_id = ?
                        )
                    )
                    OR u.user_id IN (
                        SELECT ga.admin_id FROM group_admins ga
                        WHERE ga.group_id IN (
                            SELECT ug3.group_id FROM user_groups ug3 WHERE ug3.user_id = ?
                        )
                    )
                )
                ORDER BY u.name
            """, (creator_id, creator_id))
        
        rows = cursor.fetchall()
        users = [{"user_id": row["user_id"], "name": row["name"], "group_id": row["group_id"]} for row in rows]
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users for task assignment: {e}")
        conn.close()
        return []


def reassign_user_tasks_to_group(user_id, new_group_id):
    """
    Reassign all tasks where the given user is an executor to a new group.

    Args:
        user_id (int): Telegram user ID
        new_group_id (int): target group ID

    Returns:
        int: number of tasks updated
    """
    import json
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Find tasks where assigned_to_list contains this user
        cursor.execute("SELECT task_id, assigned_to_list FROM tasks WHERE assigned_to_list IS NOT NULL")
        rows = cursor.fetchall()
        updated = 0
        for row in rows:
            assigned_json = row["assigned_to_list"]
            try:
                assigned = json.loads(assigned_json or '[]')
            except Exception:
                assigned = []
            if user_id in assigned:
                cursor.execute("UPDATE tasks SET group_id = ? WHERE task_id = ?", (new_group_id, row["task_id"]))
                updated += 1

        conn.commit()
        conn.close()
        logger.info(f"Reassigned {updated} tasks for user {user_id} to group {new_group_id}")
        return updated
    except Exception as e:
        logger.error(f"Error reassigning tasks for user {user_id}: {e}")
        conn.close()
        return 0


def set_user_name(user_id, new_name):
    """Set a user's display name (name)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()
        conn.close()
        logger.info(f"Set user {user_id} name -> {new_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting user name: {e}")
        conn.close()
        return False


def ban_user(user_id):
    """Ban a user (set banned flag and remove from admin positions)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Set user as banned
        cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        # Remove from group_admins (many-to-many admin table)
        cursor.execute("DELETE FROM group_admins WHERE admin_id = ?", (user_id,))
        # Update groups.admin_id to NULL if this user is primary admin
        cursor.execute("UPDATE groups SET admin_id = NULL WHERE admin_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Banned user {user_id} and removed from admin positions")
        return True
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        conn.close()
        return False


def unban_user(user_id):
    """Unban a user (remove banned flag)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Unbanned user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        conn.close()
        return False


def remove_user_from_all_groups(user_id):
    """Remove user from all groups (when banning)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_groups WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Removed user {user_id} from all groups")
        return True
    except Exception as e:
        logger.error(f"Error removing user from groups: {e}")
        conn.close()
        return False


def delete_user(user_id):
    """Delete a user from the system (bans them and hides from lists)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Set user as banned and deleted (deleted users don't show in lists)
        cursor.execute("UPDATE users SET banned = 1, deleted = 1 WHERE user_id = ?", (user_id,))
        # Remove from all groups
        cursor.execute("DELETE FROM user_groups WHERE user_id = ?", (user_id,))
        # Remove from group_admins (many-to-many admin table)
        cursor.execute("DELETE FROM group_admins WHERE admin_id = ?", (user_id,))
        # Update groups.admin_id to NULL if this user is primary admin
        cursor.execute("UPDATE groups SET admin_id = NULL WHERE admin_id = ?", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Deleted user {user_id} and removed from admin positions")
        return True
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        conn.close()
        return False


def cancel_user_tasks(user_id):
    """Cancel all tasks where user is creator or sole assignee.
    Remove user from tasks where they are co-assignee.
    
    Args:
        user_id: ID of user being banned/deleted
        
    Returns:
        dict with counts of cancelled and updated tasks
    """
    import json
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cancelled_count = 0
        updated_count = 0
        
        # Get all tasks where user is creator
        cursor.execute("SELECT task_id FROM tasks WHERE created_by = ? AND status != 'cancelled'", (user_id,))
        creator_tasks = [row['task_id'] for row in cursor.fetchall()]
        
        # Cancel tasks where user is creator
        if creator_tasks:
            placeholders = ','.join('?' * len(creator_tasks))
            cursor.execute(f"UPDATE tasks SET status = 'cancelled' WHERE task_id IN ({placeholders})", creator_tasks)
            cancelled_count += len(creator_tasks)
        
        # Get all tasks where user is in assigned_to_list
        cursor.execute("SELECT task_id, assigned_to_list FROM tasks WHERE assigned_to_list IS NOT NULL AND status != 'cancelled'")
        all_tasks = cursor.fetchall()
        
        for task in all_tasks:
            try:
                assigned = json.loads(task['assigned_to_list'] or '[]')
                if user_id in assigned:
                    if len(assigned) == 1:
                        # User is sole assignee - cancel task
                        cursor.execute("UPDATE tasks SET status = 'cancelled' WHERE task_id = ?", (task['task_id'],))
                        cancelled_count += 1
                    else:
                        # User is co-assignee - remove from list
                        assigned.remove(user_id)
                        cursor.execute("UPDATE tasks SET assigned_to_list = ? WHERE task_id = ?", 
                                     (json.dumps(assigned), task['task_id']))
                        updated_count += 1
            except Exception as e:
                logger.error(f"Error processing task {task['task_id']}: {e}")
                continue
        
        conn.commit()
        conn.close()
        logger.info(f"Cancelled {cancelled_count} tasks, updated {updated_count} tasks for user {user_id}")
        return {'cancelled': cancelled_count, 'updated': updated_count}
    except Exception as e:
        logger.error(f"Error cancelling user tasks: {e}")
        conn.close()
        return {'cancelled': 0, 'updated': 0}


# ============================================================================
# Task Management Functions (Updated for Groups and Media)
# ============================================================================

def create_task(date, time, description, group_id, admin_id, assigned_to_list=None):
    """
    Create a new task for a group.
    
    Args:
        date (str): Date (YYYY-MM-DD)
        time (str): Time (HH:MM)
        description (str): Task description
        group_id (int): ID of the group
        admin_id (int): ID of admin creating the task
        assigned_to_list (list): List of user IDs to assign (optional)
        
    Returns:
        int: ID of created task, or None if failed
    """
    import json
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        assigned_to_json = json.dumps(assigned_to_list) if assigned_to_list else None
        
        cursor.execute(
            """INSERT INTO tasks (date, time, description, group_id, 
               assigned_to_list, created_by, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (date, time, description, group_id, assigned_to_json, admin_id)
        )
        task_id = cursor.lastrowid
        
        # Log task creation
        cursor.execute(
            """INSERT INTO task_history (task_id, action, new_value, changed_by) 
               VALUES (?, 'created', ?, ?)""",
            (task_id, f"Task created: {description}", admin_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Created task {task_id} for group {group_id}")
        return task_id
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        conn.close()
        return None


def get_group_tasks(group_id):
    """Get all tasks for a group."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, assigned_to_list, 
                      status, has_media, created_at 
               FROM tasks WHERE group_id = ? ORDER BY created_at DESC""",
            (group_id,)
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting group tasks: {e}")
        conn.close()
        return []


def get_user_tasks(user_id):
    """Get all tasks assigned to a user (as executor)."""
    import json
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE status != 'cancelled' ORDER BY created_at DESC"""
        )
        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            assigned_list = json.loads(task.get('assigned_to_list') or '[]')
            if user_id in assigned_list:
                tasks.append(task)
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting user tasks: {e}")
        conn.close()
        return []


def get_tasks_created_by_user(user_id):
    """Get all tasks created by a user (as постановник)."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE created_by = ? AND status != 'cancelled' 
               ORDER BY created_at DESC""",
            (user_id,)
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks created by user: {e}")
        conn.close()
        return []


def get_all_tasks():
    """Get all tasks (for super admin)."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE status != 'cancelled' ORDER BY created_at DESC"""
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting all tasks: {e}")
        conn.close()
        return []


def get_multiple_groups_tasks(group_ids):
    """Get all tasks for multiple groups (for admins with multiple groups)."""
    if not group_ids:
        return []
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        placeholders = ','.join('?' * len(group_ids))
        query = f"""SELECT task_id, date, time, description, group_id, assigned_to_list, 
                           status, has_media, created_at, created_by
                    FROM tasks WHERE group_id IN ({placeholders}) AND status != 'cancelled' 
                    ORDER BY created_at DESC"""
        cursor.execute(query, group_ids)
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting multiple groups tasks: {e}")
        conn.close()
        return []


def update_task_status(task_id, new_status):
    """
    Update task status (pending, in_progress, completed, cancelled).
    
    Args:
        task_id (int): ID of the task
        new_status (str): New status
        
    Returns:
        bool: True if successful
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE task_id = ?",
            (new_status, task_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Updated task {task_id} status to {new_status}")
        return True
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        conn.close()
        return False


def update_task_assignment(task_id, assigned_to_list):
    """
    Update the list of assigned users for a task.
    
    Args:
        task_id (int): ID of the task
        assigned_to_list (list): New list of user IDs
        
    Returns:
        bool: True if successful
    """
    import json
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        assigned_to_json = json.dumps(assigned_to_list)
        cursor.execute(
            """UPDATE tasks SET assigned_to_list = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE task_id = ?""",
            (assigned_to_json, task_id)
        )
        rows_updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_updated > 0:
            logger.info(f"Updated task {task_id} assignments")
            return True
        else:
            logger.warning(f"Task {task_id} not found for assignment update")
            return False
    except Exception as e:
        logger.error(f"Error updating task assignment: {e}")
        conn.close()
        return False


def get_task_by_id(task_id):
    """Get task information by ID."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, 
                      assigned_to_list, status, has_media, created_by, created_at 
               FROM tasks WHERE task_id = ?""",
            (task_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        conn.close()
        return None


# ============================================================================
# Media Management Functions
# ============================================================================

def add_task_media(task_id, file_id, file_type, file_name=None, file_size=None):
    """
    Add a media file to a task.
    
    Args:
        task_id (int): ID of the task
        file_id (str): Telegram file_id
        file_type (str): 'photo' or 'video'
        file_name (str): Optional filename
        file_size (int): Optional file size in bytes
        
    Returns:
        int: ID of media record, or None if failed
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check media count for this task (max 20)
        cursor.execute("SELECT COUNT(*) FROM task_media WHERE task_id = ?", (task_id,))
        media_count = cursor.fetchone()[0]
        
        if media_count >= 20:
            logger.warning(f"Task {task_id} already has maximum 20 media files")
            conn.close()
            return None
        
        cursor.execute(
            """INSERT INTO task_media (task_id, file_id, file_type, file_name, file_size) 
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, file_id, file_type, file_name, file_size)
        )
        media_id = cursor.lastrowid
        
        # Update task has_media flag
        cursor.execute(
            "UPDATE tasks SET has_media = 1 WHERE task_id = ?",
            (task_id,)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Added media {media_id} to task {task_id}")
        return media_id
    except Exception as e:
        logger.error(f"Error adding task media: {e}")
        conn.close()
        return None


def get_task_media(task_id):
    """Get all media files for a task."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT media_id, file_id, file_type, file_name, file_size, added_at 
               FROM task_media WHERE task_id = ? ORDER BY added_at""",
            (task_id,)
        )
        media = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return media
    except Exception as e:
        logger.error(f"Error getting task media: {e}")
        conn.close()
        return []


def remove_task_media(media_id):
    """Remove a media file from a task."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT task_id FROM task_media WHERE media_id = ?", (media_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        task_id = row[0]
        
        cursor.execute("DELETE FROM task_media WHERE media_id = ?", (media_id,))
        
        # If no more media, update has_media flag
        cursor.execute("SELECT COUNT(*) FROM task_media WHERE task_id = ?", (task_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("UPDATE tasks SET has_media = 0 WHERE task_id = ?", (task_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"Removed media {media_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing task media: {e}")
        conn.close()
        return False


def create_registration_request(user_id, name, username=None):
    """Create a new registration request."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registration_requests (user_id, name, username, status)
            VALUES (?, ?, ?, 'pending')
        ''', (user_id, name, username))
        conn.commit()
        conn.close()
        logger.info(f"Registration request created for user {user_id}")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration request already exists for user {user_id}")
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Error creating registration request: {e}")
        conn.close()
        return False


def get_pending_registration_requests():
    """Get all pending registration requests."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM registration_requests 
            WHERE status = 'pending' 
            ORDER BY requested_at DESC
        ''')
        requests = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return requests
    except Exception as e:
        logger.error(f"Error getting registration requests: {e}")
        conn.close()
        return []


def approve_registration_request(request_id, reviewer_id):
    """Approve a registration request and create user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute("SELECT user_id, name FROM registration_requests WHERE request_id = ?", (request_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        user_id, name = row
        
        # Update request status
        cursor.execute('''
            UPDATE registration_requests 
            SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE request_id = ?
        ''', (reviewer_id, request_id))
        
        # Create user in users table
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, name, registered)
            VALUES (?, ?, 1)
        ''', (user_id, name))
        
        conn.commit()
        conn.close()
        logger.info(f"Approved registration request {request_id} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error approving registration request: {e}")
        conn.close()
        return False


def reject_registration_request(request_id, reviewer_id):
    """Reject a registration request."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE registration_requests 
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE request_id = ?
        ''', (reviewer_id, request_id))
        conn.commit()
        conn.close()
        logger.info(f"Rejected registration request {request_id}")
        return True
    except Exception as e:
        logger.error(f"Error rejecting registration request: {e}")
        conn.close()
        return False


def get_registration_request_by_user_id(user_id):
    """Get registration request for a specific user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM registration_requests 
            WHERE user_id = ? 
            ORDER BY requested_at DESC 
            LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting registration request: {e}")
        conn.close()
        return None
