<template>
  <svg 
    class="icon-subject" 
    viewBox="0 0 1024 1024" 
    version="1.1" 
    xmlns="http://www.w3.org/2000/svg"
    :width="size" 
    :height="size"
  >
    <path 
      d="M329 923.5H171c-11.7 0-21.1-9.5-21.1-21.1V321.7c0-11.7 9.5-21.1 21.1-21.1h158c11.7 0 21.1 9.5 21.1 21.1v580.6c0 11.7-9.5 21.2-21.1 21.2z m-139.1-40h120.2V340.6H189.9v542.9z" 
      :fill="color" 
    />
    <path 
      d="M739.8 923.5c-16.4 0-31.3-9-39-23.4-0.1-0.1-0.1-0.2-0.2-0.3L483.6 421c-11.3-21.5-3.1-48.2 18.3-59.6l102.3-50.1c6.4-3.4 13.6-5.2 20.8-5.2 16.4 0 31.3 9 39 23.4 0.1 0.1 0.1 0.2 0.2 0.3l219 473.3c11.3 21.5 3.1 48.2-18.3 59.6l-104.3 55.6c-6.4 3.4-13.6 5.2-20.8 5.2z m-3.6-42.2c0.9 1.6 2.5 2.1 3.7 2.1 0.7 0 1.3-0.2 1.9-0.5l104.3-55.6c2-1.1 2.8-3.6 1.7-5.7-0.1-0.1-0.1-0.2-0.2-0.3l-219-473.2c-0.9-1.6-2.5-2.1-3.7-2.1-0.7 0-1.3 0.2-1.9 0.5l-102.3 50.1c-2 1.1-2.8 3.6-1.7 5.7 0.1 0.1 0.1 0.2 0.2 0.3l217 478.7z" 
      :fill="color" 
    />
    <path 
      d="M494.4 923.5H336.5c-11.7 0-21.1-9.5-21.1-21.1V128.1c0-11.7 9.5-21.1 21.1-21.1h157.9c11.7 0 21.1 9.5 21.1 21.1v774.2c0 11.7-9.4 21.2-21.1 21.2z m-139.1-40h120.2V147H355.3v736.5z" 
      :fill="color" 
    />
    <path 
      d="M985.4 938.5H52.8c-11 0-20-9-20-20s9-20 20-20h932.6c11 0 20 9 20 20s-9 20-20 20z" 
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
  color: '#6b7280'
})
</script>

<style scoped>
.icon-subject {
  display: inline-block;
  vertical-align: middle;
  transition: all 0.3s ease;
}

.icon-subject:hover {
  transform: scale(1.1);
}
</style> 