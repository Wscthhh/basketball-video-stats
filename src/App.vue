<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  Activity,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CloudUpload,
  Cpu,
  Film,
  Play,
  Plus,
  RefreshCw,
  ScanLine,
  Search,
  Settings2,
  Upload,
  UsersRound,
  X,
} from 'lucide-vue-next'
import { api } from './api'
import type { Clip, EventRecord, Health, Match, Player, Run, ShotType, TabKey, Workspace } from './types'

const jerseyColors = [
  { name: '白色', value: '#F4F5F0' },
  { name: '黑色', value: '#171A18' },
  { name: '红色', value: '#D73A3A' },
  { name: '蓝色', value: '#3267D6' },
  { name: '深蓝', value: '#17345C' },
  { name: '绿色', value: '#249464' },
  { name: '黄色', value: '#F2C94C' },
  { name: '橙色', value: '#F28C28' },
  { name: '紫色', value: '#7548B8' },
  { name: '灰色', value: '#8A9490' },
]

const tab = ref<TabKey>('overview')
const matches = ref<Match[]>([])
const match = ref<Match | null>(null)
const workspace = ref<Workspace | null>(null)
const health = ref<Health | null>(null)
const loadError = ref('')
const actionError = ref('')
const activeClipId = ref('')
const selectedPlayerId = ref('')
const selectedTeamId = ref('')
const highlights = ref<EventRecord[]>([])
const videoRef = ref<HTMLVideoElement | null>(null)
const highlightVideoRef = ref<HTMLVideoElement | null>(null)
const activeHighlight = ref<{ event: EventRecord; clip: Clip } | null>(null)
const showCreate = ref(false)
const showMatchMenu = ref(false)
const showImport = ref(false)
const showPlayerEditor = ref(false)
const showPlayerDetail = ref(false)
const showHighlightPlayer = ref(false)
const pendingFiles = ref<File[]>([])
const search = ref('')
const filter = ref('all')
const pollTimer = ref<number>()
const pollingRunId = ref('')
const busy = ref(false)
const mergeTargetId = ref('')

const createDraft = reactive({
  name: '',
  playedAt: '',
  venue: '',
  homeName: '',
  homeColor: '#F4F5F0',
  awayName: '',
  awayColor: '#171A18',
})
const playerDraft = reactive<Partial<Player>>({})
const manualDraft = reactive<{ type: 'attempt' | 'make'; shotType: ShotType; playerId: string; seconds: number }>({ type: 'attempt', shotType: 'twoPoint', playerId: '', seconds: 0 })
let workspaceRequest = 0

const clips = computed(() => workspace.value?.clips ?? [])
const events = computed(() => workspace.value?.events ?? [])
const players = computed(() => workspace.value?.players ?? [])
const runs = computed(() => workspace.value?.runs ?? [])
const selectedClip = computed(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? clips.value[0])
const selectedEvents = computed(() => events.value.filter((event) => event.clipId === selectedClip.value?.id))
const selectedPlayer = computed(() => players.value.find((player) => player.id === selectedPlayerId.value))
const pendingCount = computed(() => events.value.filter((event) => event.status === 'pending').length)
const confirmedCount = computed(() => events.value.filter((event) => event.status === 'confirmed').length)
const candidateCount = computed(() => events.value.filter((event) => event.status === 'pending').length)
const currentRun = computed<Run | undefined>(() => runs.value[0])
const teamTabs = computed(() => [...(workspace.value?.teams ?? [])].sort((left, right) => (left.side === 'home' ? 0 : 1) - (right.side === 'home' ? 0 : 1)))
const selectedTeam = computed(() => workspace.value?.teams.find((team) => team.id === selectedTeamId.value) ?? teamTabs.value[0])
function eventTeamId(event: EventRecord) {
  return event.teamId ?? players.value.find((player) => player.id === event.playerId)?.teamId ?? null
}
const selectedTeamEvents = computed(() => events.value.filter((event) => eventTeamId(event) === selectedTeamId.value && event.status !== 'ignored'))
const teamStats = computed(() => workspace.value?.stats.filter((row) => row.teamId === selectedTeamId.value) ?? [])
const teamCandidateEvents = computed(() => selectedTeamEvents.value.filter((event) => event.status === 'pending'))
const teamHighlights = computed(() => selectedTeamEvents.value.filter((event) => event.type === 'make'))
const teamAnalysisTotals = computed(() => {
  const confirmed = teamStats.value.reduce((totals, row) => ({ attempts: totals.attempts + row.attempts, makes: totals.makes + row.makes, points: totals.points + row.points }), { attempts: 0, makes: 0, points: 0 })
  return {
    attempts: confirmed.attempts + teamCandidateEvents.value.filter((event) => event.type === 'attempt').length,
    makes: confirmed.makes + teamCandidateEvents.value.filter((event) => event.type === 'make').length,
    points: confirmed.points,
  }
})
const teamTotals = computed(() => teamAnalysisTotals.value)
const filteredClips = computed(() => clips.value.filter((clip) => {
  const matchesSearch = !search.value || clip.name.toLowerCase().includes(search.value.toLowerCase())
  return matchesSearch && (filter.value === 'all' || clip.status === filter.value)
}))
const readyModels = computed(() => Object.entries(health.value?.analyzer?.models ?? {})
  .filter(([, model]) => model.ready)
  .map(([name]) => name)
  .join(' / '))

