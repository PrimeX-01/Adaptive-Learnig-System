from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
from db.database import SessionLocal
from db.models import ReviewSchedule, TopicMastery, Student
from services.style_service import run_detection_for_all_subjects, update_vark_scores
import logging

logger = logging.getLogger(__name__)

EASE_FACTOR  = 2.5
MAX_INTERVAL = 180


# ══════════════════════════════════════════════════════════════════
#  SPACED REPETITION — runs daily at 02:00
# ══════════════════════════════════════════════════════════════════

def update_review_schedules():
    db = SessionLocal()
    try:
        today = date.today()
        due   = db.query(ReviewSchedule).filter(ReviewSchedule.next_review_date <= today).all()
        for r in due:
            mastery = db.query(TopicMastery).filter(
                TopicMastery.student_id == r.student_id,
                TopicMastery.subject_id == r.subject_id,
                TopicMastery.topic_id   == r.topic_id,
            ).first()
            new_interval = (
                min(int(r.interval_days * EASE_FACTOR), MAX_INTERVAL)
                if mastery and mastery.mastery_prob >= 0.70 else 1
            )
            r.repetition_count += 1
            r.interval_days     = new_interval
            r.next_review_date  = today + timedelta(days=new_interval)
        db.commit()
        logger.info(f'[Scheduler] Updated {len(due)} review schedules.')
    except Exception as e:
        logger.error(f'[Scheduler] Review update error: {e}')
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════
#  STYLE DETECTION — runs every Sunday at 03:00
# ══════════════════════════════════════════════════════════════════

def detect_styles_for_all_students():
    """
    Run per-subject dominant style detection for every student.
    Updates student_subject_style rows when a new dominant style
    is detected with sufficient confidence.
    """
    db = SessionLocal()
    try:
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


# ══════════════════════════════════════════════════════════════════
#  VARK RECOMPUTE — runs every Sunday at 04:00
# ══════════════════════════════════════════════════════════════════

def recompute_vark_for_all_students():
    """
    Recompute the four-dimensional VARK profile (v, a, r, k scores) for
    every student based on the last 90 days of style_interactions.

    This is the background half of the hybrid recompute strategy:
      - Background job   → updates stored vark_scores weekly (this function)
      - Live pull        → generate_explanation() fetches fresh scores if the
                           current session already has 5+ interactions

    Running weekly rather than daily is sufficient because VARK profiles
    shift slowly — the blend formula requires 50 weighted interactions to
    fully leave the registration self-report behind.
    """
    db = SessionLocal()
    updated = 0
    errors  = 0
    try:
        students = db.query(Student).filter(Student.is_teacher == False).all()
        for student in students:
            try:
                update_vark_scores(student.id, db)
                updated += 1
            except Exception as e:
                errors += 1
                logger.error(f'[Scheduler] VARK recompute failed for student {student.id}: {e}')
        logger.info(
            f'[Scheduler] VARK recompute complete — '
            f'{updated} updated, {errors} errors.'
        )
    except Exception as e:
        logger.error(f'[Scheduler] VARK recompute job error: {e}')
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════
#  HELPER — schedule mastered topic for spaced repetition
# ══════════════════════════════════════════════════════════════════

def schedule_mastered_topic(student_id, subject_id, topic_id, db):
    if not db.query(ReviewSchedule).filter(
            ReviewSchedule.student_id == student_id,
            ReviewSchedule.subject_id == subject_id,
            ReviewSchedule.topic_id   == topic_id,
    ).first():
        db.add(ReviewSchedule(
            student_id       = student_id,
            subject_id       = subject_id,
            topic_id         = topic_id,
            next_review_date = date.today() + timedelta(days=1),
            interval_days    = 1,
            repetition_count = 0,
        ))
        db.commit()


# ══════════════════════════════════════════════════════════════════
#  SCHEDULER STARTUP
# ══════════════════════════════════════════════════════════════════

def start_scheduler():
    scheduler = BackgroundScheduler()

    # Daily at 02:00 — spaced repetition
    scheduler.add_job(
        update_review_schedules,
        trigger=CronTrigger(hour=2, minute=0),
        id='update_reviews',
        replace_existing=True,
    )

    # Sunday 03:00 — per-subject dominant style detection
    scheduler.add_job(
        detect_styles_for_all_students,
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='detect_styles',
        replace_existing=True,
    )

    # Sunday 04:00 — four-dimensional VARK profile recompute
    scheduler.add_job(
        recompute_vark_for_all_students,
        trigger=CronTrigger(day_of_week='sun', hour=4, minute=0),
        id='recompute_vark',
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        '[Scheduler] Background scheduler started — '
        'reviews daily 02:00, style detection Sun 03:00, '
        'VARK recompute Sun 04:00.'
    )
    return scheduler