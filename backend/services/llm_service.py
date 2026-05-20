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

MODEL_PRIMARY = 'llama-3.3-70b-versatile'   # Full explanations, quiz gen, chat
MODEL_FAST    = 'llama3-8b-8192'            # Simple feedback, hint level 1
MODEL_LONG    = 'mixtral-8x7b-32768'        # Long explanations (if needed)

# ── Hugging Face configuration ─────────────────────────────────────
HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HF_IMAGE_MODEL = os.getenv('HUGGINGFACE_IMAGE_MODEL', 'runwayml/stable-diffusion-v1-5')
# List of working free models – will try in order
HF_MODELS = [
    HF_IMAGE_MODEL,
    'stabilityai/stable-diffusion-2-1',
    'runwayml/stable-diffusion-v1-5',
]
HF_API_URL = None  # will be set per attempt

# ================================================================
#  CORE GROQ CALLER
# ================================================================
def call_groq(prompt: str,
              system: str = None,
              history: list = None,
              max_tokens: int = 600,
              temperature: float = 0.7,
              model: str = MODEL_PRIMARY) -> tuple[str, int, int]:
    messages = []

    # System message
    if system and system.strip():
        messages.append({'role': 'system', 'content': system.strip()})

    # History
    if history:
        for msg in history:
            role = msg.get('role')
            if role == 'model':
                role = 'assistant'
            content = msg.get('parts', [msg.get('content', '')])[0]
            if content and content.strip():
                messages.append({'role': role, 'content': content.strip()})

    # User message – ensure it's not empty
    if not prompt or not prompt.strip():
        prompt = "Please respond with a helpful answer."
    messages.append({'role': 'user', 'content': prompt.strip()})

    # Final sanity check
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
#  IMAGE GENERATION (Hugging Face) – with fallback models
# ================================================================
def generate_image(prompt: str) -> str | None:
    """Generate an image using Hugging Face Inference API (router endpoint)."""
    if not HF_API_KEY:
        print("[Image] No Hugging Face API key")
        return None

    # Use the router endpoint (free tier works)
    url = f"https://router.huggingface.co/hf-inference/models/{HF_IMAGE_MODEL}"
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "options": {"wait_for_model": True}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            img_b64 = base64.b64encode(response.content).decode("utf-8")
            print(f"[Image] Success for prompt: {prompt[:50]}...")
            return f"data:image/png;base64,{img_b64}"
        else:
            print(f"[Image] HF failed: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"[Image] HF error: {e}")
        return None
# ================================================================
#  SYSTEM PROMPT (FCL + learning style) – unchanged content
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
        'visual': (
            'LEARNING STYLE: Visual. Always include at least one of: ASCII diagram, Markdown table, '
            'numbered visual breakdown, or a YouTube recommendation formatted as: '
            '📹 **Watch:** [Descriptive title](https://www.youtube.com/results?search_query=ENCODED_QUERY). '
            'When an image would help, write [IMAGE: detailed description of the image to generate]. '
            'Use spacing and layout to make content scannable.'
        ),
        'auditory': (
            'LEARNING STYLE: Auditory. Write in a conversational, spoken tone as if explaining aloud. '
            'Use rhythm in explanations. Where helpful, suggest: '
            '📹 **Watch/Listen:** [title](YouTube link) for audio-visual reinforcement.'
        ),
        'reading': (
            'LEARNING STYLE: Reading/Writing. Provide well-structured written explanations with clear headings, '
            'bullet points, and concise definitions. Encourage note-taking.'
        ),
        'kinesthetic': (
            'LEARNING STYLE: Kinesthetic. Always include a hands-on practice step, worked example, '
            'or a "try it yourself" problem at the end. '
            'Frame explanations as steps to DO, not just concepts to understand.'
        ),
    }
    style = style_map.get(learning_style, style_map['reading'])

    return (
        f'You are an AI tutor specialising in {subject_label} '
        f'for the SiveAdapt adaptive learning system at the University of Eswatini. '
        f'{cog} {style} '
        'Structure every response: (1) clear explanation, (2) worked example, '
        '(3) comprehension check or practice problem. '
        'You may use Markdown, LaTeX math ($...$), and code blocks. '
        'Keep responses under 300 words unless depth is essential.'
    )

