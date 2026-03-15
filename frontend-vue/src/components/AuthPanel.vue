<template>
  <div class="auth-card">
    <div class="segmented">
      <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Sign In</button>
      <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Create Account</button>
    </div>
    <form class="auth-form" @submit.prevent="submit">
      <label v-if="mode === 'register'">
        <span>Display name</span>
        <input v-model="displayName" required />
      </label>
      <label>
        <span>Email</span>
        <input v-model="email" type="email" required />
      </label>
      <label>
        <span>Password</span>
        <input v-model="password" type="password" required />
      </label>
      <p v-if="auth.error" class="error-text">{{ auth.error }}</p>
      <button class="submit-button" :disabled="auth.loading">
        {{ mode === 'login' ? 'Initialize session' : 'Provision account' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const mode = ref<'login' | 'register'>('login');
const displayName = ref('');
const email = ref('');
const password = ref('');

async function submit() {
  if (mode.value === 'login') {
    await auth.login({ email: email.value, password: password.value });
    return;
  }
  await auth.register({
    display_name: displayName.value,
    email: email.value,
    password: password.value,
  });
}
</script>
