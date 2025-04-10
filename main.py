from flask import Flask, render_template, jsonify
import os
from database import init_db, get_all_workers, get_all_tasks, get_worker_stats

# Initialize the database
init_db()

app = Flask(__name__)

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')

@app.route('/api/workers')
def api_workers():
    """API endpoint to get all workers."""
    workers = get_all_workers()
    return jsonify(workers)

@app.route('/api/tasks')
def api_tasks():
    """API endpoint to get all tasks."""
    tasks = get_all_tasks()
    return jsonify(tasks)

@app.route('/api/stats/<int:worker_id>')
def api_worker_stats(worker_id):
    """API endpoint to get worker stats."""
    stats = get_worker_stats(worker_id)
    return jsonify(stats)

if __name__ == "__main__":
    # Start the Flask app on port 5001 to avoid conflict with gunicorn
    app.run(host="0.0.0.0", port=5001, debug=True)
