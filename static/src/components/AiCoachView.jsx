import React from 'react';
import './components.css';

const AiCoachView = ({ coachData }) => {
  // Use optional chaining (?.) to prevent crashes if data is not present
  const suggestions = coachData?.rephrasing_suggestions || [];
  const coherenceFeedback = coachData?.coherence_feedback || "No feedback available.";
  const endingRecommendation = coachData?.ending_recommendation || "No feedback available.";

  return (
    <div className="view-container">
      <h2>AI Coach Feedback</h2>
      
      <div className="feedback-section">
        <h4>Coherence and Flow</h4>
        <p>{coherenceFeedback}</p>
      </div>

      <div className="feedback-section">
        <h4>Rephrasing Suggestions</h4>
        {suggestions.length > 0 ? (
          <ul>
            {suggestions.map((item, i) => (
              <li key={i}>
                <strong>Original:</strong> "{item.original}"<br />
                <strong>Suggestion:</strong> "{item.suggestion}"
              </li>
            ))}
          </ul>
        ) : <p>No specific rephrasing suggestions needed.</p>}
      </div>

      <div className="feedback-section">
        <h4>Ending Recommendation</h4>
        <p>{endingRecommendation}</p>
      </div>
    </div>
  );
};

export default AiCoachView;