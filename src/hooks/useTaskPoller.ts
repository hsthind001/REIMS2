import { useState, useEffect, useRef } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

export interface TaskStatus {
  state: 'PENDING' | 'STARTED' | 'RETRY' | 'FAILURE' | 'SUCCESS';
  result?: any;
  error?: string;
}

export function useTaskPoller(jobId: string | null) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  
  useEffect(() => {
    if (!jobId) return;

    let mounted = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/extract/status/${jobId}`);
        if (res.ok && mounted) {
           const data = await res.json();
           setStatus(data);
           
           if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
             return; // Stop polling
           }
        }
      } catch (e) {
        console.error("Polling error", e);
      }
      
      if (mounted) {
        timeoutId = setTimeout(poll, 2000);
      }
    };

    poll();

    return () => {
      mounted = false;
      clearTimeout(timeoutId);
    };
  }, [jobId]);

  return status;
}
