from sqlalchemy.orm import Session
from db.models import Assessment

def compute_hint_density(student_id, topic_id, db, window=5) -> float:
    recent = db.query(Assessment).filter(
        Assessment.student_id==student_id, Assessment.topic_id==topic_id
    ).order_by(Assessment.created_at.desc()).limit(window).all()
    if not recent: return 0.0
    return sum(a.hints_used for a in recent) / len(recent)

def compute_recent_accuracy(student_id, topic_id, db, window=5) -> float:
    recent = db.query(Assessment).filter(
        Assessment.student_id==student_id, Assessment.topic_id==topic_id
    ).order_by(Assessment.created_at.desc()).limit(window).all()
    if not recent: return 0.5
    return sum(1 for a in recent if a.is_correct) / len(recent)

def decide_adaptation(student_id, topic_id, current_fcl, bkt_result, db) -> dict:
    hint_density   = compute_hint_density(student_id, topic_id, db)
    accuracy       = compute_recent_accuracy(student_id, topic_id, db)
    newly_mastered = bkt_result.get('newly_mastered', False)
    mastery_level  = bkt_result.get('mastery_level', 'developing')
    if newly_mastered and hint_density < 1.0:
        decision, new_fcl = 'advance_level',    min(current_fcl + 1, 13)
    elif mastery_level == 'struggling' or accuracy < 0.40:
        decision, new_fcl = 'reduce_difficulty', max(current_fcl - 1, 1)
    elif hint_density > 2.0:
        decision, new_fcl = 'retreat_sublevel',  max(current_fcl - 1, 1)
    else:
        decision, new_fcl = 'maintain',          current_fcl
    return {'adaptation_decision': decision, 'new_fcl': new_fcl,
            'fcl_changed': new_fcl != current_fcl,
            'hint_density': hint_density, 'accuracy': accuracy}
