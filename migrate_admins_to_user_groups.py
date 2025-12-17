"""
Migration script to add all group admins to user_groups table.
This ensures admins are visible in task assignment lists.
"""
import logging
from database import _get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_admins_to_user_groups():
    """Add all group admins to user_groups if not already present."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all admin-group pairs
        cursor.execute("""
            SELECT admin_id, group_id FROM group_admins
        """)
        admin_pairs = cursor.fetchall()
        
        logger.info(f"Found {len(admin_pairs)} admin-group pairs to migrate")
        
        added_count = 0
        skipped_count = 0
        
        for admin_id, group_id in admin_pairs:
            # Check if already in user_groups
            cursor.execute("""
                SELECT 1 FROM user_groups 
                WHERE user_id = %s AND group_id = %s
            """, (admin_id, group_id))
            
            if cursor.fetchone():
                skipped_count += 1
                continue
            
            # Add to user_groups
            try:
                cursor.execute("""
                    INSERT INTO user_groups (user_id, group_id) 
                    VALUES (%s, %s)
                """, (admin_id, group_id))
                added_count += 1
                logger.info(f"✓ Added admin {admin_id} to group {group_id}")
            except Exception as e:
                logger.warning(f"✗ Error adding admin {admin_id} to group {group_id}: {e}")
        
        conn.commit()
        logger.info(f"Migration complete: {added_count} added, {skipped_count} already present")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRATION: Add group admins to user_groups")
    print("=" * 60)
    migrate_admins_to_user_groups()
    print("=" * 60)
