import React from 'react';
import './avatar.css';

export interface AvatarProps {
  src?: string;
  alt?: string;
  name?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'circle' | 'square' | 'rounded';
  status?: 'online' | 'offline' | 'away' | 'busy';
  fallbackColor?: string;
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  name,
  size = 'md',
  variant = 'circle',
  status,
  fallbackColor,
  className = '',
}) => {
  const [imageError, setImageError] = React.useState(false);
  
  const getInitials = (fullName: string): string => {
    const nameParts = fullName.trim().split(' ');
    if (nameParts.length >= 2) {
      return `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`.toUpperCase();
    }
    return fullName.slice(0, 2).toUpperCase();
  };

  const getColorFromName = (fullName: string): string => {
    if (fallbackColor) return fallbackColor;
    
    // Generate a color from the name
    let hash = 0;
    for (let i = 0; i < fullName.length; i++) {
      hash = fullName.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const colors = [
      '#3b82f6', // blue
      '#8b5cf6', // purple
      '#ec4899', // pink
      '#10b981', // green
      '#f59e0b', // amber
      '#ef4444', // red
      '#06b6d4', // cyan
      '#6366f1', // indigo
    ];
    
    return colors[Math.abs(hash) % colors.length];
  };

  const avatarClasses = [
    'ui-avatar',
    `ui-avatar-${size}`,
    `ui-avatar-${variant}`,
    className
  ].filter(Boolean).join(' ');

  const statusClasses = status ? [
    'ui-avatar-status',
    `ui-avatar-status-${status}`
  ].join(' ') : '';

  const displayName = name || alt || 'User';
  const initials = getInitials(displayName);
  const backgroundColor = getColorFromName(displayName);

  return (
    <div className={avatarClasses} style={{ position: 'relative' }}>
      {src && !imageError ? (
        <img
          src={src}
          alt={alt || displayName}
          className="ui-avatar-image"
          onError={() => setImageError(true)}
        />
      ) : (
        <div 
          className="ui-avatar-fallback"
          style={{ backgroundColor }}
        >
          <span className="ui-avatar-initials">{initials}</span>
        </div>
      )}
      {status && <span className={statusClasses} />}
    </div>
  );
};

export interface AvatarGroupProps {
  children: React.ReactNode;
  max?: number;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  children,
  max = 5,
  size = 'md',
  className = '',
}) => {
  const childArray = React.Children.toArray(children);
  const visibleChildren = childArray.slice(0, max);
  const remainingCount = childArray.length - max;

  return (
    <div className={`ui-avatar-group ${className}`}>
      {visibleChildren.map((child, index) => (
        <div 
          key={index} 
          className="ui-avatar-group-item"
          style={{ zIndex: visibleChildren.length - index }}
        >
          {child}
        </div>
      ))}
      {remainingCount > 0 && (
        <div className="ui-avatar-group-item" style={{ zIndex: 0 }}>
          <Avatar 
            name={`+${remainingCount}`} 
            size={size}
            fallbackColor="#64748b"
          />
        </div>
      )}
    </div>
  );
};
