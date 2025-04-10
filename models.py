from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Admin:
    user_id: int
    username: str
    created_at: datetime = None

@dataclass
class Worker:
    user_id: int
    name: str
    phone: Optional[str] = None
    created_at: datetime = None

@dataclass
class Task:
    id: int
    address: str
    date: str
    time: str
    description: str
    status: str
    created_by: int
    worker_id: Optional[int] = None
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class WorkerTaskResponse:
    id: int
    worker_id: int
    task_id: int
    response: str
    created_at: datetime = None

@dataclass
class WorkerStats:
    user_id: int
    name: str
    tasks_accepted: int
    tasks_completed: int
    tasks_declined: int
    completion_rate: float
