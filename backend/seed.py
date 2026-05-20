from db.database import SessionLocal
from db.models import (Student, StudentPreference, StudentSubject, Subject,
                        TopicMastery, ContentItem)
from passlib.context import CryptContext

pwd = CryptContext(schemes=['bcrypt'])
db  = SessionLocal()

# ── Teachers (one per subject) ───────────────────────────────────────
teachers = [
  {'name':'Mr Dlamini (Maths)',    'email':'maths.teacher@test.com',   'subject':'MATH'},
  {'name':'Ms Mthembu (Science)',  'email':'science.teacher@test.com', 'subject':'SCI'},
  {'name':'Mr Zwane (English)',    'email':'english.teacher@test.com', 'subject':'ENG'},
  {'name':'Ms Shabangu (Social)',  'email':'social.teacher@test.com',  'subject':'SOC'},
]
teacher_objs = {}
for t in teachers:
    obj = Student(name=t['name'], email=t['email'],
                  password_hash=pwd.hash('TeacherPass123!'), is_teacher=True)
    db.add(obj); db.flush()
    teacher_objs[t['subject']] = obj

# ── 10 Test Students with multi-subject enrollment ───────────────────
students_data = [
  {'name':'Thabo Dlamini',   'email':'thabo@test.com',      'grade':8,  'subjects':['MATH','SCI']},
  {'name':'Nokwanda Nkosi',  'email':'nokwanda@test.com',   'grade':10, 'subjects':['MATH','ENG','SOC']},
  {'name':'Sipho Mthembu',   'email':'sipho@test.com',      'grade':7,  'subjects':['MATH','SCI']},
  {'name':'Lindiwe Zwane',   'email':'lindiwe@test.com',    'grade':11, 'subjects':['ENG','SOC','MATH']},
  {'name':'Bongani Dube',    'email':'bongani@test.com',    'grade':6,  'subjects':['MATH','SCI']},
  {'name':'Nompumelelo S',   'email':'nompumelelo@test.com','grade':9,  'subjects':['ENG','SCI']},
  {'name':'Mxolisi Shabangu','email':'mxolisi@test.com',    'grade':12, 'subjects':['MATH','ENG']},
  {'name':'Zanele Mkhwanazi','email':'zanele@test.com',     'grade':8,  'subjects':['SOC','ENG']},
  {'name':'Sandile Magagula','email':'sandile@test.com',    'grade':7,  'subjects':['MATH','SCI','SOC']},
  {'name':'Phiwayinkosi N',  'email':'phiwa@test.com',      'grade':10, 'subjects':['MATH','ENG']},
]

for sdata in students_data:
    student = Student(name=sdata['name'], email=sdata['email'],
                      password_hash=pwd.hash('TestPass123!'), grade=sdata['grade'])
    db.add(student); db.flush()
    db.add(StudentPreference(student_id=student.id, preferred_modality='text'))
    # Enroll in multiple subjects, each with their subject teacher
    for code in sdata['subjects']:
        subj = db.query(Subject).filter(Subject.code==code).first()
        teacher = teacher_objs.get(code)
        if subj:
            db.add(StudentSubject(
                student_id=student.id,
                subject_id=subj.id,
                teacher_id=teacher.id if teacher else None,
            ))

# ── Seed struggling pattern for Sipho (for wiring check 6) ─────────
# Give Sipho low mastery in MATH so at-risk detection triggers
sipho = db.query(Student).filter(Student.email=='sipho@test.com').first()
math_subj = db.query(Subject).filter(Subject.code=='MATH').first()
if sipho and math_subj:
    db.add(TopicMastery(student_id=sipho.id, subject_id=math_subj.id,
                         topic_id='mathematics_algebra',
                         mastery_prob=0.12, mastery_level='struggling'))

# ── Content items per subject ────────────────────────────────────────
content_items = [
  {'title':'Intro to Algebra',       'topic':'mathematics_algebra',   'difficulty_level':5, 'modality':'text',   'subject_code':'MATH'},
  {'title':'Algebra Visual Guide',   'topic':'mathematics_algebra',   'difficulty_level':5, 'modality':'visual', 'subject_code':'MATH'},
  {'title':'Algebra Audio Lesson',   'topic':'mathematics_algebra',   'difficulty_level':5, 'modality':'audio',  'subject_code':'MATH'},
  {'title':'Advanced Geometry',      'topic':'mathematics_geometry',  'difficulty_level':8, 'modality':'text',   'subject_code':'MATH'},
  {'title':'Cell Biology Basics',    'topic':'science_biology',        'difficulty_level':6, 'modality':'text',   'subject_code':'SCI'},
  {'title':'Cell Structure Diagram', 'topic':'science_biology',        'difficulty_level':6, 'modality':'visual', 'subject_code':'SCI'},
  {'title':'Photosynthesis Audio',   'topic':'science_biology',        'difficulty_level':7, 'modality':'audio',  'subject_code':'SCI'},
  {'title':'English Comprehension',  'topic':'english_comprehension',  'difficulty_level':5, 'modality':'text',   'subject_code':'ENG'},
  {'title':'Essay Writing Guide',    'topic':'english_writing',        'difficulty_level':7, 'modality':'text',   'subject_code':'ENG'},
  {'title':'Eswatini History',       'topic':'social_studies',         'difficulty_level':5, 'modality':'text',   'subject_code':'SOC'},
  {'title':'Geography Map Guide',    'topic':'social_studies',         'difficulty_level':5, 'modality':'visual', 'subject_code':'SOC'},
]
for item in content_items:
    subj = db.query(Subject).filter(Subject.code==item.pop('subject_code')).first()
    db.add(ContentItem(**item, subject_id=subj.id if subj else None))

db.commit(); db.close()
print('Database seeded: 4 teachers, 10 students, multi-subject enrollments, 11 content items.')
