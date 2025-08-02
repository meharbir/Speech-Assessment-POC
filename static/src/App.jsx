import React, { useState } from 'react';
import './App.css';
import SpeakingModeSelector from './components/SpeakingModeSelector';
import PronunciationPractice from './components/PronunciationPractice';
import ImpromptuPractice from './components/ImpromptuPractice';
import BatchPractice from './components/BatchPractice'; // Renamed component
import ChunkedImpromptuPractice from './components/ChunkedImpromptuPractice'; // New component

function App() {
  const [mode, setMode] = useState(null);

  const renderContent = () => {
    if (mode === 'pronunciation') {
      return <PronunciationPractice />;
    }
    if (mode === 'impromptu') {
      return <ImpromptuPractice />;
    }
    if (mode === 'impromptu-chunked') {
      return <ChunkedImpromptuPractice />;
    }
    if (mode === 'impromptu-batch') {
      return <BatchPractice />;
    }
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