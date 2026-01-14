import React from 'react';
import './badge.css';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'primary' | 'purple';
  size?: 'sm' | 'md' | 'lg';
  rounded?: boolean;
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  rounded = false,
  dot = false,
  className = '',
}) => {
  const badgeClasses = [
    'ui-badge',
    `ui-badge-${variant}`,
    `ui-badge-${size}`,
    rounded ? 'ui-badge-rounded' : '',
    dot ? 'ui-badge-dot' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <span className={badgeClasses}>
      {dot && <span className="ui-badge-dot-indicator" />}
      {children}
    </span>
  );
};
