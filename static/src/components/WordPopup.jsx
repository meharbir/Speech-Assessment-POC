import React from 'react';
import axios from 'axios';
import './components.css';

const WordPopup = ({ wordData, onClose }) => {
  if (!wordData) return null;

  const playCorrectPronunciation = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/synthesize?word=${wordData.Word}`, { responseType: 'blob' });
      const audioUrl = URL.createObjectURL(response.data);
      new Audio(audioUrl).play();
    } catch (error) {
      alert("Could not play audio.");
    }
  };

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <button className="popup-close" onClick={onClose}>&times;</button>
        <h3>Word Details: "{wordData.Word}"</h3>
        <p><strong>Accuracy Score:</strong> {wordData.AccuracyScore}%</p>
        <p><strong>Error Type:</strong> {wordData.ErrorType}</p>
        
        {wordData.Phonemes && wordData.Phonemes.length > 0 && (
          <>
            <p><strong>Phoneme Breakdowns:</strong></p>
            <ul>
              {wordData.Phonemes.map((p, i) => (
                <li key={i}>{p.Phoneme} - <span style={{color: p.AccuracyScore > 75 ? 'green' : 'red'}}>{p.AccuracyScore}%</span></li>
              ))}
            </ul>
          </>
        )}
        <button className="listen-button" onClick={playCorrectPronunciation}>
          Listen to Correct Pronunciation
        </button>
      </div>
    </div>
  );
};

export default WordPopup;