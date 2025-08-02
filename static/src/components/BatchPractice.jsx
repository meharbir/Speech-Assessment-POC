import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Practice.css';
import ImpromptuResultsDashboard from './ImpromptuResultsDashboard';

// --- NAME CORRECTED HERE ---
const BatchPractice = () => {
  const [status, setStatus] = useState('idle');
  const [jobId, setJobId] = useState(null);
  const [results, setResults] = useState(null);
  const [topic, setTopic] = useState('My favorite holiday');
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(pollIntervalRef.current);
  }, []);

  const handleRecord = async () => {
    setResults(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setStatus('recording');
    audioChunksRef.current = [];
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.ondataavailable = event => audioChunksRef.current.push(event.data);
    mediaRecorder.onstop = () => startAnalysis();
    mediaRecorder.start();
  };

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
    }
  };

  const startAnalysis = async () => {
    // ... (rest of the component logic is unchanged)
    setStatus('uploading');
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'long_recording.webm');
    
    try {
      const response = await axios.post('http://localhost:8000/api/analyze-batch/start', formData);
      setJobId(response.data.jobId);
      setStatus('polling');
      pollIntervalRef.current = setInterval(() => pollStatus(response.data.jobId), 30000);
    } catch (error) {
      console.error("Error starting analysis:", error);
      setStatus('error');
    }
  };
  
  const pollStatus = async (currentJobId) => {
    try {
        const response = await axios.get(`http://localhost:8000/api/analyze-batch/status?job_id=${currentJobId}`);
        if (response.data.status === 'Succeeded') {
            clearInterval(pollIntervalRef.current);
            setStatus('fetchingResults');
            fetchResults(currentJobId);
        } else if (response.data.status === 'Failed') {
            clearInterval(pollIntervalRef.current);
            setStatus('error');
        }
    } catch (error) {
        clearInterval(pollIntervalRef.current);
        setStatus('error');
    }
  };

  const fetchResults = async (currentJobId) => {
      try {
          const response = await axios.get(`http://localhost:8000/api/analyze-batch/results?job_id=${currentJobId}&topic=${topic}`);
          setResults(response.data);
          setStatus('success');
      } catch (error) {
          setStatus('error');
      }
  };

  if (status === 'success') {
      return <ImpromptuResultsDashboard results={results} />;
  }
  
  const isRecording = status === 'recording';
  const isProcessing = ['uploading', 'polling', 'fetchingResults'].includes(status);
  
  return (
    <div className="practice-container">
      <h2>Batch Processing (Very Long Audio)</h2>
      <input type="text" className="topic-input" value={topic} onChange={(e) => setTopic(e.target.value)} />
      <p className="instructions">Speak on this topic. Analysis may take several minutes.</p>
      <div className="controls">
        <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
        <button onClick={handleStop} disabled={!isRecording}>Stop</button>
      </div>
      {isProcessing && <p className="status-text">⚙️ Analysis in progress... (Status: {status})</p>}
      {isRecording && <p className="status-text">🔴 Recording...</p>}
      {status === 'error' && <p className="status-text" style={{color: 'red'}}>An error occurred. Please try again.</p>}
    </div>
  );
};

// --- NAME CORRECTED HERE ---
export default BatchPractice;