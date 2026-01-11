import React, { forwardRef } from 'react';
import './Checkbox.css';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  helperText?: string;
  error?: string;
  indeterminate?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, helperText, error, indeterminate = false, className = '', disabled, ...props }, ref) => {
    return (
      <div className={`checkbox-wrapper ${className}`}>
        <label className={`checkbox-label ${disabled ? 'checkbox-label-disabled' : ''}`}>
          <input
            ref={ref}
            type="checkbox"
            className="checkbox-input"
            disabled={disabled}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'checkbox-error' : helperText ? 'checkbox-helper' : undefined}
            {...props}
          />
          <span className={`checkbox-box ${indeterminate ? 'checkbox-indeterminate' : ''}`}>
            {indeterminate ? (
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M2 6H10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            ) : (
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M10 3L4.5 8.5L2 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </span>
          {label && <span className="checkbox-text">{label}</span>}
        </label>
        {error && (
          <p id="checkbox-error" className="checkbox-error">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id="checkbox-helper" className="checkbox-helper">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';