# ================================================================
#  CONVERSATION HISTORY MANAGEMENT
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
#  MAIN CHAT FUNCTION (with image & YouTube markers)
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

    # Parse markers
    image_url = None
    youtube_link = None

    match_img = re.search(r'\[IMAGE:\s*(.+?)\]', ai_text, re.IGNORECASE)
    if match_img:
        prompt_img = match_img.group(1).strip()
        ai_text = re.sub(r'\[IMAGE:\s*.+?\]', '', ai_text, flags=re.IGNORECASE).strip()
        if learning_style == 'visual':
            image_url = generate_image(prompt_img)
            if not image_url:
                youtube_link = recommend_youtube(prompt_img)

    match_yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', ai_text, re.IGNORECASE)
    if match_yt:
        yt_query = match_yt.group(1).strip()
        ai_text = re.sub(r'\[YOUTUBE:\s*.+?\]', '', ai_text, flags=re.IGNORECASE).strip()
        if not youtube_link:
            youtube_link = recommend_youtube(yt_query)

    save_messages(session_id, user_message, ai_text, db)
    log_groq_call(student_id, 'chat_message', MODEL_PRIMARY, tok_in, tok_out, latency_ms, db)

    return {
        'response': ai_text,
        'session_id': session_id,
        'tokens_used': tok_in + tok_out,
        'image_url': image_url,
        'youtube_link': youtube_link,
    }

