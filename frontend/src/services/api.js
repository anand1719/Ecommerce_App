import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach token to every request if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses – clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export function login(email, password) {
  return api.post('/auth/login', { email, password });
}

export function register(email, password, fullName) {
  return api.post('/auth/register', { email, password, full_name: fullName });
}

export function getMe() {
  return api.get('/auth/me');
}

export function getKafkaStatus() {
  return api.get('/kafka/status');
}

export function createProduct(data) {
  return api.post('/products', data);
}

export function getProducts() {
  return api.get('/products');
}

export default api;