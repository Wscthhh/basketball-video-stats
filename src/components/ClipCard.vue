<script setup lang="ts">
import { Download, Film, Play } from 'lucide-vue-next'
import { clipSource, formatSeconds, statusLabel } from '../presentation'
import type { Clip } from '../types'

const props = withDefaults(defineProps<{ clip: Clip; variant?: 'highlight' | 'library'; emptyEvidence?: string }>(), {
  variant: 'highlight',
  emptyEvidence: '已归属该球队',
})

defineEmits<{ open: [clip: Clip]; export: [clip: Clip] }>()
</script>

<template>
  <button v-if="props.variant === 'library'" class="clip-card" type="button" @click="$emit('open', clip)">
    <div class="clip-card-preview">
      <video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video>
      <div v-else class="professional-empty small"><Film :size="18" /></div>
    </div>
    <div class="clip-card-copy">
      <div><strong>{{ clip.name }}</strong><small>{{ formatSeconds(clip.duration ?? clip.durationSeconds) }}</small></div>
       <span class="clip-card-footer"><span>{{ statusLabel(clip.status) }}</span><button class="icon-button dark" type="button" title="导出片段" @click.stop="$emit('export', clip)"><Download :size="14" /></button></span>
    </div>
  </button>
  <article v-else class="team-highlight-card" role="button" tabindex="0" @click="$emit('open', clip)" @keydown.enter="$emit('open', clip)" @keydown.space.prevent="$emit('open', clip)">
    <span class="team-highlight-preview">
      <video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video>
      <span v-else class="preview-empty"><Film :size="18" /></span>
      <span class="play-overlay"><Play :size="18" fill="currentColor" /></span>
    </span>
    <span class="team-highlight-copy">
      <small>{{ statusLabel(clip.status) }} · {{ clipSource(clip) }}</small>
       <strong>{{ clip.name }}</strong>
       <small>{{ clip.teamEvidence || emptyEvidence }}</small>
       <button class="icon-button dark clip-export-button" type="button" title="导出片段" @click.stop="$emit('export', clip)"><Download :size="14" /></button>
    </span>
  </article>
</template>
