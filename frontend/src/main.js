import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'

// Import axios interceptor to ensure it's loaded
import './services/axios-interceptor'

const app = createApp(App)

app.use(pinia)
app.use(router)

app.mount('#app')
