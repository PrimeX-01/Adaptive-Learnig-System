# backend/services/style_service.py
"""
Style detection and personalisation service.
Works with the actual schema (models.py) – no StudentPreference, uses
Student.learning_style and VarkScore, supports school/tertiary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy.orm import Session

from db.models import (
    Student,
    Subject,
    Course,
    StudentSubjectStyle,
    StyleInteraction,
    Notification,
    ClassSubject,
    StudentClassEnrollment,
    StudentCourseEnrollment,
    VarkScore,
)
from db.database import SessionLocal

logger = logging.getLogger(__name__)

# ── Style constants ───────────────────────────────────────────────
VALID_STYLES = {"visual", "auditory", "reading", "kinesthetic"}

# ── VARK constants (unchanged) ────────────────────────────────────
SOURCE_WEIGHTS = {
    'audio_button':   3,
    'quiz':           2,
    'library':        2,
    'tutor_keyword':  1,
    'hint':           1,
    'manual':         4,
}

REGISTRATION_SEEDS = {
    'visual':      {'v': 55, 'a': 15, 'r': 20, 'k': 10},
    'auditory':    {'v': 10, 'a': 55, 'r': 20, 'k': 15},
    'reading':     {'v': 15, 'a': 10, 'r': 60, 'k': 15},
    'kinesthetic': {'v': 10, 'a': 15, 'r': 15, 'k': 60},
}

DEFAULT_SEED = {'v': 25, 'a': 25, 'r': 25, 'k': 25}

MODALITY_TO_KEY = {
    'visual':      'v',
    'auditory':    'a',
    'reading':     'r',
    'kinesthetic': 'k',
}

KEYWORD_SIGNALS = {
    'visual': [
        'show me', 'show me a', 'image', 'diagram', 'draw', 'chart',
        'visualise', 'visualize', 'picture', 'graph', 'illustration',
        'map', 'flowchart', 'sketch', 'what does it look like',
        'can you draw', 'generate an image', 'show a picture',
    ],
    'auditory': [
        'explain out loud', 'read to me', 'read it to me', 'listen',
        'say it', 'tell me', 'speak', 'can you say', 'narrate',
        'audio', 'hear', 'sound',
    ],
    'reading': [
        'write it', 'write out', 'notes', 'explain in detail',
        'step by step', 'step-by-step', 'summarise', 'summarize',
        'list the', 'give me a list', 'in writing', 'detailed explanation',
        'break it down', 'written',
    ],
    'kinesthetic': [
        'example', 'real life', 'real-life', 'how would i use',
        'how do i apply', 'practice', 'practise', 'try it',
        'let me try', 'hands on', 'hands-on', 'exercise',
        'apply this', 'application', 'in real life', 'show me how to do',
        'work through', 'can we do',
    ],
}


# ── Helpers ───────────────────────────────────────────────────────

def _get_global_style(student: Student) -> str:
    return student.learning_style or 'reading'


def _get_enrolled_subjects(db: Session, student_id: int) -> List[int]:
    """Return a list of subject_ids for a school student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.student_type != 'school':
        return []

    # Get all classes the student is enrolled in (via StudentClassEnrollment)
    enrollments = db.query(StudentClassEnrollment).filter(
        StudentClassEnrollment.student_id == student_id
    ).all()
    class_ids = [e.class_id for e in enrollments]
    if not class_ids:
        return []

    class_subjects = db.query(ClassSubject).filter(
        ClassSubject.class_id.in_(class_ids)
    ).all()
    return list({cs.subject_id for cs in class_subjects})


