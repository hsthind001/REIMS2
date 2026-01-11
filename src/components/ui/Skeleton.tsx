import React from 'react';
import './skeleton.css';

type Variant = 'rect' | 'circle' | 'text';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'rect',
  className = '',
  ...rest
}) => {
  const classes = ['ui-skeleton', `ui-skeleton-${variant}`, className].filter(Boolean).join(' ');
  return <div className={classes} aria-hidden {...rest} />;
};
