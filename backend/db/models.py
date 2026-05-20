from sqlalchemy import (Column, Integer, String, Float, Boolean, DateTime,
                         Date, Text, ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base

class Subject(Base):
    __tablename__ = 'subjects'
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False, unique=True)
    code        = Column(String(20),  nullable=False, unique=True)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    enrollments = relationship('StudentSubject', back_populates='subject')
    content     = relationship('ContentItem', back_populates='subject')

class SubjectFclPoints(Base):
    __tablename__ = 'subject_fcl_points'
    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id     = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    current_points = Column(Integer, default=0)
    total_earned   = Column(Integer, default=0)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('student_id', 'subject_id'),)

class FclPointTransaction(Base):
    __tablename__ = 'fcl_point_transactions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    points     = Column(Integer, nullable=False)
    reason     = Column(String(200), nullable=False)
    source_id  = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StudentSubjectStyle(Base):
    __tablename__ = 'student_subject_style'
    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id     = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    learning_style = Column(String(30), default='reading')
    confidence     = Column(Float, default=0.5)
    auto_detected  = Column(Boolean, default=False)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('student_id', 'subject_id'),)

class StyleInteraction(Base):
    __tablename__ = 'style_interactions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    modality   = Column(String(30), nullable=False)
    source     = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LibraryContent(Base):
    __tablename__ = 'library_content'
    id           = Column(Integer, primary_key=True, index=True)
    teacher_id   = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id   = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    title        = Column(String(300), nullable=False)
    description  = Column(Text)
    content_type = Column(String(50), nullable=False)
    file_data    = Column(Text)
    grade_min    = Column(Integer, default=1)
    grade_max    = Column(Integer, default=19)
    uploaded_at  = Column(DateTime(timezone=True), server_default=func.now())
    is_published = Column(Boolean, default=True)

class LibrarySession(Base):
    __tablename__ = 'library_sessions'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id'), nullable=False)
    content_id    = Column(Integer, ForeignKey('library_content.id'), nullable=False)
    started_at    = Column(DateTime(timezone=True), server_default=func.now())
    ended_at      = Column(DateTime(timezone=True))
    ai_tutor_used = Column(Boolean, default=False)
class Student(Base):
    __tablename__ = 'students'
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    grade         = Column(Integer)
    username         = Column(String, unique=True)
    age              = Column(Integer)
    bio              = Column(Text)
    profile_picture  = Column(Text)
    is_teacher    = Column(Boolean, default=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    reset_token         = Column(String, nullable=True)      
    reset_token_expires = Column(DateTime, nullable=True)
    subject_enrollments = relationship('StudentSubject', foreign_keys='StudentSubject.student_id', back_populates='student')
    preferences         = relationship('StudentPreference', back_populates='student', uselist=False)
    sessions            = relationship('ConversationSession', back_populates='student')
    topic_mastery       = relationship('TopicMastery', back_populates='student')
    assessments         = relationship('Assessment', back_populates='student')

class StudentSubject(Base):
    __tablename__ = 'student_subjects'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('students.id'))
    enrolled_at= Column(DateTime(timezone=True), server_default=func.now())
    student    = relationship('Student', foreign_keys=[student_id], back_populates='subject_enrollments')
    subject    = relationship('Subject', back_populates='enrollments')
    teacher    = relationship('Student', foreign_keys=[teacher_id])
    __table_args__ = (UniqueConstraint('student_id', 'subject_id'),)

class StudentPreference(Base):
    __tablename__ = 'student_preferences'
    student_id             = Column(Integer, ForeignKey('students.id'), primary_key=True)
    preferred_modality     = Column(String(20), default='text')
    feedback_style         = Column(String(20), default='detailed')
    session_length_minutes = Column(Integer, default=30)
    preferred_learning_style = Column(String(20), default='visual')
    language_level         = Column(String(20), default='standard')
    student                = relationship('Student', back_populates='preferences')

class Assessment(Base):
    __tablename__ = 'assessments'
    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id  = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id    = Column(String(100), nullable=False)
    question_id = Column(String(200))
    is_correct  = Column(Boolean, nullable=False)
    hints_used  = Column(Integer, default=0)
    fcl_level   = Column(Integer)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    student     = relationship('Student', back_populates='assessments')

class FCLHistory(Base):
    __tablename__ = 'fcl_history'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    fcl_level  = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class TopicMastery(Base):
    __tablename__ = 'topic_mastery'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id    = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id      = Column(String(100), nullable=False)
    mastery_prob  = Column(Float, default=0.15)
    mastery_level = Column(String(30), default='not_started')
    last_assessed = Column(DateTime(timezone=True), server_default=func.now())
    student       = relationship('Student', back_populates='topic_mastery')
    __table_args__ = (UniqueConstraint('student_id', 'subject_id', 'topic_id'),)

