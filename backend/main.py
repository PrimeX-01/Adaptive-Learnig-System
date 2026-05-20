from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, joblib, json
from dotenv import load_dotenv
from routers import library
from routers import (auth, students, predictions, chat, quiz,
                     hints, content, review, messages, teachers, subjects, style)
from services.scheduler import start_scheduler

load_dotenv()

app = FastAPI(title='AI Adaptive Learning API', version='1.0.0')

app.add_middleware(CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

app.include_router(library.router)
app.include_router(auth.router,        prefix='/api/auth',      tags=['Authentication'])
app.include_router(subjects.router,    prefix='/api/subjects',  tags=['Subjects'])
app.include_router(students.router,    prefix='/api/students',  tags=['Students'])
app.include_router(predictions.router, prefix='/api/predict',   tags=['ML Predictions'])
app.include_router(chat.router,        prefix='/api/chat',      tags=['Chat'])
app.include_router(quiz.router,        prefix='/api/quiz',      tags=['Quiz'])
app.include_router(hints.router,       prefix='/api/hints',     tags=['Hints'])
app.include_router(content.router,     prefix='/api/content',   tags=['Content'])
app.include_router(review.router,      prefix='/api/review',    tags=['Review'])
app.include_router(messages.router,    prefix='/api/messages',  tags=['Messaging'])
app.include_router(teachers.router,    prefix='/api/teachers',  tags=['Teachers'])
app.include_router(style.router,       prefix='/api/style',     tags=['Learning Style'])

@app.on_event('startup')
def startup_event():
    app.state.model        = joblib.load(os.getenv('MODEL_PATH',        'models/adaptive_model.joblib'))
    app.state.preprocessor = joblib.load(os.getenv('PREPROCESSOR_PATH', 'models/preprocessor.joblib'))
    with open(os.getenv('BKT_CONFIG_PATH', 'models/bkt_config.json'))  as f: app.state.bkt_config  = json.load(f)
    with open(os.getenv('FCL_MAPPING_PATH', 'models/fcl_mapping.json')) as f: app.state.fcl_mapping = json.load(f)
    print('CatBoost model and configs loaded successfully.')
    app.state.scheduler = start_scheduler()

@app.get('/api/health')
def health():
    return {'status': 'ok', 'model_loaded': hasattr(app.state, 'model'), 'db_connected': True}
