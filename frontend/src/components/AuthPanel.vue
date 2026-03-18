<template>
  <div>
    <div class="auth-error">{{ auth.error }}</div>
    <form v-if="mode === 'login'" class="auth-form active" @submit.prevent="submit">
      <div class="auth-form-inner">
        <div class="auth-field">
          <input v-model="email" type="email" placeholder=" " autocomplete="username" required />
          <label>Email</label>
        </div>
        <div class="auth-field">
          <input v-model="password" class="auth-password-input" :type="showLoginPw ? 'text' : 'password'" placeholder=" " autocomplete="current-password" required />
          <label>Password</label>
          <button class="auth-password-toggle" type="button" @click="showLoginPw = !showLoginPw" aria-label="Show password">
            <EyeOff v-if="showLoginPw" :size="18" />
            <Eye v-else :size="18" />
          </button>
        </div>
        <button class="auth-submit" :disabled="auth.loading">Initialize Session</button>
        <button class="auth-switch" type="button" @click="mode = 'register'">Create Account</button>
      </div>
    </form>
    <form v-else class="auth-form active" @submit.prevent="submit">
      <div class="auth-form-inner">
        <div class="auth-field">
          <input v-model="displayName" type="text" placeholder=" " autocomplete="username" required />
          <label>Username</label>
        </div>
        <div class="auth-field">
          <input v-model="email" type="email" placeholder=" " autocomplete="username" required />
          <label>Email</label>
        </div>
        <div class="auth-field">
          <input v-model="password" class="auth-password-input" :type="showRegPw ? 'text' : 'password'" placeholder=" " autocomplete="new-password" minlength="8" required />
          <label>Password</label>
          <button class="auth-password-toggle" type="button" @click="showRegPw = !showRegPw" aria-label="Show password">
            <EyeOff v-if="showRegPw" :size="18" />
            <Eye v-else :size="18" />
          </button>
          <p class="auth-field-hint">At least 8 characters</p>
        </div>
        <div class="auth-field">
          <input v-model="passwordConfirm" class="auth-password-input" :type="showRegPwConfirm ? 'text' : 'password'" placeholder=" " autocomplete="new-password" minlength="8" required />
          <label>Confirm Password</label>
          <button class="auth-password-toggle" type="button" @click="showRegPwConfirm = !showRegPwConfirm" aria-label="Show password">
            <EyeOff v-if="showRegPwConfirm" :size="18" />
            <Eye v-else :size="18" />
          </button>
        </div>
        <button class="auth-submit" :disabled="auth.loading">Create Account</button>
        <button class="auth-switch auth-switch-back" type="button" @click="mode = 'login'">
          <ArrowLeft :size="16" /> Return to Sign In
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Eye, EyeOff, ArrowLeft } from 'lucide-vue-next';
import { useAuthStore } from '../stores/auth';
import { useUiStore } from '../stores/ui';

const auth = useAuthStore();
const ui = useUiStore();
const mode = ref<'login' | 'register'>('login');
const displayName = ref('');
const email = ref('');
const password = ref('');
const passwordConfirm = ref('');
const showLoginPw = ref(false);
const showRegPw = ref(false);
const showRegPwConfirm = ref(false);

async function submit() {
  if (mode.value === 'login') {
    await auth.login({ email: email.value, password: password.value });
    ui.showToast(`Signed in as ${email.value}`);
    return;
  }
  if (password.value !== passwordConfirm.value) {
    auth.error = 'Passwords do not match';
    return;
  }
  if (password.value.length < 8) {
    auth.error = 'Password must be at least 8 characters';
    return;
  }
  await auth.register({
    display_name: displayName.value,
    email: email.value,
    password: password.value,
  });
  ui.showToast(`Account ready for ${email.value}`);
}
</script>
