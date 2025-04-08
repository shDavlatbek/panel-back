<template>
  <div class="home-container">
    <div class="dashboard-card">
      <h1>Dashboard</h1>
      
      <div v-if="authStore.error" class="alert alert-danger">
        {{ authStore.error }}
        <button class="close-btn" @click="authStore.clearError">×</button>
      </div>
      
      <div v-if="authStore.message" class="alert alert-success">
        {{ authStore.message }}
        <button class="close-btn" @click="authStore.clearMessage">×</button>
      </div>
      
      <div v-if="authStore.isLoggedIn" class="user-info">
        <h2>Welcome, {{ authStore.user }}</h2>
        <div class="detail-section">
          <h3>User Information</h3>
          <p><strong>Username:</strong> {{ authStore.user }}</p>
        </div>
        
        <div class="action-section">
          <h3>AQI Map</h3>
          <p>View the Air Quality Index map with IDW interpolation.</p>
          <router-link to="/map" class="btn btn-success">Go to Map</router-link>
        </div>
        
        <div class="action-section">
          <h3>Authentication Test</h3>
          <p>Test your authentication status by making a request to a protected endpoint.</p>
          <button 
            @click="testAuth" 
            class="btn btn-primary"
            :disabled="testingAuth"
          >
            <span v-if="testingAuth" class="spinner"></span>
            <span v-else>Test Authentication</span>
          </button>
        </div>
        
        <div class="action-section">
          <h3>Logout</h3>
          <p>Click the button below to logout and clear your session.</p>
          <button 
            @click="handleLogout" 
            class="btn btn-danger"
            :disabled="authStore.loading"
          >
            <span v-if="authStore.loading" class="spinner"></span>
            <span v-else>Logout</span>
          </button>
        </div>
      </div>
      
      <div v-else class="not-authenticated">
        <h2>Not Authenticated</h2>
        <p>You need to log in first.</p>
        <router-link to="/login" class="btn btn-primary">Go to Login</router-link>
      </div>
    </div>
    
    <div class="api-response-card" v-if="apiResponse">
      <h3>Last API Response</h3>
      <pre>{{ JSON.stringify(apiResponse, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const testingAuth = ref(false);
const apiResponse = ref(null);

const testAuth = async () => {
  testingAuth.value = true;
  try {
    const response = await authStore.testAuth();
    apiResponse.value = response;
  } finally {
    testingAuth.value = false;
  }
};

const handleLogout = async () => {
  const response = await authStore.logout();
  apiResponse.value = response;
  
  if (response.success) {
    router.push('/login');
  }
};
</script>

<style scoped>
.home-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.dashboard-card, .api-response-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  margin-bottom: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

h2 {
  color: #4c6ef5;
  margin-bottom: 20px;
}

h3 {
  color: #555;
  margin-bottom: 10px;
}

.user-info {
  margin-top: 20px;
}

.detail-section, .action-section {
  margin-bottom: 30px;
  padding: 20px;
  border-radius: 8px;
  background-color: #f8f9fa;
}

.btn {
  cursor: pointer;
  padding: 12px;
  border-radius: 4px;
  font-size: 16px;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  min-width: 150px;
  border: none;
}

.btn-primary {
  background-color: #4c6ef5;
  color: white;
}

.btn-danger {
  background-color: #e03131;
  color: white;
}

.btn-success {
  background-color: #2b8a3e;
  color: white;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

.alert {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-danger {
  background-color: #ffe3e3;
  color: #e03131;
}

.alert-success {
  background-color: #d3f9d8;
  color: #2b8a3e;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

pre {
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.api-response-card {
  background-color: #fff;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
