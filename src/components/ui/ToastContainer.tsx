import React from 'react';
import { Toast } from './Toast';
import type { ToastProps } from './Toast';
import './ToastContainer.css';

interface ToastContainerProps {
  toasts: ToastProps[];
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  position = 'top-right',
}) => {
  if (toasts.length === 0) return null;

  return (
    <div className={`toast-container toast-container-${position}`} aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} />
      ))}
    </div>
  );
};
