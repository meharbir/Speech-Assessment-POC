import React, { useState } from 'react';
import './components.css';
import PronunciationView from './PronunciationView';
import FluencyView from './FluencyView';
import GrammarView from './GrammarView';
import VocabularyView from './VocabularyView';
import AiCoachView from './AiCoachView';

const ResultsDashboard = ({ results }) => {
  const [activeTab, setActiveTab] = useState('pronunciation');

  // Simple placeholder for Intonation until chart is re-added
  const SimpleIntonationView = ({ score }) => (
    <div className="view-container">
      <h2>Intonation Score (Prosody): {score}%</h2>
      <p>This score reflects the naturalness of your speech rhythm and tone variation.</p>
      <p><strong>Detailed chart analysis coming soon!</strong></p>
    </div>
  );

  const renderActiveView = () => {
    switch (activeTab) {
      case 'pronunciation':
        return <PronunciationView pronunciationData={results.azureAssessment} />;
      case 'intonation':
        return <SimpleIntonationView score={results.azureAssessment.ProsodyScore} />;
      case 'fluency':
        return <FluencyView fluencyData={results.azureAssessment} />;
      case 'grammar':
        return <GrammarView grammarData={results.azureAssessment} />;
      case 'vocabulary':
        return <VocabularyView vocabData={results.azureAssessment} />;
      case 'ai_coach':
        return <AiCoachView coachData={results.logicalFlowAnalysis} />;
      default:
        return <PronunciationView pronunciationData={results.azureAssessment} />;
    }
  };

  return (
    <div className="dashboard-container">
      {results.azureAssessment.IsUsingFallbackData && (
        <div style={{
          backgroundColor: '#f8d7da',
          border: '2px solid #dc3545',
          padding: '15px',
          marginBottom: '20px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h3 style={{color: '#721c24', margin: '0 0 10px 0'}}>🚨 DEMO MODE - FAKE SCORES 🚨</h3>
          <p style={{color: '#721c24', margin: '5px 0', fontWeight: 'bold'}}>
            These scores are NOT based on your actual speech!
          </p>
          <p style={{color: '#721c24', margin: '5px 0', fontSize: '0.9em'}}>
            Azure Speech API couldn't process the WebM audio format from your browser.
            <br />
            In production, we would convert the audio to a compatible format first.
          </p>
        </div>
      )}
      <aside className="sidebar">
        <h3>Score Details</h3>
        <ul>
          <li className={activeTab === 'pronunciation' ? 'active' : ''} onClick={() => setActiveTab('pronunciation')}>
            Pronunciation <span>{results.azureAssessment.PronunciationScore}%</span>
          </li>
          <li className={activeTab === 'intonation' ? 'active' : ''} onClick={() => setActiveTab('intonation')}>
            Intonation <span>{results.azureAssessment.ProsodyScore}%</span>
          </li>
           <li className={activeTab === 'fluency' ? 'active' : ''} onClick={() => setActiveTab('fluency')}>
            Fluency <span>{results.azureAssessment.FluencyScore}%</span>
          </li>
           <li className={activeTab === 'grammar' ? 'active' : ''} onClick={() => setActiveTab('grammar')}>
            Grammar <span>{results.azureAssessment.GrammarScore}%</span>
          </li>
           <li className={activeTab === 'vocabulary' ? 'active' : ''} onClick={() => setActiveTab('vocabulary')}>
            Vocabulary <span>{results.azureAssessment.VocabScore}%</span>
          </li>
          <li className={activeTab === 'ai_coach' ? 'active' : ''} onClick={() => setActiveTab('ai_coach')}>
            AI Coach
          </li>
        </ul>
      </aside>
      <section className="main-content">
        {renderActiveView()}
      </section>
    </div>
  );
};

export default ResultsDashboard;