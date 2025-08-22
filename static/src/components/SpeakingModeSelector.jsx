import React, { useState } from 'react';
import axios from 'axios';
import './SpeakingModeSelector.css';

// A new sub-component for the "Join Class" form
const JoinClassBanner = ({ currentUser }) => {
    const [classCode, setClassCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // If the user is a guest or already in a class, don't show the banner
    if (!currentUser || currentUser.class_id) {
        return null;
    }

    const handleJoinClass = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        try {
            await axios.patch('http://localhost:8000/api/student/join-class', { class_code: classCode });
            setSuccess('Successfully joined class! Please refresh the page to see the changes.');
            // A full page reload is the simplest way to update the user's state everywhere
            setTimeout(() => window.location.reload(), 2000);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to join class. Please check the code.');
        }
    };

    return (
        <div className="join-class-banner">
            <p>You are not currently in a class. Enter a Class Code from your teacher to join.</p>
            <form onSubmit={handleJoinClass} className="join-class-form">
                <input
                    type="text"
                    value={classCode}
                    onChange={(e) => setClassCode(e.target.value)}
                    placeholder="Enter Class Code"
                />
                <button type="submit">Join Class</button>
            </form>
            {error && <p className="join-class-error">{error}</p>}
            {success && <p className="join-class-success">{success}</p>}
        </div>
    );
};


const SpeakingModeSelector = ({ onModeSelect, currentUser }) => {
  return (
    <div className="mode-selector-container">
      {/* The new banner will appear at the top */}
      <JoinClassBanner currentUser={currentUser} />

      <h1>Choose Your Practice Mode</h1>
      <div className="modes-wrapper">
        <div className="mode-card" onClick={() => onModeSelect('pronunciation')}>
          <h2>📖 Pronunciation Practice</h2>
          <p>Read a sentence and get word-by-word accuracy scores.</p>
          <span className="grade-level">Scripted Speaking</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('impromptu')}>
          <h2>🎤 Short Impromptu (&lt; 1 min)</h2>
          <p>Speak on a topic and get instant, real-time feedback.</p>
          <span className="grade-level">Fastest Analysis</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('impromptu-chunked')}>
          <h2>🗣️ Impromptu Speaking</h2>
          <p>Deliver a longer speech (1-5 min) and get fast, detailed feedback.</p>
          <span className="grade-level">Recommended Mode</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('impromptu_experimental')}>
          <h2>🔬 Experimental Pronunciation</h2>
          <p>Speak freely and get an experimental pronunciation score based on an AI-generated script.</p>
          <span className="grade-level">Advanced Test</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('impromptu-batch')}>
          <h2>🎙️ Batch Processing</h2>
          <p>For very long audio files. Analysis may take several minutes.</p>
          <span className="grade-level">Advanced Use</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('ab-test')}>
          <h2>🔬 A/B Test (Azure vs. Whisper)</h2>
          <p>Compare Azure and Whisper transcription services side-by-side.</p>
          <span className="grade-level">Research Mode</span>
        </div>
        
        <div className="mode-card" onClick={() => onModeSelect('hybrid-groq')}>
          <h2>🚀 Advanced Hybrid Analysis</h2>
          <p>Whisper + Azure + Groq with comprehensive audio metrics and AI comparison.</p>
          <span className="grade-level">Cutting Edge</span>
        </div>
      </div>
    </div>
  );
};

export default SpeakingModeSelector;