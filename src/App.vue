<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Activity, Check, CheckCheck, ChevronDown, ChevronRight, CircleAlert, CloudUpload, Cpu, Film, Play, Plus, RefreshCw, ScanLine, Search, Upload, X } from 'lucide-vue-next'
import { api } from './api'
import type { Clip, EventRecord, Health, Match, Run, ScoringEvent, ScoringResponse, TabKey, Team, Workspace } from './types'

const tab = ref<TabKey>('overview')
const matches = ref<Match[]>([])
const match = ref<Match | null>(null)
const workspace = ref<Workspace | null>(null)
const scoring = ref<ScoringResponse | null>(null)
const health = ref<Health | null>(null)
const loadError = ref('')
const actionError = ref('')
const activeClipId = ref('')
const showCreate = ref(false)
const showMatchMenu = ref(false)
const showImport = ref(false)
const showHighlightPlayer = ref(false)
const pendingFiles = ref<File[]>([])
const search = ref('')
const filter = ref('all')
const busy = ref(false)
const pollTimer = ref<number>()
const pollingRunId = ref('')
const activeHighlight = ref<{ event: ScoringEvent; clip?: Clip } | null>(null)
const highlightVideoRef = ref<HTMLVideoElement | null>(null)

const createDraft = reactive({ name: '', playedAt: '', venue: '', homeName: '', homeColor: '#F4F5F0', awayName: '', awayColor: '#171A18' })
const workspaceEvents = computed(() => workspace.value?.events ?? [])
const clips = computed(() => workspace.value?.clips ?? [])
const runs = computed(() => workspace.value?.runs ?? [])
const selectedClip = computed(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? clips.value[0])
const reviewEvents = computed(() => workspaceEvents.value.filter((event) => event.type === 'make' && event.status === 'pending'))
const currentRun = computed<Run | undefined>(() => runs.value[0])
const pendingCount = computed(() => reviewEvents.value.length)
const readyModels = computed(() => Object.entries(health.value?.analyzer?.models ?? {}).filter(([, model]) => model.ready).map(([name]) => name).join(' / '))
const filteredClips = computed(() => clips.value.filter((clip) => (!search.value || clip.name.toLowerCase().includes(search.value.toLowerCase())) && (filter.value === 'all' || clip.status === filter.value)))
const homeEvents = computed(() => (scoring.value?.home.events ?? []).filter((event) => event.status !== 'ignored'))
const awayEvents = computed(() => (scoring.value?.away.events ?? []).filter((event) => event.status !== 'ignored'))
const unassignedEvents = computed(() => (scoring.value?.unassigned ?? []).filter((event) => event.status !== 'ignored'))

function fail(error: unknown) { actionError.value = error instanceof Error ? error.message : '请求失败' }

async function loadWorkspace(matchId: string) {
  loadError.value = ''
  try {
    const [result, scoringResult] = await Promise.all([api.workspace(matchId), api.scoring(matchId)])
    workspace.value = result; match.value = result.match; scoring.value = scoringResult
    activeClipId.value = result.clips.some((clip) => clip.id === activeClipId.value) ? activeClipId.value : result.clips[0]?.id ?? ''
    const activeRun = result.runs.find((run) => run.status === 'running')
    if (activeRun && pollingRunId.value !== activeRun.id) startPolling(activeRun.id)
  } catch (error) { loadError.value = error instanceof Error ? error.message : '工作区加载失败'; workspace.value = null; scoring.value = null }
}

async function boot() {
  try { health.value = await api.health(); matches.value = await api.matches(); if (matches.value.length) await loadWorkspace((matches.value.find((item) => !item.isTest) ?? matches.value[0]).id) }
  catch (error) { health.value = null; loadError.value = error instanceof Error ? error.message : '本地分析服务不可用' }
}

