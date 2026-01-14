import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import './Tooltip.css';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  placement = 'top',
  delay = 300,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | undefined>(undefined);

  const updatePosition = () => {
    // ... same code
    if (!triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();

    let top = 0;
    let left = 0;

    switch (placement) {
      case 'top':
        top = triggerRect.top - tooltipRect.height - 8;
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
        break;
      case 'bottom':
        top = triggerRect.bottom + 8;
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2;
        left = triggerRect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2;
        left = triggerRect.right + 8;
        break;
    }

    // Keep tooltip within viewport
    const margin = 8;
    if (left < margin) left = margin;
    if (left + tooltipRect.width > window.innerWidth - margin) {
      left = window.innerWidth - tooltipRect.width - margin;
    }
    if (top < margin) top = margin;
    if (top + tooltipRect.height > window.innerHeight - margin) {
      top = window.innerHeight - tooltipRect.height - margin;
    }

    setPosition({ top, left });
  };

  useEffect(() => {
    if (isVisible) {
      updatePosition();
      window.addEventListener('scroll', updatePosition);
      window.addEventListener('resize', updatePosition);

      return () => {
        window.removeEventListener('scroll', updatePosition);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isVisible]);

  const showTooltip = () => {
    timeoutRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  const clonedChild = React.cloneElement(children as React.ReactElement<any>, {
    ref: triggerRef,
    onMouseEnter: (e: React.MouseEvent) => {
      showTooltip();
      (children.props as any).onMouseEnter?.(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      hideTooltip();
      (children.props as any).onMouseLeave?.(e);
    },
    onFocus: (e: React.FocusEvent) => {
      showTooltip();
      (children.props as any).onFocus?.(e);
    },
    onBlur: (e: React.FocusEvent) => {
      hideTooltip();
      (children.props as any).onBlur?.(e);
    },
  });

  return (
    <>
      {clonedChild}
      {isVisible &&
        createPortal(
          <div
            ref={tooltipRef}
            className={`tooltip tooltip-${placement}`}
            style={{
              top: `${position.top}px`,
              left: `${position.left}px`,
            }}
            role="tooltip"
          >
            {content}
          </div>,
          document.body
        )}
    </>
  );
};
