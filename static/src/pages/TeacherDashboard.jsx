import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TeacherDashboard.css';
import StudentProgressViewer from './StudentProgressViewer';

const BroadcastControlCard = ({ mode, title, description, placeholder, onBroadcast }) => {
    const [text, setText] = useState('');
    
    const handleBroadcast = () => {
        if (!text.trim()) {
            alert('Please enter a topic or sentence to broadcast.');
            return;
        }
        onBroadcast(mode, text);
        setText('');
    };

    return (
        <div className="control-card">
            <h3>{title}</h3>
            <p>{description}</p>
            <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={placeholder}
                rows={3}
            />
            <button onClick={handleBroadcast}>Broadcast to Class</button>
        </div>
    );
};

const TeacherDashboard = ({ studentStatuses, sendMessage }) => {
    const [myClass, setMyClass] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [newClassName, setNewClassName] = useState('');
    const [copyButtonText, setCopyButtonText] = useState('Copy Code');
    const [students, setStudents] = useState([]);
    const [viewingStudent, setViewingStudent] = useState(null);
    const [classReport, setClassReport] = useState(null);
    const [isReportLoading, setIsReportLoading] = useState(false);
    const [lastBroadcastedTopic, setLastBroadcastedTopic] = useState('');

    useEffect(() => {
        const fetchClass = async () => {
            try {
                const response = await axios.get('http://localhost:8000/api/teacher/my-class');
                setMyClass(response.data);
            } catch (err) {
                if (err.response && err.response.status === 404) {
                    // This is not an error, it just means the teacher needs to create a class.
                    setMyClass(null);
                } else {
                    setError('Could not fetch class data. Please try again later.');
                }
            } finally {
                setIsLoading(false);
            }
        };
        fetchClass();
    }, []);

    useEffect(() => {
        const fetchStudents = async () => {
            if (myClass) {
                try {
                    const response = await axios.get('http://localhost:8000/api/teacher/students');
                    setStudents(response.data);
                } catch (err) {
                    console.error('Failed to fetch students:', err);
                }
            }
        };
        fetchStudents();
    }, [myClass]);

    const handleCreateClass = async (e) => {
        e.preventDefault();
        setError('');
        if (!newClassName) {
            setError('Please enter a name for your class.');
            return;
        }
        try {
            const response = await axios.post('http://localhost:8000/api/teacher/classes', { name: newClassName });
            setMyClass(response.data);
            setNewClassName('');
        } catch (err) {
            setError('Could not create class. Please try again.');
        }
    };

    const handleCopyCode = () => {
        navigator.clipboard.writeText(myClass.class_code);
        setCopyButtonText('Copied! ✅');
        setTimeout(() => setCopyButtonText('Copy Code'), 2000);
    };

    const handleBroadcastTopic = async (mode, text) => {
        try {
            await axios.post('http://localhost:8000/api/teacher/class/topic', { mode, text });
            alert('Topic has been sent to all students!');
            setLastBroadcastedTopic(text);
        } catch (error) {
            console.error("Failed to broadcast topic:", error);
            alert('An error occurred while broadcasting the topic.');
        }
    };

    const handleGenerateReport = async (topic) => {
        setIsReportLoading(true);
        setClassReport(null);
        setError('');
        try {
            const response = await axios.post('http://localhost:8000/api/teacher/class/summary', { topic });
            setClassReport(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate class report.');
        } finally {
            setIsReportLoading(false);
        }
    };

    if (viewingStudent) {
        return <StudentProgressViewer student={viewingStudent} onBack={() => setViewingStudent(null)} />;
    }

    if (isLoading) {
        return <div className="teacher-dashboard">Loading Teacher Dashboard...</div>;
    }

    return (
        <div className="teacher-dashboard">
            <h2>Teacher Dashboard</h2>
            {error && <p className="error-message">{error}</p>}
            
            {myClass ? (
                <div className="class-info-card">
                    <h3>Your Class Details</h3>
                    <p><strong>Class Name:</strong> {myClass.name}</p>
                    <div className="class-code-section">
                        <p><strong>Share this Class Code with your students:</strong></p>
                        <p className="class-code">{myClass.class_code}</p>
                        <button onClick={handleCopyCode} className="copy-code-button">
                            {copyButtonText}
                        </button>
                    </div>
                    <p className="rubric-note">
                        Note: All AI feedback is aligned with the official CBSE ASL Grade XI-XII curriculum.
                    </p>
                </div>
            ) : (
                <div className="create-class-card">
                    <h3>Create Your First Class</h3>
                    <p>To get started, create a class. A unique code will be generated for your students to join.</p>
                    <form onSubmit={handleCreateClass} className="create-class-form">
                        <input
                            type="text"
                            value={newClassName}
                            onChange={(e) => setNewClassName(e.target.value)}
                            placeholder="e.g., Class 10A English"
                        />
                        <button type="submit">Create Class</button>
                    </form>
                </div>
            )}

            {myClass && (
                <div className="control-cards-container">
                    <BroadcastControlCard
                        mode="impromptu-chunked"
                        title="Impromptu Speaking"
                        description="Set a topic for students to speak about freely."
                        placeholder="e.g., My favorite holiday"
                        onBroadcast={handleBroadcastTopic}
                    />
                    <BroadcastControlCard
                        mode="pronunciation"
                        title="Pronunciation Practice"
                        description="Provide a sentence for students to read aloud."
                        placeholder="e.g., The quick brown fox jumps over the lazy dog."
                        onBroadcast={handleBroadcastTopic}
                    />
                    <BroadcastControlCard
                        mode="hybrid-groq"
                        title="🚀 Advanced Hybrid Analysis"
                        description="Set a topic for comprehensive analysis with Whisper, Azure, Groq, and audio metrics."
                        placeholder="e.g., The benefits of technology in education"
                        onBroadcast={handleBroadcastTopic}
                    />
                </div>
            )}

            {/* Class Actions Card */}
            {myClass && (
                <div className="class-actions-card">
                    <h3>Class Reports & Actions</h3>
                    {lastBroadcastedTopic ? (
                        <div className="report-section">
                            <p>Generate a report for the last session on: <strong>"{lastBroadcastedTopic}"</strong></p>
                            <button onClick={() => handleGenerateReport(lastBroadcastedTopic)} disabled={isReportLoading}>
                                {isReportLoading ? 'Generating...' : 'Generate Class Report'}
                            </button>
                        </div>
                    ) : (
                        <p>Broadcast a topic to your class to enable report generation.</p>
                    )}

                    {classReport && (
                        <div className="report-display">
                            <h4>Class Performance Summary</h4>
                            <div className="report-content">
                                <h5>Strengths</h5>
                                <ul>
                                    {classReport.strengths?.map((s, i) => <li key={i}>{s}</li>)}
                                </ul>
                                <h5>Areas for Improvement</h5>
                                <ul>
                                    {classReport.weaknesses?.map((w, i) => <li key={i}>{w}</li>)}
                                </ul>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Live Student Activity Grid */}
            {myClass && students.length > 0 && (
                <div className="live-dashboard-card">
                    <h3>Live Student Activity</h3>
                    <div className="student-grid">
                        {students.map(student => {
                            const status = studentStatuses[student.id] || 'waiting';
                            const displayStatus = status.charAt(0).toUpperCase() + status.slice(1);
                            return (
                                <div 
                                    key={student.id} 
                                    className={`student-card status-${status}`}
                                    onClick={() => setViewingStudent(student)}
                                >
                                    <p className="student-name">{student.full_name}</p>
                                    <p className="student-status">{displayStatus}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TeacherDashboard;