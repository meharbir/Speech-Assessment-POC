import React from 'react';
import './ImpromptuDashboard.css'; // We will create this next

const ScoreCard = ({ title, score, feedback }) => {
  const getScoreColor = (s) => {
    if (s > 90) return '#27ae60'; // Green
    if (s > 70) return '#2980b9'; // Blue
    if (s > 40) return '#f39c12'; // Yellow
    return '#c0392b'; // Red
  };

  return (
    <div className="score-card">
      <h4>{title}</h4>
      <div className="score-display">
        <div className="score-circle" style={{ borderColor: getScoreColor(score) }}>
          <span className="score-number">{score}</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ 
              width: `${score}%`, 
              backgroundColor: getScoreColor(score) 
            }}
          ></div>
        </div>
      </div>
      <p className="score-feedback">{feedback}</p>
    </div>
  );
};

export default ScoreCard;