from pydantic import BaseModel
from typing import Optional, List




# ══════════════════════════════════════════════════════════════════
#  QUIZ
# ══════════════════════════════════════════════════════════════════

class QuizGenerateRequest(BaseModel):
    student_id: int
    topic:      str
    fcl_level:  int = 5


class AssessmentSubmitRequest(BaseModel):
    student_id:      int
    question_id:     Optional[str]  = None
    question_text:   Optional[str]  = None    # sent by frontend for feedback generation
    topic_id:        str
    student_answer:  str
    correct_answer:  str
    fcl_level:       int
    hints_used:      int  = 0
    tutor_consulted: bool = False


class AssessmentResponse(BaseModel):
    # Core result
    is_correct:          bool
    feedback_text:       str
    new_mastery_prob:    float

    # FCL change (from points system)
    fcl_changed:         bool
    new_fcl:             Optional[int]   = None
    adaptation_decision: Optional[str]   = None

    # Point system (FCL 1–20)
    points_earned:       int   = 0
    total_points:        int   = 0       # cumulative total for this topic
    topic_fcl:           int   = 1       # current FCL for this topic
    points_within_level: int   = 0       # points earned within current FCL level (0–999)
    points_to_next_fcl:  int   = 1000    # points remaining to reach next FCL
    subject_fcl:         float = 1.0     # average of topic FCLs in this subject
    overall_fcl:         float = 1.0     # average of all subject FCLs


# ══════════════════════════════════════════════════════════════════
#  STUDENTS
# ══════════════════════════════════════════════════════════════════

class StudentProfileUpdate(BaseModel):
    name:              Optional[str] = None
    username:          Optional[str] = None
    bio:               Optional[str] = None
    age:               Optional[int] = None
    profile_picture:   Optional[str] = None
    learning_style:    Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  CHAT
# ══════════════════════════════════════════════════════════════════

class ChatMessageRequest(BaseModel):
    session_id:    int
    student_id:    int
    message:       str
    topic:         str
    fcl_level:     int
    learning_style:Optional[str] = 'reading'
    subject_id:    Optional[int] = None
    grade:         Optional[int] = None


class NewSessionRequest(BaseModel):
    student_id: int
    subject_id: Optional[int] = None


class SessionEndRequest(BaseModel):
    session_id:    int
    student_id:    int
    subject_id:    int
    exchange_count:int
    topic_id:      Optional[str] = None
    duration_minutes: Optional[int] = None


# ══════════════════════════════════════════════════════════════════
#  LIBRARY
# ══════════════════════════════════════════════════════════════════

class LibrarySessionEndRequest(BaseModel):
    student_id:       int
    content_id:       int
    duration_minutes: int
    ai_tutor_used:    bool = False
    topic_id:         Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  STYLE
# ══════════════════════════════════════════════════════════════════

class StyleUpdateRequest(BaseModel):
    style:      str
    subject_id: Optional[int] = None


class StyleInteractionRequest(BaseModel):
    student_id: int
    subject_id: int
    modality:   str
    source:     str


# ══════════════════════════════════════════════════════════════════
#  TEACHERS
# ══════════════════════════════════════════════════════════════════

class TeacherAwardPointsRequest(BaseModel):
    student_id: int
    subject_id: int
    topic_id:   str
    points:     int
    reason:     str


class TeacherDirectiveRequest(BaseModel):
    teacher_id: int
    student_id: Optional[int] = None
    subject_id: int
    grade_min:  Optional[int] = None
    grade_max:  Optional[int] = None
    directive:  str
    label:      Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  HINTS
# ══════════════════════════════════════════════════════════════════

class HintResponse(BaseModel):
    hint_text:   str
    hint_level:  int
    hints_left:  int


# ══════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════

class NotificationResponse(BaseModel):
    id:         int
    type:       str
    title:      str
    body:       str
    action_url: Optional[str] = None
    is_read:    bool
    created_at: str
    
class SendMessageRequest(BaseModel):
    """Request schema for sending a direct message."""
    receiver_id: int
    subject_id: Optional[int] = None   # which subject the message relates to (optional)
    subject: str                       # message subject line
    body: str
    thread_id: Optional[int] = None    # for reply threading

class BulkTipRequest(BaseModel):
    """Request schema for sending a tip (notification) to multiple students."""
    student_ids: List[int]
    subject_id: int
    tip_text: str