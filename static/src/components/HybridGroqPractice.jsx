import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Practice.css';
import HybridGroqResults from './HybridGroqResults';

const HybridGroqPractice = ({ assignedTopic, onTaskComplete, isTaskAssigned, sendMessage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [topic, setTopic] = useState(assignedTopic || 'My favorite hobby');

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
    audioChunksRef.current = [];
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.ondataavailable = event => audioChunksRef.current.push(event.data);
    mediaRecorder.onstop = () => sendAudioForAnalysis();
    mediaRecorder.start();
    
    sendStatusUpdate('recording (hybrid)');
  };

  const handleStop = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsProcessing(true);
    setIsRecording(false);
    
    sendStatusUpdate('processing');
  };

  const sendAudioForAnalysis = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    formData.append('topic', topic);
    
    try {
      const response = await axios.post('http://localhost:8000/api/analyze-hybrid-groq', formData, { 
        timeout: 120000, // 2 minute timeout for hybrid analysis
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      setResults(response.data);
      sendStatusUpdate('completed');
      
      // Don't call onTaskComplete immediately - let user view results first
    } catch (error) {
      console.error("Error during hybrid analysis:", error);
      
      let errorMessage = "An error occurred during hybrid analysis.";
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert(`Hybrid Analysis Error: ${errorMessage}`);
      sendStatusUpdate('error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTryAgain = () => {
    setResults(null);
    setIsProcessing(false);
    setIsRecording(false);
    // Call onTaskComplete when user actively chooses to go back
    if (onTaskComplete) {
      onTaskComplete();
    }
  };

  const handleChangeTopic = () => {
    const newTopic = prompt('Enter a new topic:', topic);
    if (newTopic && newTopic.trim()) {
      setTopic(newTopic.trim());
      setResults(null);
    }
  };

  if (results) {
    return (
      <HybridGroqResults 
        results={results} 
        onTryAgain={handleTryAgain} 
        onChangeTopic={!isTaskAssigned ? handleChangeTopic : null}
      />
    );
  }

  return (
    <div className="practice-container">
      <h2>🚀 Advanced Hybrid Analysis</h2>
      <p className="practice-subtitle">Whisper + Azure + Groq with Audio Metrics</p>
      
      <div className="topic-section">
        <h3>Topic: {topic}</h3>
        {!isTaskAssigned && (
          <button 
            className="change-topic-button" 
            onClick={handleChangeTopic}
            disabled={isRecording || isProcessing}
          >
            Change Topic
          </button>
        )}
      </div>

      <div className="instructions">
        <h4>🎯 What makes this analysis special:</h4>
        <ul>
          <li><strong>Groq Whisper:</strong> Lightning-fast speech transcription</li>
          <li><strong>Azure Pronunciation:</strong> Detailed word-by-word feedback</li>
          <li><strong>Dual AI Analysis:</strong> Compare OpenAI vs Groq language feedback</li>
          <li><strong>Advanced Audio Metrics:</strong> Voice quality analysis with student-friendly tips</li>
        </ul>
        <p><strong>Instructions:</strong> Speak about the topic for 1-3 minutes. You'll get comprehensive feedback on pronunciation, fluency, grammar, vocabulary, and voice quality!</p>
      </div>

      <div className="controls">
        <button 
          className="record-button" 
          onClick={handleRecord} 
          disabled={isRecording || isProcessing}
        >
          {isRecording ? 'Recording...' : 'Start Recording'}
        </button>
        <button 
          className="stop-button" 
          onClick={handleStop} 
          disabled={!isRecording || isProcessing}
        >
          Stop Recording
        </button>
      </div>

      {isRecording && (
        <div className="recording-indicator">
          <div className="recording-dot"></div>
          <span>Recording in progress... Speak about: "{topic}"</span>
        </div>
      )}

      {isProcessing && (
        <div className="processing-indicator">
          <div className="processing-steps">
            <h4>🔄 Processing your speech...</h4>
            <div className="step-list">
              <div className="step">📝 Transcribing with Groq Whisper...</div>
              <div className="step">🎙️ Analyzing pronunciation with Azure...</div>
              <div className="step">🤖 Comparing AI feedback (OpenAI vs Groq)...</div>
              <div className="step">📊 Generating voice quality insights...</div>
            </div>
            <p>This may take 30-60 seconds due to the comprehensive analysis.</p>
          </div>
        </div>
      )}

      {isTaskAssigned && (
        <div className="task-assignment-notice">
          <p>✅ This topic was assigned by your teacher</p>
        </div>
      )}
    </div>
  );
};

export default HybridGroqPractice;