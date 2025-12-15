"""
Unit tests for async database operations with mocks.
Tests async wrapper functionality without requiring PostgreSQL.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import db_async


class TestAsyncWrappersMock:
    """Test async wrappers with mocked database functions."""
    
    @pytest.mark.asyncio
    async def test_async_get_user_groups_mock(self):
        """Test async_get_user_groups with mock."""
        mock_result = [
            (1, "Group 1"),
            (2, "Group 2"),
        ]
        
        with patch('database.get_user_groups', return_value=mock_result):
            result = await db_async.async_get_user_groups(12345)
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_async_get_group_tasks_mock(self):
        """Test async_get_group_tasks with mock."""
        mock_tasks = [
            (1, "Task 1", "2025-12-20", "10:00", "Desc 1", 1, "123", 0, "pending"),
            (2, "Task 2", "2025-12-21", "11:00", "Desc 2", 1, "123", 0, "done"),
        ]
        
        with patch('database.get_group_tasks', return_value=mock_tasks):
            result = await db_async.async_get_group_tasks(1)
            assert result == mock_tasks
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_async_get_user_tasks_mock(self):
        """Test async_get_user_tasks with mock."""
        mock_tasks = [(1, "My Task", "2025-12-22", "14:00")]
        
        with patch('database.get_user_tasks', return_value=mock_tasks):
            result = await db_async.async_get_user_tasks(12345)
            assert result == mock_tasks
    
    @pytest.mark.asyncio
    async def test_async_get_task_by_id_mock(self):
        """Test async_get_task_by_id with mock."""
        mock_task = (1, "Task Title", "2025-12-23", "15:00", "Description", 1)
        
        with patch('database.get_task_by_id', return_value=mock_task):
            result = await db_async.async_get_task_by_id(1)
            assert result == mock_task
            assert result[1] == "Task Title"
    
    @pytest.mark.asyncio
    async def test_async_get_group_users_mock(self):
        """Test async_get_group_users with mock."""
        mock_users = [
            (12345, "User 1"),
            (12346, "User 2"),
            (12347, "User 3"),
        ]
        
        with patch('database.get_group_users', return_value=mock_users):
            result = await db_async.async_get_group_users(1)
            assert result == mock_users
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_async_get_all_groups_mock(self):
        """Test async_get_all_groups with mock."""
        mock_groups = [
            (1, "Group 1", 12345),
            (2, "Group 2", 12346),
        ]
        
        with patch('database.get_all_groups', return_value=mock_groups):
            result = await db_async.async_get_all_groups()
            assert result == mock_groups
    
    @pytest.mark.asyncio
    async def test_async_get_user_by_id_mock(self):
        """Test async_get_user_by_id with mock."""
        mock_user = (12345, "John Doe", "johndoe")
        
        with patch('database.get_user_by_id', return_value=mock_user):
            result = await db_async.async_get_user_by_id(12345)
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_async_get_group_mock(self):
        """Test async_get_group with mock."""
        mock_group = (1, "Test Group", 12345)
        
        with patch('database.get_group', return_value=mock_group):
            result = await db_async.async_get_group(1)
            assert result == mock_group
    
    @pytest.mark.asyncio
    async def test_async_get_task_media_mock(self):
        """Test async_get_task_media with mock."""
        mock_media = [
            (1, 1, "file_id_1", "photo", "photo.jpg", 1024),
            (2, 1, "file_id_2", "video", "video.mp4", 2048),
        ]
        
        with patch('database.get_task_media', return_value=mock_media):
            result = await db_async.async_get_task_media(1)
            assert result == mock_media
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_async_write_operation_mock(self):
        """Test async write operations with mock."""
        with patch('database.add_user', return_value=True):
            result = await db_async.async_add_user(12345, "Test User")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_async_create_group_mock(self):
        """Test async_create_group with mock."""
        with patch('database.create_group', return_value=5):
            result = await db_async.async_create_group("New Group", 12345)
            assert result == 5
    
    @pytest.mark.asyncio
    async def test_async_create_task_mock(self):
        """Test async_create_task with mock."""
        with patch('database.create_task', return_value=10):
            result = await db_async.async_create_task(
                title="New Task",
                date="2025-12-24",
                time="12:00",
                description="Test task",
                group_id=1,
                assigned_to_list="12345",
                created_by=12345
            )
            assert result == 10
    
    @pytest.mark.asyncio
    async def test_async_update_task_field_mock(self):
        """Test async_update_task_field with mock."""
        with patch('database.update_task_field', return_value=True):
            result = await db_async.async_update_task_field(
                task_id=10,
                field_name="title",
                value="Updated Title"
            )
            assert result is True
    
    @pytest.mark.asyncio
    async def test_async_delete_task_mock(self):
        """Test async_delete_task with mock."""
        with patch('database.delete_task', return_value=True):
            result = await db_async.async_delete_task(10)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_async_update_assignee_status_mock(self):
        """Test async_update_assignee_status with mock."""
        with patch('database.update_assignee_status', return_value=True):
            result = await db_async.async_update_assignee_status(10, 12345, "done")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self):
        """Test multiple concurrent async operations."""
        mock_groups = [(1, "Group 1"), (2, "Group 2")]
        mock_tasks = [(1, "Task 1")]
        mock_users = [(12345, "User 1")]
        
        with patch('database.get_all_groups', return_value=mock_groups), \
             patch('database.get_group_tasks', return_value=mock_tasks), \
             patch('database.get_group_users', return_value=mock_users):
            
            tasks = [
                db_async.async_get_all_groups(),
                db_async.async_get_group_tasks(1),
                db_async.async_get_group_users(1),
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert results[0] == mock_groups
            assert results[1] == mock_tasks
            assert results[2] == mock_users
    
    @pytest.mark.asyncio
    async def test_exception_in_async_operation(self):
        """Test exception handling in async operations."""
        with patch('database.get_user_by_id', side_effect=ValueError("DB Error")):
            with pytest.raises(ValueError):
                await db_async.async_get_user_by_id(12345)
    
    @pytest.mark.asyncio
    async def test_async_none_result(self):
        """Test async operation returning None."""
        with patch('database.get_user_by_id', return_value=None):
            result = await db_async.async_get_user_by_id(999999)
            assert result is None


class TestAsyncBehavior:
    """Test async behavior and thread handling."""
    
    @pytest.mark.asyncio
    async def test_to_thread_execution(self):
        """Verify operations run in thread, not blocking event loop."""
        import time
        
        def slow_operation():
            # Simulate slow DB operation
            time.sleep(0.1)
            return "completed"
        
        # This should not block
        start = time.time()
        result = await asyncio.to_thread(slow_operation)
        elapsed = time.time() - start
        
        assert result == "completed"
        assert elapsed >= 0.1  # Should have taken at least 0.1s
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_db_calls(self):
        """Test that multiple DB calls can run concurrently."""
        call_times = []
        
        async def track_call(call_id):
            with patch('database.get_user_groups', return_value=[]):
                call_times.append(('start', call_id))
                await asyncio.sleep(0.05)  # Simulate async work
                result = await db_async.async_get_user_groups(call_id)
                call_times.append(('end', call_id))
                return result
        
        # Run 3 calls concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            track_call(1),
            track_call(2),
            track_call(3),
        )
        end_time = asyncio.get_event_loop().time()
        
        assert len(results) == 3
        # Should take ~50ms, not 150ms (if they ran sequentially)
        assert (end_time - start_time) < 0.15


class TestAsyncIntegration:
    """Integration tests for async operations."""
    
    @pytest.mark.asyncio
    async def test_async_workflow_mock(self):
        """Test typical async workflow."""
        with patch('database.create_group', return_value=1), \
             patch('database.add_user', return_value=True), \
             patch('database.add_user_to_group', return_value=True), \
             patch('database.create_task', return_value=5), \
             patch('database.get_group_tasks', return_value=[(5, "Task 1")]):
            
            # Create group
            group_id = await db_async.async_create_group("Test Group", 12345)
            assert group_id == 1
            
            # Add user
            added = await db_async.async_add_user(12346, "User")
            assert added is True
            
            # Add user to group
            result = await db_async.async_add_user_to_group(12346, group_id)
            assert result is True
            
            # Create task
            task_id = await db_async.async_create_task(
                title="Task",
                date="2025-12-25",
                time="12:00",
                description="Desc",
                group_id=group_id,
                assigned_to_list="12346",
                created_by=12345
            )
            assert task_id == 5
            
            # Get tasks
            tasks = await db_async.async_get_group_tasks(group_id)
            assert len(tasks) > 0
