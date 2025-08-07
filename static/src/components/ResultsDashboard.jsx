import React, { useState } from 'react';
import './components.css';
import PronunciationView from './PronunciationView';
import ImpromptuResultsDashboard from './ImpromptuResultsDashboard'; // We might display impromptu results too

const ResultsDashboard = ({ results }) => {
    if (results.mode === 'pronunciation') {
        const { azureAssessment } = results;
        return (
            <div>
                {/* NEW: Display the generated text if it exists */}
                {azureAssessment.GeneratedReferenceText && (
                    <div className="generated-text-notice">
                        <h3>AI Generated Reference Text:</h3>
                        <p>The AI corrected your speech to the following text and scored your pronunciation against it.</p>
                        <p className="reference-text">{azureAssessment.GeneratedReferenceText}</p>
                    </div>
                )}
                <PronunciationView pronunciationData={azureAssessment} />
            </div>
        );
    }
    
    if (results.mode.startsWith('impromptu')) {
        return <ImpromptuResultsDashboard results={results} />;
    }

    return <div>Error: Unknown result format</div>;
};

export default ResultsDashboard;