import { createRouter, createWebHistory } from 'vue-router';
import { UI_BASE } from '../utils/api';
import HomeView from '../views/HomeView.vue';

export const router = createRouter({
  history: createWebHistory(UI_BASE),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
  ],
});
