import React from 'react';
import './components.css';

const FluencyView = ({ fluencyData }) => (
  <div className="view-container">
    <h2>Fluency Score: {fluencyData.FluencyScore}%</h2>
    <div className="metric-cards-container">
      <div className="metric-card">
        <h4>Words Per Minute</h4>
        <p>{fluencyData.Wpm}</p>
      </div>
      <div className="metric-card">
        <h4>Pauses</h4>
        <p>{fluencyData.Pause.Count} pauses detected</p>
      </div>
      <div className="metric-card">
        <h4>Filler Words</h4>
        <p>{(fluencyData.Miscues.FillerWordCount || 0)} detected</p>
      </div>
    </div>
  </div>
);

export default FluencyView;