import { useState, useEffect, useRef } from 'react';

interface ExtractionStatus {
  status: string | null;
  progress: number;
  recordsLoaded: number;
  error: string | null;
}

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

export function useExtractionStatus(uploadId: number | null): ExtractionStatus {
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [recordsLoaded, setRecordsLoaded] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const usePollingRef = useRef(false);

  useEffect(() => {
    if (!uploadId) {
      return;
    }

    // Try WebSocket first
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = API_BASE_URL.replace(/^https?:\/\//, '').replace(/^http:\/\//, '');
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/extraction-status/${uploadId}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected for upload_id=${uploadId}`);
        usePollingRef.current = false;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setStatus(data.status);
          setProgress(data.progress || 0);
          setRecordsLoaded(data.records_loaded || 0);
          if (data.error) {
            setError(data.error);
          }

          // Close if completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            ws.close();
            wsRef.current = null;
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (err) => {
        console.warn('WebSocket error, falling back to polling:', err);
        usePollingRef.current = true;
        ws.close();
        wsRef.current = null;
      };

      ws.onclose = () => {
        if (usePollingRef.current && (status === null || (status !== 'completed' && status !== 'failed'))) {
          // Fallback to polling if WebSocket closed unexpectedly
          startPolling();
        }
      };
    } catch (err) {
      console.warn('Failed to create WebSocket, using polling:', err);
      usePollingRef.current = true;
      startPolling();
    }

    // Fallback polling function
    const startPolling = () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }

      const fetchStatus = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/documents/uploads?upload_id=${uploadId}`, {
            credentials: 'include'
          });
          
          if (response.ok) {
            const data = await response.json();
            const upload = Array.isArray(data.items) 
              ? data.items.find((u: any) => u.id === uploadId)
              : data;
            
            if (upload) {
              setStatus(upload.extraction_status);
              setRecordsLoaded(upload.records_loaded || 0);
              
              if (upload.extraction_status === 'completed' || upload.extraction_status === 'failed') {
                if (pollingIntervalRef.current) {
                  clearInterval(pollingIntervalRef.current);
                  pollingIntervalRef.current = null;
                }
              }
            }
          }
        } catch (err) {
          console.error('Failed to fetch extraction status:', err);
        }
      };

      // Poll immediately, then every 5 seconds
      fetchStatus();
      pollingIntervalRef.current = setInterval(fetchStatus, 5000);
    };

    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [uploadId, status]);

  return { status, progress, recordsLoaded, error };
}

