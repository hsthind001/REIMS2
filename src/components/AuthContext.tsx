/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app
 */

import { createContext, useContext, useState, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { authService } from '../lib/auth';
import type { User, UserLogin, UserCreate } from '../types/api';
import { useAuthStore } from '../store/authStore';

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

  // Sync with store
  const setStoreUser = useAuthStore((state) => state.setUser);
  const setStoreLogout = useAuthStore((state) => state.logout);

  // Check authentication status on mount
  useEffect(() => {
    console.log('🔐 AuthContext: Starting authentication check...');
    checkAuth().catch((err) => {
      console.error('🔴 AuthContext: Error in checkAuth:', err);
      // Ensure loading state is cleared even if checkAuth fails
      setLoading(false);
      isCheckingRef.current = false;
    });
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
      
      // Add timeout to prevent hanging
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Authentication check timeout')), 10000)
      );
      
      const currentUser = await Promise.race([
        authService.getCurrentUser(),
        timeoutPromise
      ]) as User;
      
      console.log('✅ AuthContext: User authenticated:', currentUser?.username);
      setUser(currentUser);
      setStoreUser(currentUser); // Sync store
      setError(null);
    } catch (err: any) {
      console.log('ℹ️ AuthContext: Not authenticated or error:', err.status || err.message);
      setUser(null);
      setStoreLogout(); // Sync store
      // Don't set error on initial check if not authenticated, timeout, or network error
      // Network errors during initial check are expected if backend is starting up
      if (err.status !== 401 && 
          err.message !== 'Authentication check timeout' &&
          !(err.status === 0 || err.message?.includes('Network error'))) {
        console.warn('⚠️ AuthContext: Authentication error:', err.message);
        setError(err.message || 'Failed to check authentication');
      }
      // Always resolve loading state even on error
    } finally {
      console.log('✅ AuthContext: Authentication check complete, loading set to false');
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
      setStoreUser(userData); // Sync store
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
      setStoreUser(newUser); // Sync store
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
      setStoreLogout(); // Sync store
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
