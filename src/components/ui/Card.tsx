import React from 'react';
import './card.css';

type Variant = 'default' | 'elevated' | 'glass' | 'outlined';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  hoverable?: boolean;
  interactive?: boolean;
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  hoverable = false,
  interactive = false,
  className = '',
  ...rest
}) => {
  const classes = [
    'ui-card',
    `ui-card-${variant}`,
    hoverable ? 'ui-card-hover' : '',
    interactive ? 'ui-card-interactive' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={classes} {...rest} />
  );
};
