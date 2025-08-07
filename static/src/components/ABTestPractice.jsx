import React, { useState, useRef } from 'react';
import axios from 'axios';
import ABTestResults from './ABTestResults'; // Import the new results component
import './Practice.css';

const ABTestPractice = () => {
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
    if (mediaRecorderRef.current?.state === 'recording') {
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
      const response = await axios.post('http://localhost:8000/api/analyze-ab-test', formData, { timeout: 300000 });
      setResults(response.data);
    } catch (error) {
      console.error("Error during A/B test:", error);
      alert("An error occurred during the A/B test analysis.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (results) {
    return <ABTestResults results={results} />;
  }

  return (
    <div className="practice-container">
      <h2>A/B Test: Azure vs. Whisper</h2>
      <p className="instructions">Speak freely. The system will get a transcript from both Azure and Whisper, then run a pronunciation assessment on each. This will help us compare the services.</p>
      <div className="controls">
        <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
        <button onClick={handleStop} disabled={!isRecording || isProcessing}>Stop</button>
      </div>
      {isRecording && <p className="status-text">🔴 Recording...</p>}
      {isProcessing && <p className="status-text">⚙️ Running A/B Test...</p>}
    </div>
  );
};

export default ABTestPractice;