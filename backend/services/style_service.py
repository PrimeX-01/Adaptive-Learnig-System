from sqlalchemy.orm import Session
from db.models import (StudentSubjectStyle, StyleInteraction,
                        StudentSubject, Subject, Notification, Student,
                        StudentPreference)
from datetime import datetime, timedelta


# ══════════════════════════════════════════════════════════════════
#  GET / SET STYLE
# ══════════════════════════════════════════════════════════════════

def get_student_style(student_id: int, db: Session) -> str:
    """Get student's overall preferred learning style."""
    pref = db.query(StudentPreference).filter(
        StudentPreference.student_id == student_id
    ).first()
    return pref.preferred_learning_style if pref else 'reading'


def get_subject_style(student_id: int, subject_id: int, db: Session) -> str:
    """
    Get learning style for a specific subject.
    Falls back to overall style if no subject-specific style set.
    """
    record = db.query(StudentSubjectStyle).filter(
        StudentSubjectStyle.student_id == student_id,
        StudentSubjectStyle.subject_id == subject_id,
    ).first()
    if record:
        return record.learning_style
    return get_student_style(student_id, db)


def get_all_subject_styles(student_id: int, db: Session) -> list:
    """
    Get learning styles for all enrolled subjects.
    Used by dashboard personalization panel.
    """
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()

    result = []
    for e in enrollments:
        record = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id,
            StudentSubjectStyle.subject_id == e.subject_id,
        ).first()

        subj = db.query(Subject).filter(Subject.id == e.subject_id).first()
        result.append({
            'subject_id':    e.subject_id,
            'subject_name':  subj.name if subj else '—',
            'subject_code':  subj.code if subj else '—',
            'learning_style': record.learning_style if record else get_student_style(student_id, db),
            'confidence':    record.confidence if record else 0.5,
            'auto_detected': record.auto_detected if record else False,
        })
    return result


def set_subject_style(student_id: int, subject_id: int,
                       style: str, auto_detected: bool = False,
                       confidence: float = 1.0, db: Session = None):
    """Set or update the learning style for a subject. Commits."""
    VALID_STYLES = {'visual', 'auditory', 'reading', 'kinesthetic'}
    if style not in VALID_STYLES:
        style = 'reading'

    record = db.query(StudentSubjectStyle).filter(
        StudentSubjectStyle.student_id == student_id,
        StudentSubjectStyle.subject_id == subject_id,
    ).first()

    if record:
        record.learning_style = style
        record.confidence     = confidence
        record.auto_detected  = auto_detected
        record.updated_at     = datetime.utcnow()
    else:
        db.add(StudentSubjectStyle(
            student_id    = student_id,
            subject_id    = subject_id,
            learning_style= style,
            confidence    = confidence,
            auto_detected = auto_detected,
        ))
    db.commit()


def set_overall_style(student_id: int, style: str, db: Session):
    """Update the student's overall preferred learning style."""
    VALID_STYLES = {'visual', 'auditory', 'reading', 'kinesthetic'}
    if style not in VALID_STYLES:
        style = 'reading'

    pref = db.query(StudentPreference).filter(
        StudentPreference.student_id == student_id
    ).first()
    if pref:
        pref.preferred_learning_style = style
    else:
        db.add(StudentPreference(
            student_id             = student_id,
            preferred_learning_style= style,
        ))
    db.commit()


# ══════════════════════════════════════════════════════════════════
#  LOG INTERACTIONS
# ══════════════════════════════════════════════════════════════════

def log_interaction(student_id: int, subject_id: int,
                     modality: str, source: str, db: Session):
    """
    Log a single learning modality interaction.
    source: 'quiz' | 'tutor' | 'library' | 'hint'
    modality: 'visual' | 'auditory' | 'reading' | 'kinesthetic'
    Does NOT commit — caller must commit.
    """
    VALID = {'visual', 'auditory', 'reading', 'kinesthetic'}
    if modality not in VALID:
        return
    db.add(StyleInteraction(
        student_id = student_id,
        subject_id = subject_id,
        modality   = modality,
        source     = source,
    ))


def infer_modality_from_style(learning_style: str) -> str:
    """Map a learning style to an interaction modality."""
    return {
        'visual':      'visual',
        'auditory':    'auditory',
        'reading':     'reading',
        'kinesthetic': 'kinesthetic',
    }.get(learning_style, 'reading')


# ══════════════════════════════════════════════════════════════════
#  ADAPTIVE DETECTION
# ══════════════════════════════════════════════════════════════════

def detect_and_update_style(student_id: int, subject_id: int,
                              db: Session, min_interactions: int = 20) -> dict:
    """
    Analyse interaction log for a subject and detect dominant style.
    If different from current with ≥50% confidence, notify student.
    Returns detection result dict.
    """
    # Only look at last 60 days of interactions
    since = datetime.utcnow() - timedelta(days=60)
    interactions = db.query(StyleInteraction).filter(
        StyleInteraction.student_id == student_id,
        StyleInteraction.subject_id == subject_id,
        StyleInteraction.created_at >= since,
    ).all()

    if len(interactions) < min_interactions:
        return {
            'detected': False,
            'reason':   f'Only {len(interactions)} interactions — need {min_interactions}',
        }

    # Count modalities
    counts = {'visual': 0, 'auditory': 0, 'reading': 0, 'kinesthetic': 0}
    for i in interactions:
        if i.modality in counts:
            counts[i.modality] += 1

    total      = sum(counts.values()) or 1
    dominant   = max(counts, key=counts.get)
    confidence = round(counts[dominant] / total, 2)

    # Get current style
    current = get_subject_style(student_id, subject_id, db)

    if dominant == current:
        return {'detected': True, 'dominant': dominant, 'confidence': confidence, 'changed': False}

    if confidence < 0.45:
        return {'detected': True, 'dominant': dominant, 'confidence': confidence, 'changed': False,
                'reason': 'Confidence too low to update'}

    # Get subject name for notification
    subj    = db.query(Subject).filter(Subject.id == subject_id).first()
    student = db.query(Student).filter(Student.id == student_id).first()
    subj_name  = subj.name    if subj    else 'this subject'
    stud_name  = student.name if student else 'Student'

    # Update style
    set_subject_style(student_id, subject_id, dominant,
                      auto_detected=True, confidence=confidence, db=db)

    # Notify student
    style_labels = {'visual':'Visual','auditory':'Auditory','reading':'Reading/Writing','kinesthetic':'Kinesthetic'}
    db.add(Notification(
        student_id = student_id,
        type       = 'style_detected',
        title      = f'🎯 New learning pattern detected in {subj_name}',
        body       = (
            f'Based on your recent activity, SiveAdapt has noticed you tend to learn '
            f'{subj_name} best as a {style_labels.get(dominant, dominant)} learner. '
            f'Your content for this subject has been updated to match. '
            f'You can change this anytime from your profile.'
        ),
        action_url = '/profile',
    ))
    db.commit()

    return {
        'detected':    True,
        'dominant':    dominant,
        'confidence':  confidence,
        'changed':     True,
        'old_style':   current,
        'new_style':   dominant,
    }


def run_detection_for_all_subjects(student_id: int, db: Session) -> list:
    """
    Run adaptive style detection across all enrolled subjects.
    Called by a scheduler or manually from the style router.
    """
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id
    ).all()

    results = []
    for e in enrollments:
        result = detect_and_update_style(student_id, e.subject_id, db)
        results.append({'subject_id': e.subject_id, **result})

    return results