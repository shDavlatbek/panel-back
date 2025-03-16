import axios from 'axios';

// API URL configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/auth/';

// Configure axios to include credentials (cookies)
axios.defaults.withCredentials = true;

class AuthService {
  /**
   * Login user and store user info
   * @param {string} username - Username
   * @param {string} password - Password
   * @returns {Promise} - Response promise
   */
  login(username, password) {
    return axios
      .post(API_URL + 'login/', {
        username,
        password
      })
      .then(response => {
        if (response.data.success) {
          localStorage.setItem('user', JSON.stringify(response.data.result.user));
        }
        return response.data;
      });
  }

  /**
   * Logout user and remove user info
   * @returns {Promise} - Response promise
   */
  logout() {
    localStorage.removeItem('user');
    return axios.post(API_URL + 'logout/').then(response => {
      return response.data;
    });
  }

  /**
   * Test authentication
   * @returns {Promise} - Response promise
   */
  testAuth() {
    return axios.get(API_URL + 'test/').then(response => {
      return response.data;
    });
  }

  /**
   * Get currently logged in user
   * @returns {Object|null} - User object or null
   */
  getCurrentUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  /**
   * Check if user is logged in
   * @returns {boolean} - True if logged in
   */
  isLoggedIn() {
    return !!this.getCurrentUser();
  }
}

export default new AuthService(); 