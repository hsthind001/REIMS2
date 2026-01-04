/**
 * Registration Form Component
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from './AuthContext';
import type { UserCreate } from '../types/api';

export function RegisterForm() {
  const { register, loading, error } = useAuth();
  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    username: '',
    password: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState(false);

  const validateForm = (): boolean => {
    // Check all fields filled
    if (!formData.email || !formData.username || !formData.password) {
      setFormError('All fields are required');
      return false;
    }

    // Check username length
    if (formData.username.length < 3) {
      setFormError('Username must be at least 3 characters');
      return false;
    }

    // Check username format
    if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      setFormError('Username can only contain letters, numbers, underscores and hyphens');
      return false;
    }

    // Check password length
    if (formData.password.length < 8) {
      setFormError('Password must be at least 8 characters');
      return false;
    }

    // Check password strength
    const hasUpper = /[A-Z]/.test(formData.password);
    const hasLower = /[a-z]/.test(formData.password);
    const hasDigit = /[0-9]/.test(formData.password);

    if (!hasUpper || !hasLower || !hasDigit) {
      setFormError('Password must contain uppercase, lowercase, and digit');
      return false;
    }

    // Check password confirmation
    if (formData.password !== confirmPassword) {
      setFormError('Passwords do not match');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError('');
    setSuccess(false);

    if (!validateForm()) {
      return;
    }

    try {
      await register(formData);
      setSuccess(true);
      // Clear form
      setFormData({ email: '', username: '', password: '' });
      setConfirmPassword('');
    } catch (err: any) {
      setFormError(err.message || 'Registration failed');
    }
  };

  return (
    <div className="register-form-container">
      <div className="register-form-card">
        <h2>Register for REIMS</h2>
        <p className="subtitle">Create your account</p>

        {(error || formError) && (
          <div className="alert alert-error">
            {error || formError}
          </div>
        )}

        {success && (
          <div className="alert alert-success">
            Registration successful! You are now logged in.
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              disabled={loading}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              disabled={loading}
              required
              minLength={3}
              pattern="[a-zA-Z0-9_-]+"
              title="Letters, numbers, underscores and hyphens only"
              autoComplete="username"
            />
            <small>At least 3 characters, alphanumeric</small>
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
              minLength={8}
              autoComplete="new-password"
            />
            <small>At least 8 characters with uppercase, lowercase, and number</small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              required
              autoComplete="new-password"
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <div className="form-footer">
          <p>Already have an account? <a href="#login">Login here</a></p>
        </div>
      </div>
    </div>
  );
}
