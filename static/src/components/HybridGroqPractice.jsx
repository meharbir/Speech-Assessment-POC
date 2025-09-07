import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Practice.css';
import HybridGroqResults from './HybridGroqResults';

const HybridGroqPractice = ({ assignedTopic, onTaskComplete, isTaskAssigned, sendMessage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [topic, setTopic] = useState(assignedTopic || 'My favorite hobby');
  
  // Progressive loading states
  const [useProgressiveLoading, setUseProgressiveLoading] = useState(true);
  const [fastResults, setFastResults] = useState(null);
  const [slowResults, setSlowResults] = useState(null);
  const [slowLoading, setSlowLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

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
    
    if (useProgressiveLoading) {
      // NEW: Progressive loading approach
      await sendAudioForProgressiveAnalysis(audioBlob);
    } else {
      // EXISTING: Original single-endpoint approach (fallback)
      await sendAudioForLegacyAnalysis(audioBlob);
    }
  };

  const sendAudioForProgressiveAnalysis = async (audioBlob) => {
    try {
      // Step 1: Call fast endpoint
      console.log('[PROGRESSIVE] Starting fast analysis...');
      const fastFormData = new FormData();
      fastFormData.append('audio_file', audioBlob, 'recording.webm');
      fastFormData.append('topic', topic);
      
      const fastResponse = await axios.post('http://localhost:8000/api/analyze-hybrid-fast', fastFormData, { 
        timeout: 30000, // 30 second timeout for fast analysis
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      console.log('[PROGRESSIVE] Fast analysis completed');
      setFastResults(fastResponse.data);
      setSessionId(fastResponse.data.session_id);
      
      // Show fast results immediately
      setIsProcessing(false); // Stop the main processing indicator
      sendStatusUpdate('fast_completed');
      
      // Step 2: Start slow processing in background
      setSlowLoading(true);
      console.log('[PROGRESSIVE] Starting slow analysis...');
      
      const slowFormData = new FormData();
      slowFormData.append('audio_file', audioBlob, 'recording.webm');
      slowFormData.append('session_id', fastResponse.data.session_id);
      slowFormData.append('transcript', fastResponse.data.transcript);
      slowFormData.append('topic', topic);
      
      const slowResponse = await axios.post('http://localhost:8000/api/analyze-hybrid-slow', slowFormData, { 
        timeout: 120000, // 2 minute timeout for slow analysis
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      console.log('[PROGRESSIVE] Slow analysis completed');
      setSlowResults(slowResponse.data);
      setSlowLoading(false);
      sendStatusUpdate('completed');
      
      // Optional: Combine and save results to database
      try {
        await axios.post('http://localhost:8000/api/analyze-hybrid-combine', {
          session_id: fastResponse.data.session_id,
          fast_results: JSON.stringify(fastResponse.data),
          slow_results: JSON.stringify(slowResponse.data)
        }, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        console.log('[PROGRESSIVE] Results combined and saved to database');
      } catch (combineError) {
        console.warn('[PROGRESSIVE] Failed to save combined results:', combineError);
        // Non-critical error - don't interrupt user experience
      }
      
    } catch (error) {
      console.error("Error during progressive analysis:", error);
      
      // If fast analysis fails, fall back to legacy mode
      if (!fastResults) {
        console.log('[PROGRESSIVE] Fast analysis failed, falling back to legacy mode...');
        setUseProgressiveLoading(false);
        await sendAudioForLegacyAnalysis(audioBlob);
        return;
      }
      
      // If slow analysis fails, show error in slow tabs only
      setSlowLoading(false);
      setSlowResults({ error: "Slow processing failed. Fast results are still available." });
      sendStatusUpdate('partial_completed');
    }
  };

  const sendAudioForLegacyAnalysis = async (audioBlob) => {
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
      console.error("Error during legacy analysis:", error);
      
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
    // Reset all states
    setResults(null);
    setFastResults(null);
    setSlowResults(null);
    setSlowLoading(false);
    setSessionId(null);
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
      // Reset all states
      setResults(null);
      setFastResults(null);
      setSlowResults(null);
      setSlowLoading(false);
      setSessionId(null);
    }
  };

  // Show results - either progressive or legacy
  if (results || fastResults) {
    return (
      <HybridGroqResults 
        results={results}  // Legacy mode results
        fastResults={fastResults}  // Progressive mode fast results
        slowResults={slowResults}  // Progressive mode slow results
        slowLoading={slowLoading}  // Progressive mode loading state
        sessionId={sessionId}      // Progressive mode session tracking
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