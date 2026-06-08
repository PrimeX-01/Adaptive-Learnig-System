from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from db.database import get_db
from db.models   import (Student, Subject, StudentSubject, Assessment,
                          Notification, StudentPreference)
from auth        import get_current_student

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class TopicCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class TopicUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    name:            Optional[str] = None
    username:        Optional[str] = None
    bio:             Optional[str] = None
    email:           Optional[str] = None
    profile_picture: Optional[str] = None

class GradeAssignmentRequest(BaseModel):
    teacher_id: int
    subject_id: int
    grade:      int

class DirectiveRequest(BaseModel):
    teacher_id: int
    student_id: Optional[int] = None
    subject_id: int
    grade_min:  Optional[int] = None
    grade_max:  Optional[int] = None
    directive:  str
    label:      Optional[str] = None

class DirectiveUpdateRequest(BaseModel):
    directive:  Optional[str]  = None
    label:      Optional[str]  = None
    is_active:  Optional[bool] = None

class AwardPointsRequest(BaseModel):
    student_id: int
    subject_id: int
    topic_id:   str
    points:     int
    reason:     str

class BulkTipRequest(BaseModel):
    student_ids: List[int]
    topic_id:    str
    custom_note: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  TOPIC MANAGEMENT
# ══════════════════════════════════════════════════════════════════

