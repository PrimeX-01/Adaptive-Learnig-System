from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Student
import os

SECRET_KEY                 = os.getenv('SECRET_KEY', 'change-me-in-production')
ALGORITHM                  = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES= 60 * 8  # 8 hours

pwd_context   = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta]=None) -> str:
    to_encode = data.copy()
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_student(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)) -> Student:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Could not validate credentials',
                        headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload    = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id = payload.get('sub')
        if student_id is None: raise exc
        student_id = int(student_id)
    except (JWTError, ValueError): raise exc
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student: raise exc
    return student