function fail(error: unknown) {
  actionError.value = error instanceof Error ? error.message : '请求失败'
}

async function loadWorkspace(matchId: string) {
  const requestId = ++workspaceRequest
  const previousClip = activeClipId.value
  loadError.value = ''
  try {
    const result = await api.workspace(matchId)
    if (requestId !== workspaceRequest) return
    workspace.value = result
    match.value = result.match
    if (!result.teams.some((team) => team.id === selectedTeamId.value)) {
      selectedTeamId.value = result.match.homeTeam.id ?? result.teams.find((team) => team.side === 'home')?.id ?? result.teams[0]?.id ?? ''
    }
    activeClipId.value = result.clips.some((clip) => clip.id === previousClip)
      ? previousClip
      : result.clips[0]?.id ?? ''
    const activeRun = result.runs.find((run) => run.status === 'running')
    if (activeRun && pollingRunId.value !== activeRun.id) startPolling(activeRun.id)
  } catch (error) {
    if (requestId !== workspaceRequest) return
    loadError.value = error instanceof Error ? error.message : '工作区加载失败'
    workspace.value = null
  }
}

async function boot() {
  loadError.value = ''
  try {
    health.value = await api.health()
    matches.value = await api.matches()
    if (matches.value.length) {
      const firstMatch = matches.value.find((item) => !item.isTest) ?? matches.value[0]
      await loadWorkspace(firstMatch.id)
    }
  } catch (error) {
    health.value = null
    loadError.value = error instanceof Error ? error.message : '本地分析服务不可用'
  }
}

