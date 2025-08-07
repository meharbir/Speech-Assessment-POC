import React, { useState } from 'react';
import axios from 'axios';
import ScoreCard from './ScoreCard';
import PronunciationHighlights from './PronunciationHighlights';
import './ImpromptuDashboard.css';

// Custom EncouragementCard component (no scores, only positive feedback)
const EncouragementCard = ({ title, feedback, icon }) => {
  return (
    <div className="score-card encouragement-card">
      <h4><span>{icon}</span> {title}</h4>
      <div className="encouragement-content">
        <p className="encouragement-feedback">{feedback}</p>
      </div>
    </div>
  );
};

const ImpromptuResultsDashboard = ({ results, onTryAgain, onChangeTopic }) => {
  const { aiCoachAnalysis, transcript } = results;
  const [showAllGrammar, setShowAllGrammar] = useState(false);
  const [showAllVocab, setShowAllVocab] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState('coach');

  const grammarErrors = aiCoachAnalysis.grammar_errors || [];
  const vocabularySuggestions = aiCoachAnalysis.vocabulary_suggestions || [];
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

  const renderCoachView = () => (
    <>
      <div className="score-cards-grid">
        <EncouragementCard 
          icon="📝"
          title="Grammar" 
          feedback={aiCoachAnalysis.grammar_feedback || "Grammar analysis pending..."} 
        />
        <EncouragementCard 
          icon="📚"
          title="Vocabulary" 
          feedback={aiCoachAnalysis.vocabulary_feedback || "Vocabulary analysis pending..."} 
        />
        <EncouragementCard 
          icon="🔗"
          title="Coherence" 
          feedback={aiCoachAnalysis.coherence_feedback ? 
            (aiCoachAnalysis.coherence_feedback.length > 150 ? 
              aiCoachAnalysis.coherence_feedback.substring(0, 150) + "..." : 
              aiCoachAnalysis.coherence_feedback) : 
            "Coherence analysis pending..."} 
        />
        <EncouragementCard 
          icon="🗣️"
          title="Fluency" 
          feedback={aiCoachAnalysis.fluency_feedback ? 
            (aiCoachAnalysis.fluency_feedback.length > 150 ? 
              aiCoachAnalysis.fluency_feedback.substring(0, 150) + "..." : 
              aiCoachAnalysis.fluency_feedback) : 
            "Fluency analysis pending..."} 
        />
      </div>

      <div className="feedback-section">
        <h3>📄 Transcript</h3>
        <p className="transcript-display">{transcript}</p>
      </div>

      <div className="feedback-section">
        <h3>📝 Grammar Corrections</h3>
        {grammarErrors.length > 0 ? (
          <>
            <ul className="feedback-list">
              {(showAllGrammar ? grammarErrors : grammarErrors.slice(0, 3)).map((item, i) => (
                <li key={i}>
                  <p><strong>Original:</strong> <span className="text-original">{item.error}</span></p>
                  <p><strong>Correction:</strong> <span className="text-correction">{item.correction}</span></p>
                  <p className="explanation"><strong>Explanation:</strong> {item.explanation}</p>
                </li>
              ))}
            </ul>
            {grammarErrors.length > 3 && (
              <button onClick={() => setShowAllGrammar(!showAllGrammar)} className="show-more-button">
                {showAllGrammar ? 'Show Fewer' : `Show All ${grammarErrors.length} Errors`}
              </button>
            )}
          </>
        ) : <p>No grammatical errors detected. Excellent work!</p>}
      </div>

      <div className="feedback-section">
        <h3>📚 Vocabulary Enhancements</h3>
        {vocabularySuggestions.length > 0 ? (
          <>
            <ul className="feedback-list">
              {(showAllVocab ? vocabularySuggestions : vocabularySuggestions.slice(0, 3)).map((item, i) => (
                <li key={i}>
                  <p><strong>Original:</strong> "{item.original}"</p>
                  <p><strong>Enhanced:</strong> "{item.enhanced}"</p>
                  <p className="explanation"><strong>Why it's better:</strong> {item.explanation}</p>
                </li>
              ))}
            </ul>
            {vocabularySuggestions.length > 3 && (
              <button onClick={() => setShowAllVocab(!showAllVocab)} className="show-more-button">
                {showAllVocab ? 'Show Fewer' : `Show All ${vocabularySuggestions.length} Enhancements`}
              </button>
            )}
          </>
        ) : <p>Your vocabulary was clear and effective.</p>}
      </div>

      <div className="feedback-section">
        <h3>🔗 Coherence Analysis</h3>
        <p>{aiCoachAnalysis.coherence_feedback}</p>
      </div>

      <div className="feedback-section">
        <h3>🗣️ Fluency Analysis</h3>
        <p>{aiCoachAnalysis.fluency_feedback}</p>
      </div>
    </>
  );

  return (
    <div className="impromptu-dashboard">
      <div className="dashboard-header">
        <h2>Your Speech Analysis</h2>
        <div className="header-buttons">
          {onTryAgain && (
            <button className="action-button try-again" onClick={onTryAgain}>
              🔄 Try Again
            </button>
          )}
          {onChangeTopic && (
            <button className="action-button change-topic" onClick={onChangeTopic}>
              💡 Change Topic
            </button>
          )}
        </div>
      </div>

      <div className="tabs">
        <button 
          className={`tab-button ${activeTab === 'coach' ? 'active' : ''}`} 
          onClick={() => setActiveTab('coach')}>
          AI Coach Feedback
        </button>
        {results.pronunciationAssessment && (
          <button 
            className={`tab-button ${activeTab === 'pronunciation' ? 'active' : ''}`} 
            onClick={() => setActiveTab('pronunciation')}>
            Pronunciation Details
          </button>
        )}
      </div>

      <div className="tab-content">
        {activeTab === 'coach' && renderCoachView()}
        {activeTab === 'pronunciation' && <PronunciationHighlights assessment={results.pronunciationAssessment} />}
      </div>

      {/* Rewritten Sample at the very bottom */}
      <div className="feedback-section rewritten-bottom">
        <h3>✨ Rewritten Sample</h3>
        <div className="sample-container">
          <p className="transcript-display">{aiCoachAnalysis.rewritten_sample}</p>
          <button className="listen-button" onClick={playSampleAudio} disabled={isAudioPlaying}>
            {isAudioPlaying ? 'Playing...' : '▶️ Listen to Sample'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImpromptuResultsDashboard;