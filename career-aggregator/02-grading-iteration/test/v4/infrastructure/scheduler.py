from apscheduler.schedulers.background import BackgroundScheduler
from infrastructure.database import get_session

_scheduler = BackgroundScheduler()
_jobs = {}

def start_scheduler():
    _scheduler.start()

def stop_scheduler():
    _scheduler.shutdown()

def add_job(func, id: str, trigger: str, **kwargs):
    _jobs[id] = _scheduler.add_job(func, id=id, replace_existing=True, trigger=trigger, **kwargs)

def remove_job(id: str):
    if id in _jobs:
        _jobs[id].remove()
        del _jobs[id]

def update_grading_schedule(cron_expression: str, func):
    remove_job("grading")
    parts = cron_expression.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        add_job(func, "grading", "cron", minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)
