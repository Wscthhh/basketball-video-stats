<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Activity, Check, CheckCheck, ChevronDown, ChevronRight, CircleAlert, CloudUpload, Cpu, Film, Play, Plus, RefreshCw, ScanLine, Search, Upload, X } from 'lucide-vue-next'
import { api } from './api'
import type { Clip, ClipCollections, Health, Match, Run, TabKey, Team, Workspace } from './types'

const tab = ref<TabKey>('overview')
const matches = ref<Match[]>([])
const match = ref<Match | null>(null)
const workspace = ref<Workspace | null>(null)
const collections = ref<ClipCollections | null>(null)
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
const activeHighlight = ref<Clip | null>(null)
const highlightVideoRef = ref<HTMLVideoElement | null>(null)

const createDraft = reactive({ name: '', playedAt: '', venue: '', homeName: '', homeColor: '#F4F5F0', awayName: '', awayColor: '#171A18' })
const clips = computed(() => workspace.value?.clips ?? [])
const runs = computed(() => workspace.value?.runs ?? [])
const selectedClip = computed(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? clips.value[0])
const unresolvedClips = computed(() => collections.value?.unresolved ?? clips.value.filter((clip) => !clip.teamId))
const currentRun = computed<Run | undefined>(() => runs.value[0])
const pendingCount = computed(() => unresolvedClips.value.length)
const readyModels = computed(() => Object.entries(health.value?.analyzer?.models ?? {}).filter(([, model]) => model.ready).map(([name]) => name).join(' / '))
const filteredClips = computed(() => clips.value.filter((clip) => (!search.value || clip.name.toLowerCase().includes(search.value.toLowerCase())) && (filter.value === 'all' || clip.status === filter.value)))
const homeClips = computed(() => collections.value?.home.clips ?? clips.value.filter((clip) => clip.teamId === teamBySide('home')?.id))
const awayClips = computed(() => collections.value?.away.clips ?? clips.value.filter((clip) => clip.teamId === teamBySide('away')?.id))

function fail(error: unknown) { actionError.value = error instanceof Error ? error.message : '请求失败' }

