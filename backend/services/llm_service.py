import os
import json
import time
import uuid
import re
import requests
import base64
from urllib.parse import quote
from sqlalchemy.orm import Session
from groq import Groq
from db.models import ConversationMessage, LLMApiLog

# ── Groq configuration ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise RuntimeError('GROQ_API_KEY not set in .env')

client = Groq(api_key=GROQ_API_KEY)

MODEL_PRIMARY = 'llama-3.3-70b-versatile'
MODEL_FAST    = 'llama-3.1-8b-instant'
MODEL_LONG    = 'mixtral-8x7b-32768'

# ── Hugging Face configuration ─────────────────────────────────────
HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HF_IMAGE_MODEL = os.getenv('HUGGINGFACE_IMAGE_MODEL', 'runwayml/stable-diffusion-v1-5')

# ================================================================
#  IMAGE GENERATION (unchanged)
# ================================================================
def _image_from_huggingface(prompt: str) -> str | None:
    if not HF_API_KEY:
        return None
    url = f"https://router.huggingface.co/hf-inference/models/{HF_IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            img_b64 = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{img_b64}"
    except:
        pass
    return None

def _image_from_pollinations(prompt: str) -> str | None:
    try:
        encoded = quote(prompt[:200])
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            img_b64 = base64.b64encode(resp.content).decode("utf-8")
            return f"data:image/png;base64,{img_b64}"
    except:
        pass
    return None

