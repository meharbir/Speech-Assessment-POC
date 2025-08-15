import React from 'react';
import { MyProgressPage } from './MyProgressPage'; // We will export this from MyProgressPage next

const StudentProgressViewer = ({ student, onBack }) => {
    return (
        <div>
            <button className="back-to-list-button" onClick={onBack}>
                &larr; Back to Live Dashboard
            </button>
            <h2>Viewing Progress for: {student.full_name}</h2>
            <MyProgressPage userId={student.id} />
        </div>
    );
};

export default StudentProgressViewer;