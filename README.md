# 🤖 Team Task Management Telegram Bot

Telegram bot for managing team tasks with support for groups, administrators, and employees.

**Database:** PostgreSQL (local development & Railway production) | **Status:** ✅ Production Ready

## ✨ Features

### 👑 Super Admin:
- Group management (creation, editing, deletion)
- User management (registration, blocking, deletion)
- Appointing group administrators
- Distributing users across groups
- Creating tasks for any group

### 👨‍💼 Group Administrator:
- Creating tasks for your group
- Assigning executors (up to 10 per task)
- Viewing group tasks
- Managing task statuses

### 👷 Employee:
- Receiving notifications about new tasks
- Viewing assigned tasks
- Changing task statuses (In progress → Completed)
- Viewing statistics

### 📋 Task:
- Title, description, deadline (date + time)
- Media files (photos, videos, documents)
- Multiple assignees per task
- Status change history
- Automatic deadline reminders

---

## 🚀 Quick start

### Local launch

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/Telegram-Bot-for-Team-Task-Management.git
cd Telegram-Bot-for-Team-Task-Management
```

2. **Setup PostgreSQL** (Docker recommended):
```bash
# Option A: Docker Compose (easiest)
docker-compose up -d

# Option B: Manual installation
# See local/POSTGRESQL_SETUP.md for detailed instructions
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
# Automatically creates tables and schema
python database.py
```

5. Configure the `.env` file:
```bash
cp .env.example .env
# Edit .env: add TELEGRAM_BOT_TOKEN and SUPER_ADMIN_ID
# DATABASE_URL is optional (uses local PostgreSQL if not set)
```

6. Run the bot:
```bash
# Development mode (polling)
python bot.py
```

**For detailed PostgreSQL setup:** see [`local/POSTGRESQL_SETUP.md`](local/POSTGRESQL_SETUP.md)

### ☁️ Deploy on Railway.app (recommended)

**Quick deployment:**
1. Fork this repository
2. Create a project on [Railway.app](https://railway.app)
3. Add **PostgreSQL plugin** (Railway automatically manages DATABASE_URL)
4. Connect the GitHub repository
5. Add environment variables:
   - `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
   - `SUPER_ADMIN_ID` - Your Telegram user ID
   - `ENVIRONMENT=production`
   - `USE_WEBHOOK=true`
   - `RAILWAY_URL` - Your Railway app URL
6. Railway will automatically deploy the bot ✅

Database schema initializes automatically on first deployment!


---

## 📁 Project structure

```
├── bot.py                 # Main bot file
├── db_postgres.py         # PostgreSQL connection handler
├── database.py            # Database operations (PostgreSQL)
├── handlers/              # Command handlers
│   ├── common/            # Common commands (/start, /help)
│   ├── super_admin/       # Super admin functions
│   ├── group_admin/       # Group admin functions
│   ├── workers/           # Worker functions
│   ├── tasks/             # Creating and viewing tasks
│   ├── notifications.py   # Notifications
│   └── registration.py    # User registration
├── utils/                 # Utility functions
│   ├── helpers.py         # Calendar, time, buttons
│   └── permissions.py     # Access rights verification
├── requirements.txt       # Python dependencies
├── railway.json           # Railway configuration
├── Procfile               # Start command for hosting
├── runtime.txt            # Python version
├── .env.example           # Example environment variables
```

---

## ⚙️ Configuration

### Environment variables (.env)

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUPER_ADMIN_ID=your_telegram_user_id
```

**Where to get it:**
- `TELEGRAM_BOT_TOKEN`: [@BotFather](https://t.me/BotFather) → /newbot
- `SUPER_ADMIN_ID`: [@userinfobot](https://t.me/userinfobot) → /start

### Database

The SQLite database (`task_management.db`) is created automatically when you first start the bot.

---

## 🧪 Testing

Running tests:
```bash
python -m pytest tests/ -v
```

Coverage tests:
```bash
pytest tests/ --cov=. --cov-report=html
```


## 🛠️ Technologies

- **Python 3.10+**
- **python-telegram-bot 20.7** - Telegram Bot API
- **APScheduler 3.10** - Reminder scheduling
- **SQLite3** - Database
- **python-dotenv** - Environment variable management

---

## 📊 System capabilities

### User hierarchy:
```
Super admin (full access)
    ↓
Group admin (manage your group)
    ↓
Employee (task execution)
```

### Task lifecycle:
```
New → In progress → Completed
         ↓
    (Cancelled)
```

---

## 🔐 Security

- ✅ Bot token is stored in `.env` (not in Git)
- ✅ `.env` in `.gitignore`
- ✅ Access rights check for each action
- ✅ User data validation
- ✅ Logging of all operations

---

## 📝 Licence

This project is created for internal use. All rights reserved.

---

## 📞 Contact

**GitHub:** Author of the repository on which this solution is based [HullyMully/Telegram-Bot-for-Team-Task-Management](https://github.com/HullyMully/Telegram-Bot-for-Team-Task-Management)

---

## 🎉 Acknowledgements

Thank you to everyone who uses this bot for team task management!

**Version:** 2.2  
**Last update:** December 2025