/* ── SiveAdapt API client (simplified, using native fetch) ── */
const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api';

function getToken() {
  return localStorage.getItem('sa_token');
}

async function request(method, path, body = null) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const url = `${BASE_URL}${path}`;
  const options = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  };

  console.log(`[client] ${method} ${url}`, body ? body : '');

  const res = await fetch(url, options);

  if (res.status === 401) {
    localStorage.removeItem('sa_token');
    localStorage.removeItem('sa_user');
    window.location.href = '/auth';
    return null;
  }

  // Try to parse JSON, but handle empty responses
  let data = null;
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await res.json();
  } else {
    const text = await res.text();
    console.warn('[client] Non-JSON response:', text);
    data = { message: text };
  }

  if (!res.ok) {
    const message = data.detail || data.message || `Request failed: ${res.status}`;
    throw new Error(message);
  }

  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),
};

/* ── SSE streaming helper (unchanged) ── */
export async function streamRequest(path, body, onChunk, onDone, onError) {
  const token = getToken();
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(`Stream error: ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) { onDone?.(); break; }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const chunk = line.slice(6);
          if (chunk === '[DONE]') { onDone?.(); return; }
          onChunk?.(chunk);
        }
      }
    }
  } catch (err) {
    onError?.(err);
  }
}