import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import './breadcrumb.css';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
  onClick?: () => void;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: React.ReactNode;
  showHome?: boolean;
  homeHref?: string;
  onHomeClick?: () => void;
  className?: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator,
  showHome = true,
  homeHref = '/',
  onHomeClick,
  className = '',
}) => {
  const defaultSeparator = separator || <ChevronRight className="w-4 h-4" />;

  const handleItemClick = (item: BreadcrumbItem, e: React.MouseEvent) => {
    if (item.onClick) {
      e.preventDefault();
      item.onClick();
    }
  };

  const handleHomeClick = (e: React.MouseEvent) => {
    if (onHomeClick) {
      e.preventDefault();
      onHomeClick();
    }
  };

  return (
    <nav aria-label="Breadcrumb" className={`ui-breadcrumb ${className}`}>
      <ol className="ui-breadcrumb-list">
        {showHome && (
          <>
            <li className="ui-breadcrumb-item">
              <a
                href={homeHref}
                onClick={handleHomeClick}
                className="ui-breadcrumb-link"
                aria-label="Home"
              >
                <Home className="w-4 h-4" />
              </a>
            </li>
            {items.length > 0 && (
              <li className="ui-breadcrumb-separator" aria-hidden="true">
                {defaultSeparator}
              </li>
            )}
          </>
        )}

        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <React.Fragment key={index}>
              <li className={`ui-breadcrumb-item ${isLast ? 'ui-breadcrumb-item-active' : ''}`}>
                {item.href || item.onClick ? (
                  <a
                    href={item.href || '#'}
                    onClick={(e) => handleItemClick(item, e)}
                    className="ui-breadcrumb-link"
                    aria-current={isLast ? 'page' : undefined}
                  >
                    {item.icon && <span className="ui-breadcrumb-icon">{item.icon}</span>}
                    {item.label}
                  </a>
                ) : (
                  <span className="ui-breadcrumb-text">
                    {item.icon && <span className="ui-breadcrumb-icon">{item.icon}</span>}
                    {item.label}
                  </span>
                )}
              </li>

              {!isLast && (
                <li className="ui-breadcrumb-separator" aria-hidden="true">
                  {defaultSeparator}
                </li>
              )}
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
};