# ================================================================
#  QUESTION GENERATOR (using Groq)
# ================================================================
def generate_question(topic: str, fcl_level: int, app_state,
                      recent_questions: list = None,
                      learning_style: str = 'reading') -> dict:
    print(f"[generate_question] Topic: {topic}, FCL: {fcl_level}, Style: {learning_style}")

    # Hard constraints for low FCL
    if fcl_level <= 4:
        concept_restriction = (
            "The question MUST be about extremely simple, everyday concepts. "
            "For mathematics: only counting, single‑digit addition/subtraction, or naming shapes. "
            "Do NOT use algebra, equations, matrices, fractions, decimals, or any word like 'row', 'matrix', 'linear', 'solve for x', 'variable', 'function', 'graph', 'cubic', 'derivative'. "
            "Use only concrete objects (apples, toys, animals) and very short words."
        )
    else:
        concept_restriction = ""

    student_type, difficulty_desc = get_fcl_description(fcl_level, topic)
    recent_questions = (recent_questions or [])[-10:]

    avoid_block = ''
    if recent_questions:
        numbered = '\n'.join(f'  {i+1}. {q}' for i, q in enumerate(recent_questions))
        avoid_block = f'\nALREADY ASKED — do NOT repeat or closely resemble:\n{numbered}\nChoose a DIFFERENT concept, scenario or number set.\n'

    # Style hints
    if learning_style == 'visual':
        style_hint = (
            "LEARNING STYLE: Visual. The question should be accompanied by a simple ASCII diagram or "
            "a clear visual description. Use [IMAGE: detailed description] if an image would help. "
            "Even for multiple choice, prefer visual scenarios (e.g., 'Which shape has four equal sides?' "
            "with shapes described in words or ascii)."
        )
    else:
        style_hint = {
            'auditory':    "Frame the question as something that could be discussed or described verbally.",
            'kinesthetic': "Frame the question as a practical problem, procedure, or hands-on scenario.",
            'reading':     "Frame the question as a text-based comprehension or definition task.",
        }.get(learning_style, '')

    prompt = (
        f'Generate ONE multiple-choice question about {topic.replace("_", " ")} '
        f'for a {student_type} (FCL level {fcl_level}/13).\n\n'
        f'DIFFICULTY RULES (follow strictly):\n{difficulty_desc}\n\n'
        f'{concept_restriction}\n\n'
        f'STYLE HINT: {style_hint}\n\n'
        f'{avoid_block}'
        f'The question MUST be appropriate for a {student_type}. '
        f'Do NOT use knowledge beyond what a {student_type} would have.\n\n'
        'Return ONLY valid JSON — no preamble, no explanation:\n'
        '{'
        '"question_id":"<uuid4>",'
        '"question_text":"<the question>",'
        '"options":["<A>","<B>","<C>","<D>"],'
        '"correct_answer":"<exact text of correct option>",'
        '"difficulty":"low|medium|high"'
        '}'
    )

    try:
        raw, _, _ = call_groq(prompt=prompt, max_tokens=500, temperature=0.4, model=MODEL_PRIMARY)
        print(f"[DEBUG] Groq raw response: {raw[:500]}")
    except Exception as e:
        print(f"[ERROR] Groq call failed: {e}")
        return {
            'question_id': str(uuid.uuid4()),
            'question_text': 'What is 2 + 2?',
            'options': ['3', '4', '5', '6'],
            'correct_answer': '4',
            'difficulty': 'low',
            'image_url': None,
        }

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
        q = {
            'question_id': str(uuid.uuid4()),
            'question_text': 'What is 5 + 3?',
            'options': ['6', '7', '8', '9'],
            'correct_answer': '8',
            'difficulty': 'low',
        }
        print("[WARNING] Using fallback question due to JSON parsing error.")

    # Ensure required keys
    if 'question_id' not in q:
        q['question_id'] = str(uuid.uuid4())
    if 'options' not in q or not isinstance(q['options'], list):
        q['options'] = ['A', 'B', 'C', 'D']
    if 'correct_answer' not in q:
        q['correct_answer'] = q.get('options', ['A'])[0]
    if 'difficulty' not in q:
        q['difficulty'] = 'medium'

    # ----- IMAGE GENERATION for visual learners -----
    image_url = None
    if learning_style == 'visual' and 'question_text' in q:
        match_img = re.search(r'\[IMAGE:\s*(.+?)\]', q['question_text'], re.IGNORECASE)
        if match_img:
            img_prompt = match_img.group(1).strip()
            # Remove the marker from the question text
            q['question_text'] = re.sub(r'\[IMAGE:\s*.*?\]', '', q['question_text']).strip()
            # Generate the image
            image_url = generate_image(img_prompt)
            if not image_url:
                print(f"[WARNING] Could not generate image for prompt: {img_prompt}")
    q['image_url'] = image_url

    # Post‑processing filter for low FCL (≤4) – reject advanced terms
    if fcl_level <= 4:
        forbidden_words = [
            'cubic', 'derivative', 'integral', 'matrix', 'vector',
            'row', 'column', 'linear algebra', 'graph of a function',
            'polynomial degree', 'local maximum', 'local minimum',
            'differentiable', 'continuous', 'limit', 'asymptote',
            'function f(x)', 'f(x) =', 'x^3', 'x³'
        ]
        q_text = q.get('question_text', '').lower()
        if any(word in q_text for word in forbidden_words):
            print(f"[WARNING] Question too hard for FCL {fcl_level}, using fallback.")
            q = {
                'question_id': str(uuid.uuid4()),
                'question_text': 'What is 2 + 4?',
                'options': ['5', '6', '7', '8'],
                'correct_answer': '6',
                'difficulty': 'low',
                'image_url': None,
            }

    return q

# ================================================================
#  HINT GENERATOR (using Groq)
# ================================================================
HINT_INSTRUCTIONS = {
    1: (
        'Give a very short DIRECTIONAL HINT using simple words a young child knows. '
        'Point to the right idea using an everyday object as an example. '
        'Maximum 2 short sentences. Do NOT show numbers, steps, or the answer. '
        'Be warm and encouraging.',
        'Give a DIRECTIONAL HINT — point toward the right concept without revealing the approach. '
        'Maximum 2 sentences. Do NOT give any steps or show the answer.',
    ),
    2: (
        'Give a STEP HINT using the simplest words possible. '
        'Tell the child WHAT to think about first, using an everyday example. '
        'Maximum 2 short sentences. Do NOT give the answer.',
        'Give a STRUCTURAL HINT — outline the approach without showing the calculation or answer. '
        'Maximum 3 sentences.',
    ),
    3: (
        'Give a GUIDED HINT showing the very first small step in plain words. '
        'Tell the child exactly what to do next in one simple sentence. '
        'Maximum 3 short sentences. Still do NOT give the final answer.',
        'Give a NEAR-ANSWER HINT — show the first step clearly and indicate what to do next. '
        'The student should be able to finish from here. Maximum 4 sentences.',
    ),
}

