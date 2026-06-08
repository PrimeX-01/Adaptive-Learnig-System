import json, os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import audio


from db.database import Base, engine
from routers import (
    auth, subjects, students, chat,
    quiz, hints, content, review,
    messages, teachers, style, library,
)

# ── Try importing optional routers ───────────────────────────────
try:
    from routers import predictions
    HAS_PREDICTIONS = True
except ImportError:
    HAS_PREDICTIONS = False


# ══════════════════════════════════════════════════════════════════
#  APP FACTORY
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title       = 'SiveAdapt API',
    description = 'Adaptive Learning System — University of Eswatini',
    version     = '2.0.0',
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ['http://localhost:3000', 'http://127.0.0.1:3000',
                         'http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials = True,
    allow_methods     = ['*'],
    allow_headers     = ['*'],
)


# ══════════════════════════════════════════════════════════════════
#  STARTUP — load config files into app.state
# ══════════════════════════════════════════════════════════════════

@app.on_event('startup')
async def startup():
    # Load FCL mapping
    try:
        mapping_path = os.path.join(os.path.dirname(__file__), 'fcl_mapping.json')
        with open(mapping_path) as f:
            app.state.fcl_mapping = json.load(f)
    except FileNotFoundError:
        app.state.fcl_mapping = {
            'topic_subject_map': {
                'mathematics_algebra':    'MATH',
                'mathematics_geometry':   'MATH',
                'mathematics_calculus':   'MATH',
                'mathematics_statistics': 'MATH',
                'science_biology':        'SCI',
                'science_chemistry':      'SCI',
                'science_physics':        'SCI',
                'english_comprehension':  'ENG',
                'english_writing':        'ENG',
                'english_literature':     'ENG',
                'social_studies':         'SOC',
                'civics':                 'SOC',
                'computer_science':       'CS',
                'programming':            'CS',
            }
        }
        print('[Startup] fcl_mapping.json not found — using default topic map')

    # Load BKT config
    try:
        bkt_path = os.path.join(os.path.dirname(__file__), 'bkt_config.json')
        with open(bkt_path) as f:
            app.state.bkt_config = json.load(f)
    except FileNotFoundError:
        app.state.bkt_config = {
            'p_learn': 0.3, 'p_guess': 0.2,
            'p_slip':  0.1, 'p_known_init': 0.5,
        }
        print('[Startup] bkt_config.json not found — using defaults')

    print('[Startup] SiveAdapt API ready ✓')


# ══════════════════════════════════════════════════════════════════
#  ROUTER REGISTRATION
# ══════════════════════════════════════════════════════════════════

app.include_router(auth.router,      prefix='/api/auth',      tags=['Authentication'])
app.include_router(subjects.router,  prefix='/api/subjects',  tags=['Subjects'])
app.include_router(students.router,  prefix='/api/students',  tags=['Students'])
app.include_router(chat.router,      prefix='/api/chat',      tags=['Chat'])
app.include_router(quiz.router,      prefix='/api/quiz',      tags=['Quiz'])
app.include_router(hints.router,     prefix='/api/hints',     tags=['Hints'])
app.include_router(content.router,   prefix='/api/content',   tags=['Content'])
app.include_router(review.router,    prefix='/api/review',    tags=['Review'])
app.include_router(messages.router,  prefix='/api/messages',  tags=['Messages'])
app.include_router(teachers.router,  prefix='/api/teachers',  tags=['Teachers'])
app.include_router(style.router,     prefix='/api/style',     tags=['Learning Style'])
app.include_router(library.router,   prefix='/api/library',   tags=['Library'])
app.include_router(audio.router)

if HAS_PREDICTIONS:
    app.include_router(predictions.router, prefix='/api/predict', tags=['ML Predictions'])


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.get('/api/health/ai')
def ai_health():
    """Check if the AI (Groq) API key is configured."""
    import os
    if os.getenv('GROQ_API_KEY'):
        return {"status": "connected", "message": "AI service available"}
    else:
        return {"status": "disconnected", "message": "GROQ_API_KEY not set in .env"}


@app.get('/health', tags=['Health'])
def health_check():
    return {
        'status':  'ok',
        'version': '2.0.0',
        'system':  'SiveAdapt',
    }


@app.get('/', tags=['Health'])
def root():
    return {
        'message': 'SiveAdapt API v2.0 — Adaptive Learning System',
        'docs':    '/docs',
        'health':  '/health',
    }


# ══════════════════════════════════════════════════════════════════
#  START BACKGROUND SCHEDULER
# ══════════════════════════════════════════════════════════════════

from services.scheduler import start_scheduler
scheduler = start_scheduler()

