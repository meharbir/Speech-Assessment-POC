import React from 'react';
import axios from 'axios';
import './components.css';

const WordPopup = ({ wordData, onClose }) => {
  if (!wordData) return null;

  const playCorrectPronunciation = async () => {
    try {
      console.log(`Requesting TTS for word: ${wordData.Word}`);
      const response = await axios.get(`http://localhost:8000/api/synthesize?word=${wordData.Word}`, {
        responseType: 'blob' // Important to handle audio data
      });
      
      if (response.data && response.data.size > 0) {
        const audioUrl = URL.createObjectURL(response.data);
        const audio = new Audio(audioUrl);
        
        audio.oncanplaythrough = () => {
          audio.play().catch(e => {
            console.error("Audio play failed:", e);
            alert("Could not play audio. Your browser may have blocked autoplay.");
          });
        };
        
        audio.onerror = () => {
          console.error("Audio failed to load");
          URL.revokeObjectURL(audioUrl);
          alert("Audio file is corrupted or unsupported.");
        };
        
        // Clean up the blob URL to prevent memory leaks
        audio.onended = () => URL.revokeObjectURL(audioUrl);
      } else {
        alert("No audio data received from server.");
      }
    } catch (error) {
      console.error("Error playing audio:", error);
      if (error.response && error.response.status === 500) {
        alert("Text-to-speech service is temporarily unavailable. This is a known issue with the demo.");
      } else {
        alert("Could not play audio. Please try again.");
      }
    }
  };

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <button className="popup-close" onClick={onClose}>&times;</button>
        <h3>Word Details: "{wordData.Word}"</h3>
        <p><strong>Accuracy Score:</strong> {wordData.AccuracyScore}%</p>
        <p><strong>Error Type:</strong> {wordData.ErrorType}</p>
        <p><strong>Phoneme Breakdowns:</strong></p>
        <ul>
          {wordData.Phonemes.map((p, i) => (
            <li key={i}>{p.Phoneme} - <span style={{color: p.AccuracyScore > 75 ? 'green' : 'red'}}>{p.AccuracyScore}%</span></li>
          ))}
        </ul>
        <button className="listen-button" onClick={playCorrectPronunciation}>
          Listen to Correct Pronunciation
        </button>
      </div>
    </div>
  );
};

export default WordPopup;