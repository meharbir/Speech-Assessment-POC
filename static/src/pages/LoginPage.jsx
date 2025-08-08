import React, { useState } from 'react';
import axios from 'axios';
import './Auth.css'; // Import the CSS

const LoginPage = ({ onLoginSuccess, onSwitchToSignup, onContinueAsGuest }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        const params = new URLSearchParams();
        params.append('username', email);
        params.append('password', password);

        try {
            const response = await axios.post('http://localhost:8000/token', params);
            onLoginSuccess(response.data.access_token);
        } catch (err) {
            setError('Invalid email or password. Please try again.');
            console.error('Login failed:', err);
        }
    };

    return (
        <div className="auth-container">
            <h1>Login</h1>
            {error && <p className="error-message">{error}</p>}
            <form onSubmit={handleSubmit} className="auth-form">
                <div className="form-group">
                    <label>Email</label>
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div className="form-group">
                    <label>Password</label>
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <button type="submit" className="auth-button">Login</button>
            </form>
            <div className="switch-auth">
                <p>
                    Don't have an account?{' '}
                    <button onClick={onSwitchToSignup}>Sign Up</button>
                </p>
                <p>
                    Or{' '}
                    <button onClick={onContinueAsGuest}>Continue as Guest</button>
                </p>
            </div>
        </div>
    );
};

export default LoginPage;