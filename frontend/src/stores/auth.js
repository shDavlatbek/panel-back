import { defineStore } from 'pinia';
import AuthService from '@/services/auth.service';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: AuthService.getCurrentUser(),
    isLoggedIn: AuthService.isLoggedIn(),
    loading: false,
    error: null,
    message: null
  }),
  
  actions: {
    async login(username, password) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await AuthService.login(username, password);
        if (response.success) {
          this.user = AuthService.getCurrentUser();
          this.isLoggedIn = true;
          this.message = response.result?.message || 'Login successful';
        } else {
          this.error = response.detail || 'Login failed';
        }
        return response;
      } catch (error) {
        this.error = error.message || 'Login failed';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    async logout() {
      this.loading = true;
      
      try {
        const response = await AuthService.logout();
        this.user = null;
        this.isLoggedIn = false;
        this.message = response.result?.message || 'Logout successful';
        return response;
      } catch (error) {
        this.error = error.message || 'Logout failed';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    async testAuth() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await AuthService.testAuth();
        this.message = response.result?.message || 'Authentication successful';
        return response;
      } catch (error) {
        this.error = error.message || 'Authentication failed';
        return { success: false, detail: this.error };
      } finally {
        this.loading = false;
      }
    },
    
    clearMessage() {
      this.message = null;
    },
    
    clearError() {
      this.error = null;
    }
  }
}); 