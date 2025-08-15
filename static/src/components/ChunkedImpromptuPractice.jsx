import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Practice.css';
import ImpromptuResultsDashboard from './ImpromptuResultsDashboard';

const ChunkedImpromptuPractice = ({ assignedTopic, onTaskComplete, isTaskAssigned, sendMessage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [topic, setTopic] = useState(assignedTopic || 'My favorite holiday');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Update topic when assignedTopic changes
  useEffect(() => {
    if (assignedTopic) {
      setTopic(assignedTopic);
    }
  }, [assignedTopic]);

  const sendStatusUpdate = (status) => {
    if (sendMessage) {
      sendMessage({ type: 'status_update', status: status });
    }
  };

  const handleRecord = async () => {
    setResults(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setIsRecording(true);
    sendStatusUpdate('recording');
    audioChunksRef.current = [];
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.ondataavailable = event => audioChunksRef.current.push(event.data);
    mediaRecorder.onstop = () => sendAudioForAnalysis();
    mediaRecorder.start();
  };

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
    }
    setIsProcessing(true);
    setIsRecording(false);
    sendStatusUpdate('processing');
  };

  const sendAudioForAnalysis = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'long_recording.webm');
    formData.append('topic', topic);

    try {
      const response = await axios.post('http://localhost:8000/api/analyze-chunked', formData, {
        timeout: 300000 // 5 minute timeout for longer processing
      });
      setResults(response.data);
      sendStatusUpdate('completed');
    } catch (error) {
      console.error("Error sending audio to backend:", error);
      alert("An error occurred during analysis. The audio might be too long or the server is busy.");
      sendStatusUpdate('error');
    } finally {
      setIsProcessing(false);
    }
  };

  if (results) {
    return (
      <>
        {isTaskAssigned && (
          <button className="task-complete-button" onClick={onTaskComplete}>
            ✅ Mark as Complete & Return to Menu
          </button>
        )}
        <ImpromptuResultsDashboard results={results} />
      </>
    );
  }

  return (
    <div className="practice-container">
      <h2>Impromptu Speaking Practice</h2>
      {assignedTopic && (
        <div className="assigned-text-indicator">
          🎯 <strong>Teacher Assignment:</strong> Speak about the topic below assigned by your teacher
        </div>
      )}
      <input 
        type="text" 
        className="topic-input"
        value={topic} 
        onChange={(e) => setTopic(e.target.value)} 
      />
      <p className="instructions">Speak on this topic. You will receive feedback in 15-30 seconds.</p>
      <div className="controls">
        <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
        <button onClick={handleStop} disabled={!isRecording || isProcessing}>Stop</button>
      </div>
      {isRecording && <p className="status-text">🔴 Recording...</p>}
      {isProcessing && <p className="status-text">⚙️ Analyzing your speech, please wait...</p>}
    </div>
  );
};

export default ChunkedImpromptuPractice;