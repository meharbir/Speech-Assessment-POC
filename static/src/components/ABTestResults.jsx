import React, { useState } from 'react';
import ScoreCard from './ScoreCard';
import './ImpromptuDashboard.css'; // Reuse existing styles

const ResultColumn = ({ title, data }) => {
    const [activeTab, setActiveTab] = useState('pronunciation');
    const grammarErrors = data.aiCoachAnalysis?.grammar_errors || [];
    const positiveHighlights = data.aiCoachAnalysis?.positive_highlights || [];

    return (
        <div className="result-column">
            <h3>{title}</h3>
            
            {/* Tabs for each column */}
            <div className="tabs">
                <button 
                    className={`tab-button ${activeTab === 'pronunciation' ? 'active' : ''}`} 
                    onClick={() => setActiveTab('pronunciation')}>
                    Pronunciation
                </button>
                <button 
                    className={`tab-button ${activeTab === 'coach' ? 'active' : ''}`} 
                    onClick={() => setActiveTab('coach')}>
                    AI Coach
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'pronunciation' && (
                    <>
                        <div className="feedback-section">
                            <h4>Transcript</h4>
                            <p className="transcript-display">{data.transcript}</p>
                        </div>
                        <div className="feedback-section">
                            <h4>Pronunciation Score</h4>
                            <div className="score-circle" style={{margin: '10px 0', borderColor: '#3498db', borderWidth: '5px'}}>
                                <span className="score-number">{data.pronunciationAssessment.PronunciationScore}</span>
                            </div>
                        </div>
                        <div className="feedback-section">
                            <h4>Interactive Transcript</h4>
                            <div className="transcript-text">
                                {data.pronunciationAssessment.Words.map((word, index) => (
                                    <span 
                                    key={index} 
                                    className={word.AccuracyScore > 75 ? 'word-correct' : 'word-incorrect'}
                                    >
                                    {word.Word}{' '}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </>
                )}

                {activeTab === 'coach' && data.aiCoachAnalysis && !data.aiCoachAnalysis.error && (
                    <>
                        <div className="score-cards-grid" style={{gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px'}}>
                            <ScoreCard icon="📝" title="Grammar" score={data.aiCoachAnalysis.grammar_score} feedback={`${grammarErrors.length} errors`} />
                            <ScoreCard icon="📚" title="Vocabulary" score={data.aiCoachAnalysis.vocabulary_score} feedback="Score" />
                            <ScoreCard icon="🔗" title="Coherence" score={data.aiCoachAnalysis.coherence_score} feedback="Score" />
                            <ScoreCard icon="🗣️" title="Fluency" score={data.aiCoachAnalysis.fluency_score} feedback="Score" />
                        </div>

                        <div className="feedback-section">
                            <h4>🛠️ Grammar Corrections</h4>
                            {grammarErrors.length > 0 ? (
                                <ul className="feedback-list">
                                    {grammarErrors.slice(0, 2).map((item, i) => (
                                        <li key={i}>
                                            <p><strong>Original:</strong> <span className="text-original">{item.error}</span></p>
                                            <p><strong>Correction:</strong> <span className="text-correction">{item.correction}</span></p>
                                        </li>
                                    ))}
                                </ul>
                            ) : <p>No grammatical errors detected!</p>}
                        </div>

                        <div className="feedback-section">
                            <h4>✨ Rewritten Sample</h4>
                            <p style={{fontSize: '0.9em', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '5px'}}>
                                {data.aiCoachAnalysis.rewritten_sample}
                            </p>
                        </div>

                        <div className="feedback-section">
                            <h4>👍 Highlights</h4>
                            <ul className="feedback-list">
                                {positiveHighlights.slice(0, 2).map((item, i) => (
                                    <li key={i} className="highlight">{item}</li>
                                ))}
                            </ul>
                        </div>
                    </>
                )}

                {activeTab === 'coach' && data.aiCoachAnalysis?.error && (
                    <div className="feedback-section">
                        <p style={{color: 'red'}}>AI Coach analysis failed: {data.aiCoachAnalysis.error}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

const ABTestResults = ({ results }) => {
  return (
    <div className="ab-test-results-container">
      <h2>A/B Test Results: Complete Comparison</h2>
      <p style={{textAlign: 'center', marginBottom: '20px', color: '#7f8c8d'}}>
        Compare transcription accuracy, pronunciation scores, and AI coaching feedback side-by-side
      </p>
      <div className="columns-wrapper">
        <ResultColumn title="Azure STT Track" data={results.azure_track} />
        <ResultColumn title="Whisper STT Track" data={results.whisper_track} />
      </div>
    </div>
  );
};

export default ABTestResults;