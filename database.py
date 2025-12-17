"""
Database module for Team Task Management Bot.
Handles all database operations including creating tasks, managing users,
and tracking performance metrics.

Uses PostgreSQL exclusively (local or Railway) with connection pooling.
"""
import logging
from datetime import datetime
from contextlib import contextmanager
from db_postgres import get_db_connection

# Track pool instance for connection management
_db_pool_instance = None

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize database tables if they don't exist."""
    try:
        db_conn = get_db_connection()
        conn = db_conn.get_connection()
        cursor = conn.cursor()
        logger.info("Database connection established successfully")
        
        # Note: init_db doesn't use context manager as it's special initialization
        # We'll return the connection manually at the end
    except Exception as e:
        logger.error(f"Failed to connect to database during initialization: {e}")
        raise
    
    # Create users table first (no dependencies)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT,
        group_id INTEGER,
        registered INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0,
        deleted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create groups table (after users exists)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        group_id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        admin_id BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users(user_id)
    )
    ''')
    
    # Add group_id foreign key to users (after groups exists)
    try:
        cursor.execute('''
        ALTER TABLE users
        ADD CONSTRAINT fk_user_group FOREIGN KEY (group_id) REFERENCES groups(group_id)
        ''')
    except Exception:
        pass  # Constraint might already exist
    
    # Create tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id SERIAL PRIMARY KEY,
        title TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        description TEXT NOT NULL,
        group_id INTEGER NOT NULL,
        assigned_to_list TEXT,
        has_media INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_by BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(group_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    )
    ''')
    
    # Create task_media table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_media (
        media_id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL,
        file_id TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_name TEXT,
        file_size INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    )
    ''')
    
    # Create task_history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_history (
        history_id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        changed_by BIGINT,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id),
        FOREIGN KEY (changed_by) REFERENCES users(user_id)
    )
    ''')
    
    # Create registration_requests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registration_requests (
        request_id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        username TEXT,
        status TEXT DEFAULT 'pending',
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_by BIGINT,
        reviewed_at TIMESTAMP
    )
    ''')
    
    # Create group_admins table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_admins (
        id SERIAL PRIMARY KEY,
        group_id INTEGER NOT NULL,
        admin_id BIGINT NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
        FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE(group_id, admin_id)
    )
    ''')
    
    # Create user_groups table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_groups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        group_id INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
        UNIQUE(user_id, group_id)
    )
    ''')
    
    # Create task_assignees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_assignees (
        id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL,
        user_id BIGINT NOT NULL,
        status TEXT DEFAULT 'pending',
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE(task_id, user_id)
    )
    ''')
    
    conn.commit()
    conn.close()  # Will automatically return to pool
    logger.info("Database initialized")


class _PoolAwareConnection:
    """Wrapper around psycopg2 connection that returns to pool on close()"""
    def __init__(self, conn, pool_instance):
        self._conn = conn
        self._pool_instance = pool_instance
        self._returned = False
    
    def close(self):
        """Close connection by returning it to the pool"""
        if not self._returned:
            try:
                self._pool_instance.return_connection(self._conn)
                self._returned = True
            except Exception:
                # If return fails, close for real as fallback
                try:
                    self._conn.close()
                except Exception:
                    pass
    
    def __getattr__(self, name):
        """Proxy all other attributes to the wrapped connection"""
        return getattr(self._conn, name)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _get_db_connection():
    """
    Get database connection from pool.
    Automatically returns to pool when conn.close() is called.
    """
    global _db_pool_instance
    
    db_conn = get_db_connection()
    conn = db_conn.get_connection()
    
    # Store pool reference for later cleanup
    _db_pool_instance = db_conn
    
    # Wrap connection to return to pool on close()
    return _PoolAwareConnection(conn, db_conn)


def add_user(user_id, name, username=None):
    """
    Add a new user to the database.
    
    Args:
        user_id (int): Telegram user ID of the user
        name (str): Name of the user
        username (str, optional): Telegram username (without @)
        
    Returns:
        bool: True if user was added, False if user already exists
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            # user already exists
            conn.close()
            return False
        
        cursor.execute(
            "INSERT INTO users (user_id, name, username) VALUES (%s, %s, %s)",
            (user_id, name, username)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added user {name} (ID: {user_id}, username: {username})")
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            # user doesn't exist
            conn.close()
            return False
        
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
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
    Includes group admins even if they're not in user_groups.
    
    Returns:
        list: List of dictionaries containing user information with group_name and all_groups
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT DISTINCT u.user_id, u.name, u.username, u.banned,
                   STRING_AGG(DISTINCT g.group_id::text, ',') as group_ids,
                   STRING_AGG(DISTINCT g.name, ',') as group_names
            FROM users u
            LEFT JOIN user_groups ug ON u.user_id = ug.user_id
            LEFT JOIN groups g ON ug.group_id = g.group_id
            WHERE u.deleted = 0
            GROUP BY u.user_id, u.name, u.username, u.banned
            ORDER BY u.name
        """)
        rows = cursor.fetchall()
        users = []
        for row in rows:
            # Parse group_ids and group_names (convert tuple to dict)
            user_id = row[0]
            name = row[1]
            username = row[2]
            banned = row[3]
            group_ids_str = row[4] if row[4] else ""
            group_names_str = row[5] if row[5] else ""
            
            # Get first group (for backwards compatibility)
            group_id = int(group_ids_str.split(',')[0]) if group_ids_str else None
            group_name = group_names_str.split(',')[0] if group_names_str else None
            
            users.append({
                "user_id": user_id,
                "name": name,
                "username": username,
                "group_id": group_id,
                "group_name": group_name,
                "all_groups": group_names_str,  # All groups comma-separated
                "banned": banned
            })
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        conn.close()
        return []


