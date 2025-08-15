import { useState, useRef, useEffect, useCallback } from 'react';

export const useWebSocket = (currentUser, token) => {
  const [wsStatus, setWsStatus] = useState('Disconnected');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [assignedTask, setAssignedTask] = useState(null);
  const [studentStatuses, setStudentStatuses] = useState({});
  const wsRef = useRef(null);

  // Function to send messages through WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message:', message);
    }
  }, []);

  useEffect(() => {
    // DO NOT ATTEMPT TO CONNECT if we don't have a logged-in user with a class_id and a token.
    if (!currentUser || !currentUser.class_id || !token) {
      return;
    }

    let ws;

    // This function will be called to establish connection
    const connect = () => {
      setWsStatus('Connecting...');
      console.log(`Attempting to connect WebSocket (Attempt: ${reconnectAttempts + 1}) for class: ${currentUser.class_id}`);
      
      ws = new WebSocket(`ws://localhost:8000/ws/${currentUser.class_id}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connection established.");
        setWsStatus('Connected');
        setReconnectAttempts(0); // Reset attempts on successful connection
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'new_topic') {
          console.log("New task received from teacher:", message.payload);
          setAssignedTask(message.payload);
        } else if (message.type === 'student_status_update') {
          // Teacher receiving student status updates
          const { student_id, status } = message.payload;
          setStudentStatuses(prev => ({
            ...prev,
            [student_id]: status
          }));
        } else if (message.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
        } else {
          console.log("WebSocket message received:", message);
        }
      };

      ws.onclose = (event) => {
        console.log(`WebSocket connection closed (Code: ${event.code}). Reconnecting...`);
        setWsStatus('Disconnected');
        // Only attempt to reconnect if it was not a clean close
        if (event.code !== 1000) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // Exponential backoff up to 30s
            setTimeout(() => setReconnectAttempts(prev => prev + 1), delay);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        ws.close();
      };
    };

    connect();

    // Cleanup function
    return () => {
      if (ws) {
        // Set a flag to prevent reconnection attempts on manual logout/unmount
        ws.onclose = () => {}; 
        ws.close();
      }
    };
  }, [currentUser, token, reconnectAttempts]); // Re-run effect on these dependencies

  return {
    wsStatus,
    assignedTask,
    studentStatuses,
    sendMessage,
    setAssignedTask
  };
};