<script setup lang="ts">
import { computed, ref } from 'vue'
import { Film, RefreshCw, Search, Upload } from 'lucide-vue-next'
import ClipCard from './ClipCard.vue'
import type { Clip } from '../types'

const props = defineProps<{ clips: Clip[]; busy: boolean; polling: boolean }>()
defineEmits<{ openClip: [clip: Clip]; exportClip: [clip: Clip]; reanalyze: []; importClips: [] }>()

const search = ref('')
const filter = ref('all')
const filteredClips = computed(() => props.clips.filter((clip) =>
  (!search.value || clip.name.toLowerCase().includes(search.value.toLowerCase()))
  && (filter.value === 'all' || clip.status === filter.value),
))
</script>

<template>
  <section class="tool-panel library-panel">
    <div class="panel-header">
      <div><div class="panel-kicker">素材管理</div><h2>片段库</h2></div>
      <div class="panel-actions">
        <button class="button button-quiet compact" type="button" :disabled="busy || polling || !clips.length" @click="$emit('reanalyze')"><RefreshCw :size="15" /> 重新分析全部</button>
        <button class="button button-acid" type="button" @click="$emit('importClips')"><Upload :size="16" /> 导入片段</button>
      </div>
    </div>
    <div class="library-toolbar">
      <label class="search-field"><Search :size="16" /><input v-model="search" placeholder="搜索文件名" /></label>
      <div class="filter-pills">
        <button v-for="item in [{ value: 'all', label: '全部' }, { value: 'queued', label: '排队中' }, { value: 'review', label: '待复核' }, { value: 'failed', label: '失败' }]" :key="item.value" :class="{ active: filter === item.value }" type="button" @click="filter = item.value">{{ item.label }}</button>
      </div>
    </div>
    <div v-if="filteredClips.length" class="clip-grid">
        <ClipCard v-for="clip in filteredClips" :key="clip.id" :clip="clip" variant="library" @open="$emit('openClip', $event)" @export="$emit('exportClip', $event)" />
    </div>
    <div v-else class="professional-empty"><Film :size="24" /><strong>暂无符合条件的片段</strong><span>导入本场比赛视频后开始分析。</span></div>
  </section>
</template>
