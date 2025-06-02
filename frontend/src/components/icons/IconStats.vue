<template>
  <svg 
    class="icon-stats" 
    viewBox="0 0 1024 1024" 
    version="1.1" 
    xmlns="http://www.w3.org/2000/svg"
    :width="size" 
    :height="size"
  >
    <path 
      d="M870.4 12.8H153.6A140.9024 140.9024 0 0 0 12.8 153.6v716.8A140.9024 140.9024 0 0 0 153.6 1011.2h504.32a38.4 38.4 0 0 0 0-76.8H153.6c-35.2768 0-64-28.7232-64-64V153.6c0-35.2768 28.7232-64 64-64h716.8c35.2768 0 64 28.7232 64 64v716.8c0 35.2768-28.7232 64-64 64h-11.4688a38.4 38.4 0 0 0 0 76.8H870.4A140.9024 140.9024 0 0 0 1011.2 870.4V153.6A140.9024 140.9024 0 0 0 870.4 12.8z" 
      :fill="color" 
    />
    <path 
      d="M256 371.2a38.4 38.4 0 0 0-38.4 38.4v409.6a38.4 38.4 0 0 0 76.8 0V409.6A38.4 38.4 0 0 0 256 371.2zM473.6 256v512a38.4 38.4 0 0 0 76.8 0V256a38.4 38.4 0 0 0-76.8 0zM768 576a38.4 38.4 0 0 0-38.4 38.4v204.8a38.4 38.4 0 0 0 76.8 0v-204.8a38.4 38.4 0 0 0-38.4-38.4zM257.024 217.6h-0.512c-21.1968 0-38.144 17.2032-38.144 38.4s17.4592 38.4 38.656 38.4a38.4 38.4 0 0 0 0-76.8z" 
      :fill="color" 
    />
  </svg>
</template>

<script setup lang="ts">
interface Props {
  size?: string | number
  color?: string
}

withDefaults(defineProps<Props>(), {
  size: '24',
  color: '#438CFF'
})
</script>

<style scoped>
.icon-stats {
  display: inline-block;
  vertical-align: middle;
  transition: all 0.3s ease;
}

.icon-stats:hover {
  transform: scale(1.1);
}
</style> 