def get_users_without_group():
    """Get all users without any group assigned (using user_groups table)."""
    conn = _get_db_connection()
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id, name, banned FROM users WHERE user_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tasks (date, time, description) VALUES (%s, %s, %s) RETURNING task_id",
            (date, time, description)
        )
        task_id = cursor.fetchone()[0]
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT task_id, date, time, description, assigned_to FROM tasks WHERE task_id = %s", 
            (task_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "task_id": row[0],
                "date": row[1],
                "time": row[2],
                "description": row[3],
                "assigned_to": row[4]
            }
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if task exists
        cursor.execute("SELECT task_id, assigned_to FROM tasks WHERE task_id = %s", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return False
        
        # Check if task is already assigned
        if task[1] is not None and response == "accepted":
            conn.close()
            return False
        
        cursor.execute(
            "UPDATE tasks SET assigned_to = %s WHERE task_id = %s",
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT t.task_id, t.date, t.time, t.description, t.assigned_to, u.name as user_name "
            "FROM tasks t LEFT JOIN users u ON t.assigned_to = u.user_id "
            "ORDER BY t.created_at DESC"
        )
        tasks = []
        for row in cursor.fetchall():
            task = {
                'task_id': row[0],
                'date': row[1],
                'time': row[2],
                'description': row[3],
                'assigned_to': row[4],
                'user_name': row[5]
            }
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

    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get accepted tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM user_responses WHERE user_id = %s AND response = 'accepted'",
            (user_id,)
        )
        accepted = cursor.fetchone()[0]
        
        # Get declined tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM user_responses WHERE user_id = %s AND response = 'declined'",
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        if admin_id is None:
            cursor.execute(
                "INSERT INTO groups (name) VALUES (%s) RETURNING group_id",
                (name,)
            )
        else:
            cursor.execute(
                "INSERT INTO groups (name, admin_id) VALUES (%s, %s) RETURNING group_id",
                (name, admin_id)
            )

        group_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        logger.info(f"Created group '{name}' (ID: {group_id})")
        return group_id
    except Exception as e:
        logger.error(f"Error creating group (likely duplicate name): {e}")
        conn.close()
        return None
    

