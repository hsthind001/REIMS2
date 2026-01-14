import React from 'react';
import { motion } from 'framer-motion';
import './button.css';

export type Variant = 
  | 'primary' 
  | 'secondary' 
  | 'ghost' 
  | 'danger' 
  | 'success' 
  | 'warning' 
  | 'info' 
  | 'premium' 
  | 'outline'
  | 'default';

export type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  className = '',
  children,
  disabled,
  type = 'button',
  ...rest
}) => {
  const classes = [
    'ui-btn',
    `ui-btn-${variant}`,
    `ui-btn-${size}`,
    className
  ].filter(Boolean).join(' ');

  return (
    <motion.button
      whileHover={!(disabled || loading) ? { scale: 1.01, translateY: -1 } : {}}
      whileTap={!(disabled || loading) ? { scale: 0.99, translateY: 0 } : {}}
      className={classes}
      disabled={disabled || loading}
      type={type}
      {...rest as any}
    >
      {loading ? (
        <span className="ui-btn-spinner" aria-hidden />
      ) : (
        icon && <span className="ui-btn-icon">{icon}</span>
      )}
      <span className="ui-btn-text">{children}</span>
    </motion.button>
  );
};
