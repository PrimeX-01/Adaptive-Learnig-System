from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    Text, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


# ═══════════════════════════════════════════════════════════════════
#  PRINCIPALS
# ═══════════════════════════════════════════════════════════════════

class Admin(Base):
    __tablename__ = 'admins'
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Teacher(Base):
    __tablename__ = 'teachers'
    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    email           = Column(String(200), unique=True, nullable=False, index=True)
    password_hash   = Column(String(255), nullable=False)
    username        = Column(String(100), unique=True)
    bio             = Column(Text)
    profile_picture = Column(Text)
    status          = Column(String(20), default='pending')
    reset_token         = Column(String(200))
    reset_token_expires = Column(DateTime)
    registered_at   = Column(DateTime(timezone=True), server_default=func.now())

    class_subjects  = relationship('TeacherClassSubject', back_populates='teacher')
    directives      = relationship('TeacherAiDirective',
                                   foreign_keys='TeacherAiDirective.teacher_id',
                                   back_populates='teacher')


class Lecturer(Base):
    __tablename__ = 'lecturers'
    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    email           = Column(String(200), unique=True, nullable=False, index=True)
    password_hash   = Column(String(255), nullable=False)
    username        = Column(String(100), unique=True)
    bio             = Column(Text)
    profile_picture = Column(Text)
    faculty_id      = Column(Integer, ForeignKey('faculties.id', ondelete='SET NULL'))
    status          = Column(String(20), default='pending')
    reset_token         = Column(String(200))
    reset_token_expires = Column(DateTime)
    registered_at   = Column(DateTime(timezone=True), server_default=func.now())

    faculty         = relationship('Faculty', back_populates='lecturers')
    course_assignments = relationship('LecturerCourseAssignment', back_populates='lecturer')
    directives      = relationship('TeacherAiDirective',
                                   foreign_keys='TeacherAiDirective.lecturer_id',
                                   back_populates='lecturer')


class Student(Base):
    __tablename__ = 'students'
    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    email           = Column(String(200), unique=True, nullable=False, index=True)
    password_hash   = Column(String(255), nullable=False)
    username        = Column(String(100), unique=True)
    bio             = Column(Text)
    profile_picture = Column(Text)
    student_type    = Column(String(20), nullable=False, default='school')
    grade_id        = Column(Integer, ForeignKey('grades.id',   ondelete='SET NULL'))
    class_id        = Column(Integer, ForeignKey('classes.id',  ondelete='SET NULL'))
    faculty_id      = Column(Integer, ForeignKey('faculties.id',   ondelete='SET NULL'))
    programme_id    = Column(Integer, ForeignKey('programmes.id',  ondelete='SET NULL'))
    current_level   = Column(Integer, default=1)
    current_semester= Column(Integer, default=1)
    learning_style  = Column(String(30), default='reading')
    reset_token         = Column(String(200))
    reset_token_expires = Column(DateTime)
    registered_at   = Column(DateTime(timezone=True), server_default=func.now())

    grade           = relationship('Grade',   back_populates='students')
    class_          = relationship('Class',   back_populates='students',
                                   foreign_keys=[class_id])
    faculty         = relationship('Faculty', back_populates='students',
                                   foreign_keys=[faculty_id])
    programme       = relationship('Programme', back_populates='students')
    class_enrollments = relationship('StudentClassEnrollment', back_populates='student')
    course_enrollments = relationship('StudentCourseEnrollment', back_populates='student')
    assessments     = relationship('Assessment', back_populates='student')
    sessions        = relationship('ConversationSession', back_populates='student')
    topic_mastery   = relationship('TopicMastery', back_populates='student')
    vark_scores     = relationship('VarkScore', back_populates='student', uselist=False)


# ═══════════════════════════════════════════════════════════════════
#  SCHOOL STRUCTURE
# ═══════════════════════════════════════════════════════════════════

