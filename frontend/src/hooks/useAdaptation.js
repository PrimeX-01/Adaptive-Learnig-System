import { useState, useCallback } from 'react';
import api from '../services/api';

export function useAdaptation(initialFCL = 5, initialSubjectId = null) {
  const [fcl,       setFCL]       = useState(initialFCL);
  const [subjectId, setSubjectId] = useState(initialSubjectId);
  const [modality,  setModality]  = useState('text');

  const refreshFCL = useCallback(async (studentId, topicId) => {
    try {
      const { data } = await api.get(`/api/students/${studentId}/fcl/${topicId}`);
      setFCL(data.fcl_level);
      setModality(data.preferred_modality || 'text');
    } catch (err) {
      console.error('FCL refresh failed:', err);
    }
  }, []);

  return { fcl, setFCL, subjectId, setSubjectId, modality, setModality, refreshFCL };
}
