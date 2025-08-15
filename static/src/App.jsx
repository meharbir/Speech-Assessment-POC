import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import { useWebSocket } from './hooks/useWebSocket';
import SpeakingModeSelector from './components/SpeakingModeSelector';
import PronunciationPractice from './components/PronunciationPractice';
import ImpromptuPractice from './components/ImpromptuPractice';
import BatchPractice from './components/BatchPractice';
import ChunkedImpromptuPractice from './components/ChunkedImpromptuPractice';
import ExperimentalPractice from './components/ExperimentalPractice';
import ABTestPractice from './components/ABTestPractice';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import MyProgressPage from './pages/MyProgressPage';
import TeacherDashboard from './pages/TeacherDashboard';

function App() {
  const [mode, setMode] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('user_token'));
  const [showLogin, setShowLogin] = useState(true);
  // Add this line with the other useState hooks
  const [isGuest, setIsGuest] = useState(false);
  const [view, setView] = useState('practice'); // 'practice' or 'progress'
  const [currentUser, setCurrentUser] = useState(null);
  
  // WebSocket hook
  const { wsStatus, assignedTask, studentStatuses, sendMessage, setAssignedTask } = useWebSocket(currentUser, token);

  // Effect to update axios headers when token changes
  useEffect(() => {
    const fetchUser = async () => {
        if (token) {
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            localStorage.setItem('user_token', token);
            try {
                const response = await axios.get('http://localhost:8000/api/users/me');
                setCurrentUser(response.data);
            } catch (error) {
                console.error("Could not fetch user data:", error);
                handleLogout();
            }
        } else {
            delete axios.defaults.headers.common['Authorization'];
            localStorage.removeItem('user_token');
            setCurrentUser(null);
        }
    };
    fetchUser();
  }, [token]);

  // Effect to force student into practice view when assigned task is received
  useEffect(() => {
    if (assignedTask && currentUser?.role === 'student') {
      setView('practice');
    }
  }, [assignedTask, currentUser]);

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

  const handleTaskComplete = () => {
    setAssignedTask(null);
    setMode(null); // Return to the mode selector screen
  };

  // While we have a token but haven't finished fetching the user, show a loading state.
  if (token && !currentUser) {
    return <div>Loading your profile, please wait...</div>;
  }

  // If we have a user, determine what to show based on their role
  if (currentUser) {
    if (currentUser.role === 'teacher') {
      return (
          <div className="App">
            <header className="App-header">
              <h1>AI Speech Assessment</h1>
              <div className="header-nav">
                <button className="logout-button" onClick={handleLogout}>Logout</button>
              </div>
            </header>
            <main>
              <TeacherDashboard studentStatuses={studentStatuses} sendMessage={sendMessage} />
            </main>
          </div>
      );
    } 
    else if (currentUser.role === 'student') {
        const renderContent = () => {
          const practiceMode = assignedTask ? assignedTask.mode : mode;
          
          if (practiceMode === 'pronunciation') {
            return <PronunciationPractice assignedText={assignedTask ? assignedTask.text : ''} onTaskComplete={handleTaskComplete} isTaskAssigned={!!assignedTask} sendMessage={sendMessage} />;
          }
          if (practiceMode === 'impromptu') {
            return <ImpromptuPractice />;
          }
          if (practiceMode === 'impromptu-chunked') {
            return <ChunkedImpromptuPractice assignedTopic={assignedTask ? assignedTask.text : ''} onTaskComplete={handleTaskComplete} isTaskAssigned={!!assignedTask} sendMessage={sendMessage} />;
          }
          if (practiceMode === 'impromptu_experimental') {
            return <ExperimentalPractice />;
          }
          if (practiceMode === 'impromptu-batch') {
            return <BatchPractice />;
          }
          if (practiceMode === 'ab-test') {
            return <ABTestPractice />;
          }
          // If no task is assigned, show the mode selector
          return <SpeakingModeSelector onModeSelect={setMode} currentUser={currentUser} />;
        };
        
        return (
            <div className="App">
                <header className="App-header">
                    <h1>AI Speech Assessment</h1>
                    {view === 'practice' && mode && (
                        <button className="back-button" onClick={() => setMode(null)}>&larr; Change Mode</button>
                    )}
                    {view === 'progress' && (
                         <button className="back-button" onClick={() => setView('practice')}>&larr; Back to Practice</button>
                    )}
                    <div className="header-nav">
                        {/* Add this new status indicator */}
                        <span className={`ws-status-indicator ws-status-${wsStatus.toLowerCase()}`}>
                            ● {wsStatus}
                        </span>
                        <button className="nav-button" onClick={() => setView('practice')} disabled={view === 'practice'}>Practice</button>
                        <button 
                            className="nav-button" 
                            onClick={() => setView('progress')} 
                            disabled={view === 'progress' || !!assignedTask}
                        >
                            My Progress {!!assignedTask && '🔒'}
                        </button>
                        <button className="logout-button" onClick={handleLogout}>Logout</button>
                    </div>
                </header>
                <main>
                    {view === 'practice' ? renderContent() : <MyProgressPage />}
                </main>
            </div>
        );
    }
  }

  // If there's no token/user and not a guest, show the auth pages
  if (!isGuest) {
      return (
        showLogin ? 
        <LoginPage
          onLoginSuccess={handleLoginSuccess}
          onSwitchToSignup={() => setShowLogin(false)}
          onContinueAsGuest={() => setIsGuest(true)}
        /> : 
        <SignupPage
          onSignupSuccess={handleSignupSuccess}
          onSwitchToLogin={() => setShowLogin(true)}
        />
      );
  }

  // If in guest mode, show the student practice view
  const renderContent = () => {
    const practiceMode = assignedTask ? assignedTask.mode : mode;
    
    if (practiceMode === 'pronunciation') {
      return <PronunciationPractice assignedText={assignedTask ? assignedTask.text : ''} onTaskComplete={handleTaskComplete} isTaskAssigned={!!assignedTask} sendMessage={sendMessage} />;
    }
    if (practiceMode === 'impromptu') {
      return <ImpromptuPractice />;
    }
    if (practiceMode === 'impromptu-chunked') {
      return <ChunkedImpromptuPractice assignedTopic={assignedTask ? assignedTask.text : ''} onTaskComplete={handleTaskComplete} isTaskAssigned={!!assignedTask} sendMessage={sendMessage} />;
    }
    if (practiceMode === 'impromptu_experimental') {
      return <ExperimentalPractice />;
    }
    if (practiceMode === 'impromptu-batch') {
      return <BatchPractice />;
    }
    if (practiceMode === 'ab-test') {
      return <ABTestPractice />;
    }
    // If no task is assigned, show the mode selector
    return <SpeakingModeSelector onModeSelect={setMode} currentUser={currentUser} />;
  };

  return (
      <div className="App">
          <header className="App-header">
              <h1>AI Speech Assessment</h1>
              {mode && (
                  <button className="back-button" onClick={() => setMode(null)}>&larr; Change Mode</button>
              )}
              <div className="header-nav">
                  <span className="guest-indicator">Guest Mode</span>
                  <button className="logout-button" onClick={() => setIsGuest(false)}>Exit Guest Mode</button>
              </div>
          </header>
          <main>
              {renderContent()}
          </main>
      </div>
  );
}

export default App;