class HintRequest(Base):
    __tablename__ = 'hint_requests'
    id                   = Column(Integer, primary_key=True, index=True)
    student_id           = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id           = Column(Integer, ForeignKey('subjects.id'))
    question_id          = Column(String(200), nullable=False)
    hint_level_requested = Column(Integer, nullable=False)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__       = (CheckConstraint('hint_level_requested IN (1,2,3)'),)

class ConversationSession(Base):
    __tablename__ = 'conversation_sessions'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at   = Column(DateTime(timezone=True))
    student    = relationship('Student', back_populates='sessions')
    messages   = relationship('ConversationMessage', back_populates='session')

class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'
    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('conversation_sessions.id'), nullable=False)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    session    = relationship('ConversationSession', back_populates='messages')

class ReviewSchedule(Base):
    __tablename__    = 'review_schedule'
    id               = Column(Integer, primary_key=True, index=True)
    student_id       = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id       = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id         = Column(String(100), nullable=False)
    next_review_date = Column(Date, nullable=False)
    interval_days    = Column(Integer, default=1)
    repetition_count = Column(Integer, default=0)
    __table_args__   = (UniqueConstraint('student_id', 'subject_id', 'topic_id'),)

class ContentItem(Base):
    __tablename__    = 'content_items'
    id               = Column(Integer, primary_key=True, index=True)
    subject_id       = Column(Integer, ForeignKey('subjects.id'))
    title            = Column(String(300), nullable=False)
    topic            = Column(String(100), nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    modality         = Column(String(20), nullable=False)
    content_text     = Column(Text)
    diagram_code     = Column(Text)
    subject          = relationship('Subject', back_populates='content')

class Message(Base):
    __tablename__ = 'messages'
    id          = Column(Integer, primary_key=True, index=True)
    sender_id   = Column(Integer, ForeignKey('students.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id  = Column(Integer, ForeignKey('subjects.id'))
    subject     = Column(Text, nullable=False)
    body        = Column(Text, nullable=False)
    is_read     = Column(Boolean, default=False)
    thread_id   = Column(Integer)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    sender      = relationship('Student', foreign_keys=[sender_id])
    receiver    = relationship('Student', foreign_keys=[receiver_id])

class Notification(Base):
    __tablename__ = 'notifications'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    sender_id  = Column(Integer, ForeignKey('students.id'))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    type       = Column(String(50), nullable=False)
    title      = Column(String(300), nullable=False)
    body       = Column(Text)
    is_read    = Column(Boolean, default=False)
    action_url = Column(String(300))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
class LLMApiLog(Base):
    __tablename__ = 'llm_api_logs'
    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    endpoint   = Column(String(100))
    model_used = Column(String(100))
    tokens_in  = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# New tables for the hierarchical points-based FCL system

class TopicFcl(Base):
    __tablename__ = 'topic_fcl'
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id    = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id      = Column(String(100), nullable=False)
    total_points  = Column(Integer, default=0)
    current_fcl   = Column(Integer, default=1)
    last_updated  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('student_id', 'subject_id', 'topic_id'),)

class TopicPointTransaction(Base):
    __tablename__ = 'topic_point_transactions'
    id           = Column(Integer, primary_key=True, index=True)
    student_id   = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id   = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id     = Column(String(100), nullable=False)
    points       = Column(Integer, nullable=False)
    reason       = Column(String(200), nullable=False)
    source_id    = Column(String(200))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

class ActiveSession(Base):
    __tablename__ = 'active_sessions'
    id             = Column(Integer, primary_key=True, index=True)
    student_id     = Column(Integer, ForeignKey('students.id'), nullable=False)
    session_type   = Column(String(50), nullable=False)   # 'tutor' or 'library'
    topic_id       = Column(String(100), nullable=False)
    subject_id     = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    start_time     = Column(DateTime(timezone=True), server_default=func.now())
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    total_seconds  = Column(Integer, default=0)
    ended          = Column(Boolean, default=False)

class TeacherAward(Base):
    __tablename__ = 'teacher_awards'
    id           = Column(Integer, primary_key=True, index=True)
    teacher_id   = Column(Integer, ForeignKey('students.id'), nullable=False)
    student_id   = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject_id   = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    topic_id     = Column(String(100), nullable=False)
    points       = Column(Integer, nullable=False)
    reason       = Column(Text)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())