async function createMatch() {
  if (!createDraft.name.trim() || !createDraft.homeName.trim() || !createDraft.awayName.trim()) { fail(new Error('请填写比赛名称和两队名称')); return }
  busy.value = true
  try { const created = await api.createMatch({ name: createDraft.name.trim(), playedAt: createDraft.playedAt || undefined, venue: createDraft.venue.trim() || undefined, homeTeam: { name: createDraft.homeName.trim(), color: createDraft.homeColor }, awayTeam: { name: createDraft.awayName.trim(), color: createDraft.awayColor } }); matches.value = [created, ...matches.value]; showCreate.value = false; await loadWorkspace(created.id) }
  catch (error) { fail(error) } finally { busy.value = false }
}
async function switchMatch(id: string) { showMatchMenu.value = false; if (id !== match.value?.id) await loadWorkspace(id) }
async function refresh() { if (match.value) await loadWorkspace(match.value.id) }
async function upload() {
  if (!match.value || !pendingFiles.value.length || busy.value) return
  busy.value = true
  try { const result = await api.upload(match.value.id, pendingFiles.value); pendingFiles.value = []; showImport.value = false; await refresh(); if (result.accepted.length) await analyze(result.accepted.map((clip) => clip.id)); if (result.skipped.length) actionError.value = `已跳过 ${result.skipped.length} 个重复或不支持的文件` }
  catch (error) { fail(error) } finally { busy.value = false }
}
async function analyze(clipIds = clips.value.filter((clip) => ['queued', 'failed', 'interrupted'].includes(clip.status ?? '')).map((clip) => clip.id)) {
  if (!match.value || !clipIds.length) return
  try { const run = await api.analyze(match.value.id, clipIds); if (workspace.value) workspace.value.runs = [run, ...workspace.value.runs.filter((item) => item.id !== run.id)]; startPolling(run.id) } catch (error) { fail(error) }
}
async function reanalyzeAll() { if (!match.value || !clips.value.length || busy.value) return; busy.value = true; try { await analyze(clips.value.map((clip) => clip.id)) } finally { busy.value = false } }
function stopPolling() { if (pollTimer.value) window.clearTimeout(pollTimer.value); pollTimer.value = undefined; pollingRunId.value = '' }
function startPolling(runId: string) { stopPolling(); pollingRunId.value = runId; const poll = async () => { try { const run = await api.task(runId); if (workspace.value) workspace.value.runs = [run, ...workspace.value.runs.filter((item) => item.id !== runId)]; if (['completed', 'failed', 'error', 'interrupted'].includes(run.status ?? '')) { stopPolling(); await refresh() } else pollTimer.value = window.setTimeout(() => void poll(), 1500) } catch (error) { stopPolling(); fail(error) } }; void poll() }

async function setTeam(event: EventRecord, teamId: string | null) { try { await api.updateEvent(event.id, { teamId, status: event.status }); await refresh() } catch (error) { fail(error) } }
async function eventAction(event: EventRecord, status: 'confirmed' | 'ignored') {
  try { await api.updateEvent(event.id, status === 'confirmed' ? { teamId: event.teamId ?? null, status: 'confirmed' } : { status: 'ignored' }); await refresh() } catch (error) { fail(error) }
}
async function confirmAll() { if (busy.value || !reviewEvents.value.length) return; busy.value = true; try { await Promise.all(reviewEvents.value.map((event) => api.updateEvent(event.id, { teamId: event.teamId ?? null, status: 'confirmed' }))); await refresh() } catch (error) { fail(error) } finally { busy.value = false } }

