<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Activity, ChevronRight, CircleAlert, RefreshCw, X } from 'lucide-vue-next'
import { api } from './api'
import AppSidebar from './components/AppSidebar.vue'
import ClipLibrary from './components/ClipLibrary.vue'
import ClipPreviewModal from './components/ClipPreviewModal.vue'
import ClipReviewQueue from './components/ClipReviewQueue.vue'
import CreateMatchModal from './components/CreateMatchModal.vue'
import ImportClipsModal from './components/ImportClipsModal.vue'
import MatchOverview from './components/MatchOverview.vue'
import TeamHighlightExports from './components/TeamHighlightExports.vue'
import WorkspaceHeader from './components/WorkspaceHeader.vue'
import type { Clip, ClipCollections, CreateMatchDraft, Health, Match, Run, TabKey, TeamHighlightExport, Workspace } from './types'

const tab = ref<TabKey>('overview')
const matches = ref<Match[]>([])
const match = ref<Match | null>(null)
const workspace = ref<Workspace | null>(null)
const collections = ref<ClipCollections | null>(null)
const teamHighlights = ref<TeamHighlightExport[]>([])
const health = ref<Health | null>(null)
const loadError = ref('')
const actionError = ref('')
const activeClipId = ref('')
const showCreate = ref(false)
const showImport = ref(false)
const pendingFiles = ref<File[]>([])
const busy = ref(false)
const pollTimer = ref<number>()
const exportPollTimer = ref<number>()
const pollingRunId = ref('')
const createDraft = ref<CreateMatchDraft>({
  name: '',
  playedAt: '',
  venue: '',
  homeName: '',
  homeColor: '#F4F5F0',
  awayName: '',
  awayColor: '#171A18',
})

const clips = computed(() => workspace.value?.clips ?? [])
const runs = computed(() => workspace.value?.runs ?? [])
const analysisRun = computed(() => runs.value.find((run) => run.id === pollingRunId.value) ?? runs.value.find((run) => run.status === 'running') ?? runs.value[0])
const activeClip = computed(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? null)
const homeTeam = computed(() => workspace.value?.teams.find((team) => team.side === 'home') ?? match.value?.homeTeam)
const awayTeam = computed(() => workspace.value?.teams.find((team) => team.side === 'away') ?? match.value?.awayTeam)
const isConfirmedClip = (clip: Clip) => clip.teamConfirmed === true || clip.teamSource === 'manual'
const unresolvedClips = computed(() => collections.value?.unresolved ?? clips.value.filter((clip) => !isConfirmedClip(clip)))
const homeClips = computed(() => collections.value?.home.clips ?? clips.value.filter((clip) => isConfirmedClip(clip) && clip.teamId === homeTeam.value?.id))
const awayClips = computed(() => collections.value?.away.clips ?? clips.value.filter((clip) => isConfirmedClip(clip) && clip.teamId === awayTeam.value?.id))
const readyModels = computed(() => Object.entries(health.value?.analyzer?.models ?? {}).filter(([, model]) => model.ready).map(([name]) => name).join(' / '))

function fail(error: unknown) {
  actionError.value = error instanceof Error ? error.message : '请求失败'
}

function fallbackCollections(result: Workspace): ClipCollections {
  const homeId = result.match.homeTeam.id ?? result.teams.find((team) => team.side === 'home')?.id
  const awayId = result.match.awayTeam.id ?? result.teams.find((team) => team.side === 'away')?.id
  return {
    home: { team: result.match.homeTeam, clips: result.clips.filter((clip) => isConfirmedClip(clip) && clip.teamId === homeId) },
    away: { team: result.match.awayTeam, clips: result.clips.filter((clip) => isConfirmedClip(clip) && clip.teamId === awayId) },
    unresolved: result.clips.filter((clip) => !isConfirmedClip(clip) || (clip.teamId !== homeId && clip.teamId !== awayId)),
  }
}

async function loadWorkspace(matchId: string) {
  loadError.value = ''
  try {
    const [result, collectionResponse, exportResponse] = await Promise.all([
      api.workspace(matchId),
      api.clipCollections(matchId).catch(() => null),
      api.teamHighlights(matchId).catch(() => []),
    ])
    workspace.value = result
    match.value = result.match
    collections.value = collectionResponse ?? fallbackCollections(result)
    teamHighlights.value = exportResponse
    if (teamHighlights.value.some((item) => item.status === 'queued' || item.status === 'running')) startExportPolling()
    if (activeClipId.value && !result.clips.some((clip) => clip.id === activeClipId.value)) activeClipId.value = ''
    const activeRun = result.runs.find((run) => run.status === 'running')
    if (activeRun && pollingRunId.value !== activeRun.id) startPolling(activeRun.id)
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '工作区加载失败'
    workspace.value = null
    collections.value = null
  }
}

