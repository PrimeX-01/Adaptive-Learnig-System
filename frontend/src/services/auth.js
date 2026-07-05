import { api } from './client';

function normalize(data) {
  const nameParts  = (data.name || '').trim().split(' ');
  const first_name = nameParts[0] || '';
  const last_name  = nameParts.slice(1).join(' ') || '';

  return {
    access_token: data.access_token,
    token_type:   data.token_type || 'bearer',
    user: {
      id:               data.user_id,
      name:             data.name,
      first_name,
      last_name,
      role:             data.role,
      is_teacher:       data.role === 'teacher',
      student_type:     data.student_type     || null,
      learning_style:   data.learning_style   || 'reading',
      dominant_vark:    data.learning_style   || 'reading',
      overall_fcl:      data.overall_fcl      ?? 1.0,
      grade_id:         data.grade_id         || null,
      class_id:         data.class_id         || null,
      faculty_id:       data.faculty_id       || null,
      programme_id:     data.programme_id     || null,
      current_level:    data.current_level    || null,
      current_semester: data.current_semester || null,
      profile_pic:      data.profile_pic      || '',
      status:           data.status           || 'active',
    },
  };
}

export async function loginUser(email, password) {
  const data = await api.post('/auth/login', { email, password });
  if (data.status === 'pending') {
    return { status: 'pending', role: data.role, message: data.message };
  }
  return normalize(data);
}

/* ── Unified registration ── */
export async function registerUser(payload) {
  // payload comes from Register.jsx:
  // { first_name, last_name, email, password, role, ... }
  switch (payload.role) {
    case 'student':
      return registerStudent(payload);
    case 'teacher':
      return registerTeacher(payload);
    case 'lecturer':
      return registerLecturer(payload);
    default:
      throw new Error(`Unknown role for registration: ${payload.role}`);
  }
}

/* ── Student registration (school / tertiary) ── */
async function registerStudent(formData) {
  const body = {
    name:         `${formData.first_name} ${formData.last_name}`.trim(),
    email:        formData.email,
    password:     formData.password,
    student_type: formData.education_level,   // 'school' or 'tertiary'
    learning_style: formData.learning_style || 'reading',
  };

  if (formData.education_level === 'school') {
    // Backend requires grade_id and class_id
    body.grade_id = formData.grade_id;
    body.class_id = formData.class_id;
  } else {
    // Tertiary: faculty_id, programme_id, level, course_pcl_ids
    body.faculty_id   = formData.faculty_id;
    body.programme_id = formData.programme_id;
    body.level        = formData.level;
    body.course_pcl_ids = formData.course_pcl_ids || [];
  }

  const data = await api.post('/auth/register/student', body);
  return normalize(data);
}

/* ── Teacher registration ── */
async function registerTeacher(formData) {
  const body = {
    name:  `${formData.first_name} ${formData.last_name}`.trim(),
    email: formData.email,
    password: formData.password,
    class_subject_ids: formData.class_subject_ids || [],
  };
  return api.post('/auth/register/teacher', body);
}

/* ── Lecturer registration ── */
async function registerLecturer(formData) {
  const body = {
    name:       `${formData.first_name} ${formData.last_name}`.trim(),
    email:      formData.email,
    password:   formData.password,
    faculty_id: formData.faculty_id,
    pcl_ids:    formData.pcl_ids || [],
  };
  return api.post('/auth/register/lecturer', body);
}

export async function logoutUser() {
  return Promise.resolve();
}

export async function forgotPassword(email) {
  return api.post('/auth/forgot-password', { email });
}

export async function resetPassword(token, new_password) {
  return api.post('/auth/reset-password', { token, new_password });
}