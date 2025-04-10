import sqlite3
import os
from datetime import datetime

# Database file path
DB_FILE = "task_manager.db"

def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access rows by name
    return conn

def init_database():
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create admins table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create workers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        user_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
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
        status TEXT DEFAULT 'pending',
        created_by INTEGER,
        worker_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (user_id),
        FOREIGN KEY (worker_id) REFERENCES workers (user_id)
    )
    ''')
    
    # Create worker_task_responses table to track worker responses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_task_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_id) REFERENCES workers (user_id),
        FOREIGN KEY (task_id) REFERENCES tasks (id),
        UNIQUE(worker_id, task_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def register_admin(user_id, username):
    """Register a new admin."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Admin already exists
        return False
    finally:
        conn.close()

def is_admin(user_id):
    """Check if a user is an admin."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def register_worker(user_id, name, phone=None):
    """Register a new worker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO workers (user_id, name, phone) VALUES (?, ?, ?)",
            (user_id, name, phone)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Update existing worker
        cursor.execute(
            "UPDATE workers SET name = ?, phone = ? WHERE user_id = ?",
            (name, phone, user_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()

def is_worker_registered(user_id):
    """Check if a worker is registered."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM workers WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def list_all_workers():
    """Get a list of all registered workers."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, name, phone FROM workers")
    workers = cursor.fetchall()
    
    conn.close()
    return [dict(worker) for worker in workers]

def get_worker_stats():
    """Get performance statistics for all workers."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get worker information including task statistics
    cursor.execute('''
    SELECT 
        w.user_id,
        w.name,
        COUNT(CASE WHEN wtr.response = 'accepted' THEN 1 END) as tasks_accepted,
        COUNT(CASE WHEN t.status = 'completed' AND t.worker_id = w.user_id THEN 1 END) as tasks_completed,
        COUNT(CASE WHEN wtr.response = 'declined' THEN 1 END) as tasks_declined
    FROM workers w
    LEFT JOIN worker_task_responses wtr ON w.user_id = wtr.worker_id
    LEFT JOIN tasks t ON t.id = wtr.task_id
    GROUP BY w.user_id
    ''')
    
    workers = cursor.fetchall()
    conn.close()
    
    # Calculate additional metrics
    result = []
    for worker in workers:
        worker_dict = dict(worker)
        
        # Calculate completion rate
        tasks_accepted = worker_dict['tasks_accepted'] or 0
        tasks_completed = worker_dict['tasks_completed'] or 0
        
        completion_rate = 0
        if tasks_accepted > 0:
            completion_rate = round((tasks_completed / tasks_accepted) * 100, 1)
        
        worker_dict['completion_rate'] = completion_rate
        result.append(worker_dict)
    
    return result

def create_task_record(address, date, time, description, admin_id):
    """Create a new task record in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO tasks (address, date, time, description, created_by) VALUES (?, ?, ?, ?, ?)",
        (address, date, time, description, admin_id)
    )
    
    # Get the ID of the created task
    task_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return task_id

def list_tasks(status_filter=None):
    """Get a list of all tasks, optionally filtered by status."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT 
        t.id,
        t.address,
        t.date,
        t.time,
        t.description,
        t.status,
        t.worker_id,
        w.name as worker_name
    FROM tasks t
    LEFT JOIN workers w ON t.worker_id = w.user_id
    '''
    
    params = ()
    if status_filter:
        query += " WHERE t.status = ? "
        params = (status_filter,)
    
    query += " ORDER BY t.created_at DESC"
    
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    
    conn.close()
    return [dict(task) for task in tasks]

def get_pending_tasks():
    """Get a list of pending tasks."""
    return list_tasks("pending")

def assign_task(task_id, worker_id):
    """Assign a task to a worker."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if the task is still pending
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    
    if not task or task['status'] != 'pending':
        conn.close()
        return False
    
    # Update the task status and assign to worker
    cursor.execute(
        "UPDATE tasks SET status = 'assigned', worker_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (worker_id, task_id)
    )
    
    # Record the worker's response
    try:
        cursor.execute(
            "INSERT INTO worker_task_responses (worker_id, task_id, response) VALUES (?, ?, ?)",
            (worker_id, task_id, 'accepted')
        )
    except sqlite3.IntegrityError:
        # Update existing response
        cursor.execute(
            "UPDATE worker_task_responses SET response = ? WHERE worker_id = ? AND task_id = ?",
            ('accepted', worker_id, task_id)
        )
    
    conn.commit()
    conn.close()
    
    return True

def update_task_status(task_id, worker_id, response):
    """Update a worker's response to a task."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Record the worker's response
    try:
        cursor.execute(
            "INSERT INTO worker_task_responses (worker_id, task_id, response) VALUES (?, ?, ?)",
            (worker_id, task_id, response)
        )
    except sqlite3.IntegrityError:
        # Update existing response
        cursor.execute(
            "UPDATE worker_task_responses SET response = ? WHERE worker_id = ? AND task_id = ?",
            (response, worker_id, task_id)
        )
    
    conn.commit()
    conn.close()
