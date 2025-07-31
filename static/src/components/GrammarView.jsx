import React from 'react';
import './components.css';

const GrammarView = ({ grammarData }) => (
  <div className="view-container">
    <h2>Grammar Score: {grammarData.GrammarScore}%</h2>
    <h4>Detected Grammatical Errors:</h4>
    <ul>
      {grammarData.GrammaticalErrors && grammarData.GrammaticalErrors.length > 0 ? (
        grammarData.GrammaticalErrors.map((error, i) => <li key={i}>{error.Message}</li>)
      ) : (
        <p>No grammatical errors detected. Great job!</p>
      )}
    </ul>
  </div>
);

export default GrammarView;