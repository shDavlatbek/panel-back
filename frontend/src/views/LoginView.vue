<template>
  <div class="login-container">
    <div class="card">
      <h1>Login</h1>
      
      <div v-if="authStore.error" class="alert alert-danger">
        {{ authStore.error }}
        <button class="close-btn" @click="authStore.clearError">×</button>
      </div>
      
      <div v-if="authStore.message" class="alert alert-success">
        {{ authStore.message }}
        <button class="close-btn" @click="authStore.clearMessage">×</button>
      </div>
      
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-control"
            required
            placeholder="Enter username"
          />
        </div>
        
        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-control"
            required
            placeholder="Enter password"
          />
        </div>
        
        <div class="form-group">
          <button class="btn btn-primary btn-block" :disabled="authStore.loading">
            <span v-if="authStore.loading" class="spinner"></span>
            <span v-else>Login</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');

// Check if already logged in
onMounted(() => {
  if (authStore.isLoggedIn) {
    router.push('/');
  }
});

const handleLogin = async () => {
  const response = await authStore.login(username.value, password.value);
  
  if (response.success) {
    router.push('/');
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  padding: 20px;
}

.card {
  width: 100%;
  max-width: 400px;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: white;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #555;
}

.form-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.btn {
  cursor: pointer;
  padding: 12px;
  border-radius: 4px;
  font-size: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  border: none;
}

.btn-primary {
  background-color: #4c6ef5;
  color: white;
}

.btn:disabled {
  background-color: #a5b4fc;
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style> 