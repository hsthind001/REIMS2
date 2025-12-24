/**
 * Login Form Component
 */

import { useState, FormEvent } from 'react';
import { Link, useLocation, useNavigate, type Location } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { UserLogin } from '../types/api';

export function LoginForm() {
  const { login, loading, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formData, setFormData] = useState<UserLogin>({
    username: '',
    password: '',
  });
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSuccess(false);

    if (!formData.username || !formData.password) {
      setFormError('Please enter both username and password');
      return;
    }

    try {
      await login(formData);
      setSuccess(true);
      // Clear form
      setFormData({ username: '', password: '' });

      const redirectTo = (location.state as { from?: Location })?.from?.pathname || '/';
      navigate(redirectTo, { replace: true });
    } catch (err: any) {
      setFormError(err.message || 'Login failed');
    }
  };

  return (
    <div className="login-form-container">
      <div className="login-form-card">
        <h2>Login to REIMS</h2>
        <p className="subtitle">Real Estate Investment Management System</p>

        {(error || formError) && (
          <div className="alert alert-error">
            {error || formError}
          </div>
        )}

        {success && (
          <div className="alert alert-success">
            Login successful! Redirecting...
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              disabled={loading}
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              disabled={loading}
              required
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="form-footer">
          <p>Don't have an account? <Link to="/register">Register here</Link></p>
        </div>
      </div>
    </div>
  );
}
