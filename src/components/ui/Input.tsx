import React, { forwardRef } from 'react';
import './Input.css';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      className = '',
      required,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <div className={`input-wrapper ${fullWidth ? 'input-wrapper-full' : ''} ${className}`}>
        {label && (
          <label className="input-label">
            {label}
            {required && <span className="input-required">*</span>}
          </label>
        )}
        <div
          className={`input-container ${error ? 'input-container-error' : ''} ${
            disabled ? 'input-container-disabled' : ''
          }`}
        >
          {leftIcon && <span className="input-icon input-icon-left">{leftIcon}</span>}
          <input
            ref={ref}
            className={`input ${leftIcon ? 'input-with-left-icon' : ''} ${
              rightIcon ? 'input-with-right-icon' : ''
            }`}
            disabled={disabled}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'input-error' : helperText ? 'input-helper' : undefined}
            {...props}
          />
          {rightIcon && <span className="input-icon input-icon-right">{rightIcon}</span>}
        </div>
        {error && (
          <p id="input-error" className="input-error">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id="input-helper" className="input-helper">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
