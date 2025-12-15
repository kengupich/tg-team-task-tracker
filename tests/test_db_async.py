"""
Tests for async database operations.
Ensures that async wrappers don't break functionality and are thread-safe.
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database
import db_async
from tests.conftest import test_db


class TestAsyncDatabaseOperations:
    """Test async wrapper functions."""
    
    @pytest.mark.asyncio
    async def test_async_get_user_groups(self, test_db):
        """Test async_get_user_groups returns same result as sync version."""
        # Create test user and group
        user_id = 12345
        database.add_user(user_id, "Test User")
        group_id = database.create_group("Test Group", user_id)
        database.add_user_to_group(user_id, group_id)
        
        # Compare sync vs async
        sync_result = database.get_user_groups(user_id)
        async_result = await db_async.async_get_user_groups(user_id)
        
        assert sync_result == async_result
        assert len(async_result) > 0
    
    @pytest.mark.asyncio
    async def test_async_get_group_tasks(self, test_db):
        """Test async_get_group_tasks."""
        # Create test data
        user_id = 12346
        database.add_user(user_id, "Admin User")
        group_id = database.create_group("Tasks Group", user_id)
        
        task_id = database.create_task(
            title="Test Task",
            date="2025-12-20",
            time="10:00",
            description="Test description",
            group_id=group_id,
            assigned_to_list=str(user_id),
            created_by=user_id
        )
        
        # Compare sync vs async
        sync_result = database.get_group_tasks(group_id)
        async_result = await db_async.async_get_group_tasks(group_id)
        
        assert sync_result == async_result
        assert len(async_result) > 0
    
    @pytest.mark.asyncio
    async def test_async_get_user_tasks(self, test_db):
        """Test async_get_user_tasks."""
        # Create test data
        user_id = 12347
        database.add_user(user_id, "Task User")
        group_id = database.create_group("User Tasks Group", user_id)
        database.add_user_to_group(user_id, group_id)
        
        task_id = database.create_task(
            title="User Task",
            date="2025-12-21",
            time="14:00",
            description="User task description",
            group_id=group_id,
            assigned_to_list=str(user_id),
            created_by=user_id
        )
        
        # Compare sync vs async
        sync_result = database.get_user_tasks(user_id)
        async_result = await db_async.async_get_user_tasks(user_id)
        
        assert sync_result == async_result
    
    @pytest.mark.asyncio
    async def test_async_get_task_by_id(self, test_db):
        """Test async_get_task_by_id."""
        # Create test data
        user_id = 12348
        database.add_user(user_id, "Creator User")
        group_id = database.create_group("Creator Group", user_id)
        
        task_id = database.create_task(
            title="Test Task for ID",
            date="2025-12-22",
            time="15:30",
            description="Description for ID test",
            group_id=group_id,
            assigned_to_list=str(user_id),
            created_by=user_id
        )
        
        # Compare sync vs async
        sync_result = database.get_task_by_id(task_id)
        async_result = await db_async.async_get_task_by_id(task_id)
        
        assert sync_result == async_result
        assert async_result is not None
        assert async_result[1] == "Test Task for ID"  # title
    
    @pytest.mark.asyncio
    async def test_async_get_group_users(self, test_db):
        """Test async_get_group_users."""
        # Create test data
        admin_id = 12349
        user1_id = 12350
        user2_id = 12351
        
        database.add_user(admin_id, "Admin")
        database.add_user(user1_id, "User 1")
        database.add_user(user2_id, "User 2")
        
        group_id = database.create_group("Multi User Group", admin_id)
        database.add_user_to_group(admin_id, group_id)
        database.add_user_to_group(user1_id, group_id)
        database.add_user_to_group(user2_id, group_id)
        
        # Compare sync vs async
        sync_result = database.get_group_users(group_id)
        async_result = await db_async.async_get_group_users(group_id)
        
        assert sync_result == async_result
        assert len(async_result) == 3
    
    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self, test_db):
        """Test multiple concurrent async operations."""
        # Create multiple test entities
        user_ids = []
        group_ids = []
        
        for i in range(3):
            user_id = 13000 + i
            database.add_user(user_id, f"Concurrent User {i}")
            user_ids.append(user_id)
            
            group_id = database.create_group(f"Concurrent Group {i}", user_id)
            group_ids.append(group_id)
            database.add_user_to_group(user_id, group_id)
        
        # Run multiple async operations concurrently
        tasks = [
            db_async.async_get_user_groups(user_ids[0]),
            db_async.async_get_group_users(group_ids[0]),
            db_async.async_get_user_tasks(user_ids[1]),
            db_async.async_get_all_groups(),
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 4
        assert all(isinstance(r, list) for r in results)
    
    @pytest.mark.asyncio
    async def test_async_write_operations(self, test_db):
        """Test async write operations."""
        user_id = 13100
        
        # Test async_add_user
        result = await db_async.async_add_user(user_id, "Async User")
        assert result is True
        
        # Verify user was created
        user = database.get_user_by_id(user_id)
        assert user is not None
        assert user[1] == "Async User"
    
    @pytest.mark.asyncio
    async def test_async_group_creation(self, test_db):
        """Test async group creation."""
        user_id = 13101
        database.add_user(user_id, "Group Creator")
        
        # Create group asynchronously
        group_id = await db_async.async_create_group("Async Created Group", user_id)
        
        # Verify group was created
        group = database.get_group(group_id)
        assert group is not None
        assert group[1] == "Async Created Group"
    
    @pytest.mark.asyncio
    async def test_async_task_creation(self, test_db):
        """Test async task creation."""
        user_id = 13102
        database.add_user(user_id, "Task Creator")
        group_id = database.create_group("Task Group", user_id)
        
        # Create task asynchronously
        task_id = await db_async.async_create_task(
            title="Async Created Task",
            date="2025-12-25",
            time="12:00",
            description="Created async",
            group_id=group_id,
            assigned_to_list=str(user_id),
            created_by=user_id
        )
        
        # Verify task was created
        task = database.get_task_by_id(task_id)
        assert task is not None
        assert task[1] == "Async Created Task"
    
    @pytest.mark.asyncio
    async def test_async_exception_handling(self, test_db):
        """Test exception handling in async operations."""
        # Try to get non-existent user
        result = await db_async.async_get_user_by_id(999999)
        assert result is None  # Should return None, not raise exception
    
    @pytest.mark.asyncio
    async def test_async_update_task(self, test_db):
        """Test async task update."""
        user_id = 13103
        database.add_user(user_id, "Update User")
        group_id = database.create_group("Update Group", user_id)
        
        task_id = database.create_task(
            title="Original Title",
            date="2025-12-26",
            time="11:00",
            description="Original description",
            group_id=group_id,
            assigned_to_list=str(user_id),
            created_by=user_id
        )
        
        # Update task asynchronously
        result = await db_async.async_update_task(
            task_id,
            title="Updated Title",
            description="Updated description"
        )
        
        # Verify update
        task = database.get_task_by_id(task_id)
        assert task[1] == "Updated Title"
        assert task[4] == "Updated description"


class TestAsyncPerformance:
    """Performance tests for async vs sync operations."""
    
    @pytest.mark.asyncio
    async def test_async_bulk_reads(self, test_db):
        """Test async operations with bulk data."""
        # Create bulk test data
        user_id = 13200
        database.add_user(user_id, "Bulk User")
        group_id = database.create_group("Bulk Group", user_id)
        database.add_user_to_group(user_id, group_id)
        
        # Create multiple tasks
        for i in range(10):
            database.create_task(
                title=f"Bulk Task {i}",
                date="2025-12-27",
                time=f"{10 + i%14}:00",
                description=f"Bulk task {i}",
                group_id=group_id,
                assigned_to_list=str(user_id),
                created_by=user_id
            )
        
        # Async bulk read
        tasks = [
            db_async.async_get_group_tasks(group_id)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(len(r) >= 10 for r in results)
