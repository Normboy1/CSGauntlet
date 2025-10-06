import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface AuthContextType {
  isAuthenticated: boolean;
  user: any | null;
  token: string | null;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, username: string, password: string, password2?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const navigate = useNavigate();

  const login = async (emailOrUsername: string, password: string) => {
    try {
      // Determine if input is email or username
      const isEmail = emailOrUsername.includes('@');
      const payload = isEmail 
        ? { email: emailOrUsername, password }
        : { username: emailOrUsername, password };
        
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const data = await response.json();
      const newToken = data.token;
      localStorage.setItem('token', newToken);
      setToken(newToken);

      // Get user info
      const userResponse = await fetch('/api/profile', {
        headers: {
          'Authorization': `Bearer ${newToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
        setIsAuthenticated(true);
        navigate('/');
      } else {
        throw new Error('Failed to get user info');
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (email: string, username: string, password: string, password2?: string) => {
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, username, password, password2: password2 || password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Registration failed');
      }

      // Automatically login after registration
      await login(email, password);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    navigate('/login');
  };

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      fetch('/api/profile', {
        headers: {
          'Authorization': `Bearer ${storedToken}`,
          'Content-Type': 'application/json',
        },
      })
      .then(response => {
        if (response.ok) {
          return response.json();
        } else {
          throw new Error('Invalid token');
        }
      })
      .then(userData => {
        setUser(userData);
        setIsAuthenticated(true);
        setToken(storedToken);
      })
      .catch(() => {
        logout();
      });
    }
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