def get_group(group_id):
    """Get group information by ID."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT group_id, name, admin_id FROM groups WHERE group_id = %s", (group_id,))
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
    """Get all groups. Results are cached for 5 minutes."""
    from simple_cache import get_cache
    
    # Try cache first (TTL 5 minutes)
    cache_key = "all_groups"
    cached_result = get_cache().get(cache_key)
    if cached_result is not None:
        return cached_result
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT group_id, name, admin_id FROM groups ORDER BY name"
        )
        groups = [{"group_id": row[0], "name": row[1], "admin_id": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        # Cache result for 5 minutes
        get_cache().set(cache_key, groups, ttl=300)
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if new admin exists as a user (users table uses column 'user_id')
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (new_admin_id,))
        if not cursor.fetchone():
            logger.error(f"New admin user {new_admin_id} does not exist")
            conn.close()
            return False
        
        cursor.execute(
            "UPDATE groups SET admin_id = %s WHERE group_id = %s",
            (new_admin_id, group_id)
        )
        conn.commit()
        conn.close()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate("all_groups")
        get_cache().invalidate_pattern("user_groups_*")
        
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
    # Ensure admin_id exists in users table
    if not user_exists(admin_id):
        add_user(admin_id, f"User_{admin_id}", None)
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if group exists
        cursor.execute("SELECT group_id FROM groups WHERE group_id = %s", (group_id,))
        if not cursor.fetchone():
            logger.error(f"Group {group_id} does not exist")
            conn.close()
            return False
        
        # Add to group_admins (will do nothing if already exists due to UNIQUE constraint)
        try:
            cursor.execute(
                "INSERT INTO group_admins (group_id, admin_id) VALUES (%s, %s)",
                (group_id, admin_id)
            )
        except Exception:
            # Already exists due to UNIQUE constraint
            pass
        
        # Also add to user_groups so admin can be seen as a member of the group
        try:
            cursor.execute(
                "INSERT INTO user_groups (user_id, group_id) VALUES (%s, %s)",
                (admin_id, group_id)
            )
        except Exception:
            # Already exists due to UNIQUE constraint
            pass
        
        # Also update legacy admin_id field in groups table for backward compatibility
        cursor.execute("SELECT admin_id FROM groups WHERE group_id = %s", (group_id,))
        current_admin = cursor.fetchone()[0]
        if current_admin is None:
            cursor.execute("UPDATE groups SET admin_id = %s WHERE group_id = %s", (admin_id, group_id))
        
        conn.commit()
        conn.close()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate("all_groups")
        get_cache().invalidate_pattern("user_groups_*")
        
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM group_admins WHERE group_id = %s AND admin_id = %s",
            (group_id, admin_id)
        )
        
        # Update legacy admin_id if this was the primary admin
        cursor.execute("SELECT admin_id FROM groups WHERE group_id = %s AND admin_id = %s", (group_id, admin_id))
        if cursor.fetchone():
            # Find another admin to set as primary, or set to NULL
            cursor.execute("SELECT admin_id FROM group_admins WHERE group_id = %s LIMIT 1", (group_id,))
            new_primary = cursor.fetchone()
            new_admin_id = new_primary[0] if new_primary else None
            cursor.execute("UPDATE groups SET admin_id = %s WHERE group_id = %s", (new_admin_id, group_id))
        
        conn.commit()
        conn.close()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate("all_groups")
        get_cache().invalidate_pattern("user_groups_*")
        
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT admin_id FROM group_admins WHERE group_id = %s",
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT g.group_id, g.name, g.admin_id
            FROM groups g
            INNER JOIN group_admins ga ON g.group_id = ga.group_id
            WHERE ga.admin_id = %s
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        if group_id is None:
            # Check if admin of any group
            cursor.execute("SELECT COUNT(*) FROM group_admins WHERE admin_id = %s", (user_id,))
        else:
            # Check if admin of specific group
            cursor.execute(
                "SELECT COUNT(*) FROM group_admins WHERE admin_id = %s AND group_id = %s",
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE groups SET name = %s WHERE group_id = %s",
            (new_name, group_id)
        )
        conn.commit()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate("all_groups")
        get_cache().invalidate_pattern("user_groups_*")
        
        conn.close()
        logger.info(f"Updated group {group_id} name to '{new_name}'")
        return True
    except Exception as e:
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete in correct order to respect FK constraints
        # 1. Delete task history (references tasks)
        cursor.execute(
            "DELETE FROM task_history WHERE task_id = %s",
            (task_id,)
        )
        
        # 2. Delete assignee statuses for this task (if table exists)
        try:
            cursor.execute(
                "DELETE FROM assignee_status WHERE task_id = %s",
                (task_id,)
            )
        except Exception:
            # Table might not exist, ignore
            pass
        
        # 3. Delete all media files associated with this task
        cursor.execute(
            "DELETE FROM task_media WHERE task_id = %s",
            (task_id,)
        )
        
        # 4. Delete the task
        cursor.execute(
            "DELETE FROM tasks WHERE task_id = %s",
            (task_id,)
        )
        
        # Check rows_deleted BEFORE commit and close
        rows_deleted = cursor.rowcount
        conn.commit()
        
        logger.info(f"Delete attempt for task {task_id}: {rows_deleted} rows affected")
        
        if rows_deleted > 0:
            logger.info(f"Successfully deleted task {task_id} and its media files")
            return True
        else:
            logger.warning(f"Task {task_id} not found for deletion")
            return False
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        conn.commit()  # Rollback by not committing, but close connection properly
        return False
    finally:
        # Always close the connection to return it to the pool
        conn.close()


def delete_group(group_id):
    """
    Delete a group and unassign all users from it.
    Also cancels all tasks associated with the group.
    
    Args:
        group_id (int): ID of the group to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, unassign all users from this group
        cursor.execute(
            "UPDATE users SET group_id = NULL WHERE group_id = %s",
            (group_id,)
        )
        
        # Cancel all tasks associated with this group
        cursor.execute(
            "UPDATE tasks SET status = 'cancelled' WHERE group_id = %s",
            (group_id,)
        )
        
        # Delete the group
        cursor.execute(
            "DELETE FROM groups WHERE group_id = %s",
            (group_id,)
        )
        
        conn.commit()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate("all_groups")
        get_cache().invalidate_pattern("user_groups_*")
        
        logger.info(f"Successfully deleted group {group_id} and cancelled its tasks")
        return True
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {e}", exc_info=True)
        return False
    finally:
        # Always close the connection to return it to the pool
        conn.close()


def get_group_users(group_id):
    """Get all users in a group (from user_groups many-to-many table)."""
    import time
    start = time.time()
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get users assigned to this group via user_groups table
        q_start = time.time()
        cursor.execute(
            "SELECT u.user_id, u.name FROM users u INNER JOIN user_groups ug ON u.user_id = ug.user_id WHERE ug.group_id = %s",
            (group_id,)
        )
        q_elapsed = time.time() - q_start
        if q_elapsed > 0.1:
            logger.debug(f"🐌 get_group_users query 1 took {q_elapsed:.3f}s")
        users_rows = cursor.fetchall()

        # Get admins for this group from group_admins (may include users without group_id set)
        cursor.execute(
            "SELECT u.user_id, u.name FROM users u INNER JOIN group_admins ga ON u.user_id = ga.admin_id WHERE ga.group_id = %s",
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


def register_user(user_id, name, username=None):
    """
    Register a new user (self-registration via password).
    user is created without a group.
    
    Args:
        user_id (int): Telegram user ID
        name (str): name/first name
        username (str, optional): Telegram username (without @)
        
    Returns:
        bool: True if registered, False if already exists
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            logger.warning(f"user {user_id} already exists")
            conn.close()
            return False
        
        # Create new user without group
        cursor.execute(
            "INSERT INTO users (user_id, name, username, group_id, registered) VALUES (%s, %s, %s, NULL, 1)",
            (user_id, name, username)
        )
        conn.commit()
        conn.close()
        logger.info(f"Registered new user {name} (ID: {user_id}, username: {username})")
        return True
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        conn.close()
        return False


def is_user_registered(user_id):
    """Check if a user has registered (via password)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT registered FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] == 1 if row else False
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
        conn.close()
        return False


def has_user_group(user_id):
    """Check if user is assigned to any group (using user_groups table)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM user_groups WHERE user_id = %s", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking user groups: {e}")
        conn.close()
        return False


def add_user_to_group(user_id, group_id):
    """Add a user to a group (many-to-many relationship)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure user exists in users table (required for FK constraint)
        if not user_exists(user_id):
            logger.warning(f"User {user_id} does not exist, creating user entry")
            add_user(user_id, f"User_{user_id}", None)
        
        cursor.execute(
            "INSERT INTO user_groups (user_id, group_id) VALUES (%s, %s)",
            (user_id, group_id)
        )
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate(f"user_groups_{user_id}")
        get_cache().invalidate("all_groups")
        
        logger.info(f"Added user {user_id} to group {group_id}")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding user to group: {e}")
        conn.close()
        return False


