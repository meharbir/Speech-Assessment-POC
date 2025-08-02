import React from 'react';
import './SpeakingModeSelector.css';

const SpeakingModeSelector = ({ onModeSelect }) => {
  return (
    <div className="mode-selector-container">
      <h1>Choose Your Practice Mode</h1>
      <div className="modes-wrapper">
        <div className="mode-card" onClick={() => onModeSelect('pronunciation')}>
          <h2>📖 Pronunciation Practice</h2>
          <p>Read a sentence and get word-by-word accuracy scores.</p>
          <span className="grade-level">Scripted Speaking</span>
        </div>
        
        {/* --- REORDERED FOR BETTER UX --- */}
        <div className="mode-card" onClick={() => onModeSelect('impromptu-chunked')}>
          <h2>🗣️ Impromptu Speaking</h2>
          <p>Deliver a speech (1-5 min) and get fast, detailed feedback.</p>
          <span className="grade-level">Recommended Mode</span>
        </div>
        <div className="mode-card" onClick={() => onModeSelect('impromptu')}>
          <h2>🎤 Short Impromptu (&lt; 1 min)</h2>
          <p>Speak on a topic and get instant, real-time feedback.</p>
          <span className="grade-level">Fastest Analysis</span>
        </div>
        <div className="mode-card" onClick={() => onModeSelect('impromptu-batch')}>
          <h2>🎙️ Batch Processing (Archival)</h2>
          <p>For very long audio files. Analysis may take several minutes.</p>
          <span className="grade-level">Advanced Use</span>
        </div>

      </div>
    </div>
  );
};

export default SpeakingModeSelector;