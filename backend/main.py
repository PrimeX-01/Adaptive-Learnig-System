import json, os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import Base, engine
from routers import (
    auth, admin, students, teachers, lecturers,
    chat, quiz, hints, content, review,
    messages, style, library, audio,
)


# ══════════════════════════════════════════════════════════════════
#  APP FACTORY
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title       = 'SiveAdapt API',
    description = 'Adaptive Learning System — University of Eswatini',
    version     = '3.0.0',
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
#  STARTUP
# ══════════════════════════════════════════════════════════════════

@app.on_event('startup')
async def startup():
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

    print('[Startup] SiveAdapt API v3.0 ready ✓ (multi-role architecture)')


# ══════════════════════════════════════════════════════════════════
#  ROUTER REGISTRATION
# ══════════════════════════════════════════════════════════════════

# auth.py already declares its own prefix='/api/auth' internally
app.include_router(auth.router)

# admin.py already declares prefix='/api/admin' internally
app.include_router(admin.router)

# students.py / teachers.py / lecturers.py declare their own prefixes
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(lecturers.router)

# Existing routers — unchanged prefixes
app.include_router(chat.router,      prefix='/api/chat',      tags=['Chat'])
app.include_router(quiz.router,      prefix='/api/quiz',      tags=['Quiz'])
app.include_router(hints.router,     prefix='/api/hints',     tags=['Hints'])
app.include_router(content.router,   prefix='/api/content',   tags=['Content'])
app.include_router(review.router,    prefix='/api/review',    tags=['Review'])
app.include_router(messages.router,  prefix='/api/messages',  tags=['Messages'])
app.include_router(style.router,     prefix='/api/style',     tags=['Learning Style'])
app.include_router(library.router,   prefix='/api/library',   tags=['Library'])
app.include_router(audio.router)


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.get('/api/health/ai')
def ai_health():
    if os.getenv('GROQ_API_KEY'):
        return {'status': 'connected', 'message': 'AI service available'}
    return {'status': 'disconnected', 'message': 'GROQ_API_KEY not set in .env'}


@app.get('/health', tags=['Health'])
def health_check():
    return {'status': 'ok', 'version': '3.0.0', 'system': 'SiveAdapt'}


@app.get('/', tags=['Health'])
def root():
    return {
        'message': 'SiveAdapt API v3.0 — Multi-Role Adaptive Learning System',
        'docs':    '/docs',
        'health':  '/health',
    }


# ══════════════════════════════════════════════════════════════════
#  BACKGROUND SCHEDULER
# ══════════════════════════════════════════════════════════════════

from services.scheduler import start_scheduler
scheduler = start_scheduler()