async function createMatch() {
  if (!createDraft.name.trim() || !createDraft.homeName.trim() || !createDraft.awayName.trim()) {
    fail(new Error('请填写比赛名称和两队名称'))
    return
  }
  busy.value = true
  try {
    const created = await api.createMatch({
      name: createDraft.name.trim(),
      playedAt: createDraft.playedAt || undefined,
      venue: createDraft.venue.trim() || undefined,
      homeTeam: { name: createDraft.homeName.trim(), color: createDraft.homeColor },
      awayTeam: { name: createDraft.awayName.trim(), color: createDraft.awayColor },
    })
    matches.value = [created, ...matches.value]
    showCreate.value = false
    await loadWorkspace(created.id)
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function switchMatch(matchId: string) {
  showMatchMenu.value = false
  if (matchId === match.value?.id) return
  selectedPlayerId.value = ''
  showPlayerDetail.value = false
  await loadWorkspace(matchId)
}

async function refresh() {
  if (match.value) await loadWorkspace(match.value.id)
}

async function upload() {
  if (!match.value || !pendingFiles.value.length || busy.value) return
  busy.value = true
  try {
    const result = await api.upload(match.value.id, pendingFiles.value)
    pendingFiles.value = []
    showImport.value = false
    await refresh()
    if (result.accepted.length) await analyze(result.accepted.map((clip) => clip.id))
    if (result.skipped.length) actionError.value = `已跳过 ${result.skipped.length} 个重复或不支持的文件`
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function analyze(clipIds = clips.value.filter((clip) => ['queued', 'failed', 'interrupted'].includes(clip.status ?? '')).map((clip) => clip.id)) {
  if (!match.value || !clipIds.length) return
  try {
    const run = await api.analyze(match.value.id, clipIds)
    if (workspace.value) workspace.value.runs = [run, ...workspace.value.runs.filter((item) => item.id !== run.id)]
    startPolling(run.id)
  } catch (error) {
    fail(error)
  }
}

async function reanalyzeAll() {
  if (!match.value || !clips.value.length || busy.value) return
  busy.value = true
  try {
    const run = await api.analyze(match.value.id, clips.value.map((clip) => clip.id))
    if (workspace.value) workspace.value.runs = [run, ...workspace.value.runs.filter((item) => item.id !== run.id)]
    startPolling(run.id)
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function stopPolling() {
  if (pollTimer.value) window.clearTimeout(pollTimer.value)
  pollTimer.value = undefined
  pollingRunId.value = ''
}

function isTerminal(status?: string) {
  return ['completed', 'failed', 'error', 'interrupted'].includes(status ?? '')
}

function startPolling(runId: string) {
  stopPolling()
  pollingRunId.value = runId
  const poll = async () => {
    try {
      const run = await api.task(runId)
      if (workspace.value) workspace.value.runs = [run, ...workspace.value.runs.filter((item) => item.id !== runId)]
      if (isTerminal(run.status)) {
        stopPolling()
        await refresh()
        return
      }
      pollTimer.value = window.setTimeout(() => void poll(), 1500)
    } catch (error) {
      stopPolling()
      fail(error)
    }
  }
  void poll()
}

async function updateEvent(event: EventRecord, body: Parameters<typeof api.updateEvent>[1], refreshAfter = true) {
  await api.updateEvent(event.id, body)
  if (refreshAfter) await refresh()
}

async function eventAction(event: EventRecord, status: EventRecord['status']) {
  if (status === 'confirmed' && !event.shotType) {
    fail(new Error('请先判断该事件是罚球、两分还是三分'))
    return
  }
  try { await updateEvent(event, { status }) } catch (error) { fail(error) }
}

async function confirmAll() {
  const targets = selectedEvents.value.filter((event) => event.status === 'pending')
  if (!targets.length || busy.value) return
  if (targets.some((event) => !event.shotType)) {
    fail(new Error('存在未判断投篮类型的事件，请先选择罚球、两分或三分'))
    return
  }
  busy.value = true
  try {
    await Promise.all(targets.map((event) => api.updateEvent(event.id, { status: 'confirmed' })))
    await refresh()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function assignEvent(event: EventRecord, playerId: string) {
  const player = players.value.find((item) => item.id === playerId)
  try {
    await updateEvent(event, { playerId: playerId || null, teamId: player?.teamId ?? null })
  } catch (error) {
    fail(error)
  }
}

async function updateEventFields(event: EventRecord, body: { type?: string; shotType?: ShotType | null; points?: number | null }) {
  try { await updateEvent(event, body) } catch (error) { fail(error) }
}

async function addManualEvent() {
  if (!match.value || !selectedClip.value || busy.value) return
  const player = players.value.find((item) => item.id === manualDraft.playerId)
  busy.value = true
  try {
    await api.addEvent(match.value.id, {
      clipId: selectedClip.value.id,
      seconds: manualDraft.seconds,
      type: manualDraft.type,
      shotType: manualDraft.shotType,
      playerId: player?.id ?? null,
      teamId: player?.teamId ?? null,
      points: manualDraft.type === 'make' ? shotPoints(manualDraft.shotType) : null,
    })
    await refresh()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function editPlayer(player: Player) {
  Object.keys(playerDraft).forEach((key) => delete playerDraft[key as keyof Player])
  Object.assign(playerDraft, player)
  mergeTargetId.value = ''
  showPlayerEditor.value = true
}

async function savePlayer() {
  if (!playerDraft.id || busy.value) return
  busy.value = true
  try {
    const hasIdentity = Boolean(playerDraft.name?.trim() || playerDraft.number?.trim())
    await api.updatePlayer(playerDraft.id, {
      name: playerDraft.name?.trim() ?? '',
      number: playerDraft.number?.trim() || null,
      teamId: playerDraft.teamId || null,
      status: hasIdentity ? 'confirmed' : 'unconfirmed',
      identityType: hasIdentity ? 'manual' : 'temporary',
    })
    showPlayerEditor.value = false
    await refresh()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function mergePlayer() {
  if (!match.value || !playerDraft.id || !mergeTargetId.value || busy.value) return
  busy.value = true
  try {
    await api.mergePlayers(match.value.id, playerDraft.id, mergeTargetId.value)
    showPlayerEditor.value = false
    await refresh()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function openPlayerDetails(player?: Player) {
  if (!player) return
  selectedPlayerId.value = player.id
  showPlayerDetail.value = true
  try { highlights.value = await api.highlights(player.id) } catch (error) { fail(error) }
}

async function selectHighlight(event: EventRecord) {
  const clip = event.clipId ? clips.value.find((item) => item.id === event.clipId) : undefined
  if (!clip) {
    fail(new Error('源片段不存在'))
    return
  }
  showPlayerDetail.value = false
  activeHighlight.value = { event, clip }
  showHighlightPlayer.value = true
  await nextTick()
  const seek = event.highlightStart ?? event.seconds ?? 0
  if (!highlightVideoRef.value) return
  if (highlightVideoRef.value.readyState >= 1) {
    highlightVideoRef.value.currentTime = seek
    await highlightVideoRef.value.play().catch(() => undefined)
  } else {
    highlightVideoRef.value.addEventListener('loadedmetadata', () => {
      if (!highlightVideoRef.value) return
      highlightVideoRef.value.currentTime = seek
      void highlightVideoRef.value.play().catch(() => undefined)
    }, { once: true })
  }
}

function monitorHighlightPlayback() {
  const video = highlightVideoRef.value
  const end = activeHighlight.value?.event.highlightEnd
  if (video && end != null && video.currentTime >= end) video.pause()
}

function closeHighlightPlayer() {
  highlightVideoRef.value?.pause()
  showHighlightPlayer.value = false
  activeHighlight.value = null
}

async function openHighlightInReview() {
  if (!activeHighlight.value) return
  const { clip, event } = activeHighlight.value
  closeHighlightPlayer()
  activeClipId.value = clip.id
  tab.value = 'review'
  await nextTick()
  if (!videoRef.value) return
  const seek = event.highlightStart ?? event.seconds ?? 0
  if (videoRef.value.readyState >= 1) videoRef.value.currentTime = seek
  else videoRef.value.addEventListener('loadedmetadata', () => { if (videoRef.value) videoRef.value.currentTime = seek }, { once: true })
}

function selectClip(clip: Clip) {
  activeClipId.value = clip.id
  tab.value = 'review'
}

function eventLabel(type: string) {
  return ({ attempt: '投篮', make: '命中' } as Record<string, string>)[type] ?? '未知事件'
}

function shotTypeLabel(type?: ShotType | null) {
  return ({ freeThrow: '罚球', twoPoint: '两分', threePoint: '三分' } as Record<string, string>)[type ?? ''] ?? '待判断'
}

function shotTypeMeta(event: EventRecord) {
  if (event.shotTypeSource === 'manual') return '人工确认'
  if (event.shotType && event.shotTypeConfidence != null) return `AI ${Math.round(event.shotTypeConfidence * 100)}%`
  return '待判断'
}

function shotPoints(type?: ShotType | null) {
  if (!type) return 0
  return ({ freeThrow: 1, twoPoint: 2, threePoint: 3 } as Record<ShotType, number>)[type]
}

function selectJerseyColor(side: 'home' | 'away', color: string) {
  if (side === 'home') createDraft.homeColor = color
  else createDraft.awayColor = color
}

function statusLabel(status?: string) {
  return ({ queued: '排队中', processing: '分析中', review: '待复核', ready: '已完成', failed: '失败', interrupted: '已中断', running: '分析中', completed: '已完成' } as Record<string, string>)[status ?? ''] ?? '暂无任务'
}

function teamName(teamId?: string | null) {
  return workspace.value?.teams.find((team) => team.id === teamId)?.name || '未归属球队'
}

function playerDisplay(player?: Player) {
  return player?.displayName || player?.name || player?.code || '未归属球员'
}

function playerName(playerId?: string | null) {
  return playerDisplay(players.value.find((player) => player.id === playerId))
}

function formatSeconds(value?: number | null) {
  if (value == null) return '--:--'
  return `${Math.floor(value / 60).toString().padStart(2, '0')}:${Math.floor(value % 60).toString().padStart(2, '0')}`
}

function navCount(key: TabKey) {
  if (key === 'review') return pendingCount.value
  if (key === 'players') return players.value.length
  if (key === 'clips') return clips.value.length
  return ''
}

onMounted(boot)
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup">
        <div class="brand-mark"><ScanLine :size="20" /></div>
        <div><strong>COURTTRACE</strong><span>LOCAL SCOUTING DESK</span></div>
      </div>

      <div class="sidebar-section-label">当前比赛</div>
      <button v-if="match" class="match-switcher" type="button" :aria-expanded="showMatchMenu" @click="showMatchMenu = !showMatchMenu">
        <span class="match-badge">◎</span>
        <span class="match-copy"><strong><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</strong><small>{{ match.venue || '未填写场地' }}</small></span>
        <ChevronDown :size="16" />
      </button>
      <div v-if="showMatchMenu && matches.length" class="match-menu">
        <button v-for="item in matches" :key="item.id" type="button" :class="{ active: item.id === match?.id }" @click="switchMatch(item.id)">
          <span class="match-menu-title">{{ item.name }}<em v-if="item.isTest" class="test-tag">TEST</em></span>
        </button>
      </div>
      <button class="sidebar-create-button" type="button" @click="showCreate = true"><Plus :size="15" /> 创建比赛</button>

      <nav class="primary-nav">
        <button
          v-for="item in [{ key: 'overview', label: '比赛总览', icon: Activity }, { key: 'review', label: '复核队列', icon: CheckCheck }, { key: 'players', label: '球员身份', icon: UsersRound }, { key: 'clips', label: '片段库', icon: Film }]"
          :key="item.key"
          class="nav-item"
          :class="{ active: tab === item.key }"
          type="button"
          @click="tab = item.key as TabKey"
        >
          <component :is="item.icon" :size="18" /><span>{{ item.label }}</span><em>{{ navCount(item.key as TabKey) }}</em>
        </button>
      </nav>
      <div class="sidebar-spacer"></div>
      <div class="engine-card">
        <div class="engine-card-top"><span class="live-dot"></span><span>本地推理引擎</span><Cpu :size="15" /></div>
        <strong>{{ health?.analyzer?.mode || '未连接' }}</strong>
        <small>{{ health?.analyzer?.ready ? '模型已就绪' : '模型未就绪' }}<template v-if="readyModels"> · {{ readyModels }}</template><template v-if="health?.analyzer?.ocr?.ready"> · OCR</template></small>
      </div>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">比赛工作台 <ChevronRight :size="14" /> <strong>{{ ({ overview: '总览', review: '复核', players: '球员', clips: '片段' } as Record<string, string>)[tab] }}</strong></div>
        <div class="connection-state"><span :class="{ offline: !health }"></span>{{ health ? 'LOCAL ONLINE' : 'LOCAL OFFLINE' }}</div>
      </header>

      <div class="page-content">
        <div v-if="loadError" class="error-banner"><CircleAlert :size="17" />{{ loadError }}<button class="icon-button" type="button" title="重试" @click="boot"><RefreshCw :size="16" /></button></div>
        <div v-if="actionError" class="error-banner"><CircleAlert :size="17" />{{ actionError }}<button class="icon-button" type="button" title="关闭" @click="actionError = ''"><X :size="16" /></button></div>

        <template v-if="match && workspace">
          <section class="page-heading">
            <div>
              <div class="eyebrow"><span class="eyebrow-line"></span><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</div>
              <h1>{{ match.homeTeam.name }} <span>vs</span> {{ match.awayTeam.name }}</h1>
              <p>{{ match.playedAt || '未填写比赛日期' }}<b v-if="match.venue"> · </b>{{ match.venue }}</p>
            </div>
            <div class="heading-actions"><button class="button button-quiet" type="button" :disabled="busy || Boolean(pollingRunId) || !clips.length" @click="reanalyzeAll"><RefreshCw :size="16" /> {{ pollingRunId ? '重新分析中' : '重新分析全部' }}</button><button class="button button-acid" type="button" @click="showImport = true"><CloudUpload :size="17" /> 导入片段</button></div>
          </section>

          <section class="metric-strip">
            <div class="metric-cell metric-primary"><div class="metric-label">已接收片段</div><div class="metric-value">{{ clips.length }}</div><div class="metric-subline">当前比赛素材</div></div>
            <div class="metric-cell"><div class="metric-label">已确认事件</div><div class="metric-value">{{ confirmedCount }}</div><div class="metric-subline">{{ pendingCount }} 条等待复核</div></div>
            <div class="metric-cell"><div class="metric-label">AI 候选事件</div><div class="metric-value">{{ candidateCount }}</div><div class="metric-subline">待绑定球员和球队</div></div>
            <div class="metric-cell"><div class="metric-label">分析任务</div><div class="metric-value run-value">{{ statusLabel(currentRun?.status) }}</div><div class="metric-subline"><template v-if="currentRun">{{ currentRun.completed ?? 0 }} / {{ currentRun.total ?? 0 }} · {{ currentRun.progress ?? 0 }}%</template><template v-else>尚未提交分析</template></div></div>
          </section>

          <section v-if="tab === 'overview'" class="tool-panel team-overview-panel">
            <div class="team-tabs" role="tablist" aria-label="切换球队">
              <button
                v-for="team in teamTabs"
                :key="team.id"
                type="button"
                role="tab"
                :aria-selected="selectedTeamId === team.id"
                :class="{ active: selectedTeamId === team.id }"
                @click="selectedTeamId = team.id ?? ''"
              >
                <span class="team-color" :style="{ background: team.color || '#7f8c83' }"></span>
                <span>{{ team.name || (team.side === 'home' ? '主队' : '客队') }}</span>
                <small>{{ team.side === 'home' ? 'HOME' : 'AWAY' }}</small>
              </button>
            </div>

            <div class="team-summary-strip">
              <div><span>球员</span><strong>{{ teamStats.length || new Set(teamCandidateEvents.map((event) => event.playerId).filter(Boolean)).size }}</strong></div>
              <div><span>投篮</span><strong>{{ teamTotals.attempts }}</strong></div>
              <div><span>命中</span><strong>{{ teamTotals.makes }}<small v-if="teamCandidateEvents.filter((event) => event.type === 'make').length"> +{{ teamCandidateEvents.filter((event) => event.type === 'make').length }}待确认</small></strong></div>
              <div><span>得分</span><strong>{{ teamTotals.points }}</strong></div>
            </div>

            <div class="panel-header team-highlight-header">
              <div><div class="panel-kicker">{{ selectedTeam?.name || '当前球队' }}</div><h2>进球集锦 <span>/ CONFIRMED MAKES</span></h2></div>
              <span class="highlight-count">{{ teamHighlights.length }} 个片段<small v-if="teamCandidateEvents.length"> · {{ teamCandidateEvents.length }} 待确认</small></span>
            </div>
            <div v-if="teamHighlights.length" class="team-highlight-grid">
              <button v-for="event in teamHighlights" :key="event.id" class="team-highlight-card" type="button" @click="selectHighlight(event)">
                <span class="team-highlight-preview">
                  <video v-if="clips.find((clip) => clip.id === event.clipId)?.previewUrl" :src="clips.find((clip) => clip.id === event.clipId)?.previewUrl" muted preload="metadata"></video>
                  <span class="play-overlay"><Play :size="18" fill="currentColor" /></span>
                  <small>{{ formatSeconds(event.seconds) }}</small>
                </span>
                <span class="team-highlight-copy">
                  <strong>{{ playerName(event.playerId) }}</strong>
                  <small>{{ event.status === 'confirmed' ? `${event.points ?? 0} 分` : 'AI 待确认' }} · {{ clips.find((clip) => clip.id === event.clipId)?.name || '源片段' }}</small>
                </span>
                <ChevronRight :size="16" />
              </button>
            </div>
            <div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>当前球队暂无进球集锦</strong><span>确认该队命中事件后会自动显示。</span></div>
          </section>

          <section v-if="tab === 'review'" class="workspace-grid">
            <section class="tool-panel review-workspace">
              <div class="panel-header">
                <div><div class="panel-kicker">当前片段</div><h2>{{ selectedClip?.name || '暂无片段' }}</h2></div>
                <button v-if="selectedClip?.status === 'failed'" class="button button-quiet compact" type="button" @click="analyze([selectedClip.id])"><RefreshCw :size="15" /> 重试</button>
              </div>
              <div class="review-layout">
                <div class="video-column">
                  <div class="video-stage">
                    <video v-if="selectedClip?.previewUrl" ref="videoRef" class="source-video" controls playsinline :src="selectedClip.previewUrl"></video>
                    <div v-else class="professional-empty"><Film :size="25" /><strong>暂无源视频</strong><span>导入片段后可在此复核事件。</span></div>
                  </div>
                </div>

                <aside class="event-review-column">
                  <div class="event-column-heading">
                    <div><span class="panel-kicker">候选事件</span><h3>{{ selectedEvents.length }}</h3></div>
                    <button class="text-button" type="button" :disabled="busy || !selectedEvents.some((event) => event.status === 'pending')" @click="confirmAll"><CheckCheck :size="15" /> 全部确认</button>
                  </div>

                  <div v-if="selectedEvents.length" class="event-list">
                    <article v-for="event in selectedEvents" :key="event.id" class="event-item" :class="`event-${event.status}`">
                      <div class="event-item-top">
                        <div class="event-type-mark"><Activity :size="15" /></div>
                        <div class="event-main-copy">
                          <div class="event-title-line">
                            <select :value="event.type" @change="updateEventFields(event, { type: ($event.target as HTMLSelectElement).value })">
                              <option value="attempt">投篮</option><option value="make">命中</option>
                            </select>
                            <span>{{ formatSeconds(event.seconds) }}</span>
                          </div>
                          <p>{{ event.description || '暂无事件描述' }}</p>
                        </div>
                        <label class="shot-type-input"><span>{{ shotTypeMeta(event) }}</span><select :value="event.shotType ?? ''" @change="updateEventFields(event, { shotType: (($event.target as HTMLSelectElement).value || null) as ShotType | null })"><option value="">待判断</option><option value="freeThrow">罚球 · 1分</option><option value="twoPoint">两分 · 2分</option><option value="threePoint">三分 · 3分</option></select></label>
                      </div>
                      <div class="event-item-bottom">
                        <select :value="event.playerId ?? ''" @change="assignEvent(event, ($event.target as HTMLSelectElement).value)">
                          <option value="">未归属球员</option><option v-for="player in players" :key="player.id" :value="player.id">{{ playerDisplay(player) }}</option>
                        </select>
                        <div class="event-actions">
                          <button v-if="event.status !== 'confirmed'" class="mini-action confirm" type="button" title="确认" @click="eventAction(event, 'confirmed')"><Check :size="14" /></button>
                          <button v-if="event.status !== 'ignored'" class="mini-action ignore" type="button" title="忽略" @click="eventAction(event, 'ignored')"><X :size="14" /></button>
                          <button v-if="event.status !== 'pending'" class="mini-action muted" type="button" title="恢复待确认" @click="eventAction(event, 'pending')"><RefreshCw :size="13" /></button>
                        </div>
                      </div>
                    </article>
                  </div>
                  <div v-else class="professional-empty compact-empty"><Activity :size="20" /><strong>当前片段没有候选事件</strong></div>

                  <div v-if="selectedClip" class="manual-entry">
                    <div class="panel-kicker">手工补录</div>
                    <div class="manual-entry-grid">
                      <select v-model="manualDraft.type"><option value="attempt">投篮</option><option value="make">命中</option></select>
                      <select v-model="manualDraft.playerId"><option value="">未归属球员</option><option v-for="player in players" :key="player.id" :value="player.id">{{ playerDisplay(player) }}</option></select>
                      <label><span>秒</span><input v-model.number="manualDraft.seconds" type="number" min="0" :max="selectedClip.duration ?? undefined" step="0.1" /></label>
                      <label><span>投篮类型</span><select v-model="manualDraft.shotType"><option value="freeThrow">罚球</option><option value="twoPoint">两分</option><option value="threePoint">三分</option></select></label>
                      <button class="button button-quiet compact" type="button" :disabled="busy" @click="addManualEvent"><Plus :size="14" /> 添加</button>
                    </div>
                  </div>
                </aside>
              </div>
            </section>
          </section>

          <section v-if="tab === 'overview'" class="tool-panel stats-panel">
            <div class="panel-header"><div><div class="panel-kicker">{{ selectedTeam?.name || '当前球队' }}</div><h2>球员数据</h2></div></div>
            <div v-if="teamStats.length" class="table-wrap">
              <table class="stats-table"><thead><tr><th>球员</th><th>投篮</th><th>命中</th><th>罚球</th><th>两分</th><th>三分</th><th>得分</th></tr></thead><tbody>
                <tr v-for="row in teamStats" :key="row.playerId ?? 'unassigned'" :class="{ clickable: Boolean(row.playerId) }" @click="row.playerId && openPlayerDetails(players.find((player) => player.id === row.playerId))">
                  <td>{{ row.name || playerName(row.playerId) }}</td><td>{{ row.attempts }}</td><td>{{ row.makes }}</td><td>{{ row.freeThrowMakes }}/{{ row.freeThrowAttempts }}</td><td>{{ row.twoPointMakes }}/{{ row.twoPointAttempts }}</td><td>{{ row.threePointMakes }}/{{ row.threePointAttempts }}</td><td class="points-cell">{{ row.points }}</td>
                </tr>
              </tbody></table>
            </div>
            <div v-else class="professional-empty"><Activity :size="24" /><strong>暂无确认统计</strong><span>确认投篮或命中事件后，真实数据会显示在这里。</span></div>
          </section>

          <section v-if="tab === 'players'" class="tool-panel roster-panel">
            <div class="panel-header"><div><div class="panel-kicker">身份管理</div><h2>本场球员</h2></div></div>
            <div v-if="players.length" class="roster-columns">
              <button v-for="player in players" :key="player.id" class="roster-row" type="button" @click="editPlayer(player)">
                <span class="roster-number" :style="{ background: player.color || '#87958b' }">{{ player.number || '?' }}</span>
                <span><strong>{{ playerDisplay(player) }}</strong><small>{{ teamName(player.teamId) }} · {{ player.numberSource === 'ai' ? `OCR ${Math.round((player.numberConfidence ?? 0) * 100)}%` : player.identityType === 'temporary' ? '临时身份' : '已确认身份' }} · {{ player.tracks ?? 0 }} 段轨迹</small></span>
                <Settings2 :size="15" />
              </button>
            </div>
            <div v-else class="professional-empty"><UsersRound :size="24" /><strong>尚未识别到球员</strong><span>完成片段分析后，临时球员身份会出现在这里。</span></div>
          </section>

          <section v-if="tab === 'clips'" class="tool-panel library-panel">
            <div class="panel-header"><div><div class="panel-kicker">素材管理</div><h2>片段库</h2></div><div class="panel-actions"><button class="button button-quiet compact" type="button" :disabled="busy || Boolean(pollingRunId) || !clips.length" @click="reanalyzeAll"><RefreshCw :size="15" /> {{ pollingRunId ? '重新分析中' : '重新分析全部' }}</button><button class="button button-acid" type="button" @click="showImport = true"><Upload :size="16" /> 导入片段</button></div></div>
            <div class="library-toolbar">
              <label class="search-field"><Search :size="16" /><input v-model="search" placeholder="搜索文件名" /></label>
              <div class="filter-pills"><button v-for="item in [{ value: 'all', label: '全部' }, { value: 'queued', label: '排队中' }, { value: 'review', label: '待复核' }, { value: 'failed', label: '失败' }]" :key="item.value" :class="{ active: filter === item.value }" type="button" @click="filter = item.value">{{ item.label }}</button></div>
            </div>
            <div v-if="filteredClips.length" class="clip-grid">
              <button v-for="clip in filteredClips" :key="clip.id" class="clip-card" type="button" @click="selectClip(clip)">
                <div class="clip-card-preview"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><div v-else class="professional-empty small"><Film :size="18" /></div></div>
                <div class="clip-card-copy"><div><strong>{{ clip.name }}</strong><small>{{ formatSeconds(clip.duration) }}</small></div><span>{{ statusLabel(clip.status) }}</span></div>
              </button>
            </div>
            <div v-else class="professional-empty"><Film :size="24" /><strong>暂无符合条件的片段</strong><span>导入本场比赛视频后开始分析。</span></div>
          </section>
        </template>

        <div v-else-if="!loadError" class="professional-empty page-empty"><Activity :size="28" /><strong>尚未创建比赛</strong><span>先录入两队信息，再导入真实视频。</span></div>
      </div>
    </main>

    <div v-if="showCreate" class="modal-layer">
      <section class="modal">
        <div class="modal-header"><div><span class="panel-kicker"><Plus :size="13" /> NEW MATCH</span><h2>创建比赛</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showCreate = false"><X :size="18" /></button></div>
        <div class="form-grid">
          <label><span>比赛名称 *</span><input v-model="createDraft.name" /></label><label><span>比赛日期</span><input v-model="createDraft.playedAt" type="datetime-local" /></label>
          <label><span>比赛场地</span><input v-model="createDraft.venue" /></label><span></span>
          <label><span>主队名称 *</span><input v-model="createDraft.homeName" /></label>
          <div class="jersey-color-field"><span>主队球衣颜色 *</span><div class="jersey-palette"><button v-for="color in jerseyColors" :key="`home-${color.value}`" class="jersey-swatch" :class="{ selected: createDraft.homeColor.toUpperCase() === color.value }" type="button" :title="color.name" :style="{ background: color.value }" @click="selectJerseyColor('home', color.value)"><Check v-if="createDraft.homeColor.toUpperCase() === color.value" :size="13" /></button><label class="custom-color-swatch" title="自定义颜色"><input v-model="createDraft.homeColor" type="color" /><Plus :size="13" /></label></div><small>{{ createDraft.homeColor }}</small></div>
          <label><span>客队名称 *</span><input v-model="createDraft.awayName" /></label>
          <div class="jersey-color-field"><span>客队球衣颜色 *</span><div class="jersey-palette"><button v-for="color in jerseyColors" :key="`away-${color.value}`" class="jersey-swatch" :class="{ selected: createDraft.awayColor.toUpperCase() === color.value }" type="button" :title="color.name" :style="{ background: color.value }" @click="selectJerseyColor('away', color.value)"><Check v-if="createDraft.awayColor.toUpperCase() === color.value" :size="13" /></button><label class="custom-color-swatch" title="自定义颜色"><input v-model="createDraft.awayColor" type="color" /><Plus :size="13" /></label></div><small>{{ createDraft.awayColor }}</small></div>
        </div>
        <div class="modal-footer"><span>球队颜色用于后续身份辅助判断</span><button class="button button-acid" type="button" :disabled="busy" @click="createMatch"><Check :size="16" /> 创建并进入</button></div>
      </section>
    </div>

    <div v-if="showImport" class="modal-layer" @click.self="showImport = false">
      <section class="modal">
        <div class="modal-header"><div><span class="panel-kicker"><Upload :size="13" /> LOCAL INGEST</span><h2>导入比赛片段</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showImport = false"><X :size="18" /></button></div>
        <label class="file-picker"><CloudUpload :size="23" /><strong>选择本地视频</strong><span>支持 MP4、MOV、M4V、WebM，可多选</span><input type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" multiple @change="pendingFiles = Array.from(($event.target as HTMLInputElement).files || [])" /></label>
        <div class="modal-footer"><span>{{ pendingFiles.length }} 个文件待上传</span><button class="button button-acid" type="button" :disabled="busy || !pendingFiles.length" @click="upload"><CloudUpload :size="16" /> 上传并自动分析</button></div>
      </section>
    </div>

    <div v-if="showPlayerEditor" class="modal-layer" @click.self="showPlayerEditor = false">
      <section class="modal player-modal">
        <div class="modal-header"><div><span class="panel-kicker">IDENTITY</span><h2>编辑球员身份</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showPlayerEditor = false"><X :size="18" /></button></div>
        <div class="form-grid">
          <label><span>显示名称</span><input v-model="playerDraft.name" /></label><label><span>球衣号码</span><input v-model="playerDraft.number" /></label>
          <label><span>所属球队</span><select v-model="playerDraft.teamId"><option value="">未归属球队</option><option v-for="team in workspace?.teams" :key="team.id" :value="team.id">{{ team.name }}</option></select></label>
          <label><span>合并到另一身份</span><select v-model="mergeTargetId"><option value="">不合并</option><option v-for="player in players.filter((item) => item.id !== playerDraft.id)" :key="player.id" :value="player.id">{{ playerDisplay(player) }}</option></select></label>
        </div>
        <div class="modal-footer"><button class="button button-quiet" type="button" :disabled="busy || !mergeTargetId" @click="mergePlayer">合并身份</button><button class="button button-acid" type="button" :disabled="busy" @click="savePlayer"><Check :size="16" /> 保存修正</button></div>
      </section>
    </div>

    <div v-if="showPlayerDetail && selectedPlayer" class="detail-layer" @click.self="showPlayerDetail = false">
      <aside class="player-detail-drawer">
        <div class="drawer-header"><div><span class="panel-kicker"><UsersRound :size="13" /> PLAYER PROFILE</span><h2>{{ playerDisplay(selectedPlayer) }}</h2><p>{{ teamName(selectedPlayer.teamId) }}</p></div><button class="icon-button dark" type="button" title="关闭" @click="showPlayerDetail = false"><X :size="18" /></button></div>
        <div class="drawer-stat-grid"><div><strong>{{ selectedPlayer.number || '未设置' }}</strong><span>号码</span></div><div><strong>{{ highlights.length }}</strong><span>确认命中</span></div></div>
        <div class="drawer-section-heading"><h3>进球集锦</h3></div>
        <div v-if="highlights.length" class="highlight-list"><button v-for="event in highlights" :key="event.id" class="highlight-item" type="button" @click="selectHighlight(event)"><Play :size="15" /><span>{{ eventLabel(event.type) }} · {{ formatSeconds(event.seconds) }}</span><ChevronRight :size="15" /></button></div>
        <div v-else class="empty-highlights"><Film :size="19" /><strong>暂无已确认命中片段</strong></div>
      </aside>
    </div>

    <div v-if="showHighlightPlayer && activeHighlight" class="modal-layer highlight-player-layer" @click.self="closeHighlightPlayer">
      <section class="modal highlight-player-modal" role="dialog" aria-modal="true" aria-labelledby="highlight-player-title">
        <div class="modal-header">
          <div>
            <span class="panel-kicker">SCORING HIGHLIGHT</span>
            <h2 id="highlight-player-title">{{ playerName(activeHighlight.event.playerId) }} · {{ eventLabel(activeHighlight.event.type) }}</h2>
            <p>{{ teamName(activeHighlight.event.teamId) }} · {{ shotTypeLabel(activeHighlight.event.shotType) }} · {{ activeHighlight.event.points ?? 0 }} 分 · {{ activeHighlight.clip.name }}</p>
          </div>
          <button class="icon-button dark" type="button" title="关闭" @click="closeHighlightPlayer"><X :size="18" /></button>
        </div>
        <div class="highlight-player-video">
          <video
            ref="highlightVideoRef"
            controls
            playsinline
            :src="activeHighlight.clip.previewUrl"
            @timeupdate="monitorHighlightPlayback"
          ></video>
        </div>
        <div class="highlight-player-meta">
          <span>集锦范围 {{ formatSeconds(activeHighlight.event.highlightStart ?? activeHighlight.event.seconds) }} - {{ formatSeconds(activeHighlight.event.highlightEnd) }}</span>
          <span>事件时间 {{ formatSeconds(activeHighlight.event.seconds) }}</span>
        </div>
        <div class="modal-footer">
          <button class="button button-quiet" type="button" @click="closeHighlightPlayer">关闭</button>
          <button class="button button-acid" type="button" @click="openHighlightInReview"><CheckCheck :size="16" /> 进入复核</button>
        </div>
      </section>
    </div>
  </div>
</template>
