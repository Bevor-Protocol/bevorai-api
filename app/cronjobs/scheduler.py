def scheduled_task():
    logging.info("Scheduled task is running")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule the task to run every 30 minutes
    scheduler.add_job(scheduled_task, CronTrigger.from_crontab('*/30 * * * *'))
    scheduler.start()
    # Run the task immediately on startup
    scheduled_task()