"""
Database module for Team Task Management Bot.
Handles all database operations including creating tasks, managing workers,
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
    
    # Create workers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_to INTEGER,
        FOREIGN KEY (assigned_to) REFERENCES workers(id)
    )
    ''')
    
    # Create worker_responses table to track accepts/declines
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        response TEXT NOT NULL,  -- 'accepted' or 'declined'
        response_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_id) REFERENCES workers(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        UNIQUE(worker_id, task_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def add_worker(worker_id, username):
    """
    Add a new worker to the database.
    
    Args:
        worker_id (int): Telegram user ID of the worker
        username (str): Username of the worker
        
    Returns:
        bool: True if worker was added, False if worker already exists
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
        if cursor.fetchone():
            # Worker already exists
            conn.close()
            return False
        
        cursor.execute(
            "INSERT INTO workers (id, username) VALUES (?, ?)",
            (worker_id, username)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added worker {username} (ID: {worker_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding worker: {e}")
        conn.close()
        return False

def remove_worker(worker_id):
    """
    Remove a worker from the database.
    
    Args:
        worker_id (int): Telegram user ID of the worker
        
    Returns:
        bool: True if worker was removed, False if worker doesn't exist
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
        if not cursor.fetchone():
            # Worker doesn't exist
            conn.close()
            return False
        
        cursor.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
        conn.commit()
        conn.close()
        logger.info(f"Removed worker with ID: {worker_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing worker: {e}")
        conn.close()
        return False

def get_all_workers():
    """
    Get all registered workers.
    
    Returns:
        list: List of dictionaries containing worker information
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, username FROM workers")
        workers = [{"id": row[0], "username": row[1]} for row in cursor.fetchall()]
        conn.close()
        return workers
    except Exception as e:
        logger.error(f"Error getting workers: {e}")
        conn.close()
        return []

def get_worker_by_id(worker_id):
    """
    Get worker information by ID.
    
    Args:
        worker_id (int): Telegram user ID of the worker
        
    Returns:
        dict: Worker information or None if not found
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, username FROM workers WHERE id = ?", (worker_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"id": row[0], "username": row[1]}
        return None
    except Exception as e:
        logger.error(f"Error getting worker: {e}")
        conn.close()
        return None

def worker_exists(worker_id):
    """
    Check if a worker exists in the database.
    
    Args:
        worker_id (int): Telegram user ID of the worker
        
    Returns:
        bool: True if worker exists, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM workers WHERE id = ?", (worker_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error checking worker existence: {e}")
        conn.close()
        return False

def create_task(address, date, time, description):
    """
    Create a new task.
    
    Args:
        address (str): Location of the task
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
            "INSERT INTO tasks (address, date, time, description) VALUES (?, ?, ?, ?)",
            (address, date, time, description)
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
            "SELECT id, address, date, time, description, assigned_to FROM tasks WHERE id = ?", 
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

def update_task_status(task_id, worker_id, response):
    """
    Update task status when a worker accepts or declines.
    
    Args:
        task_id (int): ID of the task
        worker_id (int): Telegram user ID of the worker
        response (str): 'accepted' or 'declined'
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if task exists
        cursor.execute("SELECT id, assigned_to FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            return False
        
        # Check if task is already assigned
        if task[1] is not None and response == "accepted":
            conn.close()
            return False
        
        # Record the worker's response
        try:
            cursor.execute(
                "INSERT INTO worker_responses (worker_id, task_id, response) VALUES (?, ?, ?)",
                (worker_id, task_id, response)
            )
        except sqlite3.IntegrityError:
            # Worker already responded to this task, update their response
            cursor.execute(
                "UPDATE worker_responses SET response = ?, response_time = CURRENT_TIMESTAMP WHERE worker_id = ? AND task_id = ?",
                (response, worker_id, task_id)
            )
        
        # If the response is 'accepted', assign the task to the worker
        if response == "accepted":
            cursor.execute(
                "UPDATE tasks SET assigned_to = ? WHERE id = ?",
                (worker_id, task_id)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"Worker {worker_id} {response} task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        conn.rollback()
        conn.close()
        return False

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
            "SELECT t.id, t.address, t.date, t.time, t.description, t.assigned_to, w.username as worker_name "
            "FROM tasks t LEFT JOIN workers w ON t.assigned_to = w.id "
            "ORDER BY t.created_at DESC"
        )
        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            if task["worker_name"]:
                task["assigned_to_name"] = task["worker_name"]
            tasks.append(task)
        conn.close()
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        conn.close()
        return []

def get_worker_stats(worker_id):
    """
    Get performance statistics for a worker.
    
    Args:
        worker_id (int): Telegram user ID of the worker
        
    Returns:
        dict: Dictionary containing performance statistics
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Get accepted tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM worker_responses WHERE worker_id = ? AND response = 'accepted'",
            (worker_id,)
        )
        accepted = cursor.fetchone()[0]
        
        # Get declined tasks count
        cursor.execute(
            "SELECT COUNT(*) FROM worker_responses WHERE worker_id = ? AND response = 'declined'",
            (worker_id,)
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
        logger.error(f"Error getting worker stats: {e}")
        conn.close()
        return {
            "accepted": 0,
            "declined": 0,
            "total": 0,
            "acceptance_rate": 0
        }
