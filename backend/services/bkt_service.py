from sqlalchemy.orm import Session
from db.models import TopicMastery
from datetime import datetime

def bkt_update(p_learned, p_transit, p_guess, p_slip, is_correct) -> float:
    p_obs_L  = (1 - p_slip) if is_correct else p_slip
    p_obs_nL = p_guess      if is_correct else (1 - p_guess)
    denom    = p_obs_L * p_learned + p_obs_nL * (1 - p_learned)
    if denom == 0: return p_learned
    p_L_obs = (p_obs_L * p_learned) / denom
    return p_L_obs + (1 - p_L_obs) * p_transit

def update_mastery(student_id: int, subject_id: int, topic_id: str,
                    is_correct: bool, db: Session, bkt_config: dict) -> dict:
    config = bkt_config.get(topic_id, {
        'prior': 0.15, 'learns': 0.30, 'guesses': 0.20,
        'slips': 0.10, 'mastery_threshold': 0.95,
    })
    mastery = db.query(TopicMastery).filter(
        TopicMastery.student_id == student_id,
        TopicMastery.subject_id == subject_id,  # <-- subject-scoped
        TopicMastery.topic_id   == topic_id,
    ).first()
    if not mastery:
        mastery = TopicMastery(student_id=student_id, subject_id=subject_id,
                               topic_id=topic_id, mastery_prob=config['prior'],
                               mastery_level='not_started')
        db.add(mastery); db.flush()
    old_prob = mastery.mastery_prob
    new_prob = bkt_update(old_prob, config['learns'], config['guesses'],
                          config['slips'], is_correct)
    mastery.mastery_prob  = new_prob
    mastery.last_assessed = datetime.utcnow()
    threshold = config.get('mastery_threshold', 0.95)
    mastery.mastery_level = ('mastered'    if new_prob >= threshold else
                             'in_progress' if new_prob >= 0.60 else
                             'struggling'  if new_prob <= 0.20 and old_prob <= 0.25
                             else 'developing')
    db.commit()
    return {'new_mastery_prob': new_prob, 'mastery_level': mastery.mastery_level,
            'newly_mastered': new_prob >= threshold and old_prob < threshold,
            'subject_id': subject_id}
