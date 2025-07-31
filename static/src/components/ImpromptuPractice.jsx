import React, { useState, useRef } from 'react';
import axios from 'axios';
import './Practice.css';
import ImpromptuResultsDashboard from './ImpromptuResultsDashboard'; // Import the new dashboard

const ImpromptuPractice = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [topic, setTopic] = useState('My Family');
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const handleRecord = async () => {
    setResults(null);
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setIsRecording(true);
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.ondataavailable = event => audioChunksRef.current.push(event.data);
      mediaRecorder.onstop = () => sendAudioForAnalysis();
      mediaRecorder.start();
    } catch (err) {
      setError("Could not access microphone. Please check permissions.");
    }
  };

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setIsProcessing(true);
  };

  const sendAudioForAnalysis = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    formData.append('topic', topic);

    try {
      const response = await axios.post('http://localhost:8000/api/analyze?mode=impromptu', formData);
      setResults(response.data);
    } catch (error) {
      console.error("Error sending audio to backend:", error);
      setError("An error occurred during analysis. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTryAgain = () => {
    setResults(null);
    setError(null);
  };

  const handleChangeTopic = () => {
    setResults(null);
    setError(null);
    // Focus on topic input when changing topic
    setTimeout(() => {
      const topicInput = document.querySelector('.topic-input');
      if (topicInput) topicInput.focus();
    }, 100);
  };

  // --- THIS IS THE CHANGE ---
  // If we have results, render the new dashboard component
  if (results) {
    return (
      <ImpromptuResultsDashboard 
        results={results} 
        onTryAgain={handleTryAgain}
        onChangeTopic={handleChangeTopic}
      />
    );
  }

  return (
    <div className="practice-container">
      <h2>Impromptu Speaking Topic</h2>
      <input 
        type="text" 
        className="topic-input"
        value={topic} 
        onChange={(e) => setTopic(e.target.value)} 
      />
      <p className="instructions">Speak on this topic for 1-2 minutes.</p>
      <div className="controls">
        <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
        <button onClick={handleStop} disabled={!isRecording || isProcessing}>Stop</button>
      </div>
      {isRecording && <p className="status-text">🔴 Recording...</p>}
      {isProcessing && <p className="status-text">⚙️ Processing, please wait...</p>}
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}
    </div>
  );
};

export default ImpromptuPractice;