def _get_enrolled_courses(db: Session, student_id: int) -> List[int]:
    """Return a list of course_ids for a tertiary student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.student_type != 'tertiary':
        return []

    enrollments = db.query(StudentCourseEnrollment).filter(
        StudentCourseEnrollment.student_id == student_id
    ).all()
    # pcl_id links to ProgrammeCourseLevel which has course_id
    pcl_ids = [e.pcl_id for e in enrollments]
    if not pcl_ids:
        return []
    from db.models import ProgrammeCourseLevel  # local import to avoid circular
    pcls = db.query(ProgrammeCourseLevel).filter(
        ProgrammeCourseLevel.id.in_(pcl_ids)
    ).all()
    return list({pcl.course_id for pcl in pcls})


# ══════════════════════════════════════════════════════════════════
#  VARK COMPUTATION & STORAGE
# ══════════════════════════════════════════════════════════════════

def compute_vark_from_interactions(student_id: int, db: Session) -> dict:
    since = datetime.utcnow() - timedelta(days=90)
    interactions = db.query(StyleInteraction).filter(
        StyleInteraction.student_id == student_id,
        StyleInteraction.created_at >= since,
    ).all()

    counts = {'v': 0.0, 'a': 0.0, 'r': 0.0, 'k': 0.0}
    total_weight = 0.0

    for ix in interactions:
        key = MODALITY_TO_KEY.get(ix.modality)
        if not key:
            continue
        w = SOURCE_WEIGHTS.get(ix.source, 1)
        counts[key] += w
        total_weight += w

    student = db.query(Student).filter(Student.id == student_id).first()
    dominant = _get_global_style(student) if student else 'reading'
    seed = REGISTRATION_SEEDS.get(dominant, DEFAULT_SEED)

    seed_weight = max(0.0, 1.0 - total_weight / 50.0)
    behaviour_weight = 1.0 - seed_weight

    if total_weight > 0:
        behaviour = {k: (counts[k] / total_weight) * 100 for k in counts}
    else:
        behaviour = DEFAULT_SEED.copy()

    blended = {
        k: seed[k] * seed_weight + behaviour[k] * behaviour_weight
        for k in ('v', 'a', 'r', 'k')
    }

    total = sum(blended.values())
    if total > 0:
        blended = {k: round((v / total) * 100, 1) for k, v in blended.items()}

    return {
        'v': blended['v'],
        'a': blended['a'],
        'r': blended['r'],
        'k': blended['k'],
        'total_interactions': int(total_weight),
        'dominant': max(blended, key=blended.get),
    }


def update_vark_scores(student_id: int, db: Session) -> dict:
    scores = compute_vark_from_interactions(student_id, db)
    record = db.query(VarkScore).filter(VarkScore.student_id == student_id).first()
    if record:
        record.v_score = scores['v']
        record.a_score = scores['a']
        record.r_score = scores['r']
        record.k_score = scores['k']
        record.total_interactions = scores['total_interactions']
        record.last_computed = datetime.utcnow()
    else:
        db.add(VarkScore(
            student_id=student_id,
            v_score=scores['v'],
            a_score=scores['a'],
            r_score=scores['r'],
            k_score=scores['k'],
            total_interactions=scores['total_interactions'],
        ))
    db.commit()
    return scores


def get_vark_scores(student_id: int, db: Session) -> dict:
    record = db.query(VarkScore).filter(VarkScore.student_id == student_id).first()
    if record:
        return {
            'v': record.v_score,
            'a': record.a_score,
            'r': record.r_score,
            'k': record.k_score,
            'total_interactions': record.total_interactions,
            'dominant': max(
                {'v': record.v_score, 'a': record.a_score,
                 'r': record.r_score, 'k': record.k_score},
                key=lambda x: {'v': record.v_score, 'a': record.a_score,
                                'r': record.r_score, 'k': record.k_score}[x]
            ),
        }
    return update_vark_scores(student_id, db)


def seed_vark_from_registration(student_id: int, dominant_style: str, db: Session):
    seed = REGISTRATION_SEEDS.get(dominant_style, DEFAULT_SEED)
    existing = db.query(VarkScore).filter(VarkScore.student_id == student_id).first()
    if existing:
        return
    db.add(VarkScore(
        student_id=student_id,
        v_score=seed['v'],
        a_score=seed['a'],
        r_score=seed['r'],
        k_score=seed['k'],
        total_interactions=0,
    ))
    db.commit()


def build_vark_prompt_fragment(scores: dict) -> str:
    label_map = {'v': 'Visual', 'a': 'Auditory', 'r': 'Reading/Writing', 'k': 'Kinesthetic'}
    instruction_map = {
        'v': 'Use diagrams, spatial layouts, and visual structure. '
             'Suggest [IMAGE: ...] placeholders when explaining processes.',
        'a': 'Write in a conversational, spoken tone. Short sentences. Suitable for listening.',
        'r': 'Provide structured written explanations with clear headings, '
             'bullet points, and step-by-step reasoning.',
        'k': 'Include hands-on examples, try-it-yourself problems, '
             'and real-world applications the student can act on.',
    }
    sorted_scores = sorted(
        [('v', scores.get('v', 25)), ('a', scores.get('a', 25)),
         ('r', scores.get('r', 25)), ('k', scores.get('k', 25))],
        key=lambda x: x[1], reverse=True
    )
    score_line = ', '.join(f"{label_map[k]} {round(v)}%" for k, v in sorted_scores)
    primary_key = sorted_scores[0][0]
    secondary_key = sorted_scores[1][0]
    instruction = f"{instruction_map[primary_key]} Secondary preference: {instruction_map[secondary_key]}"
    evidence_note = ''
    if scores.get('total_interactions', 0) < 10:
        evidence_note = ' (Profile based on limited data — will refine as the student interacts more.)'
    return f"LEARNING PROFILE: {score_line}.{evidence_note} {instruction}"


# ══════════════════════════════════════════════════════════════════
#  STYLE GET / SET (compatible with router)
# ══════════════════════════════════════════════════════════════════

def get_student_style(student_id: int, db: Session) -> str:
    student = db.query(Student).filter(Student.id == student_id).first()
    return _get_global_style(student) if student else 'reading'


def get_subject_style(student_id: int, subject_id: int, db: Session,
                      course_id: Optional[int] = None) -> str:
    # First check a specific override for this subject (or course)
    if course_id is not None:
        record = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id,
            StudentSubjectStyle.course_id == course_id,
        ).first()
    else:
        record = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id,
            StudentSubjectStyle.subject_id == subject_id,
        ).first()
    if record and record.learning_style:
        return record.learning_style
    return get_student_style(student_id, db)


def get_all_subject_styles(student_id: int, db: Session) -> list:
    """
    Return a list of dicts with subject_name, code, style, etc.
    For school students only; returns [] for tertiary (frontend may not call this yet).
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.student_type != 'school':
        return []

    subject_ids = _get_enrolled_subjects(db, student_id)
    results = []
    for subj_id in subject_ids:
        subj = db.query(Subject).filter(Subject.id == subj_id).first()
        if not subj:
            continue
        record = db.query(StudentSubjectStyle).filter(
            StudentSubjectStyle.student_id == student_id,
            StudentSubjectStyle.subject_id == subj_id,
        ).first()
        style = record.learning_style if record else get_student_style(student_id, db)
        results.append({
            'subject_id': subj_id,
            'subject_name': subj.name,
            'subject_code': subj.code,
            'learning_style': style,
            'confidence': record.confidence if record else 0.5,
            'auto_detected': record.auto_detected if record else False,
        })
    return results