class Grade(Base):
    __tablename__ = 'grades'
    id          = Column(Integer, primary_key=True, index=True)
    label       = Column(String(50), nullable=False, unique=True)
    order_index = Column(Integer, default=0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    classes     = relationship('Class', back_populates='grade')
    students    = relationship('Student', back_populates='grade')


class Class(Base):
    __tablename__ = 'classes'
    id         = Column(Integer, primary_key=True, index=True)
    grade_id   = Column(Integer, ForeignKey('grades.id', ondelete='CASCADE'), nullable=False)
    name       = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('grade_id', 'name'),)

    grade      = relationship('Grade', back_populates='classes')
    students   = relationship('Student', back_populates='class_',
                               foreign_keys='Student.class_id')
    class_subjects = relationship('ClassSubject', back_populates='class_')
    enrollments    = relationship('StudentClassEnrollment', back_populates='class_')


class Subject(Base):
    __tablename__ = 'subjects'
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False, unique=True)
    code        = Column(String(20),  nullable=False, unique=True)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    class_subjects = relationship('ClassSubject', back_populates='subject')
    content        = relationship('ContentItem', back_populates='subject')


class ClassSubject(Base):
    __tablename__ = 'class_subjects'
    id         = Column(Integer, primary_key=True, index=True)
    class_id   = Column(Integer, ForeignKey('classes.id',   ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('class_id', 'subject_id'),)

    class_          = relationship('Class',   back_populates='class_subjects')
    subject         = relationship('Subject', back_populates='class_subjects')
    teacher_assignment = relationship('TeacherClassSubject',
                                      back_populates='class_subject', uselist=False)


class TeacherClassSubject(Base):
    __tablename__ = 'teacher_class_subjects'
    id               = Column(Integer, primary_key=True, index=True)
    teacher_id       = Column(Integer, ForeignKey('teachers.id',      ondelete='CASCADE'), nullable=False)
    class_subject_id = Column(Integer, ForeignKey('class_subjects.id', ondelete='CASCADE'), nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__   = (UniqueConstraint('class_subject_id'),)

    teacher       = relationship('Teacher',      back_populates='class_subjects')
    class_subject = relationship('ClassSubject', back_populates='teacher_assignment')


class StudentClassEnrollment(Base):
    __tablename__ = 'student_class_enrollments'
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    class_id    = Column(Integer, ForeignKey('classes.id',  ondelete='CASCADE'), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('student_id', 'class_id'),)

    student = relationship('Student', back_populates='class_enrollments')
    class_  = relationship('Class',   back_populates='enrollments')


# ═══════════════════════════════════════════════════════════════════
#  TERTIARY STRUCTURE
# ═══════════════════════════════════════════════════════════════════

class Faculty(Base):
    __tablename__ = 'faculties'
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    programmes  = relationship('Programme', back_populates='faculty')
    lecturers   = relationship('Lecturer',  back_populates='faculty')
    students    = relationship('Student',   back_populates='faculty',
                               foreign_keys='Student.faculty_id')


class Programme(Base):
    __tablename__ = 'programmes'
    id              = Column(Integer, primary_key=True, index=True)
    faculty_id      = Column(Integer, ForeignKey('faculties.id', ondelete='CASCADE'), nullable=False)
    name            = Column(String(200), nullable=False)
    duration_levels = Column(Integer, nullable=False, default=3)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__  = (UniqueConstraint('faculty_id', 'name'),)

    faculty         = relationship('Faculty', back_populates='programmes')
    students        = relationship('Student', back_populates='programme')
    course_levels   = relationship('ProgrammeCourseLevel', back_populates='programme')
    level_semesters = relationship('ProgrammeLevelSemester', back_populates='programme')


class Course(Base):
    __tablename__ = 'courses'
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    code        = Column(String(20),  nullable=False, unique=True)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    programme_levels = relationship('ProgrammeCourseLevel', back_populates='course')


class ProgrammeCourseLevel(Base):
    __tablename__ = 'programme_course_levels'
    id           = Column(Integer, primary_key=True, index=True)
    programme_id = Column(Integer, ForeignKey('programmes.id', ondelete='CASCADE'), nullable=False)
    course_id    = Column(Integer, ForeignKey('courses.id',    ondelete='CASCADE'), nullable=False)
    level        = Column(Integer, nullable=False)
    semester     = Column(Integer, nullable=False, default=1)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('programme_id', 'course_id', 'level', 'semester'),)

    programme           = relationship('Programme', back_populates='course_levels')
    course              = relationship('Course',    back_populates='programme_levels')
    lecturer_assignment = relationship('LecturerCourseAssignment',
                                       back_populates='pcl', uselist=False)
    student_enrollments = relationship('StudentCourseEnrollment', back_populates='pcl')


class ProgrammeLevelSemester(Base):
    __tablename__  = 'programme_level_semesters'
    id             = Column(Integer, primary_key=True, index=True)
    programme_id   = Column(Integer, ForeignKey('programmes.id', ondelete='CASCADE'), nullable=False)
    level          = Column(Integer, nullable=False)
    active_semester= Column(Integer, nullable=False, default=1)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('programme_id', 'level'),)

    programme = relationship('Programme', back_populates='level_semesters')


