import React, { useState } from 'react';
import WordPopup from './WordPopup';
import './components.css';

const PronunciationView = ({ pronunciationData }) => {
  const [selectedWord, setSelectedWord] = useState(null);

  if (!pronunciationData) return <div>Loading...</div>;

  return (
    <div className="view-container">
      <h2>Pronunciation Score: {pronunciationData.PronunciationScore}%</h2>
      <p>Click on a red word to see detailed feedback and hear the correct pronunciation.</p>
      
      <div className="transcript-container">
        <h3>Interactive Transcript</h3>
        <div className="transcript-text">
          {pronunciationData.Words.map((word, index) => (
            <span 
              key={index} 
              className={word.AccuracyScore > 75 ? 'word-correct' : 'word-incorrect'}
              onClick={() => word.AccuracyScore <= 75 && setSelectedWord(word)}
            >
              {word.Word}{' '}
            </span>
          ))}
        </div>
      </div>

      {selectedWord && <WordPopup wordData={selectedWord} onClose={() => setSelectedWord(null)} />}
    </div>
  );
};

export default PronunciationView;