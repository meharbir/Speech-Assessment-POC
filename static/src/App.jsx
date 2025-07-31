import React, { useState } from 'react';
import './App.css';
import SpeakingModeSelector from './components/SpeakingModeSelector';
import PronunciationPractice from './components/PronunciationPractice'; // We will create this next
import ImpromptuPractice from './components/ImpromptuPractice'; // We will create this next

function App() {
  const [mode, setMode] = useState(null); // 'pronunciation' or 'impromptu'

  const renderContent = () => {
    if (mode === 'pronunciation') {
      // For now, these are just placeholders
      return <PronunciationPractice />;
    }
    if (mode === 'impromptu') {
      return <ImpromptuPractice />;
    }
    // If no mode is selected, show the selector
    return <SpeakingModeSelector onModeSelect={setMode} />;
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Speech Assessment</h1>
        {mode && (
          <button className="back-button" onClick={() => setMode(null)}>
            &larr; Change Mode
          </button>
        )}
      </header>
      <main>
        {renderContent()}
      </main>
    </div>
  );
}

export default App;