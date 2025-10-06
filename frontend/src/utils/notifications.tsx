import React, { useState, createContext, useContext, ReactNode, useRef } from 'react';

type NotificationType = 'success' | 'error' | 'info';

interface Notification {
  id: number;
  message: string;
  type: NotificationType;
}

interface NotificationContextType {
  notifications: Notification[];
  showNotification: (message: string, type: NotificationType) => void;
  hideNotification: (id: number) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const nextId = useRef(1);

  const showNotification = (message: string, type: NotificationType) => {
    const id = nextId.current++;
    setNotifications(prev => [...prev, { id, message, type }]);
    
    // Auto-hide notification after 3 seconds
    setTimeout(() => {
      hideNotification(id);
    }, 3000);
  };

  const hideNotification = (id: number) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  };

  return (
    <NotificationContext.Provider value={{ notifications, showNotification, hideNotification }}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map(notification => (
          <div 
            key={notification.id}
            className={`p-4 rounded-md shadow-lg ${
              notification.type === 'success' ? 'bg-green-600' : 
              notification.type === 'error' ? 'bg-red-600' : 
              'bg-blue-600'
            } text-white max-w-md`}
          >
            {notification.message}
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

// Helper functions
export const toast = {
  success: (message: string) => {
    const { showNotification } = useNotification();
    showNotification(message, 'success');
  },
  error: (message: string) => {
    const { showNotification } = useNotification();
    showNotification(message, 'error');
  },
  info: (message: string) => {
    const { showNotification } = useNotification();
    showNotification(message, 'info');
  }
};
