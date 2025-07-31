import React from 'react';
import './SpeakingModeSelector.css'; // We will create this next

const SpeakingModeSelector = ({ onModeSelect }) => {
  return (
    <div className="mode-selector-container">
      <h1>Choose Your Practice Mode</h1>
      <div className="modes-wrapper">
        <div className="mode-card" onClick={() => onModeSelect('pronunciation')}>
          <h2>📖 Pronunciation Practice</h2>
          <p>Read sentences aloud and get detailed, phoneme-level feedback on your accuracy.</p>
          <span className="grade-level">Ideal for Grades K-3 & Beginners</span>
        </div>
        <div className="mode-card" onClick={() => onModeSelect('impromptu')}>
          <h2>🎤 Impromptu Speaking</h2>
          <p>Speak freely on a given topic and get holistic feedback on fluency, grammar, and structure.</p>
          <span className="grade-level">Ideal for Grades 4+ & Advanced</span>
        </div>
      </div>
    </div>
  );
};

export default SpeakingModeSelector;