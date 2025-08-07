import React, { useState } from 'react';
import WordPopup from './WordPopup';
import ScoreCard from './ScoreCard';
import './ImpromptuDashboard.css'; // Reuse styles

const PronunciationHighlights = ({ assessment }) => {
  const [selectedWord, setSelectedWord] = useState(null);

  if (!assessment) return <p>No pronunciation data available.</p>;

  return (
    <div className="pronunciation-highlights-container">
      {/* Overall Scores Section */}
      <div className="feedback-section">
        <h3>📊 Overall Pronunciation Scores</h3>
        <div className="score-cards-grid">
          <ScoreCard 
            icon="🎯" 
            title="Overall Pronunciation" 
            score={assessment.PronunciationScore || 0} 
            feedback={assessment.PronunciationScore ? "Combined accuracy score" : "Basic assessment only"} 
          />
          <ScoreCard 
            icon="✅" 
            title="Accuracy" 
            score={assessment.AccuracyScore || 0} 
            feedback="How accurately words match reference" 
          />
          <ScoreCard 
            icon="🌊" 
            title="Fluency" 
            score={assessment.FluencyScore || 0} 
            feedback={assessment.FluencyScore ? "Smoothness and naturalness" : "Not available in basic mode"} 
          />
          <ScoreCard 
            icon="🎵" 
            title="Prosody" 
            score={assessment.ProsodyScore || 0} 
            feedback={assessment.ProsodyScore ? "Stress, rhythm, and intonation" : "Not available in basic mode"} 
          />
        </div>
      </div>

      {assessment.GeneratedReferenceText && (
        <div className="feedback-section">
            <h3>AI Generated Reference Text</h3>
            <p className="transcript-display">{assessment.GeneratedReferenceText}</p>
        </div>
      )}
      
      <div className="feedback-section">
        <h3>Interactive Transcript</h3>
        <p>Click on a red word to see detailed feedback.</p>
        <div className="transcript-text">
          {assessment.Words.map((word, index) => (
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

export default PronunciationHighlights;