# Import all the requir module from fast apis
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Text, Enum, TIMESTAMP, func, select
import enum
from datetime import datetime
import logging
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
import os
from aiocache import RedisCache
from aiocache.serializers import JsonSerializer

from fastapi.middleware.cors import CORSMiddleware

# Keycloak Setup
from fastapi_keycloak import FastAPIKeycloak
from fastapi.security import OAuth2PasswordBearer
import requests

# FastAPI app initialization
app = FastAPI(title="Task Management API Docs",  
              description="API documentation for managing tasks in the Task Management System",  
              version="1.0.0")

# Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Database setup
DATABASE_URL = "postgresql+asyncpg://rahulm:postgres@localhost:5432/task_db"
engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

#Adding a Middleware for cros  
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Database schema for the Task Management APIs
# Enum for task status
class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"

# Database model
class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

# Pydantic models
class Task(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class CreateTask(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

class UpdateTask(BaseModel):
    title: Optional[str] = None
    status: Optional[TaskStatus] = None

# Keycloak credentials for OAuth2 Authentication
url = "http://localhost:8080/realms/task-api/protocol/openid-connect/token"
data = {
    "client_id": "task-client",
    "client_secret": "EjpMWS6VvCjkZrmWx6Gncw4Is8gs8hd8",
    "grant_type": "client_credentials",
}

response = requests.post(url, data=data)
if response.status_code == 200:
    token = response.json().get("access_token")
    print(f"Access Token: {token}")
else:
    print(f"Failed to get token: {response.status_code} - {response.text}")

# Keycloak Integration (get_keycloak_user)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

print("OAuth token",oauth2_scheme)
def get_keycloak_user(token: str = Depends(oauth2_scheme)) -> Dict:
    try:
        # Print the received token for debugging
        print("Received Token:", token)

        # Replace this with your actual Keycloak public key or use `options={"verify_signature": False}`
        public_key = "abc"

        # Decode the JWT token and validate its signature using the public key
        payload = jwt.decode(token, public_key, algorithms=["RS256"], audience="<Your-CLIENT-ID>")
        print("Decoded token payload:", payload)

        # Extract the user_id (subject) or any other relevant claim
        user_id = payload.get("sub")  # "sub" is usually the user identifier in Keycloak tokens
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: Missing user ID")

        # Return user information
        user = {"user_id": user_id}
        print("User:", user)  # To see the decoded user data
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Dependency to get the database session
async def get_db():
    async with async_session() as session:
        yield session

# Helper function for pagination
async def paginate(db: AsyncSession, query, page: int, size: int):
    try:
        result = await db.execute(query.offset((page - 1) * size).limit(size))
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pagination failed: {str(e)}")

# Prometheus Metrics Setup
REQUEST_COUNT = Counter("http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status_code"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Histogram of HTTP request duration", ["method", "endpoint"])

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Redis cache
cache = RedisCache(
    endpoint="localhost",  
    port=6379,             
    serializer=JsonSerializer()
)
# Api end point for creating an task
@app.post("/tasks", response_model=Task)
async def create_task(task: CreateTask, db: AsyncSession = Depends(get_db), user: dict = Depends(get_keycloak_user)):
    with REQUEST_LATENCY.labels(method="POST", endpoint="/tasks").time():
        try:
            new_task = TaskModel(**task.dict(), updated_at=datetime.utcnow())
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)
            logger.info(f"Created task: {new_task.id}")
            REQUEST_COUNT.labels(method="POST", endpoint="/tasks", status_code="200").inc()
            return new_task
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create task: {str(e)}")
            REQUEST_COUNT.labels(method="POST", endpoint="/tasks", status_code="500").inc()
            raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

# Get All Tasks with Pagination
@app.get("/tasks", response_model=List[Task])
async def get_all_tasks(page: int = Query(1, gt=0), size: int = Query(10, gt=0), db: AsyncSession = Depends(get_db), user: dict = Depends(get_keycloak_user)):
    with REQUEST_LATENCY.labels(method="GET", endpoint="/tasks").time():
        try:
            query = select(TaskModel).order_by(TaskModel.created_at)
            paginated_tasks = await paginate(db, query, page, size)
            logger.info(f"Fetched {len(paginated_tasks)} tasks")
            REQUEST_COUNT.labels(method="GET", endpoint="/tasks", status_code="200").inc()
            return paginated_tasks
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {str(e)}")
            REQUEST_COUNT.labels(method="GET", endpoint="/tasks", status_code="500").inc()
            raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")

# Update Task
@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, updated_task: UpdateTask, db: AsyncSession = Depends(get_db), user: dict = Depends(get_keycloak_user)):
    with REQUEST_LATENCY.labels(method="PUT", endpoint=f"/tasks/{task_id}").time():
        try:
            query = select(TaskModel).filter(TaskModel.id == task_id)
            result = await db.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            for key, value in updated_task.dict(exclude_unset=True).items():
                setattr(task, key, value)

            await db.commit()
            await db.refresh(task)
            await cache.set(f"task_{task.id}", task.dict())
            logger.info(f"Updated task: {task.id}")
            REQUEST_COUNT.labels(method="PUT", endpoint=f"/tasks/{task_id}", status_code="200").inc()
            return task
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update task: {str(e)}")
            REQUEST_COUNT.labels(method="PUT", endpoint=f"/tasks/{task_id}", status_code="500").inc()
            raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

# //Api endpoint for deleteing an task from data base based of the task id 
@app.delete("/tasks/{task_id}", response_model=dict)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_keycloak_user)):
    with REQUEST_LATENCY.labels(method="DELETE", endpoint=f"/tasks/{task_id}").time():
        try:
            query = select(TaskModel).filter(TaskModel.id == task_id)
            result = await db.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            await db.delete(task)
            await db.commit()
            await cache.delete(f"task_{task.id}")
            logger.info(f"Deleted task: {task_id}")
            REQUEST_COUNT.labels(method="DELETE", endpoint=f"/tasks/{task_id}", status_code="200").inc()
            return {"detail": "Task deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete task: {str(e)}")
            REQUEST_COUNT.labels(method="DELETE", endpoint=f"/tasks/{task_id}", status_code="500").inc()
            raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

# Api end point check health check of the database connections
@app.get("/health", response_model=dict)
async def health_check(db: AsyncSession = Depends(get_db)):
    with REQUEST_LATENCY.labels(method="GET", endpoint="/health").time():
        try:
            await db.execute(select(1))
            logger.info("Health check passed")
            REQUEST_COUNT.labels(method="GET", endpoint="/health", status_code="200").inc()
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            REQUEST_COUNT.labels(method="GET", endpoint="/health", status_code="500").inc()
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