def remove_user_from_group(user_id, group_id):
    """Remove a user from a group (many-to-many relationship)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM user_groups WHERE user_id = %s AND group_id = %s",
            (user_id, group_id)
        )
        conn.commit()
        
        # Invalidate caches
        from simple_cache import get_cache
        get_cache().invalidate(f"user_groups_{user_id}")
        get_cache().invalidate("all_groups")
        
        conn.close()
        logger.info(f"Removed user {user_id} from group {group_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing user from group: {e}")
        conn.close()
        return False


def get_user_groups(user_id):
    """Get all groups a user belongs to. Results are cached for 5 minutes."""
    from simple_cache import get_cache
    
    # Try cache first (TTL 5 minutes)
    cache_key = f"user_groups_{user_id}"
    cached_result = get_cache().get(cache_key)
    if cached_result is not None:
        return cached_result
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT g.group_id, g.name FROM groups g INNER JOIN user_groups ug ON g.group_id = ug.group_id WHERE ug.user_id = %s",
            (user_id,)
        )
        rows = cursor.fetchall()
        groups = [{"group_id": row[0], "name": row[1]} for row in rows]
        conn.close()
        
        # Cache result for 5 minutes
        get_cache().set(cache_key, groups, ttl=300)
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
        List of users with user_id, name, group_id, group_name, username
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        if creator_is_super_admin:
            # Super admin can assign to anyone including group admins - get ALL groups user belongs to
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.name, u.username,
                       STRING_AGG(DISTINCT g.group_id::text, ',') as group_ids,
                       STRING_AGG(DISTINCT g.name, ',') as group_names
                FROM users u
                LEFT JOIN user_groups ug ON u.user_id = ug.user_id
                LEFT JOIN groups g ON ug.group_id = g.group_id
                WHERE u.banned = 0 AND u.deleted = 0
                GROUP BY u.user_id, u.name, u.username
                ORDER BY u.name
            """)
        elif creator_is_group_admin and creator_admin_groups:
            # Group admin can assign to users in their managed groups + themselves
            group_ids_str = ','.join(str(gid) for gid in creator_admin_groups)
            query = f"""
                SELECT DISTINCT u.user_id, u.name, u.username,
                       STRING_AGG(DISTINCT g.group_id::text, ',') as group_ids,
                       STRING_AGG(DISTINCT g.name, ',') as group_names
                FROM users u
                LEFT JOIN user_groups ug ON u.user_id = ug.user_id
                LEFT JOIN groups g ON ug.group_id = g.group_id
                WHERE u.banned = 0 AND u.deleted = 0 AND (
                    ug.group_id IN ({group_ids_str})
                    OR u.user_id = %s
                )
                GROUP BY u.user_id, u.name, u.username
                ORDER BY u.name
            """
            cursor.execute(query, (creator_id,))
        else:
            # Regular worker: users from worker's OWN groups + admins of those groups + ALWAYS include self
            # First get worker's groups
            cursor.execute("""
                SELECT DISTINCT group_id FROM user_groups WHERE user_id = %s
            """, (creator_id,))
            worker_groups = [row[0] for row in cursor.fetchall()]
            
            if worker_groups:
                # Worker has groups - include users from those groups and admins
                group_ids_str = ','.join(str(gid) for gid in worker_groups)
                query = f"""
                    SELECT DISTINCT u.user_id, u.name, u.username,
                           STRING_AGG(DISTINCT g.group_id::text, ',') as group_ids,
                           STRING_AGG(DISTINCT g.name, ',') as group_names
                    FROM users u
                    LEFT JOIN user_groups ug ON u.user_id = ug.user_id
                    LEFT JOIN groups g ON ug.group_id = g.group_id
                    WHERE u.banned = 0 AND u.deleted = 0 AND (
                        u.user_id = %s
                        OR ug.group_id IN ({group_ids_str})
                        OR u.user_id IN (
                            SELECT ga.admin_id FROM group_admins ga
                            WHERE ga.group_id IN ({group_ids_str})
                        )
                    )
                    GROUP BY u.user_id, u.name, u.username
                    ORDER BY u.name
                """
                cursor.execute(query, (creator_id,))
            else:
                # Worker has no groups - can only assign to themselves
                cursor.execute("""
                    SELECT DISTINCT u.user_id, u.name, u.username,
                           STRING_AGG(DISTINCT g.group_id::text, ',') as group_ids,
                           STRING_AGG(DISTINCT g.name, ',') as group_names
                    FROM users u
                    LEFT JOIN user_groups ug ON u.user_id = ug.user_id
                    LEFT JOIN groups g ON ug.group_id = g.group_id
                    WHERE u.banned = 0 AND u.deleted = 0 AND u.user_id = %s
                    GROUP BY u.user_id, u.name, u.username
                    ORDER BY u.name
                """, (creator_id,))
        
        rows = cursor.fetchall()
        users = []
        for row in rows:
            # Parse group_ids and group_names
            group_ids_str = row[3] if row[3] else ""
            group_names_str = row[4] if row[4] else ""
            
            # Get first group (for backwards compatibility)
            group_id = int(group_ids_str.split(',')[0]) if group_ids_str else None
            group_name = group_names_str.split(',')[0] if group_names_str else None
            
            users.append({
                "user_id": row[0],
                "name": row[1],
                "username": row[2],
                "group_id": group_id,
                "group_name": group_name,
                "all_groups": group_names_str  # All groups comma-separated
            })
        
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # Find tasks where assigned_to_list contains this user
        cursor.execute("SELECT task_id, assigned_to_list FROM tasks WHERE assigned_to_list IS NOT NULL")
        rows = cursor.fetchall()
        updated = 0
        for row in rows:
            assigned_json = row[1]
            try:
                assigned = json.loads(assigned_json or '[]')
            except Exception:
                assigned = []
            if user_id in assigned:
                cursor.execute("UPDATE tasks SET group_id = %s WHERE task_id = %s", (new_group_id, row[0]))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET name = %s WHERE user_id = %s", (new_name, user_id))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # Set user as banned
        cursor.execute("UPDATE users SET banned = 1 WHERE user_id = %s", (user_id,))
        # Remove from group_admins (many-to-many admin table)
        cursor.execute("DELETE FROM group_admins WHERE admin_id = %s", (user_id,))
        # Update groups.admin_id to NULL if this user is primary admin
        cursor.execute("UPDATE groups SET admin_id = NULL WHERE admin_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET banned = 0 WHERE user_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_groups WHERE user_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # Set user as banned and deleted (deleted users don't show in lists)
        cursor.execute("UPDATE users SET banned = 1, deleted = 1 WHERE user_id = %s", (user_id,))
        # Remove from all groups
        cursor.execute("DELETE FROM user_groups WHERE user_id = %s", (user_id,))
        # Remove from group_admins (many-to-many admin table)
        cursor.execute("DELETE FROM group_admins WHERE admin_id = %s", (user_id,))
        # Update groups.admin_id to NULL if this user is primary admin
        cursor.execute("UPDATE groups SET admin_id = NULL WHERE admin_id = %s", (user_id,))
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cancelled_count = 0
        updated_count = 0
        
        # Get all tasks where user is creator
        cursor.execute("SELECT task_id FROM tasks WHERE created_by = %s AND status != 'cancelled'", (user_id,))
        creator_tasks = [row[0] for row in cursor.fetchall()]
        
        # Cancel tasks where user is creator
        if creator_tasks:
            placeholders = ','.join('%s' * len(creator_tasks))
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
                        cursor.execute("UPDATE tasks SET status = 'cancelled' WHERE task_id = %s", (task['task_id'],))
                        cancelled_count += 1
                    else:
                        # User is co-assignee - remove from list
                        assigned.remove(user_id)
                        cursor.execute("UPDATE tasks SET assigned_to_list = %s WHERE task_id = %s", 
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

def create_task(date, time, description, group_id, admin_id, assigned_to_list=None, title=None):
    """
    Create a new task for a group.
    
    Args:
        date (str): Date (YYYY-MM-DD)
        time (str): Time (HH:MM)
        description (str): Task description
        group_id (int): ID of the group
        admin_id (int): ID of admin creating the task
        assigned_to_list (list): List of user IDs to assign (optional)
        title (str): Task title/name (optional)
        
    Returns:
        int: ID of created task, or None if failed
    """
    import json
    
    # Ensure admin_id exists in users table (for super admins who may not be registered)
    if not user_exists(admin_id):
        add_user(admin_id, f"User_{admin_id}", None)
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        assigned_to_json = json.dumps(assigned_to_list) if assigned_to_list else None
        
        cursor.execute(
            """INSERT INTO tasks (title, date, time, description, group_id, 
               assigned_to_list, created_by, status) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending') RETURNING task_id""",
            (title, date, time, description, group_id, assigned_to_json, admin_id)
        )
        task_id = cursor.fetchone()[0]
        
        # Log task creation
        cursor.execute(
            """INSERT INTO task_history (task_id, action, new_value, changed_by) 
               VALUES (%s, 'created', %s, %s)""",
            (task_id, f"Task created: {description}", admin_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Created task {task_id} for group {group_id}")
        
        # Add assignees to task_assignees table with 'pending' status
        if assigned_to_list:
            add_task_assignees(task_id, assigned_to_list, initial_status='pending')
        
        return task_id
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        conn.close()
        return None


def get_group_tasks(group_id):
    """Get all tasks for a group."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                      status, has_media, created_at 
               FROM tasks WHERE group_id = %s ORDER BY created_at DESC""",
            (group_id,)
        )
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "task_id": row[0],
                "date": row[1],
                "time": row[2],
                "description": row[3],
                "title": row[4],
                "group_id": row[5],
                "assigned_to_list": row[6],
                "status": row[7],
                "has_media": row[8],
                "created_at": row[9]
            })
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting group tasks: {e}")
        conn.close()
        return []


def get_user_tasks(user_id):
    """Get all active tasks assigned to a user (as executor), excluding completed."""
    import json
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE status NOT IN ('cancelled', 'completed') ORDER BY created_at DESC"""
        )
        tasks = []
        for row in cursor.fetchall():
            task = {
                "task_id": row[0],
                "date": row[1],
                "time": row[2],
                "description": row[3],
                "title": row[4],
                "group_id": row[5],
                "assigned_to_list": row[6],
                "status": row[7],
                "has_media": row[8],
                "created_at": row[9],
                "created_by": row[10]
            }
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
    """Get all active tasks created by a user (as постановник), excluding completed."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE created_by = %s AND status NOT IN ('cancelled', 'completed') 
               ORDER BY created_at DESC""",
            (user_id,)
        )
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "task_id": row[0],
                "date": row[1],
                "time": row[2],
                "description": row[3],
                "title": row[4],
                "group_id": row[5],
                "assigned_to_list": row[6],
                "status": row[7],
                "has_media": row[8],
                "created_at": row[9],
                "created_by": row[10]
            })
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks created by user: {e}")
        conn.close()
        return []


def get_user_archived_tasks(user_id):
    """Get all completed tasks assigned to a user (archived)."""
    import json
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by, updated_at
               FROM tasks WHERE status = 'completed' ORDER BY updated_at DESC"""
        )
        tasks = []
        for row in cursor.fetchall():
            task = {
                'task_id': row[0],
                'date': row[1],
                'time': row[2],
                'description': row[3],
                'group_id': row[4],
                'assigned_to_list': row[5],
                'status': row[6],
                'has_media': row[7],
                'created_at': row[8],
                'created_by': row[9],
                'updated_at': row[10]
            }
            assigned_list = json.loads(task.get('assigned_to_list') or '[]')
            if user_id in assigned_list:
                tasks.append(task)
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting user archived tasks: {e}")
        conn.close()
        return []


