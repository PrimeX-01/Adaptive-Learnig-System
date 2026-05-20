from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
from db.database import SessionLocal
from db.models import ReviewSchedule, TopicMastery, Student
from services.style_service import run_detection_for_all_subjects   # <-- add this import
import logging

logger = logging.getLogger(__name__)

EASE_FACTOR  = 2.5
MAX_INTERVAL = 180

def update_review_schedules():
    db = SessionLocal()
    try:
        today = date.today()
        due   = db.query(ReviewSchedule).filter(ReviewSchedule.next_review_date<=today).all()
        for r in due:
            mastery = db.query(TopicMastery).filter(
                TopicMastery.student_id==r.student_id,
                TopicMastery.subject_id==r.subject_id,
                TopicMastery.topic_id==r.topic_id).first()
            new_interval = (min(int(r.interval_days*EASE_FACTOR), MAX_INTERVAL)
                            if mastery and mastery.mastery_prob >= 0.70 else 1)
            r.repetition_count += 1
            r.interval_days     = new_interval
            r.next_review_date  = today + timedelta(days=new_interval)
        db.commit()
        logger.info(f'[Scheduler] Updated {len(due)} review schedules.')
    except Exception as e:
        logger.error(f'[Scheduler] Review update error: {e}')
    finally:
        db.close()

# ── NEW: Adaptive style detection ─────────────────────────────────
def detect_styles_for_all_students():
    """
    Run learning style detection for every student in the system.
    This is called weekly to identify changes in learning patterns.
    """
    db = SessionLocal()
    try:
        # Get all students who are not teachers
        students = db.query(Student).filter(Student.is_teacher == False).all()
        results = []
        for student in students:
            try:
                result = run_detection_for_all_subjects(student.id, db)
                results.append({'student_id': student.id, 'result': result})
            except Exception as e:
                logger.error(f'Style detection failed for student {student.id}: {e}')
        logger.info(f'[Scheduler] Style detection completed for {len(students)} students.')
        return results
    finally:
        db.close()

def schedule_mastered_topic(student_id, subject_id, topic_id, db):
    if not db.query(ReviewSchedule).filter(
            ReviewSchedule.student_id==student_id,
            ReviewSchedule.subject_id==subject_id,
            ReviewSchedule.topic_id==topic_id).first():
        db.add(ReviewSchedule(student_id=student_id, subject_id=subject_id,
                               topic_id=topic_id,
                               next_review_date=date.today()+timedelta(days=1),
                               interval_days=1, repetition_count=0))
        db.commit()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Existing review schedule job (daily at 2:00 AM)
    scheduler.add_job(update_review_schedules,
                       trigger=CronTrigger(hour=2, minute=0),
                       id='update_reviews', replace_existing=True)
    # NEW: Weekly style detection job (Sundays at 3:00 AM)
    scheduler.add_job(detect_styles_for_all_students,
                       trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
                       id='detect_styles', replace_existing=True)
    scheduler.start()
    logger.info('[Scheduler] Background scheduler started (reviews daily, style detection weekly).')
    return scheduler