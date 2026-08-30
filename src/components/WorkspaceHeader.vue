<script setup lang="ts">
import { CloudUpload, RefreshCw } from 'lucide-vue-next'
import type { Match } from '../types'

defineProps<{
  match: Match
  clipCount: number
  homeClipCount: number
  awayClipCount: number
  unresolvedCount: number
  busy: boolean
  polling: boolean
}>()

defineEmits<{ reanalyze: []; importClips: [] }>()
</script>

<template>
  <section class="page-heading">
    <div>
      <div class="eyebrow"><span class="eyebrow-line"></span><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</div>
      <h1>{{ match.homeTeam.name }} <span>vs</span> {{ match.awayTeam.name }}</h1>
      <p>{{ match.playedAt || '未填写比赛日期' }}<b v-if="match.venue"> · </b>{{ match.venue }}</p>
    </div>
    <div class="heading-actions">
      <button class="button button-quiet" type="button" :disabled="busy || polling || !clipCount" @click="$emit('reanalyze')">
        <RefreshCw :size="16" /> {{ polling ? '重新分析中' : '重新分析全部' }}
      </button>
      <button class="button button-acid" type="button" @click="$emit('importClips')"><CloudUpload :size="17" /> 导入片段</button>
    </div>
  </section>
  <section class="metric-strip">
    <div class="metric-cell metric-primary"><div class="metric-label">全部片段</div><div class="metric-value">{{ clipCount }}</div><div class="metric-subline">当前比赛导入素材</div></div>
    <div class="metric-cell"><div class="metric-label">主队片段</div><div class="metric-value">{{ homeClipCount }}</div><div class="metric-subline">按球队归属</div></div>
    <div class="metric-cell"><div class="metric-label">客队片段</div><div class="metric-value">{{ awayClipCount }}</div><div class="metric-subline">按球队归属</div></div>
    <div class="metric-cell"><div class="metric-label">待归属</div><div class="metric-value">{{ unresolvedCount }}</div><div class="metric-subline">需要人工判断</div></div>
  </section>
</template>
