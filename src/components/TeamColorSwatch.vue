<script setup lang="ts">
withDefaults(defineProps<{ color?: string | null; size?: 'small' | 'medium' }>(), { size: 'small' })
</script>

<template>
  <span class="team-color-swatch" :class="`team-color-swatch-${size}`" :style="{ '--team-color': color || '#68756d' }" :title="color || '未设置球队颜色'"></span>
</template>

<style scoped>
.team-color-swatch{display:inline-block;flex:0 0 auto;background:var(--team-color);border:1px solid rgba(234,244,231,.65);border-radius:50%;box-shadow:0 0 0 2px rgba(0,0,0,.28)}.team-color-swatch-small{width:9px;height:9px}.team-color-swatch-medium{width:13px;height:13px}.team-color-swatch[style*="#F4F5F0"],.team-color-swatch[style*="#f4f5f0"]{border-color:#58675e}
</style>
