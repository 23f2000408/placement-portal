const { createApp } = Vue;

createApp({
  data() {
    return { message: 'Placement Portal SPA testing.' };
  },
  template: `\
  <div class="container mt-5">\
    <h1 class="mb-3">Placement Portal</h1>\
    <p>{{ message }}</p>\
    <p class="text-muted">.</p>\
  </div>`
}).mount('#app');