class LecturerCourseAssignment(Base):
    __tablename__  = 'lecturer_course_assignments'
    id          = Column(Integer, primary_key=True, index=True)
    lecturer_id = Column(Integer, ForeignKey('lecturers.id',              ondelete='CASCADE'), nullable=False)
    pcl_id      = Column(Integer, ForeignKey('programme_course_levels.id', ondelete='CASCADE'), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('pcl_id'),)

    lecturer = relationship('Lecturer',             back_populates='course_assignments')
    pcl      = relationship('ProgrammeCourseLevel', back_populates='lecturer_assignment')


class StudentCourseEnrollment(Base):
    __tablename__  = 'student_course_enrollments'
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey('students.id',               ondelete='CASCADE'), nullable=False)
    pcl_id      = Column(Integer, ForeignKey('programme_course_levels.id', ondelete='CASCADE'), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('student_id', 'pcl_id'),)

    student = relationship('Student',             back_populates='course_enrollments')
    pcl     = relationship('ProgrammeCourseLevel', back_populates='student_enrollments')


class LevelAdvancementHistory(Base):
    __tablename__ = 'level_advancement_history'
    id           = Column(Integer, primary_key=True, index=True)
    student_id   = Column(Integer, ForeignKey('students.id',    ondelete='CASCADE'), nullable=False)
    programme_id = Column(Integer, ForeignKey('programmes.id',  ondelete='SET NULL'))
    from_level   = Column(Integer, nullable=False)
    to_level     = Column(Integer, nullable=False)
    advanced_at  = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════
#  VARK & LEARNING STYLE
# ═══════════════════════════════════════════════════════════════════

class VarkScore(Base):
    __tablename__      = 'vark_scores'
    id                 = Column(Integer, primary_key=True, index=True)
    student_id         = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'),
                                nullable=False, unique=True)
    v_score            = Column(Float, default=25.0)
    a_score            = Column(Float, default=25.0)
    r_score            = Column(Float, default=25.0)
    k_score            = Column(Float, default=25.0)
    total_interactions = Column(Integer, default=0)
    last_computed      = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship('Student', back_populates='vark_scores')


class StyleInteraction(Base):
    __tablename__ = 'style_interactions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id  = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    modality   = Column(String(30), nullable=False)
    source     = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudentSubjectStyle(Base):
    __tablename__ = 'student_subject_style'
    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id     = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id      = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    learning_style = Column(String(30), default='reading')
    confidence     = Column(Float, default=0.5)
    auto_detected  = Column(Boolean, default=False)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════
#  FCL & POINTS
# ═══════════════════════════════════════════════════════════════════

class TopicFcl(Base):
    __tablename__ = 'topic_fcl'
    id           = Column(Integer, primary_key=True, index=True)
    student_id   = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id   = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id    = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id     = Column(String(200), nullable=False)
    total_points = Column(Integer, default=0)
    current_fcl  = Column(Integer, default=1)
    is_active    = Column(Boolean, default=True)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now())


class TopicPointTransaction(Base):
    __tablename__ = 'topic_point_transactions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id  = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id   = Column(String(200), nullable=False)
    points     = Column(Integer, nullable=False)
    reason     = Column(String(300))
    source_id  = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════
#  ASSESSMENTS & MASTERY
# ═══════════════════════════════════════════════════════════════════