function stopExportPolling() {
  if (exportPollTimer.value) window.clearTimeout(exportPollTimer.value)
  exportPollTimer.value = undefined
}

function startExportPolling() {
  stopExportPolling()
  const poll = async () => {
    if (!match.value) return
    try {
      teamHighlights.value = await api.teamHighlights(match.value.id)
      if (teamHighlights.value.some((item) => item.status === 'queued' || item.status === 'running')) exportPollTimer.value = window.setTimeout(() => void poll(), 1200)
    } catch (error) {
      fail(error)
    }
  }
  void poll()
}

async function boot() {
  try {
    health.value = await api.health()
    matches.value = await api.matches()
    if (matches.value.length) await loadWorkspace((matches.value.find((item) => !item.isTest) ?? matches.value[0]).id)
  } catch (error) {
    health.value = null
    loadError.value = error instanceof Error ? error.message : '本地分析服务不可用'
  }
}

async function createMatch() {
  const draft = createDraft.value
  if (!draft.name.trim() || !draft.homeName.trim() || !draft.awayName.trim()) {
    fail(new Error('请填写比赛名称和两队名称'))
    return
  }
  busy.value = true
  try {
    const created = await api.createMatch({
      name: draft.name.trim(),
      playedAt: draft.playedAt || undefined,
      venue: draft.venue.trim() || undefined,
      homeTeam: { name: draft.homeName.trim(), color: draft.homeColor },
      awayTeam: { name: draft.awayName.trim(), color: draft.awayColor },
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

async function switchMatch(id: string) {
  if (id !== match.value?.id) {
    activeClipId.value = ''
    await loadWorkspace(id)
  }
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
    await analyze(clips.value.map((clip) => clip.id))
  } finally {
    busy.value = false
  }
}

function stopPolling() {
  if (pollTimer.value) window.clearTimeout(pollTimer.value)
  pollTimer.value = undefined
  pollingRunId.value = ''
}

function startPolling(runId: string) {
  stopPolling()
  pollingRunId.value = runId
  const poll = async () => {
    try {
      const run: Run = await api.task(runId)
      if (workspace.value) workspace.value.runs = [run, ...runs.value.filter((item) => item.id !== runId)]
      if (['completed', 'failed', 'error', 'interrupted'].includes(run.status ?? '')) {
        stopPolling()
        await refresh()
      } else {
        pollTimer.value = window.setTimeout(() => void poll(), 1500)
      }
    } catch (error) {
      stopPolling()
      fail(error)
    }
  }
  void poll()
}

function openClip(clip: Clip) {
  activeClipId.value = clip.id
}

function exportClip(clip: Clip) {
  window.location.href = api.downloadClipUrl(clip.id)
}

async function generateTeamHighlight(teamId: string) {
  if (!match.value || busy.value) return
  busy.value = true
  try {
    await api.generateTeamHighlight(match.value.id, teamId)
    startExportPolling()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function navigateReviewClip(direction: -1 | 1) {
  const index = unresolvedClips.value.findIndex((clip) => clip.id === activeClipId.value)
  const target = unresolvedClips.value[index + direction]
  if (target) activeClipId.value = target.id
}

function advanceReviewClip(previousId: string, previousIndex: number) {
  if (!unresolvedClips.value.length) {
    closeClip()
    return
  }
  const next = unresolvedClips.value[previousIndex] ?? unresolvedClips.value[previousIndex - 1]
  if (next && next.id !== previousId) activeClipId.value = next.id
  else closeClip()
}

function closeClip() {
  activeClipId.value = ''
}

async function setClipTeam(teamId: string | null): Promise<boolean> {
  if (!activeClip.value || busy.value) return false
  busy.value = true
  try {
    await api.updateClipTeam(activeClip.value.id, teamId)
    await refresh()
    return true
  } catch (error) {
    fail(error)
    return false
  } finally {
    busy.value = false
  }
}

async function confirmClipTeam(teamId: string | null) {
  const previousId = activeClipId.value
  const previousIndex = unresolvedClips.value.findIndex((clip) => clip.id === previousId)
  if (await setClipTeam(teamId)) {
    if (teamId && previousIndex >= 0) advanceReviewClip(previousId, previousIndex)
    else closeClip()
  }
}

async function reassignClipTeam(teamId: string | null) {
  if (await setClipTeam(teamId)) closeClip()
}

function startReassign() {}

function cancelReassign() {}

async function deleteActiveClip() {
  const clip = activeClip.value
  if (!clip || busy.value || !window.confirm(`确定删除片段“${clip.name}”吗？此操作无法撤销。`)) return
  const reviewIndex = unresolvedClips.value.findIndex((item) => item.id === clip.id)
  busy.value = true
  try {
    await api.deleteClip(clip.id)
    await refresh()
    if (reviewIndex >= 0) advanceReviewClip(clip.id, reviewIndex)
    else closeClip()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

onMounted(boot)
onBeforeUnmount(() => { stopPolling(); stopExportPolling() })
</script>

<template>
  <div class="app-shell">
    <AppSidebar :tab="tab" :matches="matches" :match="match" :health="health" :ready-models="readyModels" :pending-count="unresolvedClips.length" :clip-count="clips.length" @select-tab="tab = $event" @select-match="switchMatch" @create-match="showCreate = true" />
    <main class="main-shell">
      <header class="topbar"><div class="breadcrumb">比赛工作台 <ChevronRight :size="14" /><strong>{{ tab === 'overview' ? '总览' : tab === 'review' ? '复核' : '片段' }}</strong></div><div class="connection-state"><span :class="{ offline: !health }"></span>{{ health ? 'LOCAL ONLINE' : 'LOCAL OFFLINE' }}</div></header>
      <div class="page-content">
        <div v-if="loadError" class="error-banner"><CircleAlert :size="17" />{{ loadError }}<button class="icon-button" type="button" title="重试" @click="boot"><RefreshCw :size="16" /></button></div>
        <div v-if="actionError" class="error-banner"><CircleAlert :size="17" />{{ actionError }}<button class="icon-button" type="button" title="关闭" @click="actionError = ''"><X :size="16" /></button></div>
        <template v-if="match && workspace">
           <WorkspaceHeader :match="match" :clip-count="clips.length" :home-clip-count="homeClips.length" :away-clip-count="awayClips.length" :unresolved-count="unresolvedClips.length" :busy="busy" :polling="Boolean(pollingRunId)" :analysis-run="analysisRun" @reanalyze="reanalyzeAll" @import-clips="showImport = true" />
           <template v-if="tab === 'overview'"><TeamHighlightExports :home-team="homeTeam" :away-team="awayTeam" :exports="teamHighlights" :busy="busy" @generate="generateTeamHighlight" /><MatchOverview :home-team="homeTeam" :away-team="awayTeam" :home-clips="homeClips" :away-clips="awayClips" :unresolved-clips="unresolvedClips" @open-clip="openClip" @export-clip="exportClip" /></template>
          <ClipReviewQueue v-else-if="tab === 'review'" :clips="unresolvedClips" @open-clip="openClip" />
           <ClipLibrary v-else :clips="clips" :busy="busy" :polling="Boolean(pollingRunId)" @open-clip="openClip" @export-clip="exportClip" @reanalyze="reanalyzeAll" @import-clips="showImport = true" />
        </template>
        <div v-else-if="!loadError" class="professional-empty page-empty"><Activity :size="28" /><strong>尚未创建比赛</strong><span>先录入两队信息，再导入真实视频。</span></div>
      </div>
    </main>

    <CreateMatchModal v-if="showCreate" v-model:draft="createDraft" :busy="busy" @close="showCreate = false" @submit="createMatch" />
    <ImportClipsModal v-if="showImport" :files="pendingFiles" :busy="busy" @close="showImport = false" @select-files="pendingFiles = $event" @upload="upload" />
    <ClipPreviewModal v-if="activeClip" :clip="activeClip" :home-team="homeTeam" :away-team="awayTeam" :busy="busy" :review-clips="unresolvedClips" @close="closeClip" @confirm-team="confirmClipTeam" @save-team="reassignClipTeam" @start-reassign="startReassign" @cancel-reassign="cancelReassign" @delete-clip="deleteActiveClip" @export-clip="exportClip" @navigate="navigateReviewClip" />
  </div>
</template>
