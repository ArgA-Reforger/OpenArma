from celery.schedules import schedule

from backend.app.task.utils.tzcrontab import TzAwareCrontab

# Reference: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
LOCAL_BEAT_SCHEDULE = {
    'test_sync_task': {
        'task': 'task_demo',
        'schedule': schedule(30),
    },
    'test_async_task': {
        'task': 'task_demo_async',
        'schedule': TzAwareCrontab('1'),
    },
    'test_params_task': {
        'task': 'task_demo_params',
        'schedule': TzAwareCrontab('1'),
        'args': ['Hello, '],
        'kwargs': {'world': 'World'},
    },
    'clean_operation_log': {
        'task': 'backend.app.task.tasks.db_log.tasks.delete_db_opera_log',
        'schedule': TzAwareCrontab('0', '0', day_of_week='6'),
    },
    'clean_login_log': {
        'task': 'backend.app.task.tasks.db_log.tasks.delete_db_login_log',
        'schedule': TzAwareCrontab('0', '0', day_of_month='15'),
    },
}
