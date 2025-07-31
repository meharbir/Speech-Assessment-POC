import React from 'react';
import ScoreCard from './ScoreCard';
import './ImpromptuDashboard.css';

const ImpromptuResultsDashboard = ({ results, onTryAgain, onChangeTopic }) => {
  const { aiCoachAnalysis, transcript, azureMetrics } = results;

  // Error boundary and empty state handling
  const safeAiCoachAnalysis = {
    fluency_score: aiCoachAnalysis?.fluency_score || 0,
    fluency_feedback: aiCoachAnalysis?.fluency_feedback || "Good speaking pace overall.",
    grammar_score: aiCoachAnalysis?.grammar_score || 0,
    grammar_errors: aiCoachAnalysis?.grammar_errors || [],
    vocabulary_score: aiCoachAnalysis?.vocabulary_score || 0,
    vocabulary_feedback: aiCoachAnalysis?.vocabulary_feedback || "Good vocabulary usage overall.",
    coherence_score: aiCoachAnalysis?.coherence_score || 0,
    coherence_feedback: aiCoachAnalysis?.coherence_feedback || "Speech flows well with clear connections.",
    positive_highlights: aiCoachAnalysis?.positive_highlights || ["You spoke clearly and confidently.", "Good effort on this topic!"],
    rewritten_sample: aiCoachAnalysis?.rewritten_sample || "Sample rewrite not available."
  };

  const safeAzureMetrics = {
    fluencyScore: azureMetrics?.fluencyScore || 0,
    prosodyScore: azureMetrics?.prosodyScore || 0
  };

  return (
    <div className="impromptu-dashboard">
      <div className="dashboard-header">
        <h2>📊 Impromptu Speaking Analysis</h2>
        <div className="action-buttons">
          <button className="try-again-btn" onClick={onTryAgain}>
            🔄 Try Again
          </button>
          <button className="change-topic-btn" onClick={onChangeTopic}>
            ✏️ Change Topic
          </button>
          <button className="export-btn" onClick={() => window.print()}>
            📤 Export Results
          </button>
        </div>
      </div>
      
      <div className="score-cards-grid">
        <ScoreCard 
          title="📝 Grammar" 
          score={safeAiCoachAnalysis.grammar_score} 
          feedback={`${safeAiCoachAnalysis.grammar_errors.length} errors found`} 
        />
        <ScoreCard 
          title="📚 Vocabulary" 
          score={safeAiCoachAnalysis.vocabulary_score} 
          feedback={safeAiCoachAnalysis.vocabulary_feedback} 
        />
        <ScoreCard 
          title="🔗 Coherence" 
          score={safeAiCoachAnalysis.coherence_score} 
          feedback={safeAiCoachAnalysis.coherence_feedback}
        />
        <ScoreCard 
          title="🎤 Fluency" 
          score={safeAiCoachAnalysis.fluency_score} 
          feedback={safeAiCoachAnalysis.fluency_feedback}
        />
      </div>

      <div className="feedback-section">
        <h3>Transcript</h3>
        <p className="transcript-display">{transcript}</p>
      </div>

      <div className="feedback-section">
        <h3>Grammar Corrections</h3>
        {aiCoachAnalysis.grammar_errors.length > 0 ? (
          <ul className="feedback-list">
            {aiCoachAnalysis.grammar_errors.map((item, i) => (
              <li key={i}>
                <p><strong>Original:</strong> <span className="text-original">{item.error}</span></p>
                <p><strong>Correction:</strong> <span className="text-correction">{item.correction}</span></p>
                <p className="explanation"><strong>Explanation:</strong> {item.explanation}</p>
              </li>
            ))}
          </ul>
        ) : <p>No grammatical errors detected. Excellent work!</p>}
      </div>

      <div className="feedback-section">
        <h3>✨ What You Did Well</h3>
        <ul className="feedback-list">
          {safeAiCoachAnalysis.positive_highlights.map((item, i) => (
            <li key={i} className="highlight">{item}</li>
          ))}
        </ul>
      </div>

      <div className="feedback-section">
        <h3>📝 Sample Improved Version</h3>
        <div className="rewritten-sample">
          <p className="sample-text">{safeAiCoachAnalysis.rewritten_sample}</p>
          <p className="sample-note">
            <em>This is how you could express your ideas with better grammar, vocabulary, and structure.</em>
          </p>
        </div>
      </div>

      <div className="feedback-section">
        <h3>💡 Tips for Improvement</h3>
        <div className="tips-grid">
          {safeAiCoachAnalysis.grammar_score < 70 && (
            <div className="tip-card">
              <h4>📝 Grammar Tips</h4>
              <p>Practice sentence structure and verb tenses. Read more to internalize correct grammar patterns.</p>
            </div>
          )}
          {safeAiCoachAnalysis.vocabulary_score < 70 && (
            <div className="tip-card">
              <h4>📚 Vocabulary Tips</h4>
              <p>Expand your vocabulary by learning 5 new words daily. Use synonyms to avoid repetition.</p>
            </div>
          )}
          {safeAiCoachAnalysis.coherence_score < 70 && (
            <div className="tip-card">
              <h4>🔗 Coherence Tips</h4>
              <p>Use transition words like "first," "however," "therefore" to connect your ideas clearly.</p>
            </div>
          )}
          {safeAiCoachAnalysis.fluency_score < 70 && (
            <div className="tip-card">
              <h4>🎤 Fluency Tips</h4>
              <p>Practice speaking at a steady pace. Pause naturally between sentences, not in the middle of thoughts.</p>
            </div>
          )}
        </div>
      </div>

      <div className="feedback-section">
        <h3>📊 Speaking Metrics</h3>
        <div className="metrics-grid">
          <div className="metric-item">
            <span className="metric-label">Azure Fluency Score:</span>
            <span className="metric-value">{safeAzureMetrics.fluencyScore}/100</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Prosody (Rhythm) Score:</span>
            <span className="metric-value">{safeAzureMetrics.prosodyScore}/100</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImpromptuResultsDashboard;