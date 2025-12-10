# Тестування Telegram Bot

## 🚀 Швидкий старт

```bash
# Встановити залежності
pip install pytest pytest-asyncio pytest-cov

# Запустити всі тести
pytest

# З покриттям коду
pytest --cov=database --cov-report=html
```

HTML звіт буде у `htmlcov/index.html`

---

## Встановлення залежностей

```bash
# Встановити dev залежності
uv pip install -e ".[dev]"

# Або вручну
uv pip install pytest pytest-asyncio pytest-cov
```

## Запуск тестів

### 🚀 Запуск всіх тестів проєкту (одна команда)
```bash
pytest
```
Ця команда автоматично знайде та запустить всі тести в папці `tests/`.

### З покриттям коду
```bash
pytest --cov=database --cov=bot --cov-report=html
pytest --cov=database --cov-report=term-missing  # З деталями пропущених рядків
```

### Тільки швидкі тести
```bash
pytest -m "not slow"
```

### Конкретний файл або тест
```bash
pytest tests/test_database.py              # Тести бази даних
pytest tests/test_tasks.py                 # Тести завдань
pytest tests/test_permissions.py           # Тести прав доступу
pytest tests/test_database.py::TestUserManagement::test_add_user  # Окремий тест
```

### Детальний вивід
```bash
pytest -v              # Докладний
pytest -vv             # Дуже докладний
pytest -v --tb=short   # З коротким traceback
```

### Паралельний запуск (швидше)
```bash
pip install pytest-xdist
pytest -n auto  # Використовує всі доступні CPU
```

## Структура тестів

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures (test_db, sample_users, etc.)
├── test_database.py         # Тести database.py (19 тестів: користувачі, групи, ban/delete)
├── test_tasks.py            # Тести завдань (20 тестів: створення, редагування, видалення)
├── test_permissions.py      # Тести прав доступу (18 тестів: super_admin, group_admin)
└── README.md               # Цей файл
```

**Загальна кількість тестів: 57+**

## Покриття коду

Після запуску з `--cov-report=html` відкрийте:
```
htmlcov/index.html
```

## Написання нових тестів

### Приклад тесту з використанням fixtures:

```python
def test_example(test_db, sample_users):
    """Test description."""
    from database import add_user, get_user_by_id
    
    # Arrange
    user_id, name = sample_users[0]['user_id'], sample_users[0]['name']
    
    # Act
    add_user(user_id, name)
    user = get_user_by_id(user_id)
    
    # Assert
    assert user is not None
    assert user['name'] == name
```

## Поточне покриття

### test_database.py (19 тестів):
- ✅ User CRUD (add, get, get_all)
- ✅ User banning/unbanning
- ✅ User deletion
- ✅ Group CRUD
- ✅ Multi-group membership (add, remove, get_user_groups)
- ✅ Task cancellation (creator, sole assignee, co-assignee)

### test_tasks.py (20 тестів):
- ✅ Task creation (simple, with assignees)
- ✅ Task retrieval (by ID, by group)
- ✅ Task status updates (pending → completed, cancelled)
- ✅ Task assignment updates
- ✅ Task deletion
- ✅ Task filtering by status

### test_permissions.py (18 тестів):
- ✅ Super admin checks
- ✅ Group admin permissions (add, remove, check)
- ✅ User group membership checks
- ✅ Permission combinations (admin + member)
- ✅ Edge cases (non-existent users/groups)

### Ще не покрито:
- ⏳ Task media attachments
- ⏳ Task history/comments
- ⏳ Registration requests
- ⏳ Performance tracking/analytics
- ⏳ Bot handlers (потребує mock telegram API)

## Continuous Integration

Для автоматичного запуску створіть `.github/workflows/tests.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install uv
      - run: uv pip install -e ".[dev]"
      - run: pytest --cov --cov-report=term
```

## Статистика

Запустіть для отримання статистики:
```bash
pytest --durations=10  # 10 найповільніших тестів
pytest --collect-only  # Показати всі тести без запуску
```
