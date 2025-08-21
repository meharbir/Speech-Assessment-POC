import React from 'react';
import './ImpromptuDashboard.css';

const ScoreCard = ({ title, score = 0, feedback, icon }) => {
  const getScoreColor = (s) => {
    if (s >= 90) return '#27ae60'; // Emerald
    if (s >= 70) return '#2980b9'; // Belize Hole
    if (s >= 40) return '#f39c12'; // Orange
    return '#c0392b'; // Pomegranate
  };

  return (
    <div className="score-card">
      <h4><span>{icon}</span> {title}</h4>
      <div className="score-circle" style={{ borderColor: getScoreColor(score) }}>
        <span className="score-number">{score}</span>
      </div>
      <p className="score-feedback">{feedback}</p>
    </div>
  );
};

export default ScoreCard;