def _placeholder_image(prompt: str) -> str:
    safe_text = prompt.replace('"', '&quot;')[:60]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
      <rect width="400" height="300" fill="#1e293b"/>
      <text x="200" y="150" font-family="Arial" font-size="16" fill="#00d4c8" text-anchor="middle">🎨 {safe_text}</text>
      <text x="200" y="180" font-family="Arial" font-size="12" fill="#64748b" text-anchor="middle">(Image generation unavailable – try again)</text>
    </svg>'''
    return f'data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}'

def generate_image(prompt: str) -> str | None:
    print(f"[Image] Generating image for: {prompt[:80]}...")
    img = _image_from_huggingface(prompt) or _image_from_pollinations(prompt)
    if img:
        return img
    print("[Image] All providers failed – using placeholder SVG")
    return _placeholder_image(prompt)

def recommend_youtube(query: str, fcl_level: int = 8) -> str:
    level_str = ('for kids' if fcl_level <= 4 else
                 'for middle school' if fcl_level <= 7 else
                 'for high school' if fcl_level <= 10 else 'university level')
    search_query = quote(f"{query} {level_str} explained")
    return f"https://www.youtube.com/results?search_query={search_query}"

# ================================================================
#  CORE GROQ CALLER (unchanged)
# ================================================================
def call_groq(prompt: str,
              system: str = None,
              history: list = None,
              max_tokens: int = 600,
              temperature: float = 0.7,
              model: str = MODEL_PRIMARY) -> tuple[str, int, int]:
    messages = []
    if system and system.strip():
        messages.append({'role': 'system', 'content': system.strip()})
    if history:
        for msg in history:
            role = msg.get('role')
            if role == 'model':
                role = 'assistant'
            content = msg.get('parts', [msg.get('content', '')])[0]
            if content and content.strip():
                messages.append({'role': role, 'content': content.strip()})
    if not prompt or not prompt.strip():
        prompt = "Please respond with a helpful answer."
    messages.append({'role': 'user', 'content': prompt.strip()})
    if not messages:
        raise ValueError("No messages to send to Groq")
    print(f"[DEBUG] call_groq: sending {len(messages)} messages, first user content: {messages[-1]['content'][:100]}")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content
    tok_in = response.usage.prompt_tokens
    tok_out = response.usage.completion_tokens
    return text, tok_in, tok_out

# ================================================================
#  SYSTEM PROMPT BUILDER (unchanged)
# ================================================================
def build_system_prompt(fcl_level: int, topic: str,
                         learning_style: str = 'reading',
                         subject_name: str = None) -> str:
    subject_label = subject_name or topic.replace('_', ' ').title()
    if fcl_level <= 4:
        cog = (
            f'You are tutoring a young primary school child (FCL 1-4) in {subject_label}. '
            'Use very simple words — maximum 12 words per sentence. '
            'Use concrete everyday examples (animals, fruit, toys). '
            'Never use technical terms. Be warm, patient and encouraging. '
            'End every response with one simple question.'
        )
    elif fcl_level <= 7:
        cog = (
            f'You are tutoring a middle school student (FCL 5-7) in {subject_label}. '
            'Use clear everyday language. Define any subject-specific terms immediately. '
            'Keep paragraphs short (2-3 sentences). Use relatable real-world examples.'
        )
    elif fcl_level <= 10:
        cog = (
            f'You are tutoring a secondary school student (FCL 8-10) in {subject_label}. '
            'Use standard academic language. You may introduce technical terms with definitions. '
            'Structured explanations with numbered steps are appropriate.'
        )
    else:
        cog = (
            f'You are tutoring an advanced tertiary student (FCL 11-13) in {subject_label}. '
            'Use formal academic and discipline-specific language freely. '
            'You may reference theory, research findings, and technical proofs.'
        )

    style_map = {
        'visual': 'LEARNING STYLE: Visual. Include [IMAGE: description] or visual markers. Use spacing.',
        'auditory': 'LEARNING STYLE: Auditory. Write in conversational spoken tone.',
        'reading': 'LEARNING STYLE: Reading/Writing. Provide structured written explanations.',
        'kinesthetic': 'LEARNING STYLE: Kinesthetic. Include a hands-on step or try-it-yourself problem.',
    }
    style = style_map.get(learning_style, style_map['reading'])

    return (
        f'You are an AI tutor specialising in {subject_label} '
        f'for the SiveAdapt adaptive learning system at the University of Eswatini. '
        f'{cog} {style} '
        'Structure every response: (1) explanation, (2) example, (3) comprehension check. '
        'Keep responses under 300 words.'
    )

# ================================================================
#  CONVERSATION HISTORY (unchanged)
# ================================================================
def load_conversation_history(session_id: int, db: Session) -> list:
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.session_id == session_id
    ).order_by(ConversationMessage.created_at).all()
    return [{'role': 'model' if m.role == 'assistant' else m.role, 'parts': [m.content]} for m in messages]

def save_messages(session_id: int, user_msg: str, ai_msg: str, db: Session):
    db.add(ConversationMessage(session_id=session_id, role='user', content=user_msg))
    db.add(ConversationMessage(session_id=session_id, role='assistant', content=ai_msg))
    db.commit()

def log_groq_call(student_id, endpoint, model, tokens_in, tokens_out, latency_ms, db):
    try:
        db.add(LLMApiLog(
            student_id=student_id, endpoint=endpoint, model_used=model,
            tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms,
        ))
        db.commit()
    except Exception:
        pass

# ================================================================
#  MAIN CHAT FUNCTION (unchanged)
# ================================================================
def generate_explanation(session_id: int, student_id: int,
                         user_message: str, topic: str, fcl_level: int,
                         app_state, db: Session,
                         learning_style: str = 'reading') -> dict:
    history = load_conversation_history(session_id, db)
    system_prompt = build_system_prompt(fcl_level, topic, learning_style)

    start_ms = int(time.time() * 1000)
    ai_text, tok_in, tok_out = call_groq(
        prompt=user_message,
        system=system_prompt,
        history=history,
        max_tokens=1000,
        temperature=0.7,
        model=MODEL_PRIMARY,
    )
    latency_ms = int(time.time() * 1000) - start_ms

    image_url = None
    youtube_link = None
    cleaned_text = ai_text

    img_match = re.search(r'\[IMAGE:\s*(.+?)\]', ai_text, re.IGNORECASE)
    if img_match:
        prompt_img = img_match.group(1).strip()
        cleaned_text = re.sub(r'\[IMAGE:\s*.+?\]', '', ai_text, flags=re.IGNORECASE).strip()
        if learning_style == 'visual':
            image_url = generate_image(prompt_img)
            if not image_url:
                youtube_link = recommend_youtube(prompt_img, fcl_level)

    yt_match = re.search(r'\[YOUTUBE:\s*(.+?)\]', ai_text, re.IGNORECASE)
    if yt_match:
        yt_query = yt_match.group(1).strip()
        cleaned_text = re.sub(r'\[YOUTUBE:\s*.+?\]', '', cleaned_text, flags=re.IGNORECASE).strip()
        if not youtube_link:
            youtube_link = recommend_youtube(yt_query, fcl_level)

    save_messages(session_id, user_message, cleaned_text, db)
    log_groq_call(student_id, 'chat_message', MODEL_PRIMARY, tok_in, tok_out, latency_ms, db)

    return {
        'response': cleaned_text,
        'session_id': session_id,
        'tokens_used': tok_in + tok_out,
        'image_url': image_url,
        'youtube_link': youtube_link,
    }

# ================================================================
#  IMPROVED QUESTION GENERATOR (with variety enforcement)
# ================================================================
# Define subtopic lists for major topics
SUBGENRE_MAP = {
    'science_biology': [
        'cell structure', 'photosynthesis', 'human body systems', 'ecosystems',
        'genetics', 'evolution', 'plant biology', 'animal classification',
        'microorganisms', 'food chains', 'reproduction', 'respiratory system'
    ],
    'mathematics_algebra': [
        'linear equations', 'quadratic equations', 'factoring', 'graphing lines',
        'exponents', 'inequalities', 'word problems', 'functions', 'systems of equations'
    ],
    'mathematics_geometry': [
        'angles', 'triangles', 'circles', 'area and perimeter',
        'volume', 'Pythagorean theorem', 'transformations', 'coordinate geometry'
    ],
    'english_comprehension': [
        'main idea', 'inference', 'vocabulary in context', 'author purpose',
        'text structure', 'summarisation', 'character analysis', 'plot elements'
    ],
    'social_studies': [
        'ancient civilizations', 'government branches', 'map skills',
        'economics basics', 'historical events', 'cultural geography'
    ],
}

def extract_subtopic(question_text: str) -> str | None:
    """Try to guess the subtopic from the question text."""
    text = question_text.lower()
    for topic in SUBGENRE_MAP.get('science_biology', []):
        if topic in text:
            return topic
    return None

def generate_question(topic: str, fcl_level: int, app_state,
                      recent_questions: list = None,
                      learning_style: str = 'reading') -> dict:
    print(f"[generate_question] Topic: {topic}, FCL: {fcl_level}, Style: {learning_style}")

    # Hard constraints for low FCL
    if fcl_level <= 4:
        concept_restriction = (
            "The question MUST be about extremely simple, everyday concepts. "
            "Use only concrete objects (apples, toys, animals) and very short words. "
            "No technical terms."
        )
    else:
        concept_restriction = ""

    student_type, difficulty_desc = get_fcl_description(fcl_level, topic)

    # --- Enforce subtopic variety ---
    subtopics = SUBGENRE_MAP.get(topic, ['various concepts within this subject'])
    # Extract previously used subtopics from recent_questions
    used_subtopics = set()
    if recent_questions:
        for q in recent_questions:
            sub = extract_subtopic(q)
            if sub:
                used_subtopics.add(sub)
    available = [s for s in subtopics if s not in used_subtopics]
    if not available:
        available = subtopics  # if all used, cycle through the list again

    chosen_subtopic = available[0] if available else subtopics[0]
    print(f"[generate_question] Chosen subtopic: {chosen_subtopic}")

    avoid_block = ''
    if recent_questions:
        numbered = '\n'.join(f'  {i+1}. {q}' for i, q in enumerate(recent_questions))
        avoid_block = f'\nPREVIOUS QUESTIONS (do NOT repeat or closely resemble):\n{numbered}\n'

    variety_instruction = f"""
You are generating a multiple-choice question for the topic "{topic}".
The specific subtopic you MUST cover is: {chosen_subtopic}.
Do NOT ask about any other subtopic. Do NOT repeat previous questions.
Keep the question appropriate for a {student_type} (FCL {fcl_level}/13).
"""

    # Style hints
    if learning_style == 'visual':
        style_hint = "Include a visual description or use [IMAGE: ...] if helpful."
    else:
        style_hint = {
            'auditory': 'Frame as a spoken question.',
            'kinesthetic': 'Frame as a hands-on or procedural problem.',
            'reading': 'Frame as a text-based comprehension task.',
        }.get(learning_style, '')

    prompt = (
        f'Generate ONE multiple-choice question about {topic.replace("_", " ")} '
        f'for a {student_type} (FCL level {fcl_level}/13).\n\n'
        f'DIFFICULTY RULES:\n{difficulty_desc}\n\n'
        f'{concept_restriction}\n'
        f'{variety_instruction}\n'
        f'STYLE HINT: {style_hint}\n'
        f'{avoid_block}\n'
        'Return ONLY valid JSON:\n'
        '{'
        '"question_id":"<uuid4>",'
        '"question_text":"<the question>",'
        '"options":["<A>","<B>","<C>","<D>"],'
        '"correct_answer":"<exact text of correct option>",'
        '"difficulty":"low|medium|high"'
        '}'
    )

    try:
        raw, _, _ = call_groq(prompt=prompt, max_tokens=500, temperature=0.6, model=MODEL_PRIMARY)
        print(f"[DEBUG] Groq raw response: {raw[:300]}")
    except Exception as e:
        print(f"[ERROR] Groq call failed: {e}")
        return fallback_question(topic, fcl_level, learning_style)

    # Parse JSON
    try:
        q = json.loads(raw.strip())
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            json_str = m.group()
            json_str = json_str.replace('\\', '\\\\')
            try:
                q = json.loads(json_str)
            except:
                q = None
        else:
            q = None

    if not q:
        return fallback_question(topic, fcl_level, learning_style)

    # Ensure required keys
    if 'question_id' not in q:
        q['question_id'] = str(uuid.uuid4())
    if 'options' not in q or not isinstance(q['options'], list):
        q['options'] = ['A', 'B', 'C', 'D']
    if 'correct_answer' not in q:
        q['correct_answer'] = q.get('options', ['A'])[0]
    if 'difficulty' not in q:
        q['difficulty'] = 'medium'

    # Image generation for visual learners
    image_url = None
    if learning_style == 'visual' and 'question_text' in q:
        match_img = re.search(r'\[IMAGE:\s*(.+?)\]', q['question_text'], re.IGNORECASE)
        if match_img:
            img_prompt = match_img.group(1).strip()
            q['question_text'] = re.sub(r'\[IMAGE:\s*.*?\]', '', q['question_text']).strip()
            image_url = generate_image(img_prompt)
    q['image_url'] = image_url

    # Post‑processing filter for low FCL
    if fcl_level <= 4:
        forbidden_words = ['cubic', 'derivative', 'integral', 'matrix', 'function f(x)', 'x^3']
        q_text = q.get('question_text', '').lower()
        if any(word in q_text for word in forbidden_words):
            return fallback_question(topic, fcl_level, learning_style)

    return q

def fallback_question(topic: str, fcl_level: int, learning_style: str) -> dict:
    """Return a safe fallback question when LLM fails."""
    return {
        'question_id': str(uuid.uuid4()),
        'question_text': 'What is the capital of France?',
        'options': ['Berlin', 'Madrid', 'Paris', 'Lisbon'],
        'correct_answer': 'Paris',
        'difficulty': 'low',
        'image_url': None,
    }

# ================================================================
#  HINT GENERATOR (unchanged)
# ================================================================
HINT_INSTRUCTIONS = {
    1: ('Give a very short DIRECTIONAL HINT. Max 2 sentences. Do NOT give the answer.',
        'Give a DIRECTIONAL HINT. Max 2 sentences.'),
    2: ('Give a STEP HINT. Max 2 sentences. Do NOT give the answer.',
        'Give a STRUCTURAL HINT. Max 3 sentences.'),
    3: ('Give a GUIDED HINT showing the first step. Max 3 sentences.',
        'Give a NEAR-ANSWER HINT. Max 4 sentences.'),
}

def generate_hint(question_text: str, correct_answer: str, topic: str,
                  fcl_level: int, hint_level: int,
                  app_state, db: Session, student_id: int) -> str:
    child_instr, std_instr = HINT_INSTRUCTIONS[hint_level]
    instruction = child_instr if fcl_level <= 4 else std_instr
    guardrail = '\nIMPORTANT: Student is young child. Use simple words.' if fcl_level <= 4 else ''
    prompt = (
        f'Question: {question_text}\nCorrect answer: {correct_answer}\n\n'
        f'{instruction}{guardrail}\nStudent FCL: {fcl_level}/13.'
    )
    max_tok = 120 if fcl_level <= 4 else 180
    hint_text, tok_in, tok_out = call_groq(
        prompt=prompt, max_tokens=max_tok, temperature=0.4,
        model=MODEL_FAST if hint_level == 1 else MODEL_PRIMARY
    )
    log_groq_call(student_id, f'hint_level_{hint_level}', MODEL_FAST, tok_in, tok_out, 0, db)
    return hint_text.strip()

# ================================================================
#  FEEDBACK GENERATOR (unchanged)
# ================================================================
FEEDBACK_TONE = {
    range(1, 5): 'Very warm and simple.',
    range(5, 8): 'Friendly and clear.',
    range(8, 11): 'Constructive and academic.',
    range(11, 14): 'Precise and analytical.',
}
def get_feedback_tone(fcl_level: int) -> str:
    for r, tone in FEEDBACK_TONE.items():
        if fcl_level in r:
            return tone
    return 'Clear and constructive.'

def generate_feedback(question_text: str, selected_answer: str,
                      correct_answer: str, topic: str, fcl_level: int,
                      app_state, db: Session, student_id: int) -> dict:
    is_correct = selected_answer.strip().lower() == correct_answer.strip().lower()
    tone = get_feedback_tone(fcl_level)
    topic_label = topic.replace('_', ' ')
    start_ms = int(time.time() * 1000)

    if is_correct:
        prompt = f'A student correctly answered a {topic_label} question (FCL {fcl_level}/13).\nQUESTION: {question_text}\nTHEIR ANSWER: {selected_answer}\n\nTONE: {tone}\nGive brief positive reinforcement (2-3 sentences).'
        raw, tok_in, tok_out = call_groq(prompt=prompt, max_tokens=250, temperature=0.5, model=MODEL_FAST)
        log_groq_call(student_id, 'quiz_feedback_correct', MODEL_FAST, tok_in, tok_out, int(time.time()*1000)-start_ms, db)
        return {'is_correct': True, 'feedback': raw.strip(), 'explanation': None}
    else:
        prompt = f'A student answered a {topic_label} question incorrectly (FCL {fcl_level}/13).\nQUESTION: {question_text}\nTHEIR ANSWER: {selected_answer}\nCORRECT ANSWER: {correct_answer}\n\nTONE: {tone}\nReturn JSON: {{"feedback":"<gently acknowledge, state correct answer>","explanation":"<why correct answer is right>"}}'
        raw, tok_in, tok_out = call_groq(prompt=prompt, max_tokens=400, temperature=0.4, model=MODEL_PRIMARY)
        log_groq_call(student_id, 'quiz_feedback_wrong', MODEL_PRIMARY, tok_in, tok_out, int(time.time()*1000)-start_ms, db)
        try:
            parsed = json.loads(raw.strip())
        except:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = json.loads(m.group()) if m else {'feedback': "That wasn't correct.", 'explanation': f'The correct answer is {correct_answer}.'}
        return {'is_correct': False, 'feedback': parsed.get('feedback', "That wasn't correct."), 'explanation': parsed.get('explanation', f'The correct answer is {correct_answer}.')}

# ================================================================
#  HELPER: FCL description (unchanged)
# ================================================================
def get_fcl_description(fcl_level: int, topic: str = '') -> tuple:
    if fcl_level <= 4:
        return ('primary school child aged 6–10',
                'VERY SIMPLE — one step only, everyday language, no technical terms. Short sentences.')
    elif fcl_level <= 7:
        return ('middle school student aged 11–13',
                'MODERATE — introduce simple terms with definitions. 2-3 step reasoning.')
    elif fcl_level <= 10:
        return ('high school student aged 14–17',
                'CHALLENGING — standard academic terminology, multi-step reasoning.')
    else:
        return ('university student',
                'ADVANCED — technical and discipline-specific language, abstract reasoning.')

# ================================================================
#  LIBRARY STUDY ASSISTANT (unchanged)
# ================================================================
def generate_library_explanation(content_text: str, student_question: str,
                                 topic: str, fcl_level: int,
                                 learning_style: str,
                                 session_id: int, student_id: int,
                                 db: Session) -> dict:
    system = build_system_prompt(fcl_level, topic, learning_style)
    history = load_conversation_history(session_id, db)
    if not history:
        context_msg = f'The student is studying this document:\n\n---\n{content_text[:8000]}\n---\nSummarise key points then ask what they would like to explore first.'
        user_prompt = context_msg
    else:
        user_prompt = student_question
    ai_text, tok_in, tok_out = call_groq(prompt=user_prompt, system=system, history=history, max_tokens=1000)
    save_messages(session_id, student_question or 'Start session', ai_text, db)
    log_groq_call(student_id, 'library_tutor', MODEL_PRIMARY, tok_in, tok_out, 0, db)
    return {'response': ai_text, 'session_id': session_id}

# ================================================================
#  LEARNING STYLE ANALYZER (unchanged)
# ================================================================
def analyse_learning_style(interaction_log: list, current_style: str) -> dict:
    if len(interaction_log) < 20:
        return {'detected_style': current_style, 'confidence': 0.5, 'changed': False}
    counts = {'visual': 0, 'auditory': 0, 'reading': 0, 'kinesthetic': 0}
    for interaction in interaction_log:
        m = interaction.get('modality', 'reading')
        if m in counts:
            counts[m] += 1
    total = sum(counts.values()) or 1
    dominant = max(counts, key=counts.get)
    confidence = round(counts[dominant] / total, 2)
    return {
        'detected_style': dominant,
        'confidence': confidence,
        'changed': dominant != current_style and confidence >= 0.5,
    }