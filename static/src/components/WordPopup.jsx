import React, { useState, useRef } from 'react';
import axios from 'axios';
import './components.css';

const WordPopup = ({ wordData, onClose }) => {
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const audioRef = useRef(null);
  
  if (!wordData) return null;

  const playCorrectPronunciation = async () => {
    if (isAudioPlaying) return; // Prevent double-play
    setIsAudioPlaying(true);
    
    try {
      // Stop any existing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      
      const response = await axios.get(`http://localhost:8000/api/synthesize?word=${wordData.Word}`, { responseType: 'blob' });
      const audioUrl = URL.createObjectURL(response.data);
      audioRef.current = new Audio(audioUrl);
      audioRef.current.onended = () => {
        setIsAudioPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      audioRef.current.play();
    } catch (error) {
      alert("Could not play audio.");
      setIsAudioPlaying(false);
    }
  };

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <button className="popup-close" onClick={onClose}>&times;</button>
        <h3>Word Details: "{wordData.Word}"</h3>
        <p><strong>Accuracy Score:</strong> {wordData.AccuracyScore}%</p>
        <p><strong>Error Type:</strong> {wordData.ErrorType || (wordData.AccuracyScore > 75 ? 'None' : 'Mispronunciation')}</p>
        
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
        <button className="listen-button" onClick={playCorrectPronunciation} disabled={isAudioPlaying}>
          {isAudioPlaying ? 'Playing...' : 'Listen to Correct Pronunciation'}
        </button>
      </div>
    </div>
  );
};

export default WordPopup;