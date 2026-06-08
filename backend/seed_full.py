#!/usr/bin/env python3
"""
Complete seed script with inline models – no external files needed.
Run this to create database and seed with 30 students per grade, teachers, subjects.
"""
import os
import random
from faker import Faker
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# ========== DATABASE SETUP ==========
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adaptive_learning.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== MODELS ==========
class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    min_grade = Column(Integer, default=1)
    max_grade = Column(Integer, default=18)

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class TeacherGradeAssignment(Base):
    __tablename__ = 'teacher_grade_assignments'
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    grade = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'))

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    learning_style = Column(String(20), default='visual')
    flc_progress = Column(Float, default=0.0)
    points = Column(Integer, default=0)
    quizzes_completed = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

fake = Faker()

# ========== CONFIGURATION ==========
STUDENTS_PER_GRADE = 30
MIN_TEACHERS_PER_GRADE = 7
TEACHER_GRADE_RANGE = 2

GRADE_CONFIG = {
    1: ("Grade 1", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    2: ("Grade 2", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    3: ("Grade 3", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    4: ("Grade 4", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    5: ("Grade 5", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    6: ("Grade 6", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    7: ("Grade 7", "primary", ["Mathematics", "English", "Science", "Social Studies", "Art", "Music", "Physical Education"]),
    8: ("Grade 8", "secondary", ["Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography", "Computer Science"]),
    9: ("Grade 9", "secondary", ["Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography", "Computer Science"]),
    10: ("Grade 10", "secondary", ["Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography", "Computer Science", "Economics"]),
    11: ("Grade 11", "secondary", ["Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography", "Computer Science", "Economics"]),
    12: ("Grade 12", "secondary", ["Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography", "Computer Science", "Economics"]),
    13: ("University Year 1", "tertiary", ["Calculus I", "Programming Fundamentals", "General Physics", "Academic Writing", "Introduction to Psychology", "Statistics"]),
    14: ("University Year 2", "tertiary", ["Linear Algebra", "Data Structures", "Thermodynamics", "Research Methods", "Microeconomics"]),
    15: ("University Year 3", "tertiary", ["Differential Equations", "Algorithms", "Quantum Mechanics", "Machine Learning", "Macroeconomics"]),
    16: ("University Year 4", "tertiary", ["Advanced Algorithms", "Capstone Project", "Solid State Physics", "Deep Learning", "Econometrics"]),
    17: ("Master's Year 1", "masters", ["Advanced Machine Learning", "Research Seminar", "Big Data Analytics", "Scientific Computing"]),
    18: ("Master's Year 2", "masters", ["Thesis Research", "Advanced Topics in AI", "Data Visualization", "Ethics in AI"]),
}

LEARNING_STYLES = ["visual", "auditory", "kinesthetic", "reading_writing"]

# ========== HELPER FUNCTIONS ==========
def get_or_create_subject(db: Session, name: str) -> Subject:
    subject = db.query(Subject).filter(Subject.name == name).first()
    if not subject:
        subject = Subject(name=name)
        db.add(subject)
        db.commit()
        db.refresh(subject)
    return subject

def create_teachers_for_grade(db: Session, grade: int, subjects: list):
    existing_teachers = db.query(Teacher).filter(
        Teacher.min_grade <= grade,
        Teacher.max_grade >= grade
    ).all()
    
    teachers_needed = max(0, MIN_TEACHERS_PER_GRADE - len(existing_teachers))
    
    new_teachers = []
    for _ in range(teachers_needed):
        min_g = max(1, grade - TEACHER_GRADE_RANGE)
        max_g = grade + TEACHER_GRADE_RANGE
        teacher = Teacher(
            name=fake.name(),
            email=fake.email(),
            min_grade=min_g,
            max_grade=max_g
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        new_teachers.append(teacher)
    
    return existing_teachers + new_teachers

def assign_teacher_to_subject(db: Session, grade: int, subject_name: str, teachers: list):
    subject = get_or_create_subject(db, subject_name)
    
    existing_assignments = db.query(TeacherGradeAssignment).filter(
        TeacherGradeAssignment.grade == grade,
        TeacherGradeAssignment.subject_id == subject.id
    ).all()
    assigned_teacher_ids = [a.teacher_id for a in existing_assignments]
    
    available_teachers = [t for t in teachers if t.id not in assigned_teacher_ids]
    if not available_teachers:
        min_g = max(1, grade - TEACHER_GRADE_RANGE)
        max_g = grade + TEACHER_GRADE_RANGE
        new_teacher = Teacher(
            name=fake.name(),
            email=fake.email(),
            min_grade=min_g,
            max_grade=max_g
        )
        db.add(new_teacher)
        db.commit()
        db.refresh(new_teacher)
        available_teachers = [new_teacher]
    
    chosen_teacher = random.choice(available_teachers)
    assignment = TeacherGradeAssignment(
        teacher_id=chosen_teacher.id,
        grade=grade,
        subject_id=subject.id
    )
    db.add(assignment)
    db.commit()
    return assignment

def create_students_for_grade(db: Session, grade: int, count: int):
    students = []
    for _ in range(count):
        student = Student(
            name=fake.name(),
            grade=grade,
            learning_style=random.choice(LEARNING_STYLES),
            flc_progress=random.uniform(0, 100),
            points=random.randint(0, 5000),
            quizzes_completed=random.randint(0, 80)
        )
        db.add(student)
        students.append(student)
    db.commit()
    return students

# ========== MAIN ==========
def main():
    print("🌱 Seeding database with realistic data...")
    db = SessionLocal()
    
    try:
        # Optional: clear existing data (uncomment to reset)
        # db.query(TeacherGradeAssignment).delete()
        # db.query(Student).delete()
        # db.query(Teacher).delete()
        # db.query(Subject).delete()
        # db.commit()
        
        for grade_num, (grade_name, category, subjects) in GRADE_CONFIG.items():
            print(f"\n📚 Processing {grade_name} (grade {grade_num})")
            
            teachers = create_teachers_for_grade(db, grade_num, subjects)
            print(f"   ✅ {len(teachers)} teachers available for grade {grade_num}")
            
            for subject_name in subjects:
                assign_teacher_to_subject(db, grade_num, subject_name, teachers)
            print(f"   ✅ Assigned {len(subjects)} subjects to teachers")
            
            students = create_students_for_grade(db, grade_num, STUDENTS_PER_GRADE)
            print(f"   ✅ Created {len(students)} students")
            
            if students:
                sample = students[0]
                print(f"      Sample student: {sample.name}, style={sample.learning_style}, progress={sample.flc_progress:.1f}%, points={sample.points}")
        
        print("\n🎉 Seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()