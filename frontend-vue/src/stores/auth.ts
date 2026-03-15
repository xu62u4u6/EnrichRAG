import { defineStore } from 'pinia';
import { api } from '../utils/api';
import type { User } from '../types';

interface Credentials {
  email: string;
  password: string;
}

interface Registration extends Credentials {
  display_name: string;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    bootstrapped: false,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
  },
  actions: {
    async bootstrap() {
      this.loading = true;
      try {
        const response = await api.me();
        const payload = await api.parseJson<User | null>(response);
        this.user = payload;
      } catch {
        this.user = null;
      } finally {
        this.bootstrapped = true;
        this.loading = false;
      }
    },
    async login(payload: Credentials) {
      this.loading = true;
      this.error = '';
      try {
        const response = await api.login(payload);
        this.user = await api.parseJson<User>(response);
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Login failed';
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async register(payload: Registration) {
      this.loading = true;
      this.error = '';
      try {
        const response = await api.register(payload);
        this.user = await api.parseJson<User>(response);
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Registration failed';
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async logout() {
      this.loading = true;
      try {
        await api.logout();
      } finally {
        this.user = null;
        this.loading = false;
      }
    },
  },
});
