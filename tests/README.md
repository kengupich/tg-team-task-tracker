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
pytest tests/test_tasks.py                 # Базові тести завдань
pytest tests/test_task_scenarios.py        # 🆕 Сценарні тести індивідуальних статусів
pytest tests/test_task_integration.py      # 🆕 Інтеграційні тести повних workflow
pytest tests/test_permissions.py           # Тести прав доступу
pytest tests/test_database.py::TestUserManagement::test_add_user  # Окремий тест
```

### 🚀 Запуск тільки нових тестів
```bash
# Всі нові тести для індивідуальних статусів
pytest tests/test_task_scenarios.py tests/test_task_integration.py -v

# Швидка перевірка основних сценаріїв
pytest tests/test_task_scenarios.py::TestIndividualAssigneeStatusScenarios -v

# Інтеграційні тести (повні workflow)
pytest tests/test_task_integration.py::TestCompleteTaskWorkflow -v
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
├── conftest.py                  # Pytest fixtures (test_db, sample_users, etc.)
├── test_database.py             # Тести database.py (19 тестів: користувачі, групи, ban/delete)
├── test_tasks.py                # Базові тести завдань (20 тестів: CRUD операції)
├── test_task_scenarios.py       # 🆕 Сценарні тести (40+ тестів: індивідуальні статуси)
├── test_task_integration.py     # 🆕 Інтеграційні тести (25+ тестів: повні workflow)
├── test_permissions.py          # Тести прав доступу (18 тестів: super_admin, group_admin)
├── init_demo_data.py            # Утиліта для створення тестових даних
├── check_db.py                  # Інспектор бази даних
└── README.md                    # Цей файл
```

**Загальна кількість тестів: 120+**

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

### 🆕 test_task_scenarios.py (40+ тестів):
**Сценарні тести для нового функціоналу індивідуальних статусів**

#### TestTaskCreationScenarios (3 тести):
- ✅ Створення задачі з title та description
- ✅ Створення з кількома виконавцями + індивідуальні статуси
- ✅ Створення без виконавців

#### TestIndividualAssigneeStatusScenarios (5 тестів):
- ✅ Зміна статусу одним виконавцем (in_progress)
- ✅ Прогрес кількох виконавців до завершення (повний lifecycle)
- ✅ Правила агрегації статусів (5 правил)
- ✅ Незалежність статусів виконавців
- ✅ Перевірка всіх правил агрегації

#### TestTaskEditingScenarios (4 тести):
- ✅ Редагування title задачі
- ✅ Редагування description задачі
- ✅ Зміна deadline (date + time)
- ✅ Видалення виконавця перераховує статус

#### TestTaskViewingScenarios (2 тести):
- ✅ Отримання задачі зі статусами виконавців
- ✅ Список задач групи з різними статусами

#### TestTaskDeletionScenarios (1 тест):
- ✅ Видалення задачі видаляє записи виконавців

#### TestEdgeCasesAndValidation (5 тестів):
- ✅ Оновлення статусу неіснуючого виконавця
- ✅ Отримання статусу незакріпленого користувача
- ✅ Невалідне значення статусу
- ✅ Задача без виконавців має pending статус

### 🆕 test_task_integration.py (25+ тестів):
**Інтеграційні тести для повних workflow**

#### TestCompleteTaskWorkflow (1 тест):
- ✅ Повний lifecycle: створення → призначення → робота → завершення
  - Менеджер створює задачу
  - Призначає 3 розробників
  - Кожен змінює свій статус
  - Задача завершується коли всі готові

#### TestMultipleTasksWorkflow (1 тест):
- ✅ Розробник працює над кількома задачами паралельно
- ✅ Різні статуси для різних задач одного користувача

#### TestTaskReassignmentWorkflow (1 тест):
- ✅ Зміна складу команди під час роботи
- ✅ Збереження статусів при реорганізації

#### TestTaskEditingDuringWork (1 тест):
- ✅ Редагування деталей задачі не впливає на статуси
- ✅ Title, description, deadline оновлюються без втрати прогресу

#### TestConcurrentStatusChanges (1 тест):
- ✅ Одночасна зміна статусів кількома виконавцями
- ✅ Коректність агрегації при "race conditions"

#### TestTaskListingAndFiltering (1 тест):
- ✅ Перегляд групових задач з різними агрегованими статусами
- ✅ Перевірка деталей кожного виконавця

#### TestErrorHandlingInWorkflow (2 тести):
- ✅ Graceful handling відсутніх даних
- ✅ Надійний розрахунок статусу для edge cases

#### TestBackwardCompatibility (1 тест):
- ✅ Сумісність з assigned_to_list (старий формат)
- ✅ Синхронізація між старою та новою структурами

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
