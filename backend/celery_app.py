from celery import Celery
from celery.schedules import crontab


def make_celery(app):
    """Create and configure a Celery object with Flask app context for tasks and beat schedules."""
    celery = Celery(
        app.import_name,
        broker=app.config.get('REDIS_URL'),
        backend=app.config.get('REDIS_URL')
    )

    # copy Flask config to Celery
    celery.conf.update(app.config)

    # Example beat schedule: daily reminders at 07:00 and monthly report on 1st at 06:00
    celery.conf.beat_schedule = {
        'daily-interview-reminders': {
            'task': 'tasks.send_interview_reminders',
            'schedule': crontab(hour=7, minute=0),
        },
        'monthly-placement-report': {
            'task': 'tasks.generate_monthly_placement_report',
            'schedule': crontab(day_of_month='1', hour=6, minute=0),
        }
    }

    # ensure tasks run inside Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