def set_subject_style(student_id: int, subject_id: int,
                      style: str, auto_detected: bool = False,
                      confidence: float = 1.0, db: Session = None):
    if style not in VALID_STYLES:
        style = 'reading'
    record = db.query(StudentSubjectStyle).filter(
        StudentSubjectStyle.student_id == student_id,
        StudentSubjectStyle.subject_id == subject_id,
    ).first()
    if record:
        record.learning_style = style
        record.confidence = confidence
        record.auto_detected = auto_detected
        record.updated_at = datetime.utcnow()
    else:
        db.add(StudentSubjectStyle(
            student_id=student_id,
            subject_id=subject_id,
            learning_style=style,
            confidence=confidence,
            auto_detected=auto_detected,
        ))
    db.commit()
    # Also log as a manual interaction
    log_interaction(student_id, subject_id, style, 'manual', db)


def set_overall_style(student_id: int, style: str, db: Session):
    if style not in VALID_STYLES:
        style = 'reading'
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.learning_style = style
        db.commit()


# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════

def log_interaction(student_id: int, subject_id: int,
                    modality: str, source: str, db: Session):
    if modality not in VALID_STYLES:
        return
    db.add(StyleInteraction(
        student_id=student_id,
        subject_id=subject_id,
        modality=modality,
        source=source,
    ))