def generate_hint(question_text: str, correct_answer: str, topic: str,
                  fcl_level: int, hint_level: int,
                  app_state, db: Session, student_id: int) -> str:
    child_instr, std_instr = HINT_INSTRUCTIONS[hint_level]
    instruction = child_instr if fcl_level <= 4 else std_instr
    guardrail = (
        '\nIMPORTANT: Student is a young child (6–10). '
        'Use ONLY words a 7-year-old knows. No fractions, algebra, or jargon. '
        'Very short sentences.' if fcl_level <= 4 else ''
    )
    prompt = (
        f'A student is working on this {topic.replace("_", " ")} question:\n'
        f'QUESTION: {question_text}\n'
        f'CORRECT ANSWER: {correct_answer}\n\n'
        f'{instruction}{guardrail}\n'
        f'Student FCL level: {fcl_level}/13.'
    )
    max_tok = 120 if fcl_level <= 4 else 180
    hint_text, tok_in, tok_out = call_groq(
        prompt=prompt, max_tokens=max_tok, temperature=0.4, model=MODEL_FAST if hint_level == 1 else MODEL_PRIMARY
    )
    log_groq_call(student_id, f'hint_level_{hint_level}', MODEL_FAST, tok_in, tok_out, 0, db)
    return hint_text.strip()

# ================================================================
#  FEEDBACK GENERATOR (using Groq)
# ================================================================
FEEDBACK_TONE = {
    range(1, 5):   'Very warm, simple, and encouraging. Short sentences. Fun language.',
    range(5, 8):   'Friendly and clear. Briefly explain why the answer is right or wrong.',
    range(8, 11):  'Constructive and academic. Explain the correct reasoning concisely.',
    range(11, 14): 'Precise and analytical. Reference the relevant concept or rule directly.',
}
def get_feedback_tone(fcl_level: int) -> str:
    for r, tone in FEEDBACK_TONE.items():
        if fcl_level in r:
            return tone
    return 'Be clear and constructive.'

def generate_feedback(question_text: str, selected_answer: str,
                      correct_answer: str, topic: str, fcl_level: int,
                      app_state, db: Session, student_id: int) -> dict:
    is_correct = selected_answer.strip().lower() == correct_answer.strip().lower()
    tone = get_feedback_tone(fcl_level)
    topic_label = topic.replace('_', ' ')
    start_ms = int(time.time() * 1000)

    if is_correct:
        prompt = (
            f'A student correctly answered a {topic_label} question (FCL {fcl_level}/13).\n'
            f'QUESTION: {question_text}\n'
            f'THEIR ANSWER: {selected_answer}\n\n'
            f'TONE: {tone}\n'
            'Give brief positive reinforcement (2-3 sentences max). '
            'Optionally add one interesting follow-up fact. '
            'Do NOT repeat the question. No preamble.'
        )
        raw, tok_in, tok_out = call_groq(prompt=prompt, max_tokens=250, temperature=0.5, model=MODEL_FAST)
        latency_ms = int(time.time() * 1000) - start_ms
        log_groq_call(student_id, 'quiz_feedback_correct', MODEL_FAST, tok_in, tok_out, latency_ms, db)
        return {'is_correct': True, 'feedback': raw.strip(), 'explanation': None}
    else:
        prompt = (
            f'A student answered a {topic_label} question incorrectly (FCL {fcl_level}/13).\n'
            f'QUESTION: {question_text}\n'
            f'THEIR ANSWER: {selected_answer}\n'
            f'CORRECT ANSWER: {correct_answer}\n\n'
            f'TONE: {tone}\n'
            'Return ONLY valid JSON:\n'
            '{"feedback":"<1-2 sentences: acknowledge gently, state correct answer>",'
            '"explanation":"<2-4 sentences: WHY the correct answer is right, '
            f'calibrated to FCL {fcl_level}>"' + '}'
        )
        raw, tok_in, tok_out = call_groq(prompt=prompt, max_tokens=400, temperature=0.4, model=MODEL_PRIMARY)
        latency_ms = int(time.time() * 1000) - start_ms
        log_groq_call(student_id, 'quiz_feedback_wrong', MODEL_PRIMARY, tok_in, tok_out, latency_ms, db)
        try:
            parsed = json.loads(raw.strip())
        except:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = json.loads(m.group()) if m else {
                'feedback': "That wasn't quite right.",
                'explanation': f'The correct answer is: {correct_answer}',
            }
        return {
            'is_correct': False,
            'feedback': parsed.get('feedback', "That wasn't correct."),
            'explanation': parsed.get('explanation', f'The correct answer is: {correct_answer}'),
        }

