import { api } from './client';

export const getChatHistory = (subjectId) =>
  api.get(`/chat/history${subjectId ? `?subject_id=${subjectId}` : ''}`);

export const clearChatHistory = (subjectId) =>
  api.delete(`/chat/history${subjectId ? `?subject_id=${subjectId}` : ''}`);

export async function sendTutorMessage(payload, onChunk, onDone, onError) {
  console.log('[sendTutorMessage] Sending payload:', payload);
  try {
    // api.post returns the parsed JSON directly (not { data: ... })
    const responseData = await api.post('/chat/simple', payload);
    console.log('[sendTutorMessage] Response data:', responseData);
    
    let responseText = null;
    if (responseData && typeof responseData === 'object') {
      responseText = responseData.response || responseData.reply || responseData.text;
    }
    
    if (responseText && responseText.trim()) {
      console.log('[sendTutorMessage] Response text (first 100):', responseText.substring(0, 100));
      onChunk?.(responseText);
    } else {
      console.error('[sendTutorMessage] No valid response text. Data:', responseData);
      onChunk?.('The AI service returned an empty response. Please try again.');
    }
    onDone?.();
  } catch (err) {
    console.error('[sendTutorMessage] Error:', err);
    onError?.(err);
  }
}

export const sendTutorMessageSync = (payload) =>
  api.post('/chat/simple', payload);

export const getHint = (questionId) =>
  api.get(`/hints/${questionId}`);