async function loadWorkspace(matchId: string) {
  loadError.value = ''
  try {
    const [result, collectionResponse] = await Promise.all([api.workspace(matchId), api.clipCollections(matchId).catch(() => null)])
    let collectionResult: ClipCollections
    if (collectionResponse) collectionResult = collectionResponse
    else {
      const homeId = result.match.homeTeam.id ?? result.teams.find((team) => team.side === 'home')?.id
      const awayId = result.match.awayTeam.id ?? result.teams.find((team) => team.side === 'away')?.id
      collectionResult = { home: { team: result.match.homeTeam, clips: result.clips.filter((clip) => clip.teamId === homeId) }, away: { team: result.match.awayTeam, clips: result.clips.filter((clip) => clip.teamId === awayId) }, unresolved: result.clips.filter((clip) => clip.teamId !== homeId && clip.teamId !== awayId) }
    }
    workspace.value = result; match.value = result.match; collections.value = collectionResult
    activeClipId.value = result.clips.some((clip) => clip.id === activeClipId.value) ? activeClipId.value : result.clips[0]?.id ?? ''
    const activeRun = result.runs.find((run) => run.status === 'running')
    if (activeRun && pollingRunId.value !== activeRun.id) startPolling(activeRun.id)
  } catch (error) { loadError.value = error instanceof Error ? error.message : '工作区加载失败'; workspace.value = null; collections.value = null }
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

async function setClipTeam(clip: Clip, teamId: string | null) { if (busy.value) return; busy.value = true; try { await api.updateClipTeam(clip.id, teamId); await refresh() } catch (error) { fail(error) } finally { busy.value = false } }

function teamName(team?: Team) { return team?.name || '未判断' }
function teamLabel(side: 'home' | 'away') { return teamBySide(side)?.name || (side === 'home' ? '主队' : '客队') }
function teamBySide(side: 'home' | 'away') { return workspace.value?.teams.find((team) => team.side === side) ?? (side === 'home' ? match.value?.homeTeam : match.value?.awayTeam) }
function clipSource(clip: Clip) { return clip.teamSource === 'manual' ? '人工指定' : clip.teamSource === 'ai' ? 'AI 归属' : '待判断' }
function formatSeconds(value?: number | null) { return value == null ? '--:--' : `${Math.floor(value / 60).toString().padStart(2, '0')}:${Math.floor(value % 60).toString().padStart(2, '0')}` }
function statusLabel(status?: string) { return ({ queued: '排队中', processing: '分析中', review: '待复核', ready: '已完成', failed: '失败', interrupted: '已中断', running: '分析中', completed: '已完成' } as Record<string, string>)[status ?? ''] ?? '暂无任务' }
function openHighlight(clip: Clip) { activeHighlight.value = clip; showHighlightPlayer.value = true; void nextTick(() => { void highlightVideoRef.value?.play().catch(() => undefined) }) }
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
           <section class="metric-strip"><div class="metric-cell metric-primary"><div class="metric-label">全部片段</div><div class="metric-value">{{ clips.length }}</div><div class="metric-subline">当前比赛导入素材</div></div><div class="metric-cell"><div class="metric-label">主队片段</div><div class="metric-value">{{ homeClips.length }}</div><div class="metric-subline">按球队归属</div></div><div class="metric-cell"><div class="metric-label">客队片段</div><div class="metric-value">{{ awayClips.length }}</div><div class="metric-subline">按球队归属</div></div><div class="metric-cell"><div class="metric-label">待归属</div><div class="metric-value">{{ unresolvedClips.length }}</div><div class="metric-subline">需要人工判断</div></div></section>

           <section v-if="tab === 'overview'" class="tool-panel team-overview-panel"><div class="overview-columns"><div v-for="group in [{ key: 'home', label: '主队', clips: homeClips }, { key: 'away', label: '客队', clips: awayClips }]" :key="group.key" class="overview-column"><div class="panel-header"><div><div class="panel-kicker">{{ group.label }}片段</div><h2>{{ teamBySide(group.key as 'home' | 'away')?.name || group.label }} · 片段集锦</h2></div><span class="highlight-count">{{ group.clips.length }} 个片段</span></div><div v-if="group.clips.length" class="team-highlight-grid"><article v-for="clip in group.clips" :key="clip.id" class="team-highlight-card" @click="openHighlight(clip)"><span class="team-highlight-preview"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><span v-else class="preview-empty"><Film :size="18" /></span><span class="play-overlay"><Play :size="18" fill="currentColor" /></span></span><span class="team-highlight-copy"><small>{{ statusLabel(clip.status) }} · {{ clipSource(clip) }}</small><strong>{{ clip.name }}</strong><small>{{ clip.teamEvidence || '已归属该球队' }}</small></span><button class="clip-team-reassign" type="button" title="重新归属" @click.stop="setClipTeam(clip, null)"><X :size="14" /></button></article></div><div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无{{ group.label }}片段</strong><span>归属后的真实视频会显示在这里。</span></div></div></div><div class="overview-unresolved"><div class="panel-header"><div><div class="panel-kicker">UNRESOLVED CLIPS</div><h2>待归属片段</h2></div><span class="highlight-count">{{ unresolvedClips.length }} 个片段</span></div><div v-if="unresolvedClips.length" class="team-highlight-grid"><article v-for="clip in unresolvedClips" :key="clip.id" class="team-highlight-card" @click="openHighlight(clip)"><span class="team-highlight-preview"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><span v-else class="preview-empty"><Film :size="18" /></span><span class="play-overlay"><Play :size="18" fill="currentColor" /></span></span><span class="team-highlight-copy"><small>{{ statusLabel(clip.status) }} · {{ clipSource(clip) }}</small><strong>{{ clip.name }}</strong><small>{{ clip.teamEvidence || '请选择球队归属' }}</small></span><ChevronRight :size="16" /></article></div><div v-else class="professional-empty team-highlight-empty"><Film :size="24" /><strong>暂无待归属片段</strong><span>所有导入片段都已完成球队归属。</span></div></div></section>

        <section v-if="tab === 'review'" class="tool-panel review-panel"><div class="panel-header"><div><div class="panel-kicker">CLIP OWNERSHIP</div><h2>片段归属队列</h2></div><span class="highlight-count">{{ unresolvedClips.length }} 个待判断</span></div><div v-if="unresolvedClips.length" class="event-list review-list"><article v-for="clip in unresolvedClips" :key="clip.id" class="event-item clip-review-item"><div class="clip-review-video" @click="openHighlight(clip)"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><Play :size="18" fill="currentColor" /></div><div class="event-main-copy"><div class="event-title-line"><strong>{{ clip.name }}</strong><span>{{ statusLabel(clip.status) }}</span></div><p>{{ clip.teamEvidence || '请选择该片段所属球队' }}</p><div class="team-choice"><button v-for="side in ['home', 'away']" :key="side" type="button" @click="setClipTeam(clip, teamBySide(side as 'home' | 'away')?.id ?? null)">{{ teamLabel(side as 'home' | 'away') }}</button><button type="button" @click="setClipTeam(clip, null)">待判断</button></div></div></article></div><div v-else class="professional-empty"><CheckCheck :size="24" /><strong>暂无待归属片段</strong><span>分析完成后，无法判断球队的片段会出现在这里。</span></div></section>

          <section v-if="tab === 'clips'" class="tool-panel library-panel"><div class="panel-header"><div><div class="panel-kicker">素材管理</div><h2>片段库</h2></div><div class="panel-actions"><button class="button button-quiet compact" type="button" :disabled="busy || Boolean(pollingRunId) || !clips.length" @click="reanalyzeAll"><RefreshCw :size="15" /> 重新分析全部</button><button class="button button-acid" type="button" @click="showImport = true"><Upload :size="16" /> 导入片段</button></div></div><div class="library-toolbar"><label class="search-field"><Search :size="16" /><input v-model="search" placeholder="搜索文件名" /></label><div class="filter-pills"><button v-for="item in [{ value: 'all', label: '全部' }, { value: 'queued', label: '排队中' }, { value: 'review', label: '待复核' }, { value: 'failed', label: '失败' }]" :key="item.value" :class="{ active: filter === item.value }" type="button" @click="filter = item.value">{{ item.label }}</button></div></div><div v-if="filteredClips.length" class="clip-grid"><button v-for="clip in filteredClips" :key="clip.id" class="clip-card" type="button" @click="selectClip(clip)"><div class="clip-card-preview"><video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video><div v-else class="professional-empty small"><Film :size="18" /></div></div><div class="clip-card-copy"><div><strong>{{ clip.name }}</strong><small>{{ formatSeconds(clip.duration) }}</small></div><span>{{ statusLabel(clip.status) }}</span></div></button></div><div v-else class="professional-empty"><Film :size="24" /><strong>暂无符合条件的片段</strong><span>导入本场比赛视频后开始分析。</span></div></section>
        </template><div v-else-if="!loadError" class="professional-empty page-empty"><Activity :size="28" /><strong>尚未创建比赛</strong><span>先录入两队信息，再导入真实视频。</span></div>
      </div>
    </main>

     <div v-if="showCreate" class="modal-layer"><section class="modal"><div class="modal-header"><div><span class="panel-kicker"><Plus :size="13" /> NEW MATCH</span><h2>创建比赛</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showCreate = false"><X :size="18" /></button></div><div class="form-grid"><label><span>比赛名称 *</span><input v-model="createDraft.name" /></label><label><span>比赛日期</span><input v-model="createDraft.playedAt" type="datetime-local" /></label><label><span>比赛场地</span><input v-model="createDraft.venue" /></label><span></span><label><span>主队名称 *</span><input v-model="createDraft.homeName" /></label><label><span>主队颜色</span><input v-model="createDraft.homeColor" type="color" /></label><label><span>客队名称 *</span><input v-model="createDraft.awayName" /></label><label><span>客队颜色</span><input v-model="createDraft.awayColor" type="color" /></label></div><div class="modal-footer"><span>一期只管理球队片段归属</span><button class="button button-acid" type="button" :disabled="busy" @click="createMatch"><Check :size="16" /> 创建并进入</button></div></section></div>
    <div v-if="showImport" class="modal-layer" @click.self="showImport = false"><section class="modal"><div class="modal-header"><div><span class="panel-kicker"><Upload :size="13" /> LOCAL INGEST</span><h2>导入比赛片段</h2></div><button class="icon-button dark" type="button" title="关闭" @click="showImport = false"><X :size="18" /></button></div><label class="file-picker"><CloudUpload :size="23" /><strong>选择本地视频</strong><span>支持 MP4、MOV、M4V、WebM，可多选</span><input type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" multiple @change="pendingFiles = Array.from(($event.target as HTMLInputElement).files || [])" /></label><div class="modal-footer"><span>{{ pendingFiles.length }} 个文件待上传</span><button class="button button-acid" type="button" :disabled="busy || !pendingFiles.length" @click="upload"><CloudUpload :size="16" /> 上传并自动分析</button></div></section></div>
     <div v-if="showHighlightPlayer && activeHighlight" class="modal-layer highlight-player-layer" @click.self="closeHighlight"><section class="modal highlight-player-modal"><div class="modal-header"><div><span class="panel-kicker">CLIP PREVIEW</span><h2>{{ activeHighlight.name }}</h2><p>{{ statusLabel(activeHighlight.status) }} · {{ clipSource(activeHighlight) }}</p></div><button class="icon-button dark" type="button" title="关闭" @click="closeHighlight"><X :size="18" /></button></div><div class="highlight-player-video"><video ref="highlightVideoRef" controls playsinline :src="activeHighlight.previewUrl"></video></div><div class="highlight-player-meta"><span>片段状态 {{ statusLabel(activeHighlight.status) }}</span><span>球队归属 {{ activeHighlight.teamId ? teamName(workspace?.teams.find((team) => team.id === activeHighlight?.teamId)) : '待判断' }}</span></div></section></div>
  </div>
</template>
