<script setup lang="ts">
import { Film } from 'lucide-vue-next'
import ClipCard from './ClipCard.vue'
import type { Clip, Team } from '../types'
import TeamColorSwatch from './TeamColorSwatch.vue'

defineProps<{
  homeTeam?: Team
  awayTeam?: Team
  homeClips: Clip[]
  awayClips: Clip[]
  unresolvedClips: Clip[]
}>()

defineEmits<{ openClip: [clip: Clip]; exportClip: [clip: Clip] }>()
</script>

<template>
  <section class="tool-panel team-overview-panel">
    <div class="overview-columns">
      <div v-for="group in [{ key: 'home', label: '主队', team: homeTeam, clips: homeClips }, { key: 'away', label: '客队', team: awayTeam, clips: awayClips }]" :key="group.key" class="overview-column">
        <div class="panel-header"><div><div class="panel-kicker">{{ group.label }}片段</div><h2 class="team-overview-title"><TeamColorSwatch :color="group.team?.color" />{{ group.team?.name || group.label }} · 片段集锦</h2></div><span class="highlight-count">{{ group.clips.length }} 个片段</span></div>
        <div v-if="group.clips.length" class="team-highlight-grid">
           <ClipCard v-for="clip in group.clips" :key="clip.id" :clip="clip" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" />
        </div>
        <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无{{ group.label }}片段</strong><span>归属后的真实视频会显示在这里。</span></div>
      </div>
    </div>
    <div class="overview-unresolved">
      <div class="panel-header"><div><div class="panel-kicker">UNRESOLVED CLIPS</div><h2>待归属片段</h2></div><span class="highlight-count">{{ unresolvedClips.length }} 个片段</span></div>
      <div v-if="unresolvedClips.length" class="team-highlight-grid">
         <ClipCard v-for="clip in unresolvedClips" :key="clip.id" :clip="clip" empty-evidence="请选择球队归属" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" />
      </div>
      <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无待归属片段</strong><span>所有导入片段都已完成球队归属。</span></div>
    </div>
  </section>
</template>

<style scoped>
.team-overview-title{display:flex;align-items:center;gap:8px}
</style>