class Assessment(Base):
    __tablename__ = 'assessments'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id    = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id     = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id      = Column(String(100), nullable=False)
    question_id   = Column(String(200))
    is_correct    = Column(Boolean, nullable=False)
    hints_used    = Column(Integer, default=0)
    fcl_level     = Column(Integer)
    points_earned = Column(Integer, default=0)
    aids_used     = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship('Student', back_populates='assessments')


class TopicMastery(Base):
    __tablename__ = 'topic_mastery'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id    = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id     = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id      = Column(String(100), nullable=False)
    mastery_prob  = Column(Float, default=0.15)
    mastery_level = Column(String(30), default='not_started')
    last_assessed = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship('Student', back_populates='topic_mastery')


class FclHistory(Base):
    __tablename__ = 'fcl_history'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id  = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    fcl_level  = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class HintRequest(Base):
    __tablename__  = 'hint_requests'
    id                   = Column(Integer, primary_key=True, index=True)
    student_id           = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id           = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id            = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    question_id          = Column(String(200), nullable=False)
    hint_level_requested = Column(Integer, nullable=False)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__       = (CheckConstraint('hint_level_requested IN (1,2,3)'),)


class ReviewSchedule(Base):
    __tablename__ = 'review_schedule'
    id               = Column(Integer, primary_key=True, index=True)
    student_id       = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id       = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id        = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id         = Column(String(100), nullable=False)
    next_review_date = Column(Date, nullable=False)
    interval_days    = Column(Integer, default=1)
    repetition_count = Column(Integer, default=0)


# ═══════════════════════════════════════════════════════════════════
#  CONVERSATIONS & SESSIONS
# ═══════════════════════════════════════════════════════════════════

class ConversationSession(Base):
    __tablename__ = 'conversation_sessions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id  = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id   = Column(String(200))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at   = Column(DateTime(timezone=True))

    student  = relationship('Student', back_populates='sessions')
    messages = relationship('ConversationMessage', back_populates='session')


class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'
    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('conversation_sessions.id', ondelete='CASCADE'), nullable=False)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship('ConversationSession', back_populates='messages')


class ActiveSession(Base):
    __tablename__ = 'active_sessions'
    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id     = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id      = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id       = Column(String(200))
    session_type   = Column(String(50), nullable=False)
    started_at     = Column(DateTime(timezone=True), server_default=func.now())
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    ended_at       = Column(DateTime(timezone=True))
    total_minutes  = Column(Integer, default=0)


# ═══════════════════════════════════════════════════════════════════
#  LIBRARY
# ═══════════════════════════════════════════════════════════════════

class LibraryContent(Base):
    __tablename__ = 'library_content'
    id           = Column(Integer, primary_key=True, index=True)
    teacher_id   = Column(Integer, ForeignKey('teachers.id',  ondelete='CASCADE'))
    lecturer_id  = Column(Integer, ForeignKey('lecturers.id', ondelete='CASCADE'))
    subject_id   = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id    = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    title        = Column(String(300), nullable=False)
    description  = Column(Text)
    content_type = Column(String(50), nullable=False)
    file_data    = Column(Text)
    grade_id     = Column(Integer, ForeignKey('grades.id', ondelete='SET NULL'))
    level        = Column(Integer)
    is_published = Column(Boolean, default=True)
    uploaded_at  = Column(DateTime(timezone=True), server_default=func.now())


class LibrarySession(Base):
    __tablename__ = 'library_sessions'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id',       ondelete='CASCADE'), nullable=False)
    content_id    = Column(Integer, ForeignKey('library_content.id', ondelete='CASCADE'), nullable=False)
    started_at    = Column(DateTime(timezone=True), server_default=func.now())
    ended_at      = Column(DateTime(timezone=True))
    ai_tutor_used = Column(Boolean, default=False)


