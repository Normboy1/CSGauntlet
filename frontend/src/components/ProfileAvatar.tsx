import React from 'react';

interface ProfileAvatarProps {
  profilePicture?: string | null;
  username: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  showBorder?: boolean;
}

const ProfileAvatar: React.FC<ProfileAvatarProps> = ({
  profilePicture,
  username,
  size = 'md',
  className = '',
  showBorder = true
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-base',
    lg: 'w-16 h-16 text-lg',
    xl: 'w-24 h-24 text-2xl'
  };

  const borderClasses = showBorder ? 'border-2 border-gray-600' : '';
  
  // Generate initials from username
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Generate a consistent color based on username
  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-red-500',
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-teal-500'
    ];
    
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    return colors[Math.abs(hash) % colors.length];
  };

  return (
    <div 
      className={`
        ${sizeClasses[size]} 
        ${borderClasses} 
        rounded-full 
        overflow-hidden 
        flex 
        items-center 
        justify-center 
        flex-shrink-0
        ${className}
      `}
    >
      {profilePicture ? (
        <img
          src={profilePicture}
          alt={`${username}'s profile`}
          className="w-full h-full object-cover"
          onError={(e) => {
            // If image fails to load, hide it and show initials
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const parent = target.parentElement;
            if (parent) {
              parent.classList.add(getAvatarColor(username));
              parent.innerHTML = `<span class="font-semibold text-white">${getInitials(username)}</span>`;
            }
          }}
        />
      ) : (
        <div className={`w-full h-full ${getAvatarColor(username)} flex items-center justify-center`}>
          <span className="font-semibold text-white">
            {getInitials(username)}
          </span>
        </div>
      )}
    </div>
  );
};

export default ProfileAvatar;