import React, { forwardRef } from 'react';
import './Radio.css';

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  helperText?: string;
  error?: string;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ label, helperText, error, className = '', disabled, ...props }, ref) => {
    return (
      <div className={`radio-wrapper ${className}`}>
        <label className={`radio-label ${disabled ? 'radio-label-disabled' : ''}`}>
          <input
            ref={ref}
            type="radio"
            className="radio-input"
            disabled={disabled}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'radio-error' : helperText ? 'radio-helper' : undefined}
            {...props}
          />
          <span className="radio-circle">
            <span className="radio-dot" />
          </span>
          {label && <span className="radio-text">{label}</span>}
        </label>
        {error && (
          <p id="radio-error" className="radio-error">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id="radio-helper" className="radio-helper">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Radio.displayName = 'Radio';

export interface RadioGroupProps {
  name: string;
  value?: string;
  onChange?: (value: string) => void;
  children: React.ReactNode;
  label?: string;
  error?: string;
  orientation?: 'horizontal' | 'vertical';
}

export const RadioGroup: React.FC<RadioGroupProps> = ({
  name,
  value,
  onChange,
  children,
  label,
  error,
  orientation = 'vertical',
}) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.value);
  };

  return (
    <div className="radio-group">
      {label && <div className="radio-group-label">{label}</div>}
      <div className={`radio-group-items radio-group-${orientation}`} role="radiogroup">
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child) && child.type === Radio) {
            return React.cloneElement(child as React.ReactElement<RadioProps>, {
              name,
              checked: child.props.value === value,
              onChange: handleChange,
            });
          }
          return child;
        })}
      </div>
      {error && <p className="radio-group-error">{error}</p>}
    </div>
  );
};
