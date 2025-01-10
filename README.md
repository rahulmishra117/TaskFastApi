Here's a `README.md` file outlining the functionality of each API endpoint in your FastAPI project.

```markdown
# Task Management API

This API provides functionality to manage tasks in a Task Management System. It includes endpoints for creating, updating, fetching, and deleting tasks, as well as health checks. The system is designed with Keycloak integration for authentication, Redis for caching, and Prometheus for monitoring.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Endpoints](#endpoints)
  - [POST /tasks](#post-tasks)
  - [GET /tasks](#get-tasks)
  - [PUT /tasks/{task_id}](#put-tasks-id)
  - [DELETE /tasks/{task_id}](#delete-tasks-id)
  - [GET /health](#get-health)
- [Metrics](#metrics)

## Installation

1. Install dependencies using pip:

    ```bash
    pip install -r requirements.txt
    ```

2. Run the FastAPI application:

    ```bash
    uvicorn main:app --reload
    ```

## Configuration

### Environment Variables

- **DATABASE_URL**: URL of the PostgreSQL database (e.g., `postgresql+asyncpg://username:password@localhost:5432/task_db`).
- **CACHE_HOST**: Host for Redis (default: `localhost`).
- **CACHE_PORT**: Port for Redis (default: `6379`).
- **KEYCLOAK_URL**: URL for Keycloak server.
- **KEYCLOAK_CLIENT_ID**: Client ID for Keycloak.
- **KEYCLOAK_CLIENT_SECRET**: Client secret for Keycloak.

## Endpoints

### POST /tasks

Create a new task.

**Request Body**:
```json
{
    "title": "Task Title",
    "description": "Task Description",
    "status": "pending"
}
```

**Response**:
Returns the newly created task.
```json
{
    "id": "UUID",
    "title": "Task Title",
    "description": "Task Description",
    "status": "pending",
    "created_at": "2025-01-01T12:00:00",
    "updated_at": "2025-01-01T12:00:00"
}
```

**Description**: This endpoint creates a new task in the system. The task is assigned a unique ID and a default status of `pending`.

### GET /tasks

Get a list of tasks with pagination.

**Query Parameters**:
- `page` (default: 1)
- `size` (default: 10)

**Response**:
Returns a list of tasks.
```json
[
    {
        "id": "UUID",
        "title": "Task Title",
        "description": "Task Description",
        "status": "pending",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
]
```

**Description**: This endpoint retrieves tasks from the system with pagination. It returns a list of tasks based on the provided `page` and `size` parameters.

### PUT /tasks/{task_id}

Update a task's details.

**Request Body**:
```json
{
    "title": "Updated Task Title",
    "status": "completed"
}
```

**Response**:
Returns the updated task.
```json
{
    "id": "UUID",
    "title": "Updated Task Title",
    "description": "Task Description",
    "status": "completed",
    "created_at": "2025-01-01T12:00:00",
    "updated_at": "2025-01-01T12:00:00"
}
```

**Description**: This endpoint allows updating an existing task's title and/or status.

### DELETE /tasks/{task_id}

Delete a task by ID.

**Response**:
Returns a success message.
```json
{
    "detail": "Task deleted successfully"
}
```

**Description**: This endpoint deletes a task identified by the given `task_id`. The task will be removed from the database and the cache.

### GET /health

Check the health of the API.

**Response**:
Returns the health status of the service.
```json
{
    "status": "ok"
}
```

**Description**: This endpoint checks the database connection to ensure the API is operational.

## Metrics

Prometheus metrics are exposed for monitoring. The following metrics are available:

- **http_requests_total**: A counter for the total number of HTTP requests.
- **http_request_duration_seconds**: A histogram to measure the request duration in seconds.

These metrics can be accessed at the `/metrics` endpoint.

## Logging

The application uses logging to track operations and errors. The log level is set to `INFO`, and logs are written to the standard output.

## Keycloak Integration

This API uses Keycloak for OAuth2 authentication. You can authenticate using a client ID and secret, which are defined in the configuration. The authentication token is required for accessing the API endpoints, except for the health check.

Example of obtaining a token:
```bash
curl -X POST http://localhost:8080/realms/task-api/protocol/openid-connect/token \
    -d "client_id=task-client" \
    -d "client_secret=EjpMWS6VvCjkZrmWx6Gncw4Is8gs8hd8" \
    -d "grant_type=client_credentials"
```

If successful, the response will contain the access token.

# Role
    Admin
    User


