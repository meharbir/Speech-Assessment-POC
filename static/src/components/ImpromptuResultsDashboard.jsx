import React, { useState } from 'react';
import axios from 'axios';
import ScoreCard from './ScoreCard'; // Assuming ScoreCard is still used for numerical scores
import PronunciationHighlights from './PronunciationHighlights';
import './ImpromptuDashboard.css';

// A new, simpler card for displaying text feedback
const FeedbackCard = ({ title, feedback, icon }) => (
    <div className="score-card">
        <h4><span>{icon}</span> {title}</h4>
        <p className="score-feedback" style={{ marginTop: '20px', fontSize: '1em' }}>{feedback}</p>
    </div>
);

const ImpromptuResultsDashboard = ({ results, onTryAgain, onChangeTopic }) => {
  const { aiCoachAnalysis, transcript } = results;
  const [showAllErrors, setShowAllErrors] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState('coach');
  const [showAllGrammar, setShowAllGrammar] = useState(false);
  const [showAllVocab, setShowAllVocab] = useState(false);

  // Safety checks for data
  if (!aiCoachAnalysis) {
      return <div>Loading feedback...</div>;
  }

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

  const renderCoachView = () => (
    <>
      <div className="score-cards-grid">
        {/* The summary cards will remain here */}
        <FeedbackCard 
          icon="🎯"
          title="Relevance to Topic" 
          feedback={aiCoachAnalysis.relevance_feedback} 
        />
        <FeedbackCard 
          icon="🗣️"
          title="Fluency & Coherence" 
          feedback={aiCoachAnalysis.fluency_feedback} 
        />
         <FeedbackCard 
          icon="🎙️"
          title="Pronunciation" 
          feedback={aiCoachAnalysis.pronunciation_feedback} 
        />
        <ScoreCard 
          icon="📝"
          title="Grammar Score" 
          score={aiCoachAnalysis.grammar_score} 
          feedback={`${(aiCoachAnalysis.grammar_errors || []).length} errors found`} 
        />
        <ScoreCard 
          icon="📚"
          title="Vocabulary Score" 
          score={aiCoachAnalysis.vocabulary_score} 
          feedback={aiCoachAnalysis.vocabulary_feedback} 
        />
      </div>

      <div className="feedback-section">
        <h3>📄 Transcript</h3>
        <p className="transcript-display">{transcript}</p>
      </div>

      {/* --- ADDING BACK THE DETAILED SECTIONS --- */}
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
        {(aiCoachAnalysis.vocabulary_suggestions || []).length > 0 ? (
          <>
            <ul className="feedback-list">
              {(showAllVocab ? aiCoachAnalysis.vocabulary_suggestions : aiCoachAnalysis.vocabulary_suggestions.slice(0, 3)).map((item, i) => (
                <li key={i}>
                  <p><strong>Original:</strong> "{item.original}"</p>
                  <p><strong>Enhanced:</strong> "{item.enhanced}"</p>
                  <p className="explanation"><strong>Why it's better:</strong> {item.explanation}</p>
                </li>
              ))}
            </ul>
            {aiCoachAnalysis.vocabulary_suggestions.length > 3 && (
              <button onClick={() => setShowAllVocab(!showAllVocab)} className="show-more-button">
                {showAllVocab ? 'Show Fewer' : `Show All ${aiCoachAnalysis.vocabulary_suggestions.length} Enhancements`}
              </button>
            )}
          </>
        ) : <p>Your vocabulary was clear and effective.</p>}
      </div>
      
      <div className="feedback-section">
        <h3>🗣️ Fluency & Coherence Analysis</h3>
        <div className="detailed-feedback">{aiCoachAnalysis.detailed_fluency_coherence_analysis}</div>
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