def get_archived_tasks_created_by_user(user_id):
    """Get all completed tasks created by a user (archived)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by, updated_at
               FROM tasks WHERE created_by = %s AND status = 'completed' 
               ORDER BY updated_at DESC""",
            (user_id,)
        )
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'task_id': row[0],
                'date': row[1],
                'time': row[2],
                'description': row[3],
                'title': row[4],
                'group_id': row[5],
                'assigned_to_list': row[6],
                'status': row[7],
                'has_media': row[8],
                'created_at': row[9],
                'created_by': row[10],
                'updated_at': row[11]
            })
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting archived tasks created by user: {e}")
        conn.close()
        return []


def get_all_tasks():
    """Get all tasks (for super admin)."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                      status, has_media, created_at, created_by
               FROM tasks WHERE status != 'cancelled' ORDER BY created_at DESC"""
        )
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'task_id': row[0],
                'date': row[1],
                'time': row[2],
                'description': row[3],
                'title': row[4],
                'group_id': row[5],
                'assigned_to_list': row[6],
                'status': row[7],
                'has_media': row[8],
                'created_at': row[9],
                'created_by': row[10]
            })
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
        
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        placeholders = ','.join('%s' * len(group_ids))
        query = f"""SELECT task_id, date, time, description, title, group_id, assigned_to_list, 
                           status, has_media, created_at, created_by
                    FROM tasks WHERE group_id IN ({placeholders}) AND status != 'cancelled' 
                    ORDER BY created_at DESC"""
        cursor.execute(query, group_ids)
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'task_id': row[0],
                'date': row[1],
                'time': row[2],
                'description': row[3],
                'title': row[4],
                'group_id': row[5],
                'assigned_to_list': row[6],
                'status': row[7],
                'has_media': row[8],
                'created_at': row[9],
                'created_by': row[10]
            })
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE tasks SET status = %s WHERE task_id = %s",
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
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        assigned_to_json = json.dumps(assigned_to_list)
        cursor.execute(
            """UPDATE tasks SET assigned_to_list = %s, updated_at = CURRENT_TIMESTAMP 
               WHERE task_id = %s""",
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


def update_task_field(task_id, field_name, value):
    """
    Update a specific field in a task.
    
    Args:
        task_id (int): ID of the task
        field_name (str): Name of the field to update (description, assigned_to_list, etc.)
        value: New value for the field
        
    Returns:
        bool: True if successful
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Allowed fields to prevent SQL injection
        allowed_fields = ['title', 'description', 'assigned_to_list', 'date', 'time', 'has_media', 'group_id']
        
        if field_name not in allowed_fields:
            logger.warning(f"Attempted to update disallowed field: {field_name}")
            conn.close()
            return False
        
        query = f"UPDATE tasks SET {field_name} = %s, updated_at = CURRENT_TIMESTAMP WHERE task_id = %s"
        cursor.execute(query, (value, task_id))
        
        rows_updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_updated > 0:
            logger.info(f"Updated task {task_id} field {field_name}")
            return True
        else:
            logger.warning(f"Task {task_id} not found for field update")
            return False
    except Exception as e:
        logger.error(f"Error updating task field {field_name}: {e}")
        conn.close()
        return False


def get_task_by_id(task_id):
    """Get task information by ID."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT task_id, title, date, time, description, group_id, 
                      assigned_to_list, status, has_media, created_by, created_at 
               FROM tasks WHERE task_id = %s""",
            (task_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "task_id": row[0],
                "title": row[1],
                "date": row[2],
                "time": row[3],
                "description": row[4],
                "group_id": row[5],
                "assigned_to_list": row[6],
                "status": row[7],
                "has_media": row[8],
                "created_by": row[9],
                "created_at": row[10]
            }
        return None
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check media count for this task (max 20)
        cursor.execute("SELECT COUNT(*) FROM task_media WHERE task_id = %s", (task_id,))
        media_count = cursor.fetchone()[0]
        
        if media_count >= 20:
            logger.warning(f"Task {task_id} already has maximum 20 media files")
            conn.close()
            return None
        
        cursor.execute(
            """INSERT INTO task_media (task_id, file_id, file_type, file_name, file_size) 
               VALUES (%s, %s, %s, %s, %s) RETURNING media_id""",
            (task_id, file_id, file_type, file_name, file_size)
        )
        media_id = cursor.fetchone()[0]
        
        # Update task has_media flag
        cursor.execute(
            "UPDATE tasks SET has_media = 1 WHERE task_id = %s",
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
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT media_id, file_id, file_type, file_name, file_size, added_at 
               FROM task_media WHERE task_id = %s ORDER BY added_at""",
            (task_id,)
        )
        media = []
        for row in cursor.fetchall():
            media.append({
                'media_id': row[0],
                'file_id': row[1],
                'file_type': row[2],
                'file_name': row[3],
                'file_size': row[4],
                'added_at': row[5]
            })
        conn.close()
        return media
    except Exception as e:
        logger.error(f"Error getting task media: {e}")
        conn.close()
        return []


def remove_task_media(media_id):
    """Remove a media file from a task."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT task_id FROM task_media WHERE media_id = %s", (media_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        task_id = row[0]
        
        cursor.execute("DELETE FROM task_media WHERE media_id = %s", (media_id,))
        
        # If no more media, update has_media flag
        cursor.execute("SELECT COUNT(*) FROM task_media WHERE task_id = %s", (task_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("UPDATE tasks SET has_media = 0 WHERE task_id = %s", (task_id,))
        
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
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registration_requests (user_id, name, username, status)
            VALUES (%s, %s, %s, 'pending')
        ''', (user_id, name, username))
        conn.commit()
        logger.info(f"Registration request created for user {user_id}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "unique constraint" in error_msg.lower():
            logger.warning(f"Registration request already exists for user {user_id}")
        else:
            logger.error(f"Error creating registration request: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_pending_registration_requests():
    """Get all pending registration requests."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT request_id, user_id, name, username, status, requested_at, reviewed_by, reviewed_at
            FROM registration_requests 
            WHERE status = 'pending' 
            ORDER BY requested_at DESC
        ''')
        rows = cursor.fetchall()
        requests = []
        for row in rows:
            requests.append({
                'request_id': row[0],
                'user_id': row[1],
                'name': row[2],
                'username': row[3],
                'status': row[4],
                'requested_at': row[5],
                'reviewed_by': row[6],
                'reviewed_at': row[7]
            })
        conn.close()
        return requests
    except Exception as e:
        logger.error(f"Error getting registration requests: {e}")
        if conn:
            conn.close()
        return []


def approve_registration_request(request_id, reviewer_id):
    """Approve a registration request and create user."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute("SELECT user_id, name FROM registration_requests WHERE request_id = %s", (request_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        user_id, name = row
        
        # Get username from request
        cursor.execute("SELECT username FROM registration_requests WHERE request_id = %s", (request_id,))
        username_row = cursor.fetchone()
        username = username_row[0] if username_row else None
        
        # Update request status
        cursor.execute('''
            UPDATE registration_requests 
            SET status = 'approved', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE request_id = %s
        ''', (reviewer_id, request_id))
        
        # Upsert user in users table - update if exists, insert if not
        cursor.execute('''
            INSERT INTO users (user_id, name, username, registered)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE 
            SET name = COALESCE(EXCLUDED.name, users.name),
                username = COALESCE(EXCLUDED.username, users.username),
                registered = 1
        ''', (user_id, name, username))
        
        conn.commit()
        conn.close()
        logger.info(f"Approved registration request {request_id} for user {user_id} (username: {username})")
        return True
    except Exception as e:
        logger.error(f"Error approving registration request: {e}")
        conn.close()
        return False


def reject_registration_request(request_id, reviewer_id):
    """Reject a registration request."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE registration_requests 
            SET status = 'rejected', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE request_id = %s
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
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT request_id, user_id, name, username, status, requested_at, reviewed_by, reviewed_at
            FROM registration_requests 
            WHERE user_id = %s 
            ORDER BY requested_at DESC 
            LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'request_id': row[0],
                'user_id': row[1],
                'name': row[2],
                'username': row[3],
                'status': row[4],
                'requested_at': row[5],
                'reviewed_by': row[6],
                'reviewed_at': row[7]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting registration request: {e}")
        if conn:
            conn.close()
        return None


# ========== TASK ASSIGNEE STATUS FUNCTIONS ==========

def add_task_assignees(task_id, user_ids, initial_status='pending'):
    """
    Add assignees to a task with an initial status.
    
    Args:
        task_id: Task ID
        user_ids: List of user IDs to assign
        initial_status: Initial status for all assignees (default: 'pending')
    
    Returns:
        bool: Success status
    """
    if not user_ids:
        return True
    
    # Ensure all user_ids exist in users table
    for user_id in user_ids:
        if not user_exists(user_id):
            add_user(user_id, f"User_{user_id}", None)
        
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        for user_id in user_ids:
            cursor.execute('''
                INSERT INTO task_assignees (task_id, user_id, status)
                VALUES (%s, %s, %s)
            ''', (task_id, user_id, initial_status))
        
        conn.commit()
        conn.close()
        logger.info(f"Added {len(user_ids)} assignees to task {task_id} with status '{initial_status}'")
        return True
    except Exception as e:
        logger.error(f"Error adding task assignees: {e}")
        conn.close()
        return False


def get_task_assignee_statuses(task_id):
    """
    Get all assignees and their individual statuses for a task.
    
    Args:
        task_id: Task ID
    
    Returns:
        dict: {user_id: status} mapping
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, status 
            FROM task_assignees 
            WHERE task_id = %s
        ''', (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.error(f"Error getting task assignee statuses: {e}")
        conn.close()
        return {}


def get_assignee_status(task_id, user_id):
    """
    Get the status of a specific assignee for a task.
    
    Args:
        task_id: Task ID
        user_id: User ID
    
    Returns:
        str: Status ('pending', 'in_progress', 'completed', 'cancelled') or None
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status 
            FROM task_assignees 
            WHERE task_id = %s AND user_id = %s
        ''', (task_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting assignee status: {e}")
        conn.close()
        return None


def update_assignee_status(task_id, user_id, new_status):
    """
    Update the status of a specific assignee for a task.
    
    Args:
        task_id: Task ID
        user_id: User ID
        new_status: New status value
    
    Returns:
        bool: Success status
    """
    valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        logger.error(f"Invalid status: {new_status}")
        return False
        
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE task_assignees 
            SET status = %s, status_updated_at = CURRENT_TIMESTAMP
            WHERE task_id = %s AND user_id = %s
        ''', (new_status, task_id, user_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"No assignee found for task {task_id}, user {user_id}")
            conn.close()
            return False
        
        conn.commit()
        
        # Calculate and update aggregate task status
        aggregate_status = calculate_task_status(task_id)
        cursor.execute('''
            UPDATE tasks 
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = %s
        ''', (aggregate_status, task_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated task {task_id} assignee {user_id} status to '{new_status}', aggregate status: '{aggregate_status}'")
        return True
    except Exception as e:
        logger.error(f"Error updating assignee status: {e}")
        conn.close()
        return False


def calculate_task_status(task_id):
    """
    Calculate aggregate task status based on all assignee statuses.
    
    Rules:
    - If all assignees have status 'completed' → task is 'completed'
    - If at least one assignee has 'in_progress' → task is 'in_progress'
    - If all assignees have 'pending' → task is 'pending'
    - If all assignees have 'cancelled' → task is 'cancelled'
    - Mixed states prioritize: in_progress > pending > cancelled
    
    Args:
        task_id: Task ID
    
    Returns:
        str: Aggregate status
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM task_assignees 
            WHERE task_id = %s
            GROUP BY status
        ''', (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return 'pending'  # Default if no assignees
        
        status_counts = {row[0]: row[1] for row in rows}
        total_assignees = sum(status_counts.values())
        
        # All completed → completed
        if status_counts.get('completed', 0) == total_assignees:
            return 'completed'
        
        # At least one in_progress → in_progress
        if status_counts.get('in_progress', 0) > 0:
            return 'in_progress'
        
        # All cancelled → cancelled
        if status_counts.get('cancelled', 0) == total_assignees:
            return 'cancelled'
        
        # Default: pending (if mix of pending/cancelled or all pending)
        return 'pending'
        
    except Exception as e:
        logger.error(f"Error calculating task status: {e}")
        conn.close()
        return 'pending'


def remove_task_assignee(task_id, user_id):
    """
    Remove an assignee from a task.
    
    Args:
        task_id: Task ID
        user_id: User ID to remove
    
    Returns:
        bool: Success status
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM task_assignees 
            WHERE task_id = %s AND user_id = %s
        ''', (task_id, user_id))
        
        conn.commit()
        
        # Recalculate aggregate status
        if cursor.rowcount > 0:
            aggregate_status = calculate_task_status(task_id)
            cursor.execute('''
                UPDATE tasks 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = %s
            ''', (aggregate_status, task_id))
            conn.commit()
        
        conn.close()
        logger.info(f"Removed assignee {user_id} from task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing task assignee: {e}")
        conn.close()
        return False


