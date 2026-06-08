import { useState } from 'react';
import api from '../services/api';

export default function AudioPlayer({ text, label = '🔊 Listen' }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePlay = async () => {
    if (!text) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/audio/speak', { text }, {
        responseType: 'blob',
      });
      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
      audio.onended = () => URL.revokeObjectURL(audioUrl);
    } catch (err) {
      console.warn('Falling back to browser TTS', err);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
      setError('Using browser voice (API not available)');
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-1">
      <button
        onClick={handlePlay}
        disabled={loading}
        className="text-teal hover:text-teal-dim transition-colors text-sm flex items-center gap-1"
        title="Read aloud"
      >
        {loading ? (
          <span className="inline-block w-4 h-4 border-2 border-teal/30 border-t-teal rounded-full animate-spin" />
        ) : (
          <span>{label}</span>
        )}
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}