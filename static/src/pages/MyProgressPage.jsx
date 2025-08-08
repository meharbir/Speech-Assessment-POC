import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MyProgressPage.css';
import ImpromptuResultsDashboard from '../components/ImpromptuResultsDashboard';
import ResultsDashboard from '../components/ResultsDashboard'; // For pronunciation

// Helper component to render the correct summary scores for the list view
const SessionScores = ({ feedback }) => {
    // Check if feedback and feedback.data exist before accessing properties
    if (!feedback || !feedback.data) {
        return <div className="session-scores"><p>Score data is unavailable.</p></div>;
    }

    if (feedback.type === 'impromptu') {
        return (
            <div className="session-scores">
                <div className="score-item">
                    <span className="score-value">{feedback.data.grammar_score ?? 'N/A'}</span>
                    <span className="score-label">Grammar</span>
                </div>
                <div className="score-item">
                    <span className="score-value">{feedback.data.vocabulary_score ?? 'N/A'}</span>
                    <span className="score-label">Vocabulary</span>
                </div>
                <div className="score-item">
                    <span className="score-value">{feedback.data.coherence_score ?? 'N/A'}</span>
                    <span className="score-label">Coherence</span>
                </div>
                <div className="score-item">
                    <span className="score-value">{feedback.data.fluency_score ?? 'N/A'}</span>
                    <span className="score-label">Fluency</span>
                </div>
            </div>
        );
    }

    if (feedback.type === 'pronunciation') {
        return (
            <div className="session-scores">
                <div className="score-item">
                    <span className="score-value">{feedback.data.PronunciationScore ?? 'N/A'}</span>
                    <span className="score-label">Pronunciation</span>
                </div>
                <div className="score-item">
                    <span className="score-value">{feedback.data.FluencyScore ?? 'N/A'}</span>
                    <span className="score-label">Fluency</span>
                </div>
                <div className="score-item">
                    <span className="score-value">{feedback.data.CompletenessScore ?? 'N/A'}</span>
                    <span className="score-label">Completeness</span>
                </div>
            </div>
        );
    }
    return null;
};

const MyProgressPage = () => {
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedSession, setSelectedSession] = useState(null);

    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const response = await axios.get('http://localhost:8000/api/me/sessions');
                const parsedSessions = response.data.map(session => {
                    try {
                        // This correctly parses the {"type": "...", "data": ...} structure
                        return { ...session, feedback: JSON.parse(session.feedback_json) };
                    } catch (e) {
                        console.error("Failed to parse feedback JSON for session:", session.id, e);
                        return { ...session, feedback: null };
                    }
                }).filter(session => session.feedback);

                setSessions(parsedSessions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
            } catch (err) {
                setError('Could not fetch session history.');
                console.error("Failed to fetch sessions:", err);
            } finally {
                setIsLoading(false);
            }
        };
        fetchSessions();
    }, []);

    // RENDER THE DETAILED VIEW
    if (selectedSession) {
        let detailView = <p>Could not display details for this session type.</p>;

        if (selectedSession.feedback?.type === 'impromptu') {
            const resultsForDashboard = {
                transcript: selectedSession.transcript,
                aiCoachAnalysis: selectedSession.feedback.data
            };
            detailView = <ImpromptuResultsDashboard results={resultsForDashboard} />;
        } else if (selectedSession.feedback?.type === 'pronunciation') {
            const resultsForDashboard = {
                azureAssessment: selectedSession.feedback.data
            };
            detailView = <ResultsDashboard results={resultsForDashboard} />;
        }

        return (
            <div className="progress-container">
                <button className="back-to-list-button" onClick={() => setSelectedSession(null)}>
                    &larr; Back to Progress List
                </button>
                {detailView}
            </div>
        );
    }

    // RENDER THE LIST VIEW
    return (
        <div className="progress-container">
            <h2>My Progress</h2>
            <p>Here is a history of all your practice sessions. Click 'View Details' to review the full feedback.</p>
            {isLoading && <div>Loading your progress...</div>}
            {error && <div className="error-message">{error}</div>}
            {!isLoading && !error && (
                <div className="sessions-list">
                    {sessions.length > 0 ? (
                        sessions.map(session => (
                            <div key={session.id} className="session-card">
                                <div className="session-card-header">
                                    <h3>{session.topic}</h3>
                                    <p><strong>Type:</strong> <span className="session-type">{session.feedback.type || 'Unknown'}</span></p>
                                    <p><strong>Practiced on:</strong> {new Date(session.created_at).toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' })}</p>
                                </div>
                                <SessionScores feedback={session.feedback} />
                                <button className="view-details-button" onClick={() => setSelectedSession(session)}>
                                    View Details
                                </button>
                            </div>
                        ))
                    ) : (
                        <div className="session-card">
                            <p>You haven't completed any practice sessions yet. Go to the 'Practice' tab to get started!</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default MyProgressPage;