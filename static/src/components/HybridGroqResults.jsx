import React, { useState } from 'react';
import axios from 'axios';
import ScoreCard from './ScoreCard';
import PronunciationHighlights from './PronunciationHighlights';
import './ImpromptuDashboard.css';

// Feedback card for text-based feedback
const FeedbackCard = ({ title, feedback, icon }) => (
    <div className="score-card">
        <h4><span>{icon}</span> {title}</h4>
        <p className="score-feedback" style={{ marginTop: '20px', fontSize: '1em' }}>{feedback}</p>
    </div>
);

// Audio metrics card with progress bar and tips
const AudioMetricCard = ({ title, data, icon }) => {
    const score = data?.score || 0;
    const tip = data?.tip || 'No feedback available';
    const exercise = data?.exercise || '';
    
    const getProgressColor = (score) => {
        if (score >= 85) return '#4CAF50'; // Green
        if (score >= 70) return '#FF9800'; // Orange
        return '#F44336'; // Red
    };

    return (
        <div className="score-card" style={{ minHeight: '200px' }}>
            <h4><span>{icon}</span> {title}</h4>
            
            {/* Progress Bar */}
            <div style={{ margin: '15px 0' }}>
                <div style={{
                    width: '100%',
                    backgroundColor: '#f0f0f0',
                    borderRadius: '10px',
                    height: '10px',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        width: `${score}%`,
                        height: '100%',
                        backgroundColor: getProgressColor(score),
                        borderRadius: '10px',
                        transition: 'width 0.5s ease'
                    }}></div>
                </div>
                <p style={{ margin: '5px 0', fontWeight: 'bold' }}>{score}/100</p>
            </div>

            {/* Student-Friendly Tip */}
            <div style={{ textAlign: 'left' }}>
                <p style={{ fontSize: '0.9em', marginBottom: '8px' }}>{tip}</p>
                {exercise && (
                    <p style={{ 
                        fontSize: '0.8em', 
                        fontStyle: 'italic', 
                        color: '#666',
                        backgroundColor: '#f8f9fa',
                        padding: '8px',
                        borderRadius: '4px',
                        marginTop: '8px'
                    }}>
                        <strong>Try this:</strong> {exercise}
                    </p>
                )}
            </div>
        </div>
    );
};

