import React from 'react';
import { motion } from 'framer-motion';
import styles from './Card.module.css';

export interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'premium';
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  className = '',
  onClick,
  hover = true,
}) => {
  const classes = [
    styles.card,
    styles[variant],
    onClick ? styles.clickable : '',
    className
  ].filter(Boolean).join(' ');

  const Component = onClick ? motion.div : 'div';
  const motionProps = onClick
    ? {
        whileHover: hover ? { scale: 1.01 } : {},
        whileTap: { scale: 0.99 },
        onClick,
      }
    : {};

  return (
    <Component className={classes} {...motionProps}>
      {children}
    </Component>
  );
};
