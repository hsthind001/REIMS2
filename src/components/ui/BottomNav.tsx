import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './BottomNav.css';

export interface BottomNavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: string | number;
}

export interface BottomNavProps {
  items: BottomNavItem[];
}

export const BottomNav: React.FC<BottomNavProps> = ({ items }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleClick = (path: string) => {
    navigate(path);
  };

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <nav className="bottom-nav" role="navigation" aria-label="Mobile navigation">
      {items.map((item) => (
        <button
          key={item.id}
          className={`bottom-nav-item ${isActive(item.path) ? 'bottom-nav-item-active' : ''}`}
          onClick={() => handleClick(item.path)}
          aria-label={item.label}
          aria-current={isActive(item.path) ? 'page' : undefined}
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