@router.get('/subjects/{subject_id}/topics')
def get_subject_topics(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher')
    topics = db.execute(text('''
        SELECT id, name, code, description, created_at
        FROM topics
        WHERE subject_id = :sid
        ORDER BY name
    '''), {'sid': subject_id}).fetchall()
    return [{'id': t[0], 'name': t[1], 'code': t[2], 'description': t[3], 'created_at': t[4].isoformat() if t[4] else None} for t in topics]

@router.post('/subjects/{subject_id}/topics')
def create_topic(
    subject_id: int,
    req: TopicCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher')
    assignment = db.execute(text('''
        SELECT id FROM teacher_grade_assignments
        WHERE teacher_id = :tid AND subject_id = :sid LIMIT 1
    '''), {'tid': current_user.id, 'sid': subject_id}).fetchone()
    if not assignment:
        raise HTTPException(403, 'You do not teach this subject')
    result = db.execute(text('''
        INSERT INTO topics (subject_id, teacher_id, name, code, description)
        VALUES (:sid, :tid, :name, :code, :desc)
        RETURNING id
    '''), {'sid': subject_id, 'tid': current_user.id, 'name': req.name, 'code': req.code, 'desc': req.description})
    db.commit()
    new_id = result.fetchone()[0]
    return {'id': new_id, 'name': req.name, 'code': req.code, 'description': req.description}

@router.patch('/topics/{topic_id}')
def update_topic(
    topic_id: int,
    req: TopicUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher')
    owner = db.execute(text('SELECT teacher_id FROM topics WHERE id = :tid'), {'tid': topic_id}).fetchone()
    if not owner or owner[0] != current_user.id:
        raise HTTPException(403, 'You do not own this topic')
    updates = []
    params = {'id': topic_id}
    if req.name is not None:
        updates.append('name = :name')
        params['name'] = req.name
    if req.code is not None:
        updates.append('code = :code')
        params['code'] = req.code
    if req.description is not None:
        updates.append('description = :desc')
        params['desc'] = req.description
    if updates:
        db.execute(text(f'UPDATE topics SET {", ".join(updates)} WHERE id = :id'), params)
        db.commit()
    return {'status': 'updated'}

@router.delete('/topics/{topic_id}')
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher')
    result = db.execute(text('DELETE FROM topics WHERE id = :id AND teacher_id = :tid RETURNING id'), {'id': topic_id, 'tid': current_user.id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, 'Topic not found or not owned by you')
    return {'status': 'deleted'}


# ══════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════

@router.get('/profile/{teacher_id}')
def get_teacher_profile(teacher_id: int,
                         db: Session = Depends(get_db),
                         current_user = Depends(get_current_student)):
    t = db.query(Student).filter(Student.id == teacher_id, Student.is_teacher == True).first()
    if not t:
        raise HTTPException(404, 'Teacher not found')
    return {
        'id':              t.id,
        'name':            t.name,
        'email':           t.email,
        'username':        getattr(t,'username',None),
        'bio':             getattr(t,'bio',None),
        'profile_picture': getattr(t,'profile_picture',None),
        'created_at':      t.created_at.isoformat() if hasattr(t,'created_at') and t.created_at else None,
    }

@router.patch('/profile/{teacher_id}')
def update_teacher_profile(teacher_id: int, req: ProfileUpdateRequest,
                             db: Session = Depends(get_db),
                             current_user = Depends(get_current_student)):
    t = db.query(Student).filter(Student.id == teacher_id).first()
    if not t:
        raise HTTPException(404, 'Teacher not found')
    if req.name            is not None: t.name             = req.name.strip()
    if req.email           is not None: t.email            = req.email.strip()
    if req.profile_picture is not None: t.profile_picture  = req.profile_picture
    try:
        if req.username is not None: t.username = req.username.strip()
        if req.bio      is not None: t.bio      = req.bio.strip()
    except Exception:
        pass
    db.commit()
    return {'message': 'Profile updated', 'name': t.name}


# ══════════════════════════════════════════════════════════════════
#  GRADE ASSIGNMENTS
# ══════════════════════════════════════════════════════════════════

@router.get('/grade-assignments/{teacher_id}')
def get_grade_assignments(teacher_id: int,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    rows = db.execute(text(
        'SELECT ga.id, ga.subject_id, s.name AS subject_name, s.code, ga.grade '
        'FROM teacher_grade_assignments ga '
        'JOIN subjects s ON s.id = ga.subject_id '
        'WHERE ga.teacher_id = :tid '
        'ORDER BY ga.grade, s.name'
    ), {'tid': teacher_id}).fetchall()
    return [
        { 'id':r[0], 'subject_id':r[1], 'subject_name':r[2],
          'subject_code':r[3], 'grade':r[4] }
        for r in rows
    ]

@router.post('/grade-assignments')
def add_grade_assignment(req: GradeAssignmentRequest,
                          db: Session = Depends(get_db),
                          current_user = Depends(get_current_student)):
    existing = db.execute(text(
        'SELECT id FROM teacher_grade_assignments '
        'WHERE teacher_id=:tid AND subject_id=:sid AND grade=:grade'
    ), {'tid':req.teacher_id, 'sid':req.subject_id, 'grade':req.grade}).fetchone()
    if existing:
        raise HTTPException(409, 'Assignment already exists')
    result = db.execute(text(
        'INSERT INTO teacher_grade_assignments (teacher_id, subject_id, grade) '
        'VALUES (:tid, :sid, :grade) RETURNING id'
    ), {'tid':req.teacher_id, 'sid':req.subject_id, 'grade':req.grade})
    db.commit()
    new_id = result.fetchone()[0]
    subj = db.query(Subject).filter(Subject.id == req.subject_id).first()
    return {
        'id': new_id,
        'subject_id': req.subject_id,
        'subject_name': subj.name if subj else '—',
        'subject_code': subj.code if subj else '—',
        'grade': req.grade,
    }

@router.delete('/grade-assignments/{assignment_id}')
def remove_grade_assignment(assignment_id: int,
                              db: Session = Depends(get_db),
                              current_user = Depends(get_current_student)):
    db.execute(text('DELETE FROM teacher_grade_assignments WHERE id=:id'), {'id': assignment_id})
    db.commit()
    return {'status': 'removed'}


# ══════════════════════════════════════════════════════════════════
#  AI DIRECTIVES
# ══════════════════════════════════════════════════════════════════

@router.post('/directive')
def create_directive(req: DirectiveRequest,
                     db: Session = Depends(get_db),
                     current_user = Depends(get_current_student)):
    if not req.directive.strip():
        raise HTTPException(400, 'Directive text is required')
    result = db.execute(text(
        'INSERT INTO teacher_ai_directives '
        '(teacher_id, student_id, subject_id, grade_min, grade_max, directive, label) '
        'VALUES (:tid, :sid, :subid, :gmin, :gmax, :dir, :lbl) RETURNING id'
    ), {
        'tid': req.teacher_id,
        'sid': req.student_id,
        'subid': req.subject_id,
        'gmin': req.grade_min,
        'gmax': req.grade_max,
        'dir': req.directive.strip(),
        'lbl': req.label,
    })
    db.commit()
    new_id = result.fetchone()[0]
    target = 'student-specific' if req.student_id else f'grade {req.grade_min}–{req.grade_max}'
    return {
        'id': new_id,
        'status': 'created',
        'target': target,
        'message': f'Directive will be applied to AI responses for this {target}',
    }

@router.get('/directives/{teacher_id}')
def list_directives(teacher_id: int,
                    db: Session = Depends(get_db),
                    current_user = Depends(get_current_student)):
    rows = db.execute(text(
        'SELECT d.id, d.student_id, st.name AS student_name, '
        'd.subject_id, s.name AS subject_name, '
        'd.grade_min, d.grade_max, d.directive, d.label, d.is_active, d.created_at '
        'FROM teacher_ai_directives d '
        'LEFT JOIN students st ON st.id = d.student_id '
        'LEFT JOIN subjects  s  ON s.id  = d.subject_id '
        'WHERE d.teacher_id = :tid '
        'ORDER BY d.created_at DESC'
    ), {'tid': teacher_id}).fetchall()
    return [{
        'id': r[0],
        'student_id': r[1],
        'student_name': r[2],
        'subject_id': r[3],
        'subject_name': r[4],
        'grade_min': r[5],
        'grade_max': r[6],
        'directive': r[7],
        'label': r[8],
        'is_active': r[9],
        'created_at': r[10].isoformat() if r[10] else None,
        'scope': f'Student: {r[2]}' if r[1] else f'Grade {r[5]}–{r[6]}',
    } for r in rows]

@router.patch('/directive/{directive_id}')
def update_directive(directive_id: int, req: DirectiveUpdateRequest,
                     db: Session = Depends(get_db),
                     current_user = Depends(get_current_student)):
    updates = []
    params = {'id': directive_id}
    if req.directive is not None: updates.append('directive=:dir'); params['dir'] = req.directive
    if req.label is not None: updates.append('label=:lbl'); params['lbl'] = req.label
    if req.is_active is not None: updates.append('is_active=:act'); params['act'] = req.is_active
    if not updates:
        raise HTTPException(400, 'Nothing to update')
    db.execute(text(f'UPDATE teacher_ai_directives SET {",".join(updates)} WHERE id=:id'), params)
    db.commit()
    return {'status': 'updated'}

@router.delete('/directive/{directive_id}')
def delete_directive(directive_id: int,
                     db: Session = Depends(get_db),
                     current_user = Depends(get_current_student)):
    db.execute(text('DELETE FROM teacher_ai_directives WHERE id=:id'), {'id': directive_id})
    db.commit()
    return {'status': 'deleted'}


# ══════════════════════════════════════════════════════════════════
#  AWARD POINTS
# ══════════════════════════════════════════════════════════════════

@router.post('/award-points')
def award_points(req: AwardPointsRequest,
                 db: Session = Depends(get_db),
                 current_user = Depends(get_current_student)):
    if req.points < 1:
        raise HTTPException(400, 'Points must be at least 1')
    if req.points > 500:
        raise HTTPException(400, 'Cannot award more than 500 points at once')
    from services.points_service import award_teacher_points
    teacher_id = int(current_user.id) if hasattr(current_user,'id') else current_user
    result = award_teacher_points(
        teacher_id = teacher_id,
        student_id = req.student_id,
        subject_id = req.subject_id,
        topic_id   = req.topic_id,
        points     = req.points,
        reason     = req.reason,
        db         = db,
    )
    student = db.query(Student).filter(Student.id == req.student_id).first()
    teacher = db.query(Student).filter(Student.id == teacher_id).first()
    if student:
        db.add(Notification(
            student_id = req.student_id,
            type       = 'points_awarded',
            title      = f'🎁 +{req.points} points awarded by your teacher!',
            body       = (
                f'{teacher.name if teacher else "Your teacher"} awarded you {req.points} points '
                f'in {req.topic_id.replace("_"," ")}. Reason: {req.reason}'
            ),
            action_url = '/progress',
        ))
        db.commit()
    return {
        'status': 'awarded',
        'points_awarded': req.points,
        'new_topic_fcl': result.get('new_fcl'),
        'fcl_changed': result.get('fcl_changed', False),
    }


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD (CORRECTED – returns stats object)
# ══════════════════════════════════════════════════════════════════

@router.get('/dashboard/{teacher_id}')
def teacher_dashboard(teacher_id: int,
                       subject_code: Optional[str] = None,
                       grade_min: Optional[int] = None,
                       grade_max: Optional[int] = None,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    assignments = db.execute(text(
        'SELECT ga.subject_id, s.name, s.code, ga.grade '
        'FROM teacher_grade_assignments ga '
        'JOIN subjects s ON s.id = ga.subject_id '
        'WHERE ga.teacher_id = :tid'
    ), {'tid': teacher_id}).fetchall()
    teacher_subjects = [{'id':r[0], 'name':r[1], 'code':r[2], 'grade':r[3]} for r in assignments]
    if not teacher_subjects:
        rows = db.execute(text(
            'SELECT DISTINCT s.id, s.name, s.code FROM student_subjects ss '
            'JOIN subjects s ON s.id = ss.subject_id '
            'WHERE ss.teacher_id = :tid'
        ), {'tid': teacher_id}).fetchall()
        teacher_subjects = [{'id':r[0], 'name':r[1], 'code':r[2]} for r in rows]
    subject_ids = [s['id'] for s in teacher_subjects]
    if not subject_ids:
        return _empty_dashboard(teacher_subjects)
    if subject_code and subject_code != 'all':
        filtered = [s['id'] for s in teacher_subjects if s.get('code') == subject_code]
        if filtered:
            subject_ids = filtered
    grade_filter = ''
    grade_params = {}
    if grade_min is not None:
        grade_filter += ' AND st.grade >= :gmin '
        grade_params['gmin'] = grade_min
    if grade_max is not None:
        grade_filter += ' AND st.grade <= :gmax '
        grade_params['gmax'] = grade_max
    params = {'tids': tuple(subject_ids) if len(subject_ids) > 1 else (subject_ids[0],)}
    params.update(grade_params)
    students_raw = db.execute(text(f'''
        SELECT DISTINCT
            st.id AS student_id, st.name, st.grade,
            s.code AS subject_code, s.name AS subject_name, s.id AS subject_id,
            ss.teacher_id,
            COUNT(a.id) AS total_attempts,
            SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END) AS correct_count,
            AVG(CASE WHEN a.hints_used IS NOT NULL THEN a.hints_used ELSE 0 END) AS avg_hints,
            tf.current_fcl
        FROM students st
        JOIN student_subjects ss ON ss.student_id = st.id
        JOIN subjects s ON s.id = ss.subject_id
        LEFT JOIN assessments a ON a.student_id = st.id AND a.subject_id = s.id
        LEFT JOIN topic_fcl tf ON tf.student_id = st.id AND tf.subject_id = s.id
        WHERE ss.subject_id IN :tids
          AND ss.teacher_id = :tid
          {grade_filter}
        GROUP BY st.id, st.name, st.grade, s.code, s.name, s.id, ss.teacher_id, tf.current_fcl
    '''), {**params, 'tid': teacher_id}).fetchall()
    students = []
    at_risk = []
    fcl_sum = 0
    fcl_count = 0
    for r in students_raw:
        total = r[7] or 0
        correct = r[8] or 0
        accuracy = round(correct / total * 100) if total > 0 else 0
        avg_hints = round(float(r[9] or 0), 2)
        fcl = r[10] or 1
        fcl_sum += fcl
        fcl_count += 1
        is_at_risk = accuracy < 50 and total >= 5
        row = {
            'student_id': r[0], 'name': r[1], 'grade': r[2],
            'subject_code': r[3], 'subject_name': r[4], 'subject_id': r[5],
            'teacher_id': r[6],
            'total_attempts': total, 'accuracy': accuracy,
            'hint_density': avg_hints, 'fcl_level': fcl,
            'is_at_risk': is_at_risk,
            'risk_reason': 'Low accuracy' if is_at_risk else '',
        }
        students.append(row)
        if is_at_risk:
            at_risk.append(row)
    from collections import Counter
    fcl_buckets = {'FCL 1–5':0, 'FCL 6–10':0, 'FCL 11–15':0, 'FCL 16–20':0}
    for s in students:
        fcl = s['fcl_level']
        if fcl <= 5: fcl_buckets['FCL 1–5'] += 1
        elif fcl <= 10: fcl_buckets['FCL 6–10'] += 1
        elif fcl <= 15: fcl_buckets['FCL 11–15'] += 1
        else: fcl_buckets['FCL 16–20'] += 1
    fcl_distribution = [{'fcl_label': k, 'count': v} for k,v in fcl_buckets.items()]
    topic_rows = db.execute(text('''
        SELECT tf.topic_id, AVG(tf.current_fcl) AS avg_fcl, COUNT(*) AS student_count
        FROM topic_fcl tf
        WHERE tf.subject_id IN :sids
        GROUP BY tf.topic_id
        ORDER BY avg_fcl DESC
        LIMIT 10
    '''), {'sids': tuple(subject_ids) if len(subject_ids)>1 else (subject_ids[0],)}).fetchall()
    topic_fcl_distribution = [{
        'topic_fcl_label': r[0].replace('_',' ').split(' ')[-1].title(),
        'avg_fcl': round(float(r[1]),1),
        'count': r[2],
    } for r in topic_rows]

    total_students_count = len(set(s['student_id'] for s in students))
    avg_fcl = round(fcl_sum / fcl_count, 1) if fcl_count > 0 else 0

    return {
        'stats': {
            'total_students': total_students_count,
            'subjects_count': len(teacher_subjects),
            'avg_fcl': avg_fcl,
        },
        'teacher_subjects': teacher_subjects,
        'students': students,
        'at_risk': at_risk,
        'fcl_distribution': fcl_distribution,
        'topic_fcl_distribution': topic_fcl_distribution,
    }

def _empty_dashboard(teacher_subjects):
    return {
        'stats': {
            'total_students': 0,
            'subjects_count': len(teacher_subjects),
            'avg_fcl': 0,
        },
        'teacher_subjects': teacher_subjects,
        'students': [],
        'at_risk': [],
        'fcl_distribution': [],
        'topic_fcl_distribution': [],
    }


# ══════════════════════════════════════════════════════════════════
#  NEW: TOPIC DIFFICULTY HEATMAP
# ══════════════════════════════════════════════════════════════════

@router.get('/heatmap/{teacher_id}')
def get_topic_heatmap(teacher_id: int,
                       subject_id: Optional[int] = None,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    students = db.execute(text('''
        SELECT DISTINCT st.id, st.name, st.grade
        FROM student_subjects ss
        JOIN students st ON st.id = ss.student_id
        WHERE ss.teacher_id = :tid
    '''), {'tid': teacher_id}).fetchall()
    if not students:
        return {'students': [], 'topics': [], 'data': []}
    if subject_id:
        topics = db.execute(text('''
            SELECT DISTINCT topic_id
            FROM topic_fcl
            WHERE subject_id = :subid
        '''), {'subid': subject_id}).fetchall()
        subject_filter = f"AND tf.subject_id = {subject_id}"
    else:
        subj_ids = db.execute(text('''
            SELECT DISTINCT subject_id FROM teacher_grade_assignments WHERE teacher_id = :tid
        '''), {'tid': teacher_id}).fetchall()
        if not subj_ids:
            return {'students': [], 'topics': [], 'data': []}
        subj_list = ','.join(str(s[0]) for s in subj_ids)
        subject_filter = f"AND tf.subject_id IN ({subj_list})"
        topics = db.execute(text(f'''
            SELECT DISTINCT topic_id
            FROM topic_fcl
            WHERE subject_id IN ({subj_list})
        ''')).fetchall()
    topic_names = [t[0] for t in topics]
    if not topic_names:
        return {'students': [], 'topics': [], 'data': []}
    heatmap_data = []
    for stu in students:
        stu_id, stu_name, grade = stu
        row = {'student_id': stu_id, 'student_name': stu_name, 'grade': grade, 'topics': {}}
        for topic in topic_names:
            res = db.execute(text('''
                SELECT current_fcl FROM topic_fcl
                WHERE student_id = :sid AND topic_id = :tid
            '''), {'sid': stu_id, 'tid': topic}).fetchone()
            if res:
                fcl = res[0]
                if fcl <= 5:
                    mastery = 0
                elif fcl <= 10:
                    mastery = 1
                elif fcl <= 15:
                    mastery = 2
                else:
                    mastery = 3
            else:
                mastery = 0
            row['topics'][topic] = mastery
        heatmap_data.append(row)
    matrix = []
    for stu in heatmap_data:
        matrix.append([stu['topics'].get(t, 0) for t in topic_names])
    return {
        'students': [{'id': s[0], 'name': s[1], 'grade': s[2]} for s in students],
        'topics': topic_names,
        'data': matrix,
    }


# ══════════════════════════════════════════════════════════════════
#  NEW: ENGAGEMENT REPORT (inactive students)
# ══════════════════════════════════════════════════════════════════

@router.get('/engagement/{teacher_id}')
def get_engagement_report(teacher_id: int,
                           days_inactive: int = 7,
                           db: Session = Depends(get_db),
                           current_user = Depends(get_current_student)):
    cutoff = datetime.utcnow() - timedelta(days=days_inactive)
    students = db.execute(text('''
        SELECT DISTINCT st.id, st.name, st.grade, st.email
        FROM student_subjects ss
        JOIN students st ON st.id = ss.student_id
        WHERE ss.teacher_id = :tid
    '''), {'tid': teacher_id}).fetchall()
    if not students:
        return {'students': [], 'days_inactive': days_inactive}
    result = []
    for stu in students:
        stu_id, name, grade, email = stu
        last_assessment = db.execute(text('''
            SELECT MAX(created_at) FROM assessments WHERE student_id = :sid
        '''), {'sid': stu_id}).fetchone()[0]
        last_conversation = db.execute(text('''
            SELECT MAX(started_at) FROM conversation_sessions WHERE student_id = :sid
        '''), {'sid': stu_id}).fetchone()[0]
        last_activity = None
        if last_assessment and last_conversation:
            last_activity = max(last_assessment, last_conversation)
        elif last_assessment:
            last_activity = last_assessment
        elif last_conversation:
            last_activity = last_conversation
        if not last_activity:
            days = 999
        else:
            days = (datetime.utcnow() - last_activity).days
        if days >= days_inactive:
            result.append({
                'student_id': stu_id,
                'name': name,
                'grade': grade,
                'email': email,
                'days_inactive': days,
                'last_activity': last_activity.isoformat() if last_activity else None,
            })
    result.sort(key=lambda x: x['days_inactive'], reverse=True)
    return {
        'students': result,
        'days_inactive': days_inactive,
        'total_students': len(students),
    }


# ══════════════════════════════════════════════════════════════════
#  STUDENT DEEP-DIVE (unchanged)
# ══════════════════════════════════════════════════════════════════

@router.get('/student/{student_id}/deep-dive')
def student_deep_dive(student_id: int,
                       db: Session = Depends(get_db),
                       current_user = Depends(get_current_student)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')
    assessments = db.query(Assessment).filter(
        Assessment.student_id == student_id
    ).order_by(Assessment.created_at.desc()).limit(50).all()
    total = len(assessments)
    correct = sum(1 for a in assessments if a.is_correct)
    accuracy = round(correct/total*100) if total > 0 else 0
    avg_hints = round(sum(a.hints_used or 0 for a in assessments)/total, 2) if total > 0 else 0
    try:
        from services.llm_service import call_groq
        prompt = (
            f'Student profile: accuracy={accuracy}%, avg_hints_per_question={avg_hints}, '
            f'total_questions={total}. Grade: {student.grade}. '
            'In 2 sentences, give a specific teacher recommendation for this student. '
            'Be concrete and actionable.'
        )
        rec, _, _ = call_groq(
            model='llama-3.1-8b-instant',
            messages=[{'role':'user','content':prompt}],
            max_tokens=100,
        )
    except Exception:
        rec = f'Student has {accuracy}% accuracy. Consider reviewing weak topics with hints.'
    return {
        'student_id': student_id,
        'name': student.name,
        'grade': student.grade,
        'accuracy': accuracy,
        'avg_hint_density': avg_hints,
        'total_questions': total,
        'ai_recommendations': rec,
    }


# ══════════════════════════════════════════════════════════════════
#  BULK AI TIP (unchanged)
# ══════════════════════════════════════════════════════════════════

@router.post('/messages/bulk-tip')
def send_bulk_tip(req: BulkTipRequest,
                  db: Session = Depends(get_db),
                  current_user = Depends(get_current_student)):
    try:
        from services.llm_service import call_groq
        prompt = (
            f'Give a short (2–3 sentence) actionable study tip for a student '
            f'struggling with {req.topic_id.replace("_"," ")}. '
            + (f'Context: {req.custom_note}' if req.custom_note else '')
            + ' Be encouraging and specific.'
        )
        tip_text, _, _ = call_groq(
            model='llama-3.1-8b-instant',
            messages=[{'role':'user','content':prompt}],
            max_tokens=150,
        )
    except Exception:
        tip_text = f'Focus on practising {req.topic_id.replace("_"," ")} step by step.'
    topic_label = req.topic_id.replace('_',' ').title()
    for sid in req.student_ids:
        db.add(Notification(
            student_id = sid,
            type       = 'teacher_tip',
            title      = f'💡 Study tip for {topic_label}',
            body       = tip_text,
            action_url = f'/quiz?topic={req.topic_id}',
        ))
    db.commit()
    return {
        'status': 'sent',
        'recipients': len(req.student_ids),
        'tip_preview': tip_text[:120],
    }


# ══════════════════════════════════════════════════════════════════
#  SIMPLIFIED ENDPOINTS FOR THE TEACHER DASHBOARD (no teacher_id needed)
# ══════════════════════════════════════════════════════════════════

@router.get('/dashboard')
def teacher_dashboard_current(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher account')
    return teacher_dashboard(current_user.id, db=db, current_user=current_user)

@router.get('/students')
def get_my_students(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher account')
    rows = db.execute(text('''
        SELECT DISTINCT st.id, st.name, st.email, st.grade
        FROM student_subjects ss
        JOIN students st ON st.id = ss.student_id
        WHERE ss.teacher_id = :tid
        ORDER BY st.name
    '''), {'tid': current_user.id}).fetchall()
    return [
        {
            'id': r[0],
            'name': r[1],
            'email': r[2],
            'grade': r[3],
            'subject_ids': [],
        }
        for r in rows
    ]

@router.get('/students/struggling')
def get_struggling_students(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher account')
    student_ids = db.execute(text('''
        SELECT DISTINCT st.id
        FROM student_subjects ss
        JOIN students st ON st.id = ss.student_id
        WHERE ss.teacher_id = :tid
    '''), {'tid': current_user.id}).fetchall()
    if not student_ids:
        return []
    struggling = []
    for (sid,) in student_ids:
        total = db.execute(text('''
            SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM assessments WHERE student_id = :sid
        '''), {'sid': sid}).fetchone()
        total_count = total[0] or 0
        correct = total[1] or 0
        accuracy = round(correct / total_count * 100) if total_count > 0 else 0
        if total_count >= 5 and accuracy < 50:
            student = db.query(Student).filter(Student.id == sid).first()
            if student:
                fcl = db.execute(text('''
                    SELECT AVG(current_fcl) FROM topic_fcl WHERE student_id = :sid
                '''), {'sid': sid}).scalar() or 1
                struggling.append({
                    'id': sid,
                    'first_name': student.name.split()[0] if student.name else '',
                    'last_name': ' '.join(student.name.split()[1:]) if student.name else '',
                    'fcl_level': round(fcl),
                    'alert_reason': f'Accuracy {accuracy}% below 50%',
                    'is_struggling': True,
                })
    return struggling

@router.get('/directives')
def get_teacher_directives(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    if not current_user.is_teacher:
        raise HTTPException(403, 'Not a teacher account')
    rows = db.execute(text('''
        SELECT d.id, d.student_id, st.name as student_name,
               d.subject_id, s.name as subject_name,
               d.directive, d.label, d.is_active, d.created_at
        FROM teacher_ai_directives d
        LEFT JOIN students st ON st.id = d.student_id
        LEFT JOIN subjects s ON s.id = d.subject_id
        WHERE d.teacher_id = :tid
        ORDER BY d.created_at DESC
    '''), {'tid': current_user.id}).fetchall()
    return [
        {
            'id': r[0],
            'student_id': r[1],
            'student_name': r[2] if r[1] else 'All students',
            'subject_id': r[3],
            'subject_name': r[4] if r[3] else 'All subjects',
            'instruction': r[5],
            'label': r[6],
            'is_active': r[7],
            'created_at': r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]