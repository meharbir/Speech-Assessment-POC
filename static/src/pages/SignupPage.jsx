import React, { useState } from 'react';
import axios from 'axios';
import './Auth.css'; // Import the CSS

const SignupPage = ({ onSignupSuccess, onSwitchToLogin }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [role, setRole] = useState('student'); // Default role
    const [classCode, setClassCode] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        const formData = new FormData();
        formData.append('email', email);
        formData.append('hashed_password', password);
        formData.append('full_name', fullName);
        formData.append('role', role);
        
        if (role === 'student' && classCode) {
            formData.append('class_code', classCode);
        }

        const userData = {
            email,
            hashed_password: password,
            full_name: fullName,
            role,
        };

        try {
            await axios.post('http://localhost:8000/users/signup', userData, {
                params: role === 'student' ? { class_code: classCode } : {}
            });
            onSignupSuccess();
        } catch (err) {
            if (err.response?.status === 400) {
                setError(err.response.data.detail || 'Could not create account.');
            } else if (err.response?.status === 404) {
                setError('Invalid Class Code.');
            } else {
                setError('Could not create account. The email might already be in use.');
            }
            console.error('Signup failed:', err);
        }
    };

    return (
        <div className="auth-container">
            <h1>Create Account</h1>
            {error && <p className="error-message">{error}</p>}
            <form onSubmit={handleSubmit} className="auth-form">
                <div className="form-group">
                    <label>Full Name</label>
                    <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                </div>
                <div className="form-group">
                    <label>Email</label>
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div className="form-group">
                    <label>Password</label>
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <div className="form-group">
                    <label>Role</label>
                    <select value={role} onChange={(e) => setRole(e.target.value)}>
                        <option value="student">Student</option>
                        <option value="teacher">Teacher</option>
                    </select>
                </div>
                {role === 'student' && (
                    <div className="form-group">
                        <label>Class Code</label>
                        <input 
                            type="text" 
                            value={classCode} 
                            onChange={(e) => setClassCode(e.target.value.toUpperCase())} 
                            placeholder="Enter 6-character code"
                            required 
                        />
                    </div>
                )}
                <button type="submit" className="auth-button">Sign Up</button>
            </form>
            <div className="switch-auth">
                <p>
                    Already have an account?{' '}
                    <button onClick={onSwitchToLogin}>Login</button>
                </p>
            </div>
        </div>
    );
};

export default SignupPage;