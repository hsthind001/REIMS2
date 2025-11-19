/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app
 */

import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { authService } from '../lib/auth';
import type { User, UserLogin, UserCreate } from '../types/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (credentials: UserLogin) => Promise<void>;
  register: (userData: UserCreate) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastCheckRef = useRef<number>(0);
  const isCheckingRef = useRef<boolean>(false);

  // Check authentication status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // Debounce: Prevent checks within 5 seconds of last check
    const now = Date.now();
    if (now - lastCheckRef.current < 5000 || isCheckingRef.current) {
      return;
    }

    try {
      isCheckingRef.current = true;
      lastCheckRef.current = now;
      setLoading(true);
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      setError(null);
    } catch (err: any) {
      setUser(null);
      // Don't set error on initial check if not authenticated
      if (err.status !== 401) {
        setError(err.message || 'Failed to check authentication');
      }
    } finally {
      setLoading(false);
      isCheckingRef.current = false;
    }
  };

  const login = async (credentials: UserLogin) => {
    try {
      setLoading(true);
      setError(null);
      const userData = await authService.login(credentials);
      setUser(userData);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData: UserCreate) => {
    try {
      setLoading(true);
      setError(null);
      const newUser = await authService.register(userData);
      // Auto-login after registration
      setUser(newUser);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await authService.logout();
      setUser(null);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Logout failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const refreshUser = async () => {
    await checkAuth();
  };

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    refreshUser,
    isAuthenticated: user !== null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

