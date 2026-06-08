from sqlalchemy.orm import Session
from db.models import TopicMastery
from datetime import datetime

def bkt_update(p_learned: float, p_transit: float, p_guess: float, p_slip: float, is_correct: bool) -> float:
    """
    Standard BKT update formula.
    p_learned: prior probability the student knows the skill.
    p_transit: probability of learning after an opportunity (default 0.3).
    p_guess:   probability of guessing correctly when not knowing.
    p_slip:    probability of making a mistake when knowing.
    """
    # Probability of observing the response given the state
    if is_correct:
        p_obs = p_learned * (1 - p_slip) + (1 - p_learned) * p_guess
        # Posterior after seeing correct
        p_learned_given_correct = (p_learned * (1 - p_slip)) / p_obs if p_obs > 0 else p_learned
    else:
        p_obs = p_learned * p_slip + (1 - p_learned) * (1 - p_guess)
        # Posterior after seeing incorrect
        p_learned_given_incorrect = (p_learned * p_slip) / p_obs if p_obs > 0 else p_learned

    # Apply learning transition: probability of knowing after the opportunity
    p_learned_next = p_learned_given_correct if is_correct else p_learned_given_incorrect
    p_learned_next = p_learned_next + (1 - p_learned_next) * p_transit
    return min(1.0, p_learned_next)


def update_mastery(student_id: int, subject_id: int, topic_id: str,
                    is_correct: bool, db: Session, bkt_config: dict) -> dict:
    """
    Update the student's mastery probability for a specific topic.
    """
    # Get or create the mastery record
    mastery = db.query(TopicMastery).filter(
        TopicMastery.student_id == student_id,
        TopicMastery.subject_id == subject_id,
        TopicMastery.topic_id == topic_id,
    ).first()

    # Default BKT parameters (can be overridden by config)
    config = bkt_config.get(topic_id, {
        'prior': 0.15,      # P(L0) – initial probability of knowing
        'learns': 0.30,     # P(T) – probability of learning after each opportunity
        'guesses': 0.20,    # P(G) – probability of guessing correctly when not knowing
        'slips': 0.10,      # P(S) – probability of slipping (incorrect when knowing)
        'mastery_threshold': 0.95,
    })

    prior = config.get('prior', 0.15)
    learns = config.get('learns', 0.30)
    guesses = config.get('guesses', 0.20)
    slips = config.get('slips', 0.10)

    if not mastery:
        # Create new mastery record with initial prior
        mastery = TopicMastery(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            mastery_prob=prior,
            mastery_level='not_started',
        )
        db.add(mastery)
        db.flush()
        old_prob = prior
    else:
        old_prob = mastery.mastery_prob

    # Update using BKT formula
    new_prob = bkt_update(old_prob, learns, guesses, slips, is_correct)
    mastery.mastery_prob = new_prob
    mastery.last_assessed = datetime.utcnow()

    # Determine mastery level
    threshold = config.get('mastery_threshold', 0.95)
    if new_prob >= threshold:
        mastery.mastery_level = 'mastered'
    elif new_prob >= 0.60:
        mastery.mastery_level = 'proficient'
    elif new_prob >= 0.30:
        mastery.mastery_level = 'developing'
    else:
        mastery.mastery_level = 'struggling'

    db.commit()

    return {
        'new_mastery_prob': new_prob,
        'mastery_level': mastery.mastery_level,
        'newly_mastered': new_prob >= threshold and old_prob < threshold,
        'subject_id': subject_id,
    }