import React from 'react';
import './BottomNav.css';

export interface BottomNavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  badge?: string | number;
  onClick?: () => void;
  isActive?: boolean;
}

export interface BottomNavProps {
  items: BottomNavItem[];
  currentPage?: string;
}

export const BottomNav: React.FC<BottomNavProps> = ({ items, currentPage }) => {
  const isActive = (item: BottomNavItem) => {
    if (item.isActive !== undefined) return item.isActive;
    if (item.path && currentPage) {
      return currentPage === item.path || currentPage.startsWith(item.path + '/');
    }
    return false;
  };

  return (
    <nav className="bottom-nav" role="navigation" aria-label="Mobile navigation">
      {items.map((item) => (
        <button
          key={item.id}
          className={`bottom-nav-item ${isActive(item) ? 'bottom-nav-item-active' : ''}`}
          onClick={item.onClick}
          aria-label={item.label}
          aria-current={isActive(item) ? 'page' : undefined}
        >
          <span className="bottom-nav-icon">{item.icon}</span>
          <span className="bottom-nav-label">{item.label}</span>
          {item.badge !== undefined && (
            <span className="bottom-nav-badge">{item.badge}</span>
          )}
        </button>
      ))}
    </nav>
  );
};