const HybridGroqResults = ({ results, onTryAgain, onChangeTopic }) => {
  const [activeTab, setActiveTab] = useState('coach');
  const [showAllGrammar, setShowAllGrammar] = useState(false);
  const [showAllVocab, setShowAllVocab] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [aiComparison, setAiComparison] = useState('openai'); // 'openai' or 'groq'

  // Extract data from results
  const { 
    transcript, 
    topic,
    openai_coach_analysis,
    groq_language_analysis,
    azure_pronunciation,
    audio_metrics 
  } = results;

  // Get current AI analysis based on comparison toggle
  const currentAiAnalysis = aiComparison === 'openai' ? openai_coach_analysis : groq_language_analysis;
  const grammarErrors = currentAiAnalysis?.grammar_errors || [];
  const studentFriendlyTips = audio_metrics?.student_friendly_tips || {};

  const playSampleAudio = async () => {
    if (isAudioPlaying || !currentAiAnalysis?.rewritten_sample) return;
    
    setIsAudioPlaying(true);
    try {
      const response = await axios.post(
        'http://localhost:8000/api/synthesize-paragraph', 
        { text: currentAiAnalysis.rewritten_sample }, 
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

  const renderAiCoachTab = () => (
    <>
      {/* AI Comparison Toggle */}
      <div className="ai-comparison-toggle" style={{ marginBottom: '20px', textAlign: 'center' }}>
        <div style={{ 
          display: 'inline-flex', 
          backgroundColor: '#f0f0f0', 
          borderRadius: '25px', 
          padding: '4px',
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <button
            onClick={() => setAiComparison('openai')}
            style={{
              padding: '8px 16px',
              borderRadius: '20px',
              border: 'none',
              backgroundColor: aiComparison === 'openai' ? '#007bff' : 'transparent',
              color: aiComparison === 'openai' ? 'white' : '#666',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            OpenAI GPT-4
          </button>
          <button
            onClick={() => setAiComparison('groq')}
            style={{
              padding: '8px 16px',
              borderRadius: '20px',
              border: 'none',
              backgroundColor: aiComparison === 'groq' ? '#FF6B35' : 'transparent',
              color: aiComparison === 'groq' ? 'white' : '#666',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            Groq LLaMA 3.3
          </button>
        </div>
        <p style={{ fontSize: '0.9em', color: '#666', marginTop: '8px' }}>
          Compare feedback from different AI models using the same prompts
        </p>
      </div>

      {/* Score Cards */}
      <div className="score-cards-grid">
        <FeedbackCard 
          icon="🎯"
          title="Relevance to Topic" 
          feedback={currentAiAnalysis?.relevance_feedback || 'Analysis in progress'} 
        />
        <FeedbackCard 
          icon="🗣️"
          title="Fluency & Coherence" 
          feedback={currentAiAnalysis?.fluency_feedback || 'Analysis in progress'} 
        />
        <FeedbackCard 
          icon="🎙️"
          title="Pronunciation" 
          feedback={currentAiAnalysis?.pronunciation_feedback || 'Analysis in progress'} 
        />
        <ScoreCard 
          icon="📝"
          title="Grammar Score" 
          score={currentAiAnalysis?.grammar_score || 0} 
          feedback={`${grammarErrors.length} errors found`} 
        />
        <ScoreCard 
          icon="📚"
          title="Vocabulary Score" 
          score={currentAiAnalysis?.vocabulary_score || 0} 
          feedback={currentAiAnalysis?.vocabulary_feedback || 'Analysis in progress'} 
        />
      </div>

      {/* Transcript */}
      <div className="feedback-section">
        <h3>📄 Transcript</h3>
        <p className="transcript-display">{transcript}</p>
      </div>

      {/* Grammar Corrections */}
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

      {/* Vocabulary Enhancements */}
      <div className="feedback-section">
        <h3>📚 Vocabulary Enhancements</h3>
        {(currentAiAnalysis?.vocabulary_suggestions || []).length > 0 ? (
          <>
            <ul className="feedback-list">
              {(showAllVocab ? currentAiAnalysis.vocabulary_suggestions : currentAiAnalysis.vocabulary_suggestions.slice(0, 3)).map((item, i) => (
                <li key={i}>
                  <p><strong>Original:</strong> "{item.original}"</p>
                  <p><strong>Enhanced:</strong> "{item.enhanced}"</p>
                  <p className="explanation"><strong>Why it's better:</strong> {item.explanation}</p>
                </li>
              ))}
            </ul>
            {currentAiAnalysis.vocabulary_suggestions.length > 3 && (
              <button onClick={() => setShowAllVocab(!showAllVocab)} className="show-more-button">
                {showAllVocab ? 'Show Fewer' : `Show All ${currentAiAnalysis.vocabulary_suggestions.length} Enhancements`}
              </button>
            )}
          </>
        ) : <p>Your vocabulary was clear and effective.</p>}
      </div>
      
      {/* Fluency & Coherence Analysis */}
      <div className="feedback-section">
        <h3>🗣️ Fluency & Coherence Analysis</h3>
        <div className="detailed-feedback">{currentAiAnalysis?.detailed_fluency_coherence_analysis || 'Analysis in progress'}</div>
      </div>

      {/* Rewritten Sample */}
      {currentAiAnalysis?.rewritten_sample && (
        <div className="feedback-section rewritten-bottom">
          <h3>✨ Rewritten Sample</h3>
          <div className="sample-container">
            <p className="transcript-display">{currentAiAnalysis.rewritten_sample}</p>
            <button className="listen-button" onClick={playSampleAudio} disabled={isAudioPlaying}>
              {isAudioPlaying ? 'Playing...' : '▶️ Listen to Sample'}
            </button>
          </div>
        </div>
      )}
    </>
  );

  const renderAudioMetricsTab = () => (
    <>
      <div className="feedback-section">
        <h3>🎯 Voice Quality Analysis for Students</h3>
        <p>Understanding your voice quality helps you become a better speaker!</p>
      </div>

      <div className="score-cards-grid">
        <AudioMetricCard
          icon="🎵"
          title="Pitch Variety"
          data={studentFriendlyTips.pitch_variety}
        />
        <AudioMetricCard
          icon="⏱️"
          title="Speaking Fluency"
          data={studentFriendlyTips.speaking_fluency}
        />
        <AudioMetricCard
          icon="🔊"
          title="Voice Clarity"
          data={studentFriendlyTips.voice_clarity}
        />
      </div>

      {/* Technical Details (Expandable) */}
      <div className="feedback-section">
        <details style={{ marginTop: '20px' }}>
          <summary style={{ cursor: 'pointer', fontSize: '1.1em', fontWeight: 'bold' }}>
            🔧 Technical Details (Advanced)
          </summary>
          <div style={{ marginTop: '15px', fontSize: '0.9em' }}>
            <h4>Pronunciation Analysis:</h4>
            <ul>
              <li>Pitch Range: {audio_metrics?.pronunciation_analysis?.pitch_range_hz?.toFixed(1) || 'N/A'} Hz</li>
              <li>Mean Pitch: {audio_metrics?.pronunciation_analysis?.pitch_mean_hz?.toFixed(1) || 'N/A'} Hz</li>
              <li>Pitch Stability: {audio_metrics?.pronunciation_analysis?.pitch_std_hz?.toFixed(1) || 'N/A'} Hz std dev</li>
              <li>Monotonous: {audio_metrics?.pronunciation_analysis?.is_monotonous ? 'Yes' : 'No'}</li>
            </ul>
            
            <h4>Fluency Metrics:</h4>
            <ul>
              <li>Speaking Rate: {audio_metrics?.fluency_metrics?.speaking_rate_wpm?.toFixed(0) || 'N/A'} WPM</li>
              <li>Total Pauses: {audio_metrics?.fluency_metrics?.total_pauses || 'N/A'}</li>
              <li>Long Pauses: {audio_metrics?.fluency_metrics?.long_pauses || 'N/A'}</li>
              <li>Rhythm Score: {audio_metrics?.fluency_metrics?.rhythm_consistency_score?.toFixed(0) || 'N/A'}/100</li>
            </ul>
            
            <h4>Voice Quality:</h4>
            <ul>
              <li>Jitter: {audio_metrics?.voice_quality?.jitter_percent?.toFixed(2) || 'N/A'}% (Normal: &lt;1.04%)</li>
              <li>Shimmer: {audio_metrics?.voice_quality?.shimmer_percent?.toFixed(2) || 'N/A'}% (Normal: &lt;3.81%)</li>
              <li>HNR: {audio_metrics?.voice_quality?.hnr_db?.toFixed(1) || 'N/A'} dB (Good: &gt;20 dB)</li>
            </ul>
          </div>
        </details>
      </div>
    </>
  );

  return (
    <div className="impromptu-dashboard">
      <div className="dashboard-header">
        <h2>🚀 Advanced Hybrid Analysis Results</h2>
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

      {/* Topic Display */}
      <div className="feedback-section">
        <h3>Topic: {topic}</h3>
      </div>

      {/* Tab Navigation */}
      <div className="tabs">
        <button 
          className={`tab-button ${activeTab === 'coach' ? 'active' : ''}`} 
          onClick={() => setActiveTab('coach')}>
          🤖 AI Coach Comparison
        </button>
        <button 
          className={`tab-button ${activeTab === 'pronunciation' ? 'active' : ''}`} 
          onClick={() => setActiveTab('pronunciation')}>
          🎙️ Pronunciation Details
        </button>
        <button 
          className={`tab-button ${activeTab === 'audio' ? 'active' : ''}`} 
          onClick={() => setActiveTab('audio')}>
          📊 Voice Quality Insights
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'coach' && renderAiCoachTab()}
        {activeTab === 'pronunciation' && (
          <PronunciationHighlights assessment={azure_pronunciation} />
        )}
        {activeTab === 'audio' && renderAudioMetricsTab()}
      </div>
    </div>
  );
};

export default HybridGroqResults;