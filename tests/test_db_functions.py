#!/usr/bin/env python3
"""
Test database functions for groups and media
"""
from database import (
    get_all_groups, 
    get_group, 
    get_group_by_admin_id,
    get_group_users,
    create_task,
    add_task_media,
    get_task_media,
    get_user_tasks,
)

print("🧪 Testing Database Functions\n")

# Test 1: Get all groups
print("Test 1: Get all groups")
groups = get_all_groups()
print(f"  ✅ Found {len(groups)} groups")
for g in groups:
    print(f"    - {g['name']} (ID: {g['group_id']}, Admin: {g['admin_id']})")

# Test 2: Get group by admin ID
print("\nTest 2: Get group by admin ID")
group = get_group_by_admin_id(386680721)
if group:
    print(f"  ✅ Found group: {group['name']}")
else:
    print("  ❌ Group not found")

# Test 3: Get group users
print("\nTest 3: Get group users")
users = get_group_users(1)
print(f"  ✅ Found {len(users)} users in group 1")
for u in users:
    print(f"    - {u['user']} (ID: {u['user_id']})")

# Test 4: Create a task
print("\nTest 4: Create task with media support")
task_id = create_task(
    date="2025-12-10",
    time="14:30",
    description="Test task with media",
    group_id=1,
    admin_id=386680721,
    assigned_to_list=[386680722, 386680723]
)
if task_id:
    print(f"  ✅ Created task {task_id}")
else:
    print("  ❌ Failed to create task")

# Test 5: Add media to task
if task_id:
    print(f"\nTest 5: Add media to task")
    media_id = add_task_media(
        task_id=task_id,
        file_id="test_file_id_12345",
        file_type="photo",
        file_name="test_photo.jpg",
        file_size=102400
    )
    if media_id:
        print(f"  ✅ Added media {media_id}")
    else:
        print("  ❌ Failed to add media")
    
    # Test 6: Get task media
    print(f"\nTest 6: Get task media")
    media_list = get_task_media(task_id)
    print(f"  ✅ Found {len(media_list)} media files")
    for m in media_list:
        print(f"    - {m['file_type']}: {m['file_name']} ({m['file_size']} bytes)")

# Test 7: Get user tasks
print(f"\nTest 7: Get user tasks")
user_tasks = get_user_tasks(386680722)
print(f"  ✅ Found {len(user_tasks)} tasks for user 386680722")
for t in user_tasks:
    print(f"    - Task {t['task_id']}: {t['description']} ({t['status']})")

print("\n✅ All tests completed!")
