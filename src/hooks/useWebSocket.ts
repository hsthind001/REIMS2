import { useEffect, useRef, useState, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Attempt to derive WS URL from API URL
// If API ends in /api/v1, typically WS is at root /ws or /api/v1/ws
// We'll guess /ws based on common patterns, but make it overridable
const DEFAULT_WS_URL = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '/ws'); 

interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp?: string;
}

export const useWebSocket = (path: string = '', baseUrl: string = DEFAULT_WS_URL) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  
  const fullUrl = `${baseUrl}${path}`;

  const connect = useCallback(() => {
    try {
      const socket = new WebSocket(fullUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('WebSocket Connected');
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage({ ...data, timestamp: new Date().toISOString() });
        } catch (e) {
          // If not JSON, wrapped in an object
          setLastMessage({ type: 'raw', payload: event.data, timestamp: new Date().toISOString() });
        }
      };

      socket.onclose = () => {
        console.log('WebSocket Disconnected');
        setIsConnected(false);
        // Basic reconnect logic
        reconnectTimeoutRef.current = window.setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 5000);
      };

      socket.onerror = (error) => {
        console.error('WebSocket Error', error);
      };
    } catch (err) {
      console.error('WebSocket Connection Failed', err);
    }
  }, [fullUrl]);

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not open. Message not sent.', message);
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
};
