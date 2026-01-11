import React, { forwardRef } from 'react';
import './Switch.css';

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  helperText?: string;
  error?: string;
  labelPosition?: 'left' | 'right';
}

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  (
    {
      label,
      helperText,
      error,
      labelPosition = 'right',
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <div className={`switch-wrapper ${className}`}>
        <label
          className={`switch-label ${disabled ? 'switch-label-disabled' : ''} switch-label-${labelPosition}`}
        >
          {label && labelPosition === 'left' && <span className="switch-text">{label}</span>}
          <span className="switch-container">
            <input
              ref={ref}
              type="checkbox"
              className="switch-input"
              role="switch"
              disabled={disabled}
              aria-invalid={error ? 'true' : 'false'}
              aria-describedby={error ? 'switch-error' : helperText ? 'switch-helper' : undefined}
              {...props}
            />
            <span className="switch-track">
              <span className="switch-thumb" />
            </span>
          </span>
          {label && labelPosition === 'right' && <span className="switch-text">{label}</span>}
        </label>
        {error && (
          <p id="switch-error" className="switch-error">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id="switch-helper" className="switch-helper">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Switch.displayName = 'Switch';
