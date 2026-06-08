import { api } from './client';

/* ─────────────────────────────────────────────────────────────────
   Normalize the backend's flat login/register response into the
   shape the rest of the frontend expects:
     { access_token, user: { id, role, first_name, last_name, ... } }

   Backend returns:
     { access_token, student_id, name, is_teacher, grade,
       overall_fcl, learning_style, profile_pic, ... }
───────────────────────────────────────────────────────────────── */
function normalize(data) {
  const nameParts = (data.name || '').trim().split(' ');
  const first_name = nameParts[0] || '';
  const last_name  = nameParts.slice(1).join(' ') || '';

  return {
    access_token: data.access_token,
    token_type:   data.token_type || 'bearer',
    user: {
      id:             data.student_id,
      name:           data.name,
      first_name,
      last_name,
      role:           data.is_teacher ? 'teacher' : 'student',
      is_teacher:     data.is_teacher,
      grade:          data.grade,
      overall_fcl:    data.overall_fcl,
      learning_style: data.learning_style,
      dominant_vark:  data.learning_style,   // alias used in TutorChat
      profile_pic:    data.profile_pic || '',
    },
  };
}

/* ── Login ── */
export async function loginUser(email, password) {
  const data = await api.post('/auth/login', { email, password });
  return normalize(data);
}

/* ── Register ──
   Converts the new frontend payload shape into what the backend expects.

   Frontend sends:
     { first_name, last_name, email, password, role,
       grade_level?, education_level?,
       subjects? (teacher: [{name, grade_level}]) }

   Backend expects:
     { name, email, password, is_teacher,
       grade?,                         ← student
       subject_ids?,                   ← tertiary student
       teach_subject_name?,            ← teacher
       teach_subject_code?,            ← teacher
       teach_grades? }                 ← teacher
*/
export async function registerUser(payload) {
  const isTeacher = payload.role === 'teacher' || payload.is_teacher;

  const body = {
    name:       `${payload.first_name} ${payload.last_name}`.trim(),
    email:      payload.email,
    password:   payload.password,
    is_teacher: isTeacher,
  };

  if (!isTeacher) {
    // grade_level is a string from the select — convert to int
    const grade = Number(payload.grade_level) || null;
    body.grade = grade;

    if (payload.education_level === 'tertiary' && payload.subject_ids?.length) {
      body.subject_ids = payload.subject_ids;
    }
    if (payload.learning_style) {
      body.learning_style = payload.learning_style;
    }
  } else {
    // Teacher: subjects array comes as [{name, grade_level}]
    const subs = payload.subjects || [];
    if (subs.length > 0) {
      const first = subs[0];
      body.teach_subject_name = first.name;
      // Auto-generate a code from the name (e.g. "Mathematics" → "MATH")
      body.teach_subject_code = first.name
        .toUpperCase()
        .replace(/[^A-Z]/g, '')
        .slice(0, 6) || 'SUBJ';
      body.teach_grades = subs.map(s => Number(s.grade_level)).filter(Boolean);
    } else {
      // No subjects provided — backend requires at least one
      throw new Error('Please add at least one subject before creating your account.');
    }
  }

  const data = await api.post('/auth/register', body);
  return normalize(data);
}

/* ── Logout (no backend endpoint — just clear session) ── */
export async function logoutUser() {
  // Backend has no /logout route; clearing localStorage is sufficient
  return Promise.resolve();
}

/* ── Password ── */
export async function forgotPassword(email) {
  return api.post('/auth/forgot-password', { email });
}

export async function resetPassword(token, new_password) {
  return api.post('/auth/reset-password', { token, new_password });
}
