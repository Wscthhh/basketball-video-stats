<script setup lang="ts">
import { CheckCheck, Film, Play } from 'lucide-vue-next'
import { statusLabel } from '../presentation'
import type { Clip } from '../types'

defineProps<{ clips: Clip[] }>()
defineEmits<{ openClip: [clip: Clip] }>()
</script>

<template>
  <section class="tool-panel review-panel">
    <div class="panel-header"><div><div class="panel-kicker">CLIP OWNERSHIP</div><h2>片段归属队列</h2></div><span class="highlight-count">{{ clips.length }} 个待判断</span></div>
    <div v-if="clips.length" class="event-list review-list">
      <article v-for="clip in clips" :key="clip.id" class="event-item clip-review-item" role="button" tabindex="0" @click="$emit('openClip', clip)" @keydown.enter="$emit('openClip', clip)" @keydown.space.prevent="$emit('openClip', clip)">
        <div class="clip-review-video">
          <video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video>
          <Film v-else :size="20" />
          <Play :size="18" fill="currentColor" />
        </div>
        <div class="event-main-copy"><div class="event-title-line"><strong>{{ clip.name }}</strong><span>{{ statusLabel(clip.status) }}</span></div><p>{{ clip.teamEvidence || '打开详情判断该片段所属球队' }}</p></div>
      </article>
    </div>
    <div v-else class="professional-empty"><CheckCheck :size="24" /><strong>暂无待归属片段</strong><span>分析完成后，无法判断球队的片段会出现在这里。</span></div>
  </section>
</template>

<style scoped>
.clip-review-item{cursor:pointer}.clip-review-item:hover{background:#18231e}.clip-review-video>svg:last-child{color:var(--acid)}
</style>
