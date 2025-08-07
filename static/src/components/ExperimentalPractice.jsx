import React, { useState, useRef } from 'react';
import axios from 'axios';
import ResultsDashboard from './ResultsDashboard';
import './Practice.css';

const ExperimentalPractice = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const handleRecord = async () => {
    setResults(null); 
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setIsRecording(true);
    audioChunksRef.current = [];
    const mediaRecorder = new MediaRecorder(stream);
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
  };

  const sendAudioForAnalysis = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    
    try {
      const response = await axios.post('http://localhost:8000/api/analyze?mode=impromptu_experimental', formData);
      setResults(response.data);
    } catch (error) {
      console.error("Error sending audio to backend:", error);
      alert("An error occurred during experimental analysis.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (results) {
    return <ResultsDashboard results={results} />;
  }

  return (
    <div className="practice-container">
      <h2>Experimental Pronunciation Practice</h2>
      <p className="instructions">Speak freely about any topic. The AI will first transcribe your speech, correct it, and then score your pronunciation against the corrected script.</p>
      <div className="controls">
        <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
        <button onClick={handleStop} disabled={!isRecording || isProcessing}>Stop</button>
      </div>
      {isRecording && <p className="status-text">🔴 Recording...</p>}
      {isProcessing && <p className="status-text">⚙️ Performing experimental analysis...</p>}
    </div>
  );
};

export default ExperimentalPractice;