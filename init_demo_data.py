#!/usr/bin/env python3
"""
Initialize demo data for testing the bot

Sequence implemented:
1. Create 15 users (includes 4 potential admin candidates).
2. Create 4 groups.
3. Assign the first 3 groups admins; leave the 4th without admin.
4. Randomly assign 5 employees (non-admins) into the created groups.
"""
import random
from database import add_user, create_group, update_user_group, get_all_groups, update_group_admin

# --- Demo users (15 total). We include four admin-candidate IDs among them. ---
USERS = [
    (386680721, "admin_marketing"),
    (386680722, "admin_sales"),
    (386680723, "admin_support"),
    (386680724, "admin_development"),
    # Additional regular employees
    (386680700, "alice"),
    (386680701, "bob"),
    (386680702, "carol"),
    (386680703, "dave"),
    (386680704, "eve"),
    (386680705, "frank"),
    (386680706, "grace"),
    (386680707, "heidi"),
    (386680708, "ivan"),
    (386680709, "judy"),
    (386680710, "mallory"),
]

# --- Group definitions. We will attach admin IDs for first three groups only. ---
GROUPS = [
    ("Marketing", 386680721),
    ("Sales", 386680722),
    ("Support", 386680723),
    ("Development", None),  # intentionally no admin for the last group
]


def main():
    print("📌 Creating demo users (15 total)...")
    for uid, uname in USERS:
        try:
            added = add_user(uid, uname)
            if added:
                print(f"  ✅ Added user: {uname} (ID: {uid})")
            else:
                print(f"  ℹ️  User already exists: {uname} (ID: {uid})")
        except Exception as e:
            print(f"  ⚠️ Error adding user {uid}: {e}")

    print("\n📌 Creating demo groups (4)...")
    created_groups = []  # list of tuples (group_id, name, admin_id)
    for name, admin_id in GROUPS:
        try:
            group_id = create_group(name, admin_id)
            if group_id:
                print(f"  ✅ Created group: {name} (ID: {group_id}) admin: {admin_id}")
                created_groups.append((group_id, name, admin_id))
            else:
                # Maybe group already exists — try to find existing group by name
                existing = [g for g in get_all_groups() if g.get("name") == name]
                if existing:
                    eg = existing[0]
                    print(f"  ℹ️ Group '{name}' already exists (ID: {eg['group_id']}). Using existing group.")
                    # If admin_id provided and current admin differs, try to set it
                    if admin_id and eg.get("admin_id") != admin_id:
                        try:
                            if update_group_admin(eg['group_id'], admin_id):
                                print(f"    ✅ Updated group admin for '{name}' -> {admin_id}")
                            else:
                                print(f"    ⚠️ Could not update admin for existing group '{name}'")
                        except Exception as e:
                            print(f"    ⚠️ Error updating admin for group '{name}': {e}")
                    created_groups.append((eg['group_id'], name, admin_id or eg.get('admin_id')))
                else:
                    print(f"  ⚠️ Failed to create group: {name}")
        except Exception as e:
            print(f"  ❌ Error creating group {name}: {e}")

    # Ensure admin users are assigned to their groups (update users' group_id)
    print("\n📌 Assigning admins to their groups (where applicable)...")
    for group_id, name, admin_id in created_groups:
        if admin_id:
            try:
                ok = update_user_group(admin_id, group_id)
                if ok:
                    print(f"  ✅ Set user {admin_id} as member of group '{name}' (group_id={group_id})")
                else:
                    print(f"  ⚠️ Could not set group for admin {admin_id} (may not exist as user)")
            except Exception as e:
                print(f"  ⚠️ Error while setting admin {admin_id} group: {e}")

    # Randomly assign 5 non-admin employees to groups
    print("\n📌 Randomly assigning 5 employees to groups...")
    # Build list of non-admin user IDs (exclude admin candidates)
    admin_ids = {u[0] for u in USERS[:4]}
    non_admin_users = [u for u in USERS if u[0] not in admin_ids]

    # If no groups were created successfully, skip assignment
    if not created_groups:
        print("  ⚠️ No groups available to assign users to.")
    else:
        # Choose up to 5 unique users to assign
        n_assign = min(5, len(non_admin_users))
        selected = random.sample(non_admin_users, n_assign)
        group_ids = [g[0] for g in created_groups]
        for uid, uname in selected:
            target_group = random.choice(group_ids)
            try:
                ok = update_user_group(uid, target_group)
                if ok:
                    print(f"  ✅ Assigned user {uname} (ID: {uid}) -> group_id {target_group}")
                else:
                    print(f"  ⚠️ Failed to assign {uname} (ID: {uid}) to group {target_group}")
            except Exception as e:
                print(f"  ⚠️ Error assigning user {uid} to group {target_group}: {e}")

    print("\n✅ Demo data initialization complete.")


if __name__ == "__main__":
    main()
