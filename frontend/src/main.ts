import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './styles.css';

createApp(App).use(createPinia()).use(router).mount('#app');

// Auto-detect horizontal overflow on table containers
function updateTableScrollHints() {
  document.querySelectorAll<HTMLElement>('.table-wrap, .table-shell').forEach((el) => {
    el.classList.toggle('has-scroll-right', el.scrollWidth > el.clientWidth + el.scrollLeft + 4);
  });
}

const tableObserver = new MutationObserver(updateTableScrollHints);
tableObserver.observe(document.body, { childList: true, subtree: true });
window.addEventListener('resize', updateTableScrollHints);
document.addEventListener('scroll', updateTableScrollHints, true);
