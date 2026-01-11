import { useState, useCallback } from 'react';
import { type ToastProps, type ToastVariant } from '../components/ui';

let toastId = 0;

export interface ToastOptions {
  message: string;
  variant?: ToastVariant;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const useToast = () => {
  const [toasts, setToasts] = useState<ToastProps[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (options: ToastOptions) => {
      const id = `toast-${toastId++}`;
      const toast: ToastProps = {
        id,
        message: options.message,
        variant: options.variant || 'info',
        duration: options.duration !== undefined ? options.duration : 5000,
        onClose: removeToast,
        action: options.action,
      };

      setToasts((prevToasts) => [...prevToasts, toast]);
      return id;
    },
    [removeToast]
  );

  const success = useCallback(
    (message: string, options?: Omit<ToastOptions, 'message' | 'variant'>) => {
      return addToast({ message, variant: 'success', ...options });
    },
    [addToast]
  );

  const error = useCallback(
    (message: string, options?: Omit<ToastOptions, 'message' | 'variant'>) => {
      return addToast({ message, variant: 'error', ...options });
    },
    [addToast]
  );

  const warning = useCallback(
    (message: string, options?: Omit<ToastOptions, 'message' | 'variant'>) => {
      return addToast({ message, variant: 'warning', ...options });
    },
    [addToast]
  );

  const info = useCallback(
    (message: string, options?: Omit<ToastOptions, 'message' | 'variant'>) => {
      return addToast({ message, variant: 'info', ...options });
    },
    [addToast]
  );

  const dismiss = useCallback(
    (id: string) => {
      removeToast(id);
    },
    [removeToast]
  );

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    toast: addToast,
    success,
    error,
    warning,
    info,
    dismiss,
    dismissAll,
  };
};
