import React, { useState } from 'react';
import axios from 'axios';
import ScoreCard from './ScoreCard';
import './ImpromptuDashboard.css';

const ImpromptuResultsDashboard = ({ results }) => {
  const { aiCoachAnalysis, transcript } = results;
  const [showAllErrors, setShowAllErrors] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);

  const grammarErrors = aiCoachAnalysis.grammar_errors || [];
  const positiveHighlights = aiCoachAnalysis.positive_highlights || [];

  const playSampleAudio = async () => {
    if (isAudioPlaying) return;
    setIsAudioPlaying(true);
    try {
      const response = await axios.post(
        'http://localhost:8000/api/synthesize-paragraph', 
        { text: aiCoachAnalysis.rewritten_sample }, 
        { responseType: 'blob' }
      );
      const audioUrl = URL.createObjectURL(response.data);
      const audio = new Audio(audioUrl);
      audio.play();
      audio.onended = () => setIsAudioPlaying(false);
    } catch (error) {
      console.error("Error playing sample audio:", error);
      alert("Could not play the audio sample.");
      setIsAudioPlaying(false);
    }
  };

  return (
    <div className="impromptu-dashboard">
      <h2>Impromptu Speaking Analysis</h2>
      
      <div className="score-cards-grid">
        <ScoreCard 
          icon="📝"
          title="Grammar" 
          score={aiCoachAnalysis.grammar_score} 
          feedback={`${grammarErrors.length} errors found`} 
        />
        <ScoreCard 
          icon="📚"
          title="Vocabulary" 
          score={aiCoachAnalysis.vocabulary_score} 
          feedback={aiCoachAnalysis.vocabulary_feedback} 
        />
        <ScoreCard 
          icon="🔗"
          title="Coherence" 
          score={aiCoachAnalysis.coherence_score} 
          feedback={aiCoachAnalysis.coherence_feedback}
        />
        <ScoreCard 
          icon="🗣️"
          title="Fluency" 
          score={aiCoachAnalysis.fluency_score} 
          feedback={aiCoachAnalysis.fluency_feedback} 
        />
      </div>

      <div className="feedback-section">
        <h3>📄 Transcript</h3>
        <p className="transcript-display">{transcript}</p>
      </div>

      <div className="feedback-section">
        <h3>🛠️ Grammar Corrections</h3>
        {grammarErrors.length > 0 ? (
          <>
            <ul className="feedback-list">
              {(showAllErrors ? grammarErrors : grammarErrors.slice(0, 3)).map((item, i) => (
                <li key={i}>
                  <p><strong>Original:</strong> <span className="text-original">{item.error}</span></p>
                  <p><strong>Correction:</strong> <span className="text-correction">{item.correction}</span></p>
                  <p className="explanation"><strong>Explanation:</strong> {item.explanation}</p>
                </li>
              ))}
            </ul>
            {grammarErrors.length > 3 && (
              <button onClick={() => setShowAllErrors(!showAllErrors)} className="show-more-button">
                {showAllErrors ? 'Show Fewer' : `Show All ${grammarErrors.length} Errors`}
              </button>
            )}
          </>
        ) : <p>No grammatical errors detected. Excellent work!</p>}
      </div>

      <div className="feedback-section">
        <h3>🧠 Argument Strength</h3>
        <p>{aiCoachAnalysis.argument_strength_analysis}</p>
      </div>

      <div className="feedback-section">
        <h3>🗺️ Structural Blueprint</h3>
        <p className="blueprint-text">{aiCoachAnalysis.structural_blueprint}</p>
      </div>

      <div className="feedback-section">
        <h3>✨ Rewritten Sample</h3>
        <div className="sample-container">
          <p className="transcript-display">{aiCoachAnalysis.rewritten_sample}</p>
          <button className="listen-button" onClick={playSampleAudio} disabled={isAudioPlaying}>
            {isAudioPlaying ? 'Playing...' : '▶️ Listen to Sample'}
          </button>
        </div>
      </div>

      <div className="feedback-section">
        <h3>👍 What You Did Well</h3>
        <ul className="feedback-list">
          {positiveHighlights.map((item, i) => (
            <li key={i} className="highlight">{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ImpromptuResultsDashboard;