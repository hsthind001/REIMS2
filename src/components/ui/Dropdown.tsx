import React, { useState, useRef, useEffect } from 'react';
import './Dropdown.css';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'default' | 'danger';
  divider?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  closeOnSelect?: boolean;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'left',
  closeOnSelect = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const handleItemClick = (item: DropdownItem) => {
    if (item.disabled) return;

    item.onClick?.();

    if (closeOnSelect) {
      setIsOpen(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent, item: DropdownItem) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleItemClick(item);
    }
  };

  return (
    <div className="dropdown" ref={dropdownRef}>
      <div
        className="dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        aria-haspopup="true"
        aria-expanded={isOpen}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
      >
        {trigger}
      </div>

      {isOpen && (
        <div className={`dropdown-menu dropdown-menu-${align}`} role="menu">
          {items.map((item, index) => (
            <React.Fragment key={item.id}>
              {item.divider ? (
                <div className="dropdown-divider" role="separator" />
              ) : (
                <button
                  className={`dropdown-item ${item.variant === 'danger' ? 'dropdown-item-danger' : ''} ${
                    item.disabled ? 'dropdown-item-disabled' : ''
                  }`}
                  onClick={() => handleItemClick(item)}
                  onKeyDown={(e) => handleKeyDown(e, item)}
                  disabled={item.disabled}
                  role="menuitem"
                  tabIndex={0}
                >
                  {item.icon && <span className="dropdown-item-icon">{item.icon}</span>}
                  <span className="dropdown-item-label">{item.label}</span>
                </button>
              )}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};