function teamFor(event: EventRecord): Team | undefined { return workspace.value?.teams.find((team) => team.id === event.teamId) }
function teamName(team?: Team) { return team?.name || '未判断' }
function teamLabel(side: 'home' | 'away') { return teamBySide(side)?.name || (side === 'home' ? '主队' : '客队') }
function teamBySide(side: 'home' | 'away') { return workspace.value?.teams.find((team) => team.side === side) ?? (side === 'home' ? match.value?.homeTeam : match.value?.awayTeam) }
function eventSource(event: EventRecord) { return event.teamSource === 'manual' ? '人工确认' : event.teamSource === 'ai' ? 'AI 归属' : '待判断' }
function formatSeconds(value?: number | null) { return value == null ? '--:--' : `${Math.floor(value / 60).toString().padStart(2, '0')}:${Math.floor(value % 60).toString().padStart(2, '0')}` }
function statusLabel(status?: string) { return ({ queued: '排队中', processing: '分析中', review: '待复核', ready: '已完成', failed: '失败', interrupted: '已中断', running: '分析中', completed: '已完成' } as Record<string, string>)[status ?? ''] ?? '暂无任务' }
function openHighlight(event: ScoringEvent) { const clip = clips.value.find((item) => item.id === event.clipId); activeHighlight.value = { event, clip }; showHighlightPlayer.value = true; void nextTick(() => { const video = highlightVideoRef.value; const seek = event.highlightStart ?? event.seconds ?? 0; if (video) { if (video.readyState >= 1) { video.currentTime = seek; void video.play().catch(() => undefined) } else video.addEventListener('loadedmetadata', () => { video.currentTime = seek; void video.play().catch(() => undefined) }, { once: true }) } }) }
function closeHighlight() { highlightVideoRef.value?.pause(); showHighlightPlayer.value = false; activeHighlight.value = null }
function selectClip(clip: Clip) { activeClipId.value = clip.id; tab.value = 'review' }
function navCount(key: TabKey) { return key === 'review' ? pendingCount.value : key === 'clips' ? clips.value.length : '' }
onMounted(boot); onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup"><div class="brand-mark"><ScanLine :size="20" /></div><div><strong>COURTTRACE</strong><span>LOCAL SCOUTING DESK</span></div></div>
      <div class="sidebar-section-label">当前比赛</div>
      <button v-if="match" class="match-switcher" type="button" @click="showMatchMenu = !showMatchMenu"><span class="match-badge">◎</span><span class="match-copy"><strong><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</strong><small>{{ match.venue || '未填写场地' }}</small></span><ChevronDown :size="16" /></button>
      <div v-if="showMatchMenu" class="match-menu"><button v-for="item in matches" :key="item.id" type="button" :class="{ active: item.id === match?.id }" @click="switchMatch(item.id)">{{ item.name }}</button></div>
      <button class="sidebar-create-button" type="button" @click="showCreate = true"><Plus :size="15" /> 创建比赛</button>
      <nav class="primary-nav"><button v-for="item in [{ key: 'overview', label: '比赛总览', icon: Activity }, { key: 'review', label: '复核队列', icon: CheckCheck }, { key: 'clips', label: '片段库', icon: Film }].filter((item) => item.key !== 'players')" :key="item.key" class="nav-item" :class="{ active: tab === item.key }" type="button" @click="tab = item.key as TabKey"><component :is="item.icon" :size="18" /><span>{{ item.label }}</span><em>{{ navCount(item.key as TabKey) }}</em></button></nav>
      <div class="sidebar-spacer"></div><div class="engine-card"><div class="engine-card-top"><span class="live-dot"></span><span>本地推理引擎</span><Cpu :size="15" /></div><strong>{{ health?.analyzer?.mode || '未连接' }}</strong><small>{{ health?.analyzer?.ready ? '模型已就绪' : '模型未就绪' }}<template v-if="readyModels"> · {{ readyModels }}</template></small></div>
    </aside>
    <main class="main-shell">
      <header class="topbar"><div class="breadcrumb">比赛工作台 <ChevronRight :size="14" /> <strong>{{ tab === 'overview' ? '总览' : tab === 'review' ? '复核' : '片段' }}</strong></div><div class="connection-state"><span :class="{ offline: !health }"></span>{{ health ? 'LOCAL ONLINE' : 'LOCAL OFFLINE' }}</div></header>
      <div class="page-content">
        <div v-if="loadError" class="error-banner"><CircleAlert :size="17" />{{ loadError }}<button class="icon-button" type="button" title="重试" @click="boot"><RefreshCw :size="16" /></button></div><div v-if="actionError" class="error-banner"><CircleAlert :size="17" />{{ actionError }}<button class="icon-button" type="button" title="关闭" @click="actionError = ''"><X :size="16" /></button></div>
        <template v-if="match && workspace">
          <section class="page-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</div><h1>{{ match.homeTeam.name }} <span>vs</span> {{ match.awayTeam.name }}</h1><p>{{ match.playedAt || '未填写比赛日期' }}<b v-if="match.venue"> · </b>{{ match.venue }}</p></div><div class="heading-actions"><button class="button button-quiet" type="button" :disabled="busy || Boolean(pollingRunId) || !clips.length" @click="reanalyzeAll"><RefreshCw :size="16" /> {{ pollingRunId ? '重新分析中' : '重新分析全部' }}</button><button class="button button-acid" type="button" @click="showImport = true"><CloudUpload :size="17" /> 导入片段</button></div></section>
          <section class="metric-strip"><div class="metric-cell metric-primary"><div class="metric-label">已接收片段</div><div class="metric-value">{{ clips.length }}</div><div class="metric-subline">当前比赛素材</div></div><div class="metric-cell"><div class="metric-label">待复核进球</div><div class="metric-value">{{ pendingCount }}</div><div class="metric-subline">只展示疑似命中</div></div><div class="metric-cell"><div class="metric-label">已确认进球</div><div class="metric-value">{{ workspaceEvents.filter((event) => event.type === 'make' && event.status === 'confirmed').length }}</div><div class="metric-subline">主队与客队合计</div></div><div class="metric-cell"><div class="metric-label">分析任务</div><div class="metric-value run-value">{{ statusLabel(currentRun?.status) }}</div><div class="metric-subline">{{ currentRun ? `${currentRun.completed ?? 0} / ${currentRun.total ?? 0} · ${currentRun.progress ?? 0}%` : '尚未提交分析' }}</div></div></section>

          <section v-if="tab === 'overview'" class="tool-panel team-overview-panel"><div class="overview-columns"><div v-for="group in [{ key: 'home', label: '主队', events: homeEvents }, { key: 'away', label: '客队', events: awayEvents }]" :key="group.key" class="overview-column"><div class="panel-header"><div><div class="panel-kicker">{{ group.label }}</div><h2>{{ teamBySide(group.key as 'home' | 'away')?.name || group.label }} · 进球集锦</h2></div><span class="highlight-count">{{ group.events.length }} 个片段</span></div><div v-if="group.events.length" class="team-highlight-grid"><button v-for="event in group.events" :key="event.id" class="team-highlight-card" type="button" @click="openHighlight(event)"><span class="team-highlight-preview"><video v-if="event.previewUrl || clips.find((clip) => clip.id === event.clipId)?.previewUrl" :src="event.previewUrl || clips.find((clip) => clip.id === event.clipId)?.previewUrl" muted preload="metadata"></video><span class="play-overlay"><Play :size="18" fill="currentColor" /></span><small>{{ formatSeconds(event.seconds) }}</small></span><span class="team-highlight-copy"><small>{{ event.status === 'confirmed' ? '已确认' : 'AI 待确认' }} · {{ eventSource(event) }}</small><strong>进球事件</strong><small>{{ clips.find((clip) => clip.id === event.clipId)?.name || '源片段' }}</small></span><ChevronRight :size="16" /></button></div><div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无进球集锦</strong><span>真实进球数据会显示在这里。</span></div></div></div><div v-if="unassignedEvents.length" class="unassigned-note">另有 {{ unassignedEvents.length }} 个进球事件尚未判断球队</div></section>

       <section v-if="tab === 'review'" class="tool-panel review-panel"><div class="panel-header"><div><div class="panel-kicker">MAKE EVENTS</div><h2>进球复核队列</h2></div><button class="button button-acid compact" type="button" :disabled="busy || !reviewEvents.length" @click="confirmAll"><CheckCheck :size="15" /> 全部确认</button></div><div v-if="reviewEvents.length" class="event-list review-list"><article v-for="event in reviewEvents" :key="event.id" class="event-item"><div class="event-item-top"><div class="event-type-mark"><Activity :size="15" /></div><div class="event-main-copy"><div class="event-title-line"><strong>疑似进球</strong><span>{{ formatSeconds(event.seconds) }}</span></div><p>{{ event.description || 'AI 检测到疑似进球，请判断球队' }}</p></div><span class="confidence-label">AI {{ event.confidence != null ? `${Math.round(event.confidence * 100)}%` : '待确认' }}</span></div><div class="event-item-bottom"><div class="team-choice"><span>球队</span><button v-for="side in ['home', 'away']" :key="side" type="button" :class="{ selected: event.teamId === teamBySide(side as 'home' | 'away')?.id }" @click="setTeam(event, teamBySide(side as 'home' | 'away')?.id ?? null)">{{ teamLabel(side as 'home' | 'away') }}</button><button type="button" :class="{ selected: !event.teamId }" @click="setTeam(event, null)">未判断</button></div><div class="event-actions"><button class="mini-action confirm" type="button" title="确认进球" @click="eventAction(event, 'confirmed')"><Check :size="14" /></button><button class="mini-action ignore" type="button" title="忽略" @click="eventAction(event, 'ignored')"><X :size="14" /></button></div></div></article></div><div v-else class="professional-empty"><CheckCheck :size="24" /><strong>暂无待复核进球</strong><span>分析完成后，疑似进球会出现在这里。</span></div></section>

          <section v-if="tab === 'clips'" class="tool-panel library-panel"><div class="panel-header"><div><div class="panel-kicker">素材管理</div><h2>片段库</h2></div><div class="panel-actions"><button class="button button-quiet compact" type="button" :disabled="busy || Boolean(pollingRunId) || !clips.length" @click="reanalyzeAll"><RefreshCw :size="15" /> 重新分析全部</button><button class="button button-acid" type="button" @click="showImport = true"><Upload :size="16" /> 导入片段</button></div></div><div class="library-toolbar"><label class="search-field"><Search :size="16" /><input v-model="search" placeholder="搜索文件名" /></label><div class="filter-pills"><button v-for="item in [{ value: 'all', label: '全部' }, { value: 'queued', label: '排队中' }, { value: 'review', label: '待复核' }, { value: 'failed', label: '失败' }]" :key="item.value" :class="{ active: filter === item.value }" type="button" @click="filter = item.value">{{ item.label }}</button></div></div><div v-if="filteredClips.length" class="clip-grid"><button v-for="clip in filteredClips" :key="clip.id" class="clip-card" type="button" @click="selectClip(clip)"><div class="clip-card-preview"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><div v-else class="professional-empty small"><Film :size="18" /></div></div><div class="clip-card-copy"><div><strong>{{ clip.name }}</strong><small>{{ formatSeconds(clip.duration) }}</small></div><span>{{ statusLabel(clip.status) }}</span></div></button></div><div v-else class="professional-empty"><Film :size="24" /><strong>暂无符合条件的片段</strong><span>导入本场比赛视频后开始分析。</span></div></section>
        </template><div v-else-if="!loadError" class="professional-empty page-empty"><Activity :size="28" /><strong>尚未创建比赛</strong><span>先录入两队信息，再导入真实视频。</span></div>
      </div>
    </main>

    <div v-if="showCreate" class="modal-layer"><section class="modal"><div class="modal-header"><div><span class="panel-kicker"><Plus :size="13" /> NEW MATCH</span><h2>创建比赛</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showCreate = false"><X :size="18" /></button></div><div class="form-grid"><label><span>比赛名称 *</span><input v-model="createDraft.name" /></label><label><span>比赛日期</span><input v-model="createDraft.playedAt" type="datetime-local" /></label><label><span>比赛场地</span><input v-model="createDraft.venue" /></label><span></span><label><span>主队名称 *</span><input v-model="createDraft.homeName" /></label><label><span>主队颜色</span><input v-model="createDraft.homeColor" type="color" /></label><label><span>客队名称 *</span><input v-model="createDraft.awayName" /></label><label><span>客队颜色</span><input v-model="createDraft.awayColor" type="color" /></label></div><div class="modal-footer"><span>一期只记录主队/客队进球</span><button class="button button-acid" type="button" :disabled="busy" @click="createMatch"><Check :size="16" /> 创建并进入</button></div></section></div>
    <div v-if="showImport" class="modal-layer" @click.self="showImport = false"><section class="modal"><div class="modal-header"><div><span class="panel-kicker"><Upload :size="13" /> LOCAL INGEST</span><h2>导入比赛片段</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showImport = false"><X :size="18" /></button></div><label class="file-picker"><CloudUpload :size="23" /><strong>选择本地视频</strong><span>支持 MP4、MOV、M4V、WebM，可多选</span><input type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" multiple @change="pendingFiles = Array.from(($event.target as HTMLInputElement).files || [])" /></label><div class="modal-footer"><span>{{ pendingFiles.length }} 个文件待上传</span><button class="button button-acid" type="button" :disabled="busy || !pendingFiles.length" @click="upload"><CloudUpload :size="16" /> 上传并自动分析</button></div></section></div>
    <div v-if="showHighlightPlayer && activeHighlight" class="modal-layer highlight-player-layer" @click.self="closeHighlight"><section class="modal highlight-player-modal"><div class="modal-header"><div><span class="panel-kicker">SCORING HIGHLIGHT</span><h2>进球事件 · {{ activeHighlight.event.status === 'confirmed' ? '已确认' : 'AI 待确认' }}</h2><p>{{ teamName(teamFor(activeHighlight.event)) }} · {{ eventSource(activeHighlight.event) }} · {{ activeHighlight.clip?.name || '源片段' }}</p></div><button class="icon-button dark" type="button" title="关闭" @click="closeHighlight"><X :size="18" /></button></div><div class="highlight-player-video"><video ref="highlightVideoRef" controls playsinline :src="activeHighlight.event.previewUrl || activeHighlight.clip?.previewUrl"></video></div><div class="highlight-player-meta"><span>事件时间 {{ formatSeconds(activeHighlight.event.seconds) }}</span><span>集锦范围 {{ formatSeconds(activeHighlight.event.highlightStart ?? activeHighlight.event.seconds) }} - {{ formatSeconds(activeHighlight.event.highlightEnd) }}</span></div></section></div>
  </div>
</template>
