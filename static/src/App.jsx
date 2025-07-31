import React, { useState, useRef } from 'react';
import axios from 'axios';
import './App.css';
import ResultsDashboard from './components/ResultsDashboard';

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const referenceText = "The two characters in this story are the rabbit and the turtle.";

  const handleRecord = async () => {
    setResults(null); 
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setIsRecording(true);
    audioChunksRef.current = [];
    
    // Try to use WAV format if supported, otherwise fallback to WebM
    let mediaRecorder;
    if (MediaRecorder.isTypeSupported('audio/wav')) {
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/wav' });
    } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=pcm')) {
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=pcm' });
    } else {
      mediaRecorder = new MediaRecorder(stream);
    }
    mediaRecorderRef.current = mediaRecorder;
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);
      }
    };
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType });
      console.log('Audio recorded:', {
        size: audioBlob.size,
        type: audioBlob.type,
        mimeType: mediaRecorder.mimeType
      });
      await sendAudioForAnalysis(audioBlob);
    };
    mediaRecorder.start();
  };

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setIsProcessing(true);
  };

  const sendAudioForAnalysis = async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    formData.append('reference_text', referenceText);

    try {
      // --- THE FIX IS HERE ---
      // We now use the full address of the Python backend server
      const response = await axios.post('http://localhost:8000/api/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      console.log("SUCCESS! Received results from backend:", response.data);
      setResults(response.data);

    } catch (error) {
      console.error("Error sending audio to backend:", error);
      alert("An error occurred while analyzing your speech. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Speech Assessment</h1>
      </header>
      <main>
        {results ? (
          <ResultsDashboard results={results} />
        ) : (
          <div className="recording-view">
            <h2>Practice Sentence</h2>
            <p className="reference-text">{referenceText}</p>
            <div className="controls">
              <button onClick={handleRecord} disabled={isRecording || isProcessing}>Record</button>
              <button onClick={handleStop} disabled={!isRecording || isProcessing}>Stop</button>
            </div>
            {isRecording && <p className="status-text">🔴 Recording...</p>}
            {isProcessing && <p className="status-text">⚙️ Processing, please wait...</p>}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;