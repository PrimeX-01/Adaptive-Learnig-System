from pydantic import BaseModel, EmailStr
from typing import Optional, List

class RegisterRequest(BaseModel):
    name:                   str
    email:                  EmailStr
    password:               str
    grade:                  Optional[int] = None
    preferred_modality:     str = 'text'
    feedback_style:         str = 'detailed'
    session_length_minutes: int = 30
    vark_scores:            Optional[dict] = None
  
    # subject enrollments at registration
    subject_enrollments:    Optional[List[dict]] = []

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    student_id:   int
    is_teacher:   bool
    name:         str

class PredictionRequest(BaseModel):
    gender:                       str
    race_ethnicity:               str = 'group C'
    parental_level_of_education:  str
    lunch:                        str
    test_preparation_course:      str
    math_score:                   int
    reading_score:                int
    writing_score:                int
    student_id:                   Optional[int] = None

class ChatRequest(BaseModel):
    session_id: int
    student_id: int
    message:    str
    topic:      str
    fcl_level:  int

class QuizGenerateRequest(BaseModel):
    topic:      str
    fcl_level:  int
    student_id: int
    learning_style: str = 'reading'  

class AssessmentSubmitRequest(BaseModel):
    student_id:          int
    question_id:         Optional[str] = None
    question_text:       Optional[str] = None  
    topic_id:            str
    student_answer:      str
    correct_answer:      str
    fcl_level:           int
    hints_used:          int = 0                
    tutor_consulted:     bool = False           

class AssessmentResponse(BaseModel):
    is_correct:          bool
    feedback_text:       str
    new_mastery_prob:    float
    fcl_changed:         bool
    new_fcl:             Optional[int]  = None
    adaptation_decision: Optional[str]  = None
    points_earned:       int  = 0              
    current_points:      int  = 0              
    points_to_next_fcl:  int  = 0             
    subject_fcl:         Optional[int]  = None

class SubjectEnrollRequest(BaseModel):
    subject_code: str
    teacher_id:   Optional[int] = None

class UpdateTeacherRequest(BaseModel):
    subject_code: str
    teacher_id:   int

class SendMessageRequest(BaseModel):
    receiver_id: int
    subject:     str
    body:        str
    subject_id:  Optional[int] = None
    thread_id:   Optional[int] = None

class BulkTipRequest(BaseModel):
    student_ids: List[int]
    topic_id:    str
    custom_note: Optional[str] = None
