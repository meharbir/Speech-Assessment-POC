import React, { useState, useRef } from 'react';
import axios from 'axios';
import PronunciationView from './PronunciationView';
import './Practice.css'; // We will create this next

const PronunciationPractice = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const [referenceText, setReferenceText] = useState("The two characters in this story are the rabbit and the turtle.");

  const handleRecord = async () => {
    setResults(null);
    setError(null); 
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
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    setIsProcessing(true);
  };

  const sendAudioForAnalysis = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    formData.append('reference_text', referenceText);

    try {
      const response = await axios.post('http://localhost:8000/api/analyze?mode=pronunciation', formData);
      
      
      setResults(response.data);
    } catch (error) {
      console.error("Error sending audio to backend:", error);
      setError("An error occurred during analysis. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (results) {
    // For pronunciation practice, show only pronunciation results
    return <PronunciationView pronunciationData={results.azureAssessment} />;
  }

  return (
    <div className="practice-container">
      <h2>Practice Text</h2>
      <textarea 
        className="reference-text-input"
        value={referenceText}
        onChange={(e) => setReferenceText(e.target.value)}
        placeholder="Enter text to practice pronunciation..."
        rows={4}
      />
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

export default PronunciationPractice;