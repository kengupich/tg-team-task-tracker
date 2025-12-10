"""
Тест для перевірки видалення адміністраторів при бані/видаленні користувача
"""
import os
import sys
import sqlite3

# Додаємо шлях до модулів
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Встановлюємо тестову базу даних перед імпортом
import database
database.DB_FILE = 'test_tasks.db'

from database import (
    init_db, 
    add_user, 
    create_group, 
    update_group_admin,
    add_group_admin,
    ban_user,
    delete_user,
    get_group
)


def setup_test_db():
    """Створюємо тестову базу даних"""
    if os.path.exists('test_tasks.db'):
        os.remove('test_tasks.db')
    
    # Ініціалізуємо базу
    init_db()
    
    # Створюємо користувачів
    add_user(111, "Admin1")
    add_user(222, "Admin2")
    add_user(333, "RegularUser")
    
    # Створюємо групи
    group1_id = create_group("Group 1", 111)
    group2_id = create_group("Group 2", 222)
    
    # Додаємо Admin1 як multi-group адміна до Group2
    add_group_admin(group2_id, 111)
    
    return group1_id, group2_id


def check_admin_status(user_id, group_id):
    """Перевіряє чи є користувач адміном"""
    conn = sqlite3.connect('test_tasks.db')
    cursor = conn.cursor()
    
    # Перевіряємо primary admin
    cursor.execute("SELECT admin_id FROM groups WHERE group_id = ?", (group_id,))
    row = cursor.fetchone()
    is_primary = row and row[0] == user_id
    
    # Перевіряємо multi-group admin
    cursor.execute(
        "SELECT COUNT(*) FROM group_admins WHERE group_id = ? AND admin_id = ?",
        (group_id, user_id)
    )
    is_multi = cursor.fetchone()[0] > 0
    
    conn.close()
    return is_primary, is_multi


def test_ban_user_removes_admin():
    """Тест: бан користувача видаляє його з адмінів"""
    print("=== TEST 1: Ban користувача видаляє адмін-права ===")
    
    group1_id, group2_id = setup_test_db()
    
    # Перевіряємо початковий стан
    is_primary_g1, is_multi_g1 = check_admin_status(111, group1_id)
    is_primary_g2, is_multi_g2 = check_admin_status(111, group2_id)
    
    print(f"До бану Admin1 (user 111):")
    print(f"  Group1: primary={is_primary_g1}, multi={is_multi_g1}")
    print(f"  Group2: primary={is_primary_g2}, multi={is_multi_g2}")
    
    assert is_primary_g1 == True, "Admin1 має бути primary admin Group1"
    assert is_multi_g2 == True, "Admin1 має бути multi-group admin Group2"
    
    # Баняємо користувача
    ban_user(111)
    
    # Перевіряємо після бану
    is_primary_g1, is_multi_g1 = check_admin_status(111, group1_id)
    is_primary_g2, is_multi_g2 = check_admin_status(111, group2_id)
    
    print(f"\nПісля бану Admin1 (user 111):")
    print(f"  Group1: primary={is_primary_g1}, multi={is_multi_g1}")
    print(f"  Group2: primary={is_primary_g2}, multi={is_multi_g2}")
    
    assert is_primary_g1 == False, "Admin1 НЕ має бути primary admin Group1 після бану"
    assert is_multi_g2 == False, "Admin1 НЕ має бути multi-group admin Group2 після бану"
    
    # Перевіряємо що Group1.admin_id тепер NULL
    group1 = get_group(group1_id)
    assert group1['admin_id'] is None, "Group1.admin_id має бути NULL після бану primary admin"
    
    print("✅ TEST 1 PASSED: Забанений користувач втратив всі адмін-права\n")
    
    # Cleanup
    os.remove('test_tasks.db')


def test_delete_user_removes_admin():
    """Тест: видалення користувача видаляє його з адмінів"""
    print("=== TEST 2: Видалення користувача видаляє адмін-права ===")
    
    group1_id, group2_id = setup_test_db()
    
    # Перевіряємо початковий стан
    is_primary_g2, is_multi_g2 = check_admin_status(222, group2_id)
    
    print(f"До видалення Admin2 (user 222):")
    print(f"  Group2: primary={is_primary_g2}, multi={is_multi_g2}")
    
    assert is_primary_g2 == True, "Admin2 має бути primary admin Group2"
    
    # Видаляємо користувача
    delete_user(222)
    
    # Перевіряємо після видалення
    is_primary_g2, is_multi_g2 = check_admin_status(222, group2_id)
    
    print(f"\nПісля видалення Admin2 (user 222):")
    print(f"  Group2: primary={is_primary_g2}, multi={is_multi_g2}")
    
    assert is_primary_g2 == False, "Admin2 НЕ має бути primary admin Group2 після видалення"
    
    # Перевіряємо що Group2.admin_id тепер NULL
    group2 = get_group(group2_id)
    assert group2['admin_id'] is None, "Group2.admin_id має бути NULL після видалення primary admin"
    
    print("✅ TEST 2 PASSED: Видалений користувач втратив всі адмін-права\n")
    
    # Cleanup
    os.remove('test_tasks.db')


if __name__ == '__main__':
    try:
        test_ban_user_removes_admin()
        test_delete_user_removes_admin()
        print("=" * 60)
        print("✅ ВСІ ТЕСТИ ПРОЙДЕНО УСПІШНО!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕНО: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
