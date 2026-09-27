## Task overview

The current task implementation uses Celery; for the implementation approach, see [#225](https://github.com/fastapi-practices/fastapi_best_architecture/discussions/225)

## Scheduled tasks

Write scheduled tasks in `backend/app/task/tasks/beat.py`

### Simple tasks

Write task code in `backend/app/task/tasks/tasks.py`

### Hierarchical tasks

If you want to organize tasks into subdirectories for a clearer task structure, you can create any directory you like, but note that:

1. Create a new Python package directory under `backend/app/task/tasks`
2. In the new directory, make sure to add a `tasks.py` file and write the related task code in it

## Message broker

You can control the message broker choice via `CELERY_BROKER`, which supports redis and rabbitmq

For local debugging, redis is recommended

For production, rabbitmq is required
