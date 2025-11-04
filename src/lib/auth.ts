/**
 * Authentication Service
 * 
 * Handles user authentication, session management,
 * and user-related API calls
 */

import { api } from './api';
import type { User, UserCreate, UserLogin, PasswordChange } from '../types/api';

export class AuthService {
  /**
   * Register a new user
   */
  async register(userData: UserCreate): Promise<User> {
    return api.post<User>('/auth/register', userData);
  }

  /**
   * Login with username and password
   * 
   * Sets session cookie on success
   */
  async login(credentials: UserLogin): Promise<User> {
    return api.post<User>('/auth/login', credentials);
  }

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    await api.post<void>('/auth/logout');
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser(): Promise<User> {
    return api.get<User>('/auth/me');
  }

  /**
   * Change current user's password
   */
  async changePassword(passwordData: PasswordChange): Promise<void> {
    await api.post<void>('/auth/change-password', passwordData);
  }

  /**
   * Check if user is authenticated
   * 
   * Returns true if can get current user, false otherwise
   */
  async isAuthenticated(): Promise<boolean> {
    try {
      await this.getCurrentUser();
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const authService = new AuthService();