class ContentItem(Base):
    __tablename__    = 'content_items'
    id               = Column(Integer, primary_key=True, index=True)
    subject_id       = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'))
    course_id        = Column(Integer, ForeignKey('courses.id',  ondelete='CASCADE'))
    title            = Column(String(300), nullable=False)
    topic            = Column(String(100), nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    modality         = Column(String(20), nullable=False)
    content_text     = Column(Text)
    diagram_code     = Column(Text)

    subject = relationship('Subject', back_populates='content')


# ═══════════════════════════════════════════════════════════════════
#  MESSAGING & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════

class Message(Base):
    __tablename__ = 'messages'
    id            = Column(Integer, primary_key=True, index=True)
    sender_type   = Column(String(20), nullable=False)
    sender_id     = Column(Integer,    nullable=False)
    receiver_type = Column(String(20), nullable=False)
    receiver_id   = Column(Integer,    nullable=False)
    subject_id    = Column(Integer, ForeignKey('subjects.id', ondelete='SET NULL'))
    course_id     = Column(Integer, ForeignKey('courses.id',  ondelete='SET NULL'))
    subject       = Column(Text, nullable=False)
    body          = Column(Text, nullable=False)
    is_read       = Column(Boolean, default=False)
    thread_id     = Column(Integer)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = 'notifications'
    id            = Column(Integer, primary_key=True, index=True)
    receiver_type = Column(String(20), nullable=False)
    receiver_id   = Column(Integer,    nullable=False)
    sender_type   = Column(String(20))
    sender_id     = Column(Integer)
    subject_id    = Column(Integer, ForeignKey('subjects.id', ondelete='SET NULL'))
    course_id     = Column(Integer, ForeignKey('courses.id',  ondelete='SET NULL'))
    type          = Column(String(50), nullable=False)
    title         = Column(String(300), nullable=False)
    body          = Column(Text)
    is_read       = Column(Boolean, default=False)
    action_url    = Column(String(300))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════
#  TEACHER / LECTURER TOOLS
# ═══════════════════════════════════════════════════════════════════

class TeacherAiDirective(Base):
    __tablename__ = 'teacher_ai_directives'
    id          = Column(Integer, primary_key=True, index=True)
    teacher_id  = Column(Integer, ForeignKey('teachers.id',  ondelete='CASCADE'))
    lecturer_id = Column(Integer, ForeignKey('lecturers.id', ondelete='CASCADE'))
    student_id  = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'))
    subject_id  = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id   = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    directive   = Column(Text, nullable=False)
    label       = Column(String(200))
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    teacher  = relationship('Teacher',  foreign_keys=[teacher_id],  back_populates='directives')
    lecturer = relationship('Lecturer', foreign_keys=[lecturer_id], back_populates='directives')


class TeacherPointAward(Base):
    __tablename__ = 'teacher_point_awards'
    id          = Column(Integer, primary_key=True, index=True)
    teacher_id  = Column(Integer, ForeignKey('teachers.id',  ondelete='CASCADE'))
    lecturer_id = Column(Integer, ForeignKey('lecturers.id', ondelete='CASCADE'))
    student_id  = Column(Integer, ForeignKey('students.id',  ondelete='CASCADE'), nullable=False)
    subject_id  = Column(Integer, ForeignKey('subjects.id',  ondelete='CASCADE'))
    course_id   = Column(Integer, ForeignKey('courses.id',   ondelete='CASCADE'))
    topic_id    = Column(String(200))
    points      = Column(Integer, nullable=False)
    reason      = Column(Text)
    awarded_at  = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════
#  PERSONALISATION EVENTS
# ═══════════════════════════════════════════════════════════════════

class ComprehensionEvent(Base):
    __tablename__ = 'comprehension_events'
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey('students.id',           ondelete='CASCADE'), nullable=False)
    session_id  = Column(Integer, ForeignKey('conversation_sessions.id', ondelete='SET NULL'))
    event_type  = Column(String(50), nullable=False)
    title       = Column(String(200), nullable=False)
    message     = Column(Text, nullable=False)
    tier_before = Column(Integer)
    tier_after  = Column(Integer)
    trigger     = Column(String(200))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class MoodLog(Base):
    __tablename__ = 'mood_logs'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    mood       = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LlmApiLog(Base):
    __tablename__ = 'llm_api_logs'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='SET NULL'))
    endpoint   = Column(String(100))
    model_used = Column(String(100))
    tokens_in  = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
