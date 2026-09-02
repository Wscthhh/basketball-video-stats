<script setup lang="ts">
import { CloudUpload, RefreshCw } from 'lucide-vue-next'
import type { Match } from '../types'
import TeamColorSwatch from './TeamColorSwatch.vue'

defineProps<{
  match: Match
  clipCount: number
  homeClipCount: number
  awayClipCount: number
  unresolvedCount: number
  busy: boolean
  polling: boolean
  analysisRun?: { progress?: number; completed?: number; total?: number; status?: string; error?: string }
  mobileUrl?: string
  desktopMode?: boolean
  updateStatus?: string
  updateVersion?: string
  updateProgress?: number
}>()

function copyMobileUrl(url?: string) {
  if (url) void navigator.clipboard?.writeText(url)
}

const emit = defineEmits<{ reanalyze: []; importClips: []; checkUpdates: []; downloadUpdate: []; installUpdate: [] }>()
</script>

<template>
  <section class="page-heading">
    <div>
      <div class="eyebrow"><span class="eyebrow-line"></span><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</div>
       <h1><span class="team-heading"><TeamColorSwatch :color="match.homeTeam.color" size="medium" />{{ match.homeTeam.name }}</span> <span>vs</span> <span class="team-heading"><TeamColorSwatch :color="match.awayTeam.color" size="medium" />{{ match.awayTeam.name }}</span></h1>
      <p>{{ match.playedAt || '未填写比赛日期' }}<b v-if="match.venue"> · </b>{{ match.venue }}</p>
    </div>
    <div class="heading-actions">
      <button class="button button-quiet" type="button" :disabled="busy || polling || !clipCount" @click="$emit('reanalyze')">
        <RefreshCw :size="16" /> {{ polling ? '重新分析中' : '重新分析全部' }}
      </button>
      <button class="button button-acid" type="button" @click="$emit('importClips')"><CloudUpload :size="17" /> 导入片段</button>
      <button v-if="desktopMode" class="button button-quiet update-button" type="button" :disabled="updateStatus === 'checking' || updateStatus === 'downloading'" @click="updateStatus === 'available' ? emit('downloadUpdate') : updateStatus === 'downloaded' ? emit('installUpdate') : emit('checkUpdates')"><RefreshCw :size="15" />{{ updateStatus === 'checking' ? '检查中' : updateStatus === 'available' ? `下载 v${updateVersion}` : updateStatus === 'downloading' ? `下载中 ${Math.round(updateProgress || 0)}%` : updateStatus === 'downloaded' ? '重启安装更新' : updateStatus === 'latest' ? '已是最新' : '检查更新' }}</button>
    </div>
  </section>
  <section v-if="polling && analysisRun" class="analysis-progress" aria-live="polite">
    <div class="analysis-progress-heading"><strong>正在分析片段</strong><span>{{ analysisRun.completed || 0 }} / {{ analysisRun.total || 0 }} 个片段 · {{ Math.round(analysisRun.progress || 0) }}%</span></div>
    <div class="analysis-progress-track"><span :style="{ width: `${Math.max(0, Math.min(100, analysisRun.progress || 0))}%` }"></span></div>
  </section>
  <section v-else-if="analysisRun?.status === 'failed'" class="analysis-progress analysis-progress-error" role="alert"><strong>分析失败</strong><span>{{ analysisRun.error || '请检查片段后重试。' }}</span></section>
  <section v-if="mobileUrl" class="mobile-upload-link"><div><strong>手机上传</strong><span>手机连接同一 Wi-Fi 后访问此地址上传视频</span></div><code>{{ mobileUrl }}</code><button class="button button-quiet" type="button" @click="copyMobileUrl(mobileUrl)">复制地址</button></section>
  <section class="metric-strip">
    <div class="metric-cell metric-primary"><div class="metric-label">全部片段</div><div class="metric-value">{{ clipCount }}</div><div class="metric-subline">当前比赛导入素材</div></div>
    <div class="metric-cell"><div class="metric-label">主队片段</div><div class="metric-value">{{ homeClipCount }}</div><div class="metric-subline">按球队归属</div></div>
    <div class="metric-cell"><div class="metric-label">客队片段</div><div class="metric-value">{{ awayClipCount }}</div><div class="metric-subline">按球队归属</div></div>
    <div class="metric-cell"><div class="metric-label">待归属</div><div class="metric-value">{{ unresolvedCount }}</div><div class="metric-subline">需要人工判断</div></div>
  </section>
</template>

<style scoped>
.team-heading{display:inline-flex;align-items:center;gap:9px}
.team-heading :deep(.team-color-swatch){vertical-align:middle}
.analysis-progress{display:grid;gap:9px;margin-top:18px;padding:14px 16px;background:#111a16;border:1px solid #304137;border-radius:5px;color:#aab8ac;font-size:11px}.analysis-progress-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.analysis-progress-heading strong{color:#e0ebe0}.analysis-progress-track{height:5px;overflow:hidden;background:#26342c;border-radius:999px}.analysis-progress-track span{display:block;height:100%;background:var(--acid);border-radius:inherit;transition:width .3s ease}.analysis-progress-error{display:flex;align-items:center;gap:10px;color:#ffd0c8;border-color:#773d35}.analysis-progress-error strong{color:#ff9e8f}
.mobile-upload-link{display:flex;align-items:center;gap:14px;margin-top:18px;padding:12px 15px;background:#121e18;border:1px solid #365441;border-radius:5px;color:#b8c8bb;font-size:11px}.mobile-upload-link>div{display:grid;gap:4px}.mobile-upload-link strong{color:#d7ff4d}.mobile-upload-link span{color:#829187;font-size:10px}.mobile-upload-link code{min-width:0;overflow:hidden;color:#dfe9df;text-overflow:ellipsis;white-space:nowrap}.mobile-upload-link .button{margin-left:auto;flex:0 0 auto;min-height:30px;font-size:10px}
@media(max-width:760px){.analysis-progress-heading{align-items:flex-start;flex-direction:column;gap:5px}.mobile-upload-link{align-items:stretch;flex-direction:column}.mobile-upload-link .button{width:100%;margin-left:0}}
</style>
