import axios from 'axios';
import router from '@/router';

// Add a response interceptor
axios.interceptors.response.use(
  (response) => {
    // Any status code that lies within the range of 2xx
    return response;
  },
  (error) => {
    // Handle authentication errors
    if (error.response && error.response.status === 401) {
      // If not on login page already, redirect to login
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login');
      }
    }
    
    // Format error message
    let errorMessage = 'Something went wrong';
    
    if (error.response && error.response.data) {
      if (error.response.data.detail) {
        errorMessage = error.response.data.detail;
      } else if (typeof error.response.data === 'string') {
        errorMessage = error.response.data;
      }
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    // Return Promise rejection with formatted error
    return Promise.reject({
      status: error.response ? error.response.status : 500,
      message: errorMessage
    });
  }
); 