def log_interaction_and_commit(student_id: int, subject_id: int,
                               modality: str, source: str, db: Session):
    log_interaction(student_id, subject_id, modality, source, db)
    db.commit()


def infer_modality_from_style(learning_style: str) -> str:
    return learning_style if learning_style in VALID_STYLES else 'reading'


# ══════════════════════════════════════════════════════════════════
#  KEYWORD DETECTION
# ══════════════════════════════════════════════════════════════════

def detect_modality_from_text(text: str) -> Optional[str]:
    lower = text.lower()
    hits = {'visual': 0, 'auditory': 0, 'reading': 0, 'kinesthetic': 0}
    for modality, keywords in KEYWORD_SIGNALS.items():
        for kw in keywords:
            if kw in lower:
                hits[modality] += 1
    max_hits = max(hits.values())
    if max_hits == 0:
        return None
    return max(hits, key=hits.get)


# ══════════════════════════════════════════════════════════════════
#  ADAPTIVE DETECTION
# ══════════════════════════════════════════════════════════════════

def detect_and_update_style(student_id: int, subject_id: int,
                            db: Session, min_interactions: int = 20) -> dict:
    since = datetime.utcnow() - timedelta(days=60)
    interactions = db.query(StyleInteraction).filter(
        StyleInteraction.student_id == student_id,
        StyleInteraction.subject_id == subject_id,
        StyleInteraction.created_at >= since,
    ).all()

    if len(interactions) < min_interactions:
        return {
            'detected': False,
            'reason': f'Only {len(interactions)} interactions — need {min_interactions}',
        }

    counts = {'visual': 0, 'auditory': 0, 'reading': 0, 'kinesthetic': 0}
    for i in interactions:
        if i.modality in counts:
            counts[i.modality] += 1

    total = sum(counts.values()) or 1
    dominant = max(counts, key=counts.get)
    confidence = round(counts[dominant] / total, 2)
    current = get_subject_style(student_id, subject_id, db)

    if dominant == current:
        return {'detected': True, 'dominant': dominant,
                'confidence': confidence, 'changed': False}

    if confidence < 0.45:
        return {'detected': True, 'dominant': dominant, 'confidence': confidence,
                'changed': False, 'reason': 'Confidence too low to update'}

    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    subj_name = subj.name if subj else 'this subject'

    set_subject_style(student_id, subject_id, dominant,
                      auto_detected=True, confidence=confidence, db=db)

    style_labels = {
        'visual': 'Visual', 'auditory': 'Auditory',
        'reading': 'Reading/Writing', 'kinesthetic': 'Kinesthetic',
    }
    db.add(Notification(
        receiver_type='student',      # matches new Notification columns
        receiver_id=student_id,
        sender_type='system',
        type='style_detected',
        title=f'Learning pattern detected in {subj_name}',
        body=(
            f'Based on your recent activity, SiveAdapt has noticed you tend to learn '
            f'{subj_name} best as a {style_labels.get(dominant, dominant)} learner. '
            f'Your content for this subject has been updated to match. '
            f'You can change this anytime from your profile.'
        ),
        action_url='/profile',
    ))
    db.commit()

    return {
        'detected': True,
        'dominant': dominant,
        'confidence': confidence,
        'changed': True,
        'old_style': current,
        'new_style': dominant,
    }


def run_detection_for_all_subjects(student_id: int, db: Session) -> list:
    """Run detection for every subject the school student is enrolled in."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.student_type != 'school':
        return []

    subject_ids = _get_enrolled_subjects(db, student_id)
    results = []
    for subj_id in subject_ids:
        result = detect_and_update_style(student_id, subj_id, db)
        results.append({'subject_id': subj_id, **result})
    return results