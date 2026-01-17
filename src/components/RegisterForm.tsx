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
    organization_name: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

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
    // Check password strength
    const hasUpper = /[A-Z]/.test(formData.password);
    const hasLower = /[a-z]/.test(formData.password);
    const hasDigit = /[0-9]/.test(formData.password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]/.test(formData.password);

    if (!hasUpper || !hasLower || !hasDigit || !hasSpecial) {
      setFormError('Password must contain uppercase, lowercase, number, and special character');
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
            <label htmlFor="organizationName">Company / Organization Name</label>
            <input
              type="text"
              id="organizationName"
              value={formData.organization_name}
              onChange={(e) => setFormData({ ...formData, organization_name: e.target.value })}
              disabled={loading}
              placeholder="e.g. Acme Corp (Optional)"
            />
          </div>

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
              title="Letters, numbers, underscores and hyphens only"
              autoComplete="username"
            />
            <small>At least 3 characters, alphanumeric</small>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper" style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                disabled={loading}
                required
                minLength={8}
                autoComplete="new-password"
                style={{ width: '100%', paddingRight: '40px' }}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '0',
                  color: 'var(--text-secondary)'
                }}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                )}
              </button>
            </div>
            <small>At least 8 characters with uppercase, lowercase, number, and special character</small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              Confirm Password
              {confirmPassword && (
                <span style={{ 
                  fontSize: '0.8rem', 
                  color: formData.password === confirmPassword ? 'var(--success-color, #10b981)' : 'var(--error-color, #ef4444)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  {formData.password === confirmPassword ? (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      Match
                    </>
                  ) : (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                      No Match
                    </>
                  )}
                </span>
              )}
            </label>
            <div className="password-input-wrapper" style={{ position: 'relative' }}>
              <input
                type={showConfirmPassword ? "text" : "password"}
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                required
                autoComplete="new-password"
                style={{ width: '100%', paddingRight: '40px' }}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '0',
                  color: 'var(--text-secondary)'
                }}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                )}
              </button>
            </div>
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
