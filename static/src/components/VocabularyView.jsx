import React from 'react';
import './components.css';

const VocabularyView = ({ vocabData }) => (
  <div className="view-container">
    <h2>Vocabulary Score: {vocabData.VocabScore}%</h2>
    {/* Additional vocabulary metrics can be displayed here if needed */}
  </div>
);

export default VocabularyView;