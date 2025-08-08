import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import SpeakingModeSelector from './components/SpeakingModeSelector';
import PronunciationPractice from './components/PronunciationPractice';
import ImpromptuPractice from './components/ImpromptuPractice';
import BatchPractice from './components/BatchPractice';
import ChunkedImpromptuPractice from './components/ChunkedImpromptuPractice';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import MyProgressPage from './pages/MyProgressPage';

function App() {
  const [mode, setMode] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('user_token'));
  const [showLogin, setShowLogin] = useState(true);
  // Add this line with the other useState hooks
  const [isGuest, setIsGuest] = useState(false);
  const [view, setView] = useState('practice'); // 'practice' or 'progress'

  // Effect to update axios headers when token changes
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('user_token', token);
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('user_token');
    }
  }, [token]);

  const handleLoginSuccess = (newToken) => {
    setToken(newToken);
  };
  
  const handleLogout = () => {
      setToken(null);
  };

  const handleSignupSuccess = () => {
      setShowLogin(true); // Switch to login page after successful signup
      alert('Signup successful! Please log in.');
  };

  // If no token and not a guest, show the auth pages
  if (!token && !isGuest) {
    if (showLogin) {
      return (
        <LoginPage
          onLoginSuccess={handleLoginSuccess}
          onSwitchToSignup={() => setShowLogin(false)}
          onContinueAsGuest={() => setIsGuest(true)}
        />
      );
    } else {
      return (
        <SignupPage
          onSignupSuccess={handleSignupSuccess}
          onSwitchToLogin={() => setShowLogin(true)}
        />
      );
    }
  }

  // If token exists, show the main application
  const renderContent = () => {
    if (mode === 'pronunciation') return <PronunciationPractice />;
    if (mode === 'impromptu') return <ImpromptuPractice />;
    if (mode === 'impromptu-chunked') return <ChunkedImpromptuPractice />;
    if (mode === 'impromptu-batch') return <BatchPractice />;
    return <SpeakingModeSelector onModeSelect={setMode} />;
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Speech Assessment</h1>
        {view === 'practice' && mode && (
            <button className="back-button" onClick={() => setMode(null)}>
                &larr; Change Mode
            </button>
        )}
        {view === 'progress' && (
             <button className="back-button" onClick={() => setView('practice')}>
                &larr; Back to Practice
            </button>
        )}
        <div className="header-nav">
            {isGuest && <span className="guest-indicator">Guest Mode</span>}
            <button className="nav-button" onClick={() => setView('practice')} disabled={view === 'practice'}>
                Practice
            </button>
            {!isGuest && (
                <button className="nav-button" onClick={() => setView('progress')} disabled={view === 'progress'}>
                    My Progress
                </button>
            )}
            <button className="logout-button" onClick={isGuest ? () => setIsGuest(false) : handleLogout}>
                {isGuest ? 'Exit Guest Mode' : 'Logout'}
            </button>
        </div>
      </header>
      <main>
        {view === 'practice' ? renderContent() : <MyProgressPage />}
      </main>
    </div>
  );
}

export default App;