# ================================================================
#  HELPER: FCL description (unchanged)
# ================================================================
def get_fcl_description(fcl_level: int, topic: str = '') -> tuple:
    subject = topic.split('_')[0].lower() if topic else ''
    if fcl_level <= 4:
        examples = {
            'mathematics': 'counting objects, basic addition/subtraction (single digits), simple shapes',
            'science':     'names of animals, parts of the body, day/night, plants vs animals',
            'english':     'simple 3-4 letter words, naming pictures, basic sentences',
            'social':      'family members, home, school, community helpers like teachers and nurses',
            'computer':    'what a computer is, mouse and keyboard, on/off, basic internet safety',
        }.get(subject, 'very basic everyday concepts a young child would know')
        return (
            'primary school child aged 6–10 years old',
            f'VERY SIMPLE — one step only, everyday language, no technical terms. '
            f'For this topic focus on: {examples}. '
            f'Short sentences. Use familiar objects or animals as context.'
        )
    elif fcl_level <= 7:
        return ('middle school student aged 11–13',
                'MODERATE — introduce simple topic terms with brief definitions. '
                '2-3 step reasoning maximum. Real-world examples a teenager would relate to.')
    elif fcl_level <= 10:
        return ('high school student aged 14–17',
                'CHALLENGING — standard academic terminology, multi-step reasoning, '
                'analysis or application of concepts. Secondary school curriculum level.')
    else:
        return ('university student',
                'ADVANCED — technical and discipline-specific language, '
                'abstract reasoning, evaluation or synthesis. University curriculum level.')

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
        context_msg = (
            f'The student is studying the following document. '
            f'Use it as the basis for your tutoring session:\n\n'
            f'--- DOCUMENT START ---\n{content_text[:8000]}\n--- DOCUMENT END ---\n\n'
            f'Begin by briefly summarising the key points in a way appropriate '
            f'for a {get_fcl_description(fcl_level, topic)[0]}. '
            f'Then ask what they would like to explore first.'
        )
        user_prompt = context_msg
    else:
        user_prompt = student_question
    ai_text, tok_in, tok_out = call_groq(prompt=user_prompt, system=system, history=history, max_tokens=1000)
    save_messages(session_id, student_question or 'Start session', ai_text, db)
    log_groq_call(student_id, 'library_tutor', MODEL_PRIMARY, tok_in, tok_out, 0, db)
    return {'response': ai_text, 'session_id': session_id}

# ================================================================
#  YOUTUBE HELPER (unchanged)
# ================================================================
def build_youtube_url(topic: str, fcl_level: int, context: str = '') -> str:
    level_str = ('for kids' if fcl_level <= 4 else
                 'for middle school' if fcl_level <= 7 else
                 'for high school' if fcl_level <= 10 else 'university level')
    query = f"{topic.replace('_', ' ')} {level_str} {context}".strip()
    return f"https://www.youtube.com/results?search_query={quote(query)}"


def recommend_youtube(query: str, fcl_level: int = None) -> str:
    """Return a YouTube search results URL for a query.

    If fcl_level is provided, include a level hint; otherwise default to a general level.
    """
    if not query:
        return build_youtube_url('education', fcl_level or 8)
    # If the query looks like a descriptive sentence (image prompt), shorten to key nouns
    topic = query.strip()
    level = fcl_level or 8
    return build_youtube_url(topic, level)

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