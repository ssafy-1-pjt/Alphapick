<template>
  <div class="min-h-screen bg-fog text-ink">
    <AppHeader />
    <main class="pt-16">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import AppHeader from "./components/layout/AppHeader.vue";
</script>
