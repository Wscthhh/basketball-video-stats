<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Film } from 'lucide-vue-next'
import ClipCard from './ClipCard.vue'
import type { Clip, Team } from '../types'
import TeamColorSwatch from './TeamColorSwatch.vue'

const props = defineProps<{
  homeTeam?: Team
  awayTeam?: Team
  homeClips: Clip[]
  awayClips: Clip[]
  unresolvedClips: Clip[]
  pendingHomeCount: number
  pendingAwayCount: number
}>()

defineEmits<{ openClip: [clip: Clip]; exportClip: [clip: Clip] }>()

const pageSize = 6
const unresolvedPageSize = 12
const homePage = ref(1)
const awayPage = ref(1)
const unresolvedPage = ref(1)
const homePageCount = computed(() => Math.max(1, Math.ceil(props.homeClips.length / pageSize)))
const awayPageCount = computed(() => Math.max(1, Math.ceil(props.awayClips.length / pageSize)))
const unresolvedPageCount = computed(() => Math.max(1, Math.ceil(props.unresolvedClips.length / unresolvedPageSize)))
const pendingFirst = (clips: Clip[]) => [...clips].sort((a, b) => Number(!isConfirmed(b)) - Number(!isConfirmed(a)))
const isConfirmed = (clip: Clip) => clip.teamSource === 'manual' || clip.teamConfirmed === true
const orderedHomeClips = computed(() => pendingFirst(props.homeClips))
const orderedAwayClips = computed(() => pendingFirst(props.awayClips))
const orderedUnresolvedClips = computed(() => pendingFirst(props.unresolvedClips))
const visibleHomeClips = computed(() => orderedHomeClips.value.slice((homePage.value - 1) * pageSize, homePage.value * pageSize))
const visibleAwayClips = computed(() => orderedAwayClips.value.slice((awayPage.value - 1) * pageSize, awayPage.value * pageSize))
const visibleUnresolvedClips = computed(() => orderedUnresolvedClips.value.slice((unresolvedPage.value - 1) * unresolvedPageSize, unresolvedPage.value * unresolvedPageSize))

function changePage(page: 'home' | 'away' | 'unresolved', direction: -1 | 1) {
  if (page === 'home') homePage.value = Math.min(homePageCount.value, Math.max(1, homePage.value + direction))
  if (page === 'away') awayPage.value = Math.min(awayPageCount.value, Math.max(1, awayPage.value + direction))
  if (page === 'unresolved') unresolvedPage.value = Math.min(unresolvedPageCount.value, Math.max(1, unresolvedPage.value + direction))
}

watch(homePageCount, (count) => { homePage.value = Math.min(homePage.value, count) })
watch(awayPageCount, (count) => { awayPage.value = Math.min(awayPage.value, count) })
watch(unresolvedPageCount, (count) => { unresolvedPage.value = Math.min(unresolvedPage.value, count) })
</script>

<template>
  <section class="tool-panel team-overview-panel">
    <div class="overview-columns">
      <div class="overview-column">
        <div class="panel-header"><div><div class="panel-kicker">主队片段</div><h2 class="team-overview-title"><TeamColorSwatch :color="homeTeam?.color" />{{ homeTeam?.name || '主队' }} · 片段集锦 <small v-if="pendingHomeCount">待确认 {{ pendingHomeCount }} 个</small></h2></div><span class="highlight-count">{{ homeClips.length }} 个片段</span></div>
        <div v-if="homeClips.length" class="team-highlight-grid"><ClipCard v-for="clip in visibleHomeClips" :key="clip.id" :clip="clip" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" /></div>
        <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无主队片段</strong><span>归属后的真实视频会显示在这里。</span></div>
        <div v-if="homeClips.length > pageSize" class="overview-pagination"><button class="icon-button dark" type="button" title="上一页" :disabled="homePage === 1" @click="changePage('home', -1)"><ChevronLeft :size="15" /></button><span>{{ homePage }} / {{ homePageCount }}</span><button class="icon-button dark" type="button" title="下一页" :disabled="homePage === homePageCount" @click="changePage('home', 1)"><ChevronRight :size="15" /></button></div>
      </div>
      <div class="overview-column">
        <div class="panel-header"><div><div class="panel-kicker">客队片段</div><h2 class="team-overview-title"><TeamColorSwatch :color="awayTeam?.color" />{{ awayTeam?.name || '客队' }} · 片段集锦 <small v-if="pendingAwayCount">待确认 {{ pendingAwayCount }} 个</small></h2></div><span class="highlight-count">{{ awayClips.length }} 个片段</span></div>
        <div v-if="awayClips.length" class="team-highlight-grid"><ClipCard v-for="clip in visibleAwayClips" :key="clip.id" :clip="clip" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" /></div>
        <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无客队片段</strong><span>归属后的真实视频会显示在这里。</span></div>
        <div v-if="awayClips.length > pageSize" class="overview-pagination"><button class="icon-button dark" type="button" title="上一页" :disabled="awayPage === 1" @click="changePage('away', -1)"><ChevronLeft :size="15" /></button><span>{{ awayPage }} / {{ awayPageCount }}</span><button class="icon-button dark" type="button" title="下一页" :disabled="awayPage === awayPageCount" @click="changePage('away', 1)"><ChevronRight :size="15" /></button></div>
      </div>
    </div>
    <div class="overview-unresolved">
      <div class="panel-header"><div><div class="panel-kicker">UNRESOLVED CLIPS</div><h2>待归属片段 <small v-if="unresolvedClips.length">待确认 {{ unresolvedClips.length }} 个</small></h2></div><span class="highlight-count">{{ unresolvedClips.length }} 个片段</span></div>
      <div v-if="unresolvedClips.length" class="team-highlight-grid"><ClipCard v-for="clip in visibleUnresolvedClips" :key="clip.id" :clip="clip" empty-evidence="请选择球队归属" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" /></div>
      <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无待归属片段</strong><span>所有导入片段都已完成球队归属。</span></div>
      <div v-if="unresolvedClips.length > unresolvedPageSize" class="overview-pagination"><button class="icon-button dark" type="button" title="上一页" :disabled="unresolvedPage === 1" @click="changePage('unresolved', -1)"><ChevronLeft :size="15" /></button><span>{{ unresolvedPage }} / {{ unresolvedPageCount }}</span><button class="icon-button dark" type="button" title="下一页" :disabled="unresolvedPage === unresolvedPageCount" @click="changePage('unresolved', 1)"><ChevronRight :size="15" /></button></div>
    </div>
  </section>
</template>

<style scoped>
.team-overview-title{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.team-overview-title small,.overview-unresolved h2 small{color:#ffc766;font-size:10px;font-weight:500;white-space:nowrap}.overview-pagination{display:flex;align-items:center;justify-content:center;gap:10px;padding:0 16px 16px;color:#94a299;font-size:11px}.overview-pagination .icon-button:disabled{cursor:not-allowed;opacity:.35}
</style>