def get_notification_recipients(task_id, include_assignees=True):
    """
    Get all users who should receive notifications for a task.
    
    This includes:
    1. Task creator
    2. All assigned users (if include_assignees=True)
    3. Super admin (always gets notifications as invisible creator)
    4. All group admins for the task's group (as invisible creators)
    
    Returns a dict with users grouped by their role:
    {
        'creator': creator_id,
        'assignees': [list of user_ids],
        'admins': [list of admin_ids],
        'super_admin_ids': [list of super_admin_ids from SUPER_ADMIN_IDS]
    }
    
    Args:
        task_id (int): ID of the task
        include_assignees (bool): Whether to include assigned users
        
    Returns:
        dict: Dictionary with recipient information
    """
    import json
    import os
    from dotenv import load_dotenv
    
    # Load super admin IDs from environment
    load_dotenv()
    super_admin_ids_str = os.getenv("SUPER_ADMIN_ID", "0")
    super_admin_ids = [
        int(id.strip()) for id in super_admin_ids_str.split(",") if id.strip()
    ]
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get task info (creator, group_id, assigned_to_list)
        cursor.execute(
            """SELECT created_by, group_id, assigned_to_list 
               FROM tasks WHERE task_id = %s""",
            (task_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {
                'creator': None,
                'assignees': [],
                'admins': [],
                'super_admin_ids': super_admin_ids
            }
        
        creator_id, group_id, assigned_to_json = result
        
        # Parse assigned_to_list
        assignees = []
        if include_assignees and assigned_to_json:
            try:
                assignees = json.loads(assigned_to_json)
            except json.JSONDecodeError:
                assignees = []
        
        # Get group admins for this task's group
        cursor.execute(
            """SELECT admin_id FROM group_admins WHERE group_id = %s""",
            (group_id,)
        )
        group_admins = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'creator': creator_id,
            'assignees': assignees,
            'admins': group_admins,
            'super_admin_ids': super_admin_ids
        }
    except Exception as e:
        logger.error(f"Error getting notification recipients for task {task_id}: {e}")
        conn.close()
        return {
            'creator': None,
            'assignees': [],
            'admins': [],
            'super_admin_ids': super_admin_ids
        }





