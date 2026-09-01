<script setup lang="ts">
import { Download, Film, Play } from 'lucide-vue-next'
import { clipSource, clipTeamStatus, clipTeamStatusClass, formatSeconds, statusLabel } from '../presentation'
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
       <span class="clip-card-footer"><span class="clip-card-tags"><small class="status-tag analysis-tag">{{ statusLabel(clip.status) }}</small><small class="status-tag" :class="`status-tag-${clipTeamStatusClass(clip)}`">{{ clipTeamStatus(clip) }}</small></span><button class="icon-button dark" type="button" title="导出片段" @click.stop="$emit('export', clip)"><Download :size="14" /></button></span>
    </div>
  </button>
  <article v-else class="team-highlight-card" role="button" tabindex="0" @click="$emit('open', clip)" @keydown.enter="$emit('open', clip)" @keydown.space.prevent="$emit('open', clip)">
    <span class="team-highlight-preview">
      <video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video>
      <span v-else class="preview-empty"><Film :size="18" /></span>
      <span class="play-overlay"><Play :size="18" fill="currentColor" /></span>
    </span>
    <span class="team-highlight-copy">
       <span class="clip-card-tags"><small class="status-tag" :class="`status-tag-${clipTeamStatusClass(clip)}`">{{ clipTeamStatus(clip) }}</small><small class="source-tag">{{ clipSource(clip) }}</small></span>
       <strong>{{ clip.name }}</strong>
       <small>{{ clip.teamEvidence || emptyEvidence }}</small>
       <button class="icon-button dark clip-export-button" type="button" title="导出片段" @click.stop="$emit('export', clip)"><Download :size="14" /></button>
    </span>
  </article>
</template>

<style scoped>
.clip-card-tags{display:inline-flex;align-items:center;flex-wrap:wrap;gap:5px}.status-tag,.source-tag{display:inline-flex;align-items:center;min-height:18px;padding:0 6px;border:1px solid #435248;border-radius:3px;font-size:9px;line-height:1;white-space:nowrap}.status-tag-confirmed{color:#c9f58a;background:#1d321c;border-color:#78b449}.status-tag-ai{color:#ffd18d;background:#332719;border-color:#a66d2b}.status-tag-pending{color:#ffb1a3;background:#321b18;border-color:#87473e}.analysis-tag{color:#aab7ac;background:#17211c}.source-tag{color:#9cab9d;border-color:transparent;padding:0}
</style>
