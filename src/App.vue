<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleDot,
  ClipboardCheck,
  CloudUpload,
  Cpu,
  Download,
  Ellipsis,
  FileDown,
  FileVideo,
  Film,
  Gauge,
  LayoutDashboard,
  ListFilter,
  Pause,
  Play,
  Plus,
  RefreshCw,
  ScanLine,
  Search,
  Settings2,
  Sparkles,
  Target,
  Trash2,
  Upload,
  UsersRound,
  X,
} from 'lucide-vue-next'

type TabKey = 'overview' | 'review' | 'players' | 'clips'
type ClipStatus = 'ready' | 'review' | 'processing' | 'queued' | 'failed'
type EventStatus = 'pending' | 'confirmed' | 'ignored'
type EventType = '投篮' | '命中' | '三分' | '篮板' | '助攻' | '抢断' | '盖帽' | '失误' | '犯规'

interface Clip {
  id: string
  name: string
  sequence: number
  duration: string
  status: ClipStatus
  confidence: number
  capturedAt: string
  fileSize: string
  teamHint: 'home' | 'away' | 'both'
  accent: string
  previewUrl?: string
}

interface Player {
  id: string
  code: string
  name: string
  team: 'home' | 'away'
  teamName: string
  number: string
  identityType: 'number' | 'temporary'
  color: string
  confidence: number
  tracks: number
  status: 'confirmed' | 'candidate'
}

interface EventRecord {
  id: string
  clipId: string
  time: string
  seconds: number
  type: EventType
  description: string
  playerId: string
  team: 'home' | 'away'
  confidence: number
  status: EventStatus
  points: number
}

interface StatRow {
  playerId: string
  name: string
  teamName: string
  team: 'home' | 'away'
  pts: number
  fg: string
  three: string
  reb: number
  ast: number
  stl: number
  turnovers: number
  trend: 'up' | 'down' | 'flat'
}

const navItems: Array<{ key: TabKey; label: string; meta: string; icon: typeof LayoutDashboard }> = [
  { key: 'overview', label: '比赛总览', meta: '01', icon: LayoutDashboard },
  { key: 'review', label: '复核队列', meta: '12', icon: ClipboardCheck },
  { key: 'players', label: '球员身份', meta: '10', icon: UsersRound },
  { key: 'clips', label: '片段库', meta: '300', icon: Film },
]

const baseClips: Clip[] = [
  {
    id: 'clip-031',
    name: 'IMG_2031.MOV',
    sequence: 31,
    duration: '00:10',
    status: 'review',
    confidence: 0.94,
    capturedAt: '17:42:18',
    fileSize: '38.4 MB',
    teamHint: 'home',
    accent: '#d7ff4d',
  },
  {
    id: 'clip-032',
    name: 'IMG_2032.MOV',
    sequence: 32,
    duration: '00:10',
    status: 'review',
    confidence: 0.89,
    capturedAt: '17:42:31',
    fileSize: '40.1 MB',
    teamHint: 'both',
    accent: '#ff765c',
  },
  {
    id: 'clip-033',
    name: 'IMG_2033.MOV',
    sequence: 33,
    duration: '00:10',
    status: 'ready',
    confidence: 0.97,
    capturedAt: '17:42:44',
    fileSize: '35.9 MB',
    teamHint: 'away',
    accent: '#8bdcff',
  },
  {
    id: 'clip-034',
    name: 'IMG_2034.MOV',
    sequence: 34,
    duration: '00:10',
    status: 'ready',
    confidence: 0.92,
    capturedAt: '17:42:57',
    fileSize: '42.8 MB',
    teamHint: 'home',
    accent: '#d7ff4d',
  },
  {
    id: 'clip-035',
    name: 'IMG_2035.MOV',
    sequence: 35,
    duration: '00:10',
    status: 'review',
    confidence: 0.78,
    capturedAt: '17:43:10',
    fileSize: '37.7 MB',
    teamHint: 'both',
    accent: '#ffc766',
  },
  {
    id: 'clip-036',
    name: 'IMG_2036.MOV',
    sequence: 36,
    duration: '00:10',
    status: 'ready',
    confidence: 0.95,
    capturedAt: '17:43:23',
    fileSize: '39.6 MB',
    teamHint: 'away',
    accent: '#8bdcff',
  },
  {
    id: 'clip-037',
    name: 'IMG_2037.MOV',
    sequence: 37,
    duration: '00:10',
    status: 'ready',
    confidence: 0.91,
    capturedAt: '17:43:36',
    fileSize: '41.3 MB',
    teamHint: 'home',
    accent: '#d7ff4d',
  },
  {
    id: 'clip-038',
    name: 'IMG_2038.MOV',
    sequence: 38,
    duration: '00:10',
    status: 'failed',
    confidence: 0,
    capturedAt: '17:43:49',
    fileSize: '44.5 MB',
    teamHint: 'both',
    accent: '#ff765c',
  },
]

const players = ref<Player[]>([
  {
    id: 'p-home-12',
    code: 'H-12',
    name: '林子昂',
    team: 'home',
    teamName: '东岸猛禽',
    number: '12',
    identityType: 'number',
    color: '#d7ff4d',
    confidence: 0.98,
    tracks: 38,
    status: 'confirmed',
  },
  {
    id: 'p-home-t01',
    code: 'H-T01',
    name: '临时球员 01',
    team: 'home',
    teamName: '东岸猛禽',
    number: 'T01',
    identityType: 'temporary',
    color: '#b8dd62',
    confidence: 0.73,
    tracks: 24,
    status: 'candidate',
  },
  {
    id: 'p-home-07',
    code: 'H-07',
    name: '周牧',
    team: 'home',
    teamName: '东岸猛禽',
    number: '07',
    identityType: 'number',
    color: '#9bd445',
    confidence: 0.91,
    tracks: 31,
    status: 'confirmed',
  },
  {
    id: 'p-away-23',
    code: 'A-23',
    name: '陈灼',
    team: 'away',
    teamName: '北城飞行',
    number: '23',
    identityType: 'number',
    color: '#ff765c',
    confidence: 0.96,
    tracks: 42,
    status: 'confirmed',
  },
  {
    id: 'p-away-t02',
    code: 'A-T02',
    name: '临时球员 02',
    team: 'away',
    teamName: '北城飞行',
    number: 'T02',
    identityType: 'temporary',
    color: '#ff9b63',
    confidence: 0.68,
    tracks: 19,
    status: 'candidate',
  },
  {
    id: 'p-away-05',
    code: 'A-05',
    name: '魏启明',
    team: 'away',
    teamName: '北城飞行',
    number: '05',
    identityType: 'number',
    color: '#ff846d',
    confidence: 0.88,
    tracks: 27,
    status: 'confirmed',
  },
])

const clips = ref<Clip[]>(baseClips)
const events = ref<EventRecord[]>([
  {
    id: 'event-101',
    clipId: 'clip-031',
    time: '00:03.2',
    seconds: 3.2,
    type: '投篮',
    description: '右侧 45° 起跳，篮筐未完整入镜',
    playerId: 'p-home-12',
    team: 'home',
    confidence: 0.92,
    status: 'pending',
    points: 0,
  },
  {
    id: 'event-102',
    clipId: 'clip-031',
    time: '00:05.8',
    seconds: 5.8,
    type: '命中',
    description: '球网动作和回防动作匹配',
    playerId: 'p-home-12',
    team: 'home',
    confidence: 0.87,
    status: 'pending',
    points: 2,
  },
  {
    id: 'event-103',
    clipId: 'clip-031',
    time: '00:07.4',
    seconds: 7.4,
    type: '篮板',
    description: '禁区内二次争抢，归属需确认',
    playerId: 'p-home-t01',
    team: 'home',
    confidence: 0.61,
    status: 'pending',
    points: 0,
  },
  {
    id: 'event-104',
    clipId: 'clip-032',
    time: '00:04.1',
    seconds: 4.1,
    type: '助攻',
    description: '传球后 1.6 秒内完成出手',
    playerId: 'p-home-07',
    team: 'home',
    confidence: 0.74,
    status: 'pending',
    points: 0,
  },
  {
    id: 'event-105',
    clipId: 'clip-032',
    time: '00:06.9',
    seconds: 6.9,
    type: '三分',
    description: '弧顶出手，距离模型建议为三分',
    playerId: 'p-away-23',
    team: 'away',
    confidence: 0.83,
    status: 'confirmed',
    points: 3,
  },
  {
    id: 'event-106',
    clipId: 'clip-033',
    time: '00:02.6',
    seconds: 2.6,
    type: '抢断',
    description: '前场断球后直接推进',
    playerId: 'p-away-05',
    team: 'away',
    confidence: 0.9,
    status: 'confirmed',
    points: 0,
  },
])

const baseStatRows: StatRow[] = [
  {
    playerId: 'p-home-12',
    name: '林子昂',
    teamName: '东岸猛禽',
    team: 'home',
    pts: 14,
    fg: '5 / 9',
    three: '2 / 4',
    reb: 5,
    ast: 3,
    stl: 1,
    turnovers: 1,
    trend: 'up',
  },
  {
    playerId: 'p-away-23',
    name: '陈灼',
    teamName: '北城飞行',
    team: 'away',
    pts: 11,
    fg: '4 / 8',
    three: '3 / 5',
    reb: 2,
    ast: 4,
    stl: 2,
    turnovers: 2,
    trend: 'up',
  },
  {
    playerId: 'p-home-07',
    name: '周牧',
    teamName: '东岸猛禽',
    team: 'home',
    pts: 8,
    fg: '3 / 7',
    three: '0 / 2',
    reb: 7,
    ast: 2,
    stl: 0,
    turnovers: 1,
    trend: 'flat',
  },
  {
    playerId: 'p-away-05',
    name: '魏启明',
    teamName: '北城飞行',
    team: 'away',
    pts: 6,
    fg: '2 / 6',
    three: '1 / 3',
    reb: 4,
    ast: 1,
    stl: 1,
    turnovers: 3,
    trend: 'down',
  },
]

const activeTab = ref<TabKey>('overview')
const activeClipId = ref('clip-031')
const statsTab = ref<'players' | 'teams'>('players')
const clipSearch = ref('')
const clipFilter = ref<'all' | ClipStatus>('all')
const isAnalyzing = ref(false)
const analysisProgress = ref(0)
const processedClipCount = ref(284)
const totalClipCount = ref(300)
const currentSeconds = ref(7.4)
const isPlaying = ref(false)
const playbackRate = ref(1)
const videoRef = ref<HTMLVideoElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<File[]>([])
const showImport = ref(false)
const showPlayerEditor = ref(false)
const showPlayerDetail = ref(false)
const selectedPlayerId = ref('p-home-12')
const isDragging = ref(false)
const toastMessage = ref('')
const toastTimer = ref<number | undefined>()
const analysisTimer = ref<number | undefined>()
const objectUrls = ref<string[]>([])
const engineMode = ref('CUDA 已就绪')
const engineDetail = ref('CPU fallback 可用')
const backendOnline = ref(false)
const playerDraft = reactive<Player>({ ...players.value[0] })

const fallbackClip: Clip = baseClips[0]
const selectedClip = computed<Clip>(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? clips.value[0] ?? fallbackClip)
const selectedEvents = computed(() => events.value.filter((event) => event.clipId === selectedClip.value.id))
const selectedPlayer = computed(() => players.value.find((player) => player.id === selectedPlayerId.value) ?? players.value[0])
const selectedPlayerStats = computed(() => statRows.value.find((row) => row.playerId === selectedPlayerId.value) ?? statRows.value[0])
const selectedPlayerScoringEvents = computed(() => events.value.filter((event) => event.playerId === selectedPlayerId.value && event.points > 0 && event.status !== 'ignored'))
const pendingEventCount = computed(() => events.value.filter((event) => event.status === 'pending').length)
const confirmedEventCount = computed(() => events.value.filter((event) => event.status === 'confirmed').length)
const analyzedProgress = computed(() => Math.round((processedClipCount.value / totalClipCount.value) * 100))
const viewTitle = computed(() => {
  const titles: Record<TabKey, string> = {
    overview: '比赛总览',
    review: '复核队列',
    players: '球员身份',
    clips: '片段库',
  }
  return titles[activeTab.value]
})
const filteredClips = computed(() => {
  const query = clipSearch.value.trim().toLowerCase()
  return clips.value.filter((clip) => {
    const matchesQuery = !query || clip.name.toLowerCase().includes(query) || String(clip.sequence).includes(query)
    const matchesFilter = clipFilter.value === 'all' || clip.status === clipFilter.value
    return matchesQuery && matchesFilter
  })
})
const statRows = computed(() => baseStatRows)
const pendingFileSize = computed(() => {
  const bytes = pendingFiles.value.reduce((sum, file) => sum + file.size, 0)
  if (!bytes) return '0 MB'
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
})
const teamTotals = computed(() => [
  {
    team: 'home' as const,
    name: '东岸猛禽',
    score: 42,
    fg: '17 / 34',
    three: '5 / 14',
    reb: 21,
    ast: 10,
  },
  {
    team: 'away' as const,
    name: '北城飞行',
    score: 38,
    fg: '15 / 36',
    three: '6 / 18',
    reb: 19,
    ast: 12,
  },
])

function showToast(message: string) {
  toastMessage.value = message
  if (toastTimer.value) window.clearTimeout(toastTimer.value)
  toastTimer.value = window.setTimeout(() => {
    toastMessage.value = ''
  }, 2800)
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json() as Promise<T>
}

async function checkBackend() {
  try {
    const health = await apiRequest<{ cuda: boolean; ffmpeg: boolean; mode: string }>('/api/health')
    backendOnline.value = true
    engineMode.value = health.cuda ? 'CUDA 已就绪' : 'CPU fallback'
    engineDetail.value = health.ffmpeg ? 'FFmpeg 媒体处理可用' : '未检测到 FFmpeg'
  } catch {
    backendOnline.value = false
    engineMode.value = '演示模式'
    engineDetail.value = '启动本地服务后可接入分析'
  }
}

function setTab(tab: TabKey) {
  activeTab.value = tab
}

function selectClip(clip: Clip, openReview = false) {
  activeClipId.value = clip.id
  currentSeconds.value = clip.id === 'clip-031' ? 7.4 : 3.2
  isPlaying.value = false
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.currentTime = currentSeconds.value
  }
  if (openReview) activeTab.value = 'review'
}

function toggleVideo() {
  if (videoRef.value) {
    if (videoRef.value.paused) {
      void videoRef.value.play()
    } else {
      videoRef.value.pause()
    }
  } else {
    isPlaying.value = !isPlaying.value
  }
}

function updatePlaying(value: boolean) {
  isPlaying.value = value
}

function updateCurrentTime(event: Event) {
  const target = event.target as HTMLVideoElement
  currentSeconds.value = target.currentTime
}

function seekVideo() {
  if (videoRef.value) videoRef.value.currentTime = currentSeconds.value
}

function changePlaybackRate(rate: number) {
  playbackRate.value = rate
  if (videoRef.value) videoRef.value.playbackRate = rate
}

function formatTime(seconds: number) {
  const wholeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(wholeSeconds / 60)
  const remainder = wholeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function clipStatusLabel(status: ClipStatus) {
  const labels: Record<ClipStatus, string> = {
    ready: '已完成',
    review: '待复核',
    processing: '分析中',
    queued: '排队中',
    failed: '失败',
  }
  return labels[status]
}

function eventStatusLabel(status: EventStatus) {
  const labels: Record<EventStatus, string> = {
    pending: '待确认',
    confirmed: '已确认',
    ignored: '已忽略',
  }
  return labels[status]
}

function getPlayer(playerId: string) {
  return players.value.find((player) => player.id === playerId)
}

function getPlayerName(playerId: string) {
  return getPlayer(playerId)?.name ?? '未分配球员'
}

function getTeamName(team: 'home' | 'away') {
  return team === 'home' ? '东岸猛禽' : '北城飞行'
}

function confirmEvent(eventId: string) {
  const target = events.value.find((event) => event.id === eventId)
  if (!target) return
  target.status = 'confirmed'
  showToast(`${target.type}已计入统计`)
}

function ignoreEvent(eventId: string) {
  const target = events.value.find((event) => event.id === eventId)
  if (!target) return
  target.status = 'ignored'
  showToast('候选事件已忽略')
}

function confirmAllEvents() {
  const targets = events.value.filter((event) => event.clipId === selectedClip.value.id && event.status === 'pending')
  targets.forEach((event) => {
    event.status = 'confirmed'
  })
  showToast(targets.length ? `${targets.length} 个事件已确认` : '当前片段没有待确认事件')
}

function updateEventPlayer(event: EventRecord) {
  const player = getPlayer(event.playerId)
  if (player) event.team = player.team
  showToast('球员归属已更新')
}

function addManualEvent() {
  const defaultPlayer = players.value[0]
  const newEvent: EventRecord = {
    id: `event-manual-${Date.now()}`,
    clipId: selectedClip.value.id,
    time: formatTime(currentSeconds.value),
    seconds: currentSeconds.value,
    type: '投篮',
    description: '人工补录事件',
    playerId: defaultPlayer.id,
    team: defaultPlayer.team,
    confidence: 1,
    status: 'confirmed',
    points: 0,
  }
  events.value.unshift(newEvent)
  showToast('已添加人工事件')
}

function openPlayerEditor(player: Player) {
  Object.assign(playerDraft, player)
  showPlayerEditor.value = true
}

function openPlayerDetail(playerId: string) {
  selectedPlayerId.value = playerId
  showPlayerDetail.value = true
}

function openScoringEvent(event: EventRecord) {
  const clip = clips.value.find((item) => item.id === event.clipId)
  if (!clip) {
    showToast('源片段尚未在当前片段库中')
    return
  }
  showPlayerDetail.value = false
  selectClip(clip, true)
  currentSeconds.value = event.seconds
  seekVideo()
}

function savePlayer() {
  const index = players.value.findIndex((player) => player.id === playerDraft.id)
  if (index === -1) return
  players.value[index] = { ...playerDraft, code: `${playerDraft.team === 'home' ? 'H' : 'A'}-${playerDraft.number || playerDraft.code.split('-').at(-1)}` }
  events.value.forEach((event) => {
    if (event.playerId === playerDraft.id) event.team = playerDraft.team
  })
  showPlayerEditor.value = false
  showToast('球员身份已保存')
}

function triggerFilePicker() {
  fileInput.value?.click()
}

function addPendingFiles(files: File[]) {
  const videoFiles = files.filter((file) => file.type.startsWith('video/') || /\.(mp4|mov|m4v|webm)$/i.test(file.name))
  if (!videoFiles.length) {
    showToast('请选择 MP4、MOV、M4V 或 WebM 视频')
    return
  }
  pendingFiles.value = [...pendingFiles.value, ...videoFiles]
}

function onFileInput(event: Event) {
  const target = event.target as HTMLInputElement
  addPendingFiles(Array.from(target.files ?? []))
  target.value = ''
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  addPendingFiles(Array.from(event.dataTransfer?.files ?? []))
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1)
}

async function importPendingFiles() {
  if (!pendingFiles.value.length) {
    showToast('先选择要导入的片段')
    return
  }
  const filesToUpload = [...pendingFiles.value]
  const startSequence = totalClipCount.value + 1
  try {
    const formData = new FormData()
    filesToUpload.forEach((file) => formData.append('files', file))
    const result = await apiRequest<{ accepted: Array<{ id: string; name: string; previewUrl: string; sizeBytes: number; status: ClipStatus }>; skipped: string[] }>('/api/matches/friendly-game-04/clips', { method: 'POST', body: formData })
    if (result.accepted.length) {
      clips.value = [
        ...result.accepted.map((clip, index): Clip => ({
          id: clip.id,
          name: clip.name,
          sequence: startSequence + index,
          duration: '待读取',
          status: clip.status,
          confidence: 0,
          capturedAt: '刚刚导入',
          fileSize: `${(clip.sizeBytes / 1024 / 1024).toFixed(1)} MB`,
          teamHint: 'both',
          accent: index % 2 === 0 ? '#d7ff4d' : '#ff765c',
          previewUrl: clip.previewUrl,
        })),
        ...clips.value,
      ]
      totalClipCount.value += result.accepted.length
      activeClipId.value = result.accepted[0].id
    }
    pendingFiles.value = []
    showImport.value = false
    activeTab.value = 'clips'
    showToast(`${result.accepted.length} 个视频已上传到本地分析队列${result.skipped.length ? `，跳过 ${result.skipped.length} 个` : ''}`)
    void startAnalysis()
    return
  } catch {
    showToast('本地分析服务未启动，已切换为浏览器演示导入')
  }
  const imported = pendingFiles.value.map((file, index): Clip => {
    const previewUrl = URL.createObjectURL(file)
    objectUrls.value.push(previewUrl)
    return {
      id: `local-${Date.now()}-${index}`,
      name: file.name,
      sequence: startSequence + index,
      duration: '待读取',
      status: 'queued',
      confidence: 0,
      capturedAt: '刚刚导入',
      fileSize: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
      teamHint: 'both',
      accent: index % 2 === 0 ? '#d7ff4d' : '#ff765c',
      previewUrl,
    }
  })
  clips.value = [...imported, ...clips.value]
  totalClipCount.value += imported.length
  activeClipId.value = imported[0].id
  pendingFiles.value = []
  showImport.value = false
  activeTab.value = 'clips'
  showToast(`${imported.length} 个视频已加入分析队列`)
  void startAnalysis()
}

async function startAnalysis() {
  if (isAnalyzing.value) return
  const targets = clips.value.filter((clip) => clip.status === 'queued' || clip.status === 'failed')
  if (!targets.length) {
    showToast('当前没有等待分析的片段')
    return
  }
  try {
    const task = await apiRequest<{ id: string; total: number }>('/api/matches/friendly-game-04/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clip_ids: targets.map((clip) => clip.id), device: 'auto' }),
    })
    if (task.total) {
      isAnalyzing.value = true
      analysisProgress.value = 0
      targets.forEach((clip) => { clip.status = 'processing' })
      const poll = window.setInterval(async () => {
        try {
          const current = await apiRequest<{ status: string; progress: number }>('/api/tasks/' + task.id)
          analysisProgress.value = current.progress
          if (current.status === 'completed') {
            window.clearInterval(poll)
            targets.forEach((clip) => { clip.status = 'review'; clip.confidence = 0.82 })
            isAnalyzing.value = false
            showToast('本地 AI 分析完成，候选事件已进入复核队列')
          }
        } catch {
          window.clearInterval(poll)
          isAnalyzing.value = false
          showToast('分析任务状态读取失败')
        }
      }, 500)
      return
    }
  } catch {
    showToast('本地服务不可用，使用前端演示队列')
  }
  isAnalyzing.value = true
  analysisProgress.value = 0
  targets.forEach((clip) => {
    clip.status = 'processing'
  })
  let tick = 0
  analysisTimer.value = window.setInterval(() => {
    tick += 1
    analysisProgress.value = Math.min(100, tick * 12.5)
    const completed = Math.min(targets.length, Math.floor((tick / 8) * targets.length))
    targets.forEach((clip, index) => {
      if (index < completed) {
        clip.status = 'review'
        clip.confidence = 0.76 + (index % 4) * 0.05
      }
    })
    processedClipCount.value = Math.min(totalClipCount.value, processedClipCount.value + (tick % 2 === 0 ? 1 : 0))
    if (tick >= 8) {
      if (analysisTimer.value) window.clearInterval(analysisTimer.value)
      analysisTimer.value = undefined
      isAnalyzing.value = false
      analysisProgress.value = 100
      targets.forEach((clip) => {
        clip.status = 'review'
        if (!clip.confidence) clip.confidence = 0.82
      })
      processedClipCount.value = Math.min(totalClipCount.value, processedClipCount.value + targets.length)
      showToast('AI 初判完成，候选事件已进入复核队列')
    }
  }, 650)
}

function retryClip(clip: Clip) {
  clip.status = 'queued'
  showToast(`${clip.name} 已重新排队`)
}

function exportStats() {
  const header = ['球员', '球队', '得分', '投篮', '三分', '篮板', '助攻', '抢断', '失误']
  const rows = statRows.value.map((row) => [row.name, row.teamName, row.pts, row.fg, row.three, row.reb, row.ast, row.stl, row.turnovers])
  const csv = [header, ...rows].map((row) => row.join(',')).join('\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'courttrace-友谊赛-04-统计.csv'
  link.click()
  URL.revokeObjectURL(url)
  showToast('统计 CSV 已导出')
}

onBeforeUnmount(() => {
  if (analysisTimer.value) window.clearInterval(analysisTimer.value)
  if (toastTimer.value) window.clearTimeout(toastTimer.value)
  objectUrls.value.forEach((url) => URL.revokeObjectURL(url))
})

onMounted(checkBackend)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup">
        <div class="brand-mark"><ScanLine :size="20" :stroke-width="2.4" /></div>
        <div>
          <strong>COURTTRACE</strong>
          <span>LOCAL SCOUTING DESK</span>
        </div>
      </div>

      <div class="sidebar-section-label">当前比赛</div>
      <button class="match-switcher" type="button" title="切换比赛">
        <span class="match-badge">04</span>
        <span class="match-copy">
          <strong>友谊赛 · 第 04 场</strong>
          <small>08.28 / 周五 · 友谊赛场</small>
        </span>
        <ChevronDown :size="16" />
      </button>

      <nav class="primary-nav" aria-label="主导航">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeTab === item.key }"
          type="button"
          @click="setTab(item.key)"
        >
          <component :is="item.icon" :size="18" :stroke-width="activeTab === item.key ? 2.4 : 1.8" />
          <span>{{ item.label }}</span>
          <em>{{ item.meta }}</em>
        </button>
      </nav>

      <div class="sidebar-spacer"></div>

      <div class="engine-card">
        <div class="engine-card-top">
          <span class="live-dot"></span>
          <span>本地推理引擎</span>
          <Cpu :size="15" />
        </div>
        <strong>{{ engineMode }}</strong>
        <div class="engine-meter"><span style="width: 72%"></span></div>
        <small>{{ backendOnline ? engineDetail : engineDetail }}</small>
      </div>

      <div class="sidebar-footer">
        <button class="footer-action" type="button" title="设置">
          <Settings2 :size="17" />
          <span>工作区设置</span>
        </button>
        <button class="footer-action" type="button" title="帮助">
          <CircleAlert :size="17" />
          <span>分析状态</span>
        </button>
      </div>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">
          <span>比赛工作台</span>
          <ChevronRight :size="14" />
          <strong>{{ viewTitle }}</strong>
        </div>
        <div class="topbar-actions">
          <div class="connection-state"><span :class="{ offline: !backendOnline }"></span>LOCAL / {{ backendOnline ? engineMode.replace(' 已就绪', '').toUpperCase() : 'DEMO' }}</div>
          <button class="icon-button" type="button" title="通知"><Bell :size="18" /></button>
          <button class="icon-button" type="button" title="更多"><Ellipsis :size="19" /></button>
          <div class="avatar">ZG</div>
        </div>
      </header>

      <div class="page-content">
        <section class="page-heading">
          <div>
            <div class="eyebrow"><span class="eyebrow-line"></span>FRIDAY LEAGUE / GAME 04</div>
            <h1>东岸猛禽 <span>vs</span> 北城飞行</h1>
            <p>视频统计台 <b>·</b> 片段覆盖 47:12 <b>·</b> 最后同步 17:48:09</p>
          </div>
          <div class="heading-actions">
            <button class="button button-quiet" type="button" @click="exportStats">
              <Download :size="16" />
              导出统计
            </button>
            <button class="button button-acid" type="button" @click="showImport = true">
              <CloudUpload :size="17" />
              导入片段
            </button>
          </div>
        </section>

        <section class="metric-strip" aria-label="比赛处理概览">
          <div class="metric-cell metric-primary">
            <div class="metric-label"><span class="metric-index">01</span>已接收片段</div>
            <div class="metric-value">{{ processedClipCount }}<small>/ {{ totalClipCount }}</small></div>
            <div class="metric-subline"><span class="positive"><ArrowUpRight :size="13" /> 12%</span> 较上场</div>
          </div>
          <div class="metric-cell">
            <div class="metric-label"><span class="metric-index">02</span>已确认事件</div>
            <div class="metric-value">{{ confirmedEventCount }}<small> 条</small></div>
            <div class="metric-subline"><span class="warning">{{ pendingEventCount }} 条</span> 等待复核</div>
          </div>
          <div class="metric-cell">
            <div class="metric-label"><span class="metric-index">03</span>片段覆盖</div>
            <div class="metric-value">47<small>分 12 秒</small></div>
            <div class="metric-subline"><span class="positive">+ 06:41</span> 有效视频</div>
          </div>
          <div class="metric-cell metric-engine">
            <div class="metric-label"><span class="metric-index">04</span>处理状态</div>
            <div class="metric-engine-line"><span class="status-orbit"></span><strong>{{ isAnalyzing ? 'AI 分析中' : '可以开始复核' }}</strong></div>
            <div class="metric-subline">{{ isAnalyzing ? `${Math.round(analysisProgress)}% · 本地队列` : 'AI 初判已完成 94%' }}</div>
          </div>
        </section>

        <template v-if="activeTab === 'overview' || activeTab === 'review'">
          <div class="workspace-grid" :class="{ 'workspace-grid-focus': activeTab === 'review' }">
            <section class="tool-panel review-workspace">
              <div class="panel-header">
                <div>
                  <div class="panel-kicker"><span class="accent-marker"></span>{{ activeTab === 'review' ? 'AI 复核队列' : '当前片段' }}</div>
                  <h2>{{ selectedClip.name }} <span>/ FRAME {{ String(selectedClip.sequence).padStart(3, '0') }}</span></h2>
                </div>
                <div class="panel-header-actions">
                  <span class="confidence-chip"><Sparkles :size="13" /> AI {{ Math.round(selectedClip.confidence * 100) }}%</span>
                  <button class="icon-button dark" type="button" title="片段选项"><Ellipsis :size="18" /></button>
                </div>
              </div>

              <div class="review-layout">
                <div class="video-column">
                  <div class="video-stage">
                    <video
                      v-if="selectedClip.previewUrl"
                      ref="videoRef"
                      class="source-video"
                      :src="selectedClip.previewUrl"
                      playsinline
                      @play="updatePlaying(true)"
                      @pause="updatePlaying(false)"
                      @timeupdate="updateCurrentTime"
                    ></video>
                    <div v-else class="court-scene" :class="{ playing: isPlaying }">
                      <div class="court-grain"></div>
                      <div class="court-line court-line-mid"></div>
                      <div class="court-line court-line-key court-line-key-left"></div>
                      <div class="court-line court-line-key court-line-key-right"></div>
                      <div class="court-arc court-arc-left"></div>
                      <div class="court-arc court-arc-right"></div>
                      <div class="court-hoop court-hoop-left"><span></span></div>
                      <div class="court-hoop court-hoop-right"><span></span></div>
                      <div
                        v-for="(player, index) in players"
                        :key="player.id"
                        class="court-player"
                        :class="`court-player--${index + 1}`"
                        :style="{ '--player-color': player.color }"
                      >
                        <span>{{ player.number.replace('T', '') }}</span>
                      </div>
                      <div class="ball-track"><i></i><i></i><i></i><b></b></div>
                      <div class="scene-tag scene-tag-top"><CircleDot :size="12" /> AI TRACKING / 06</div>
                      <div class="scene-tag scene-tag-bottom">CAM 01 <span>·</span> GIMBAL FOLLOW</div>
                      <div class="scene-frame-label">FRAME {{ String(selectedClip.sequence).padStart(3, '0') }} <span>00:07.4</span></div>
                      <div class="scene-focus-ring"></div>
                    </div>
                    <div class="video-overlay-top">
                      <span class="rec-dot"></span> SOURCE / {{ selectedClip.previewUrl ? 'LOCAL FILE' : 'DEMO FRAME' }}
                    </div>
                    <div class="video-overlay-bottom">{{ selectedClip.capturedAt }} <span>·</span> {{ selectedClip.duration }}</div>
                  </div>

                  <div class="video-control-row">
                    <button class="play-button" type="button" :title="isPlaying ? '暂停' : '播放'" @click="toggleVideo">
                      <Pause v-if="isPlaying" :size="18" fill="currentColor" />
                      <Play v-else :size="18" fill="currentColor" />
                    </button>
                    <div class="time-readout"><strong>{{ formatTime(currentSeconds) }}</strong><span>/ 00:10</span></div>
                    <div class="scrubber-wrap">
                      <input v-model.number="currentSeconds" class="scrubber" type="range" min="0" max="10" step="0.1" @input="seekVideo" />
                      <div class="scrubber-markers">
                        <span v-for="event in selectedEvents" :key="event.id" :style="{ left: `${(event.seconds / 10) * 100}%` }" :class="`marker-${event.status}`" :title="event.type"></span>
                      </div>
                    </div>
                    <div class="speed-control">
                      <button v-for="rate in [0.5, 1, 1.5]" :key="rate" type="button" :class="{ selected: playbackRate === rate }" @click="changePlaybackRate(rate)">{{ rate }}x</button>
                    </div>
                    <button class="icon-button dark small" type="button" title="全屏预览"><Gauge :size="16" /></button>
                  </div>
                  <div class="clip-context-row">
                    <span><Film :size="14" /> 云台跟拍 · 1080p / 30fps</span>
                    <span><Target :size="14" /> {{ selectedEvents.length }} 个候选事件</span>
                  </div>
                </div>

                <aside class="event-review-column">
                  <div class="event-column-heading">
                    <div>
                      <span class="panel-kicker">候选事件</span>
                      <h3>{{ selectedEvents.length }} <small>条检测结果</small></h3>
                    </div>
                    <button class="text-button" type="button" @click="confirmAllEvents"><CheckCheck :size="15" /> 全部确认</button>
                  </div>

                  <div class="event-list">
                    <article v-for="event in selectedEvents" :key="event.id" class="event-item" :class="[`event-${event.status}`, `team-${event.team}`]">
                      <div class="event-item-top">
                        <div class="event-type-mark"><CircleDot :size="15" /></div>
                        <div class="event-main-copy">
                          <div class="event-title-line"><strong>{{ event.type }}</strong><span>{{ event.time }}</span></div>
                          <p>{{ event.description }}</p>
                        </div>
                        <span class="event-confidence">{{ Math.round(event.confidence * 100) }}%</span>
                      </div>
                      <div class="event-item-bottom">
                        <label class="player-select">
                          <span class="player-swatch" :style="{ background: getPlayer(event.playerId)?.color ?? '#78827c' }"></span>
                          <select v-model="event.playerId" aria-label="选择事件球员" @change="updateEventPlayer(event)">
                            <option v-for="player in players" :key="player.id" :value="player.id">{{ player.name }} · {{ player.code }}</option>
                          </select>
                          <ChevronDown :size="13" />
                        </label>
                        <div class="event-actions">
                          <span class="event-status-label">{{ eventStatusLabel(event.status) }}</span>
                          <button v-if="event.status === 'pending'" class="mini-action confirm" type="button" title="确认事件" @click="confirmEvent(event.id)"><Check :size="14" /></button>
                          <button v-if="event.status === 'pending'" class="mini-action ignore" type="button" title="忽略事件" @click="ignoreEvent(event.id)"><X :size="14" /></button>
                          <button v-else class="mini-action muted" type="button" title="恢复待确认" @click="event.status = 'pending'"><RefreshCw :size="13" /></button>
                        </div>
                      </div>
                    </article>
                  </div>

                  <button class="manual-event-button" type="button" @click="addManualEvent"><Plus :size="16" /> 手动记一笔</button>
                  <div class="review-note"><CircleAlert :size="14" /><span>统计仅包含已确认事件，未覆盖内容不会计为 0。</span></div>
                </aside>
              </div>
            </section>

            <aside v-if="activeTab === 'overview'" class="overview-rail">
              <section class="tool-panel identity-panel">
                <div class="rail-heading">
                  <div>
                    <span class="panel-kicker">球员身份</span>
                    <h3>AI TRACKS <span>06</span></h3>
                  </div>
                  <button class="icon-button dark small" type="button" title="身份设置" @click="setTab('players')"><Settings2 :size="15" /></button>
                </div>
                <div class="identity-list">
                  <button v-for="player in players" :key="player.id" class="identity-row" type="button" @click="openPlayerEditor(player)">
                    <span class="player-badge" :style="{ '--badge-color': player.color }">{{ player.number }}</span>
                    <span class="identity-copy"><strong>{{ player.name }}</strong><small>{{ player.teamName }} · {{ player.tracks }} tracks</small></span>
                    <span class="identity-confidence" :class="{ candidate: player.status === 'candidate' }">{{ Math.round(player.confidence * 100) }}%</span>
                    <ChevronRight :size="14" class="identity-arrow" />
                  </button>
                </div>
                <button class="rail-link" type="button" @click="setTab('players')">查看全部球员 <ArrowDownRight :size="14" /></button>
              </section>

              <section class="tool-panel queue-panel">
                <div class="rail-heading">
                  <div>
                    <span class="panel-kicker">批处理进度</span>
                    <h3>{{ isAnalyzing ? '分析进行中' : '复核准备度' }}</h3>
                  </div>
                  <span class="queue-percent">{{ isAnalyzing ? `${Math.round(analysisProgress)}%` : `${analyzedProgress}%` }}</span>
                </div>
                <div class="progress-ring" :style="{ '--progress': `${isAnalyzing ? analysisProgress : analyzedProgress}%` }"><div><strong>{{ isAnalyzing ? Math.round(analysisProgress) : analyzedProgress }}<small>%</small></strong><span>READY</span></div></div>
                <div class="queue-stats"><span><b>{{ processedClipCount }}</b> 已分析</span><span><b>{{ pendingEventCount }}</b> 待复核</span></div>
                <div class="analysis-live-state"><Sparkles :size="15" /><span>{{ isAnalyzing ? 'AI 正在处理...' : '导入后自动分析' }}</span><b>{{ isAnalyzing ? `${Math.round(analysisProgress)}%` : 'AUTO' }}</b></div>
              </section>
            </aside>
          </div>

          <section v-if="activeTab === 'overview'" class="tool-panel stats-panel">
            <div class="panel-header stats-header">
              <div>
                <div class="panel-kicker"><span class="accent-marker coral"></span>比赛数据</div>
                <h2>场上统计 <span>/ CONFIRMED ONLY</span></h2>
              </div>
              <div class="stats-header-actions">
                <div class="segmented-control">
                  <button type="button" :class="{ selected: statsTab === 'players' }" @click="statsTab = 'players'">球员</button>
                  <button type="button" :class="{ selected: statsTab === 'teams' }" @click="statsTab = 'teams'">球队</button>
                </div>
                <button class="icon-button dark" type="button" title="筛选"><ListFilter :size="17" /></button>
                <button class="button button-quiet compact" type="button" @click="exportStats"><FileDown :size="15" /> CSV</button>
              </div>
            </div>

            <div v-if="statsTab === 'players'" class="table-wrap">
              <table class="stats-table">
                <thead>
                  <tr><th class="player-col">球员</th><th>得分</th><th>投篮</th><th>三分</th><th>篮板</th><th>助攻</th><th>抢断</th><th>失误</th><th>趋势</th></tr>
                </thead>
                <tbody>
                  <tr v-for="row in statRows" :key="row.playerId">
                    <td class="player-col"><button class="player-cell-button" type="button" @click="openPlayerDetail(row.playerId)"><span class="table-avatar" :class="`table-avatar-${row.team}`">{{ row.name.slice(0, 1) }}</span><span><strong>{{ row.name }}</strong><small>{{ row.teamName }}</small></span><ChevronRight :size="14" /></button></td>
                    <td class="points-cell">{{ row.pts }}</td><td>{{ row.fg }}</td><td>{{ row.three }}</td><td>{{ row.reb }}</td><td>{{ row.ast }}</td><td>{{ row.stl }}</td><td>{{ row.turnovers }}</td>
                    <td><ArrowUpRight v-if="row.trend === 'up'" class="trend-up" :size="16" /><ArrowDownRight v-else-if="row.trend === 'down'" class="trend-down" :size="16" /><span v-else class="trend-flat">—</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="team-stat-grid">
              <article v-for="team in teamTotals" :key="team.team" class="team-stat-card" :class="`team-stat-${team.team}`">
                <div class="team-stat-top"><span class="team-dot"></span><strong>{{ team.name }}</strong><span class="team-code">{{ team.team === 'home' ? 'HOME' : 'AWAY' }}</span></div>
                <div class="team-score">{{ team.score }}<small>PTS</small></div>
                <div class="team-stat-line"><span>投篮 {{ team.fg }}</span><span>三分 {{ team.three }}</span><span>篮板 {{ team.reb }}</span><span>助攻 {{ team.ast }}</span></div>
              </article>
            </div>
          </section>

          <section v-else class="tool-panel full-queue-panel">
            <div class="panel-header">
              <div><div class="panel-kicker"><span class="accent-marker"></span>全部片段</div><h2>待复核清单 <span>/ {{ clips.length }} 个可见样本</span></h2></div>
              <div class="queue-toolbar"><button class="icon-button dark small" type="button" title="筛选"><ListFilter :size="16" /></button><button class="button button-acid compact" type="button" @click="showImport = true"><Plus :size="15" /> 导入更多</button></div>
            </div>
            <div class="queue-table">
              <button v-for="clip in clips" :key="clip.id" class="queue-row" :class="{ selected: selectedClip.id === clip.id }" type="button" @click="selectClip(clip)">
                <span class="queue-number">{{ String(clip.sequence).padStart(3, '0') }}</span>
                <span class="queue-thumb" :style="{ '--thumb-accent': clip.accent }"><span></span><i></i></span>
                <span class="queue-name"><strong>{{ clip.name }}</strong><small>{{ clip.capturedAt }} · {{ clip.fileSize }}</small></span>
                <span class="queue-event-count">{{ events.filter((event) => event.clipId === clip.id).length }} events</span>
                <span class="clip-status" :class="`clip-status-${clip.status}`"><i></i>{{ clipStatusLabel(clip.status) }}</span>
                <ChevronRight :size="16" />
              </button>
            </div>
          </section>
        </template>

        <template v-else-if="activeTab === 'players'">
          <section class="tool-panel roster-panel">
            <div class="panel-header roster-header">
              <div><div class="panel-kicker"><span class="accent-marker"></span>身份管理</div><h2>本场球员 <span>/ AI TRACK DIRECTORY</span></h2></div>
              <button class="button button-acid" type="button" @click="showToast('新增球员入口已准备')"><Plus :size="16" /> 新增球员</button>
            </div>
            <div class="roster-summary"><div><strong>06</strong><span>已检测身份</span></div><div><strong>02</strong><span>临时编号</span></div><div><strong>94%</strong><span>平均置信度</span></div><div class="roster-summary-note"><CircleAlert :size="16" /> 无号码球员使用本场临时身份，可在此绑定真实信息。</div></div>
            <div class="roster-columns">
              <div class="team-roster team-roster-home"><div class="team-roster-heading"><span class="team-color-dot home-dot"></span><div><strong>东岸猛禽</strong><small>HOME · 3 identities</small></div><span>42 PTS</span></div><button v-for="player in players.filter((item) => item.team === 'home')" :key="player.id" class="roster-row" type="button" @click="openPlayerEditor(player)"><span class="roster-number" :style="{ '--roster-color': player.color }">{{ player.number }}</span><span><strong>{{ player.name }}</strong><small>{{ player.identityType === 'temporary' ? '临时身份' : `号码 ${player.number}` }} · {{ player.tracks }} tracks</small></span><span class="roster-confidence" :class="{ candidate: player.status === 'candidate' }">{{ Math.round(player.confidence * 100) }}%</span><Settings2 :size="15" /></button></div>
              <div class="team-roster team-roster-away"><div class="team-roster-heading"><span class="team-color-dot away-dot"></span><div><strong>北城飞行</strong><small>AWAY · 3 identities</small></div><span>38 PTS</span></div><button v-for="player in players.filter((item) => item.team === 'away')" :key="player.id" class="roster-row" type="button" @click="openPlayerEditor(player)"><span class="roster-number" :style="{ '--roster-color': player.color }">{{ player.number }}</span><span><strong>{{ player.name }}</strong><small>{{ player.identityType === 'temporary' ? '临时身份' : `号码 ${player.number}` }} · {{ player.tracks }} tracks</small></span><span class="roster-confidence" :class="{ candidate: player.status === 'candidate' }">{{ Math.round(player.confidence * 100) }}%</span><Settings2 :size="15" /></button></div>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="tool-panel library-panel">
            <div class="panel-header library-header">
              <div><div class="panel-kicker"><span class="accent-marker"></span>素材管理</div><h2>片段库 <span>/ {{ totalClipCount }} TOTAL IMPORTS</span></h2></div>
              <div class="library-actions"><span class="analysis-live-label"><Sparkles :size="15" /> {{ isAnalyzing ? 'AI 分析中' : '导入后自动分析' }}</span><button class="button button-acid" type="button" @click="showImport = true"><CloudUpload :size="16" /> 导入片段</button></div>
            </div>
            <div class="library-toolbar"><label class="search-field"><Search :size="16" /><input v-model="clipSearch" type="search" placeholder="搜索文件名或片段编号" /></label><div class="filter-pills"><button v-for="filter in [['all', '全部'], ['review', '待复核'], ['ready', '已完成'], ['queued', '排队中'], ['failed', '失败']] as const" :key="filter[0]" type="button" :class="{ active: clipFilter === filter[0] }" @click="clipFilter = filter[0]">{{ filter[1] }}</button></div><span class="library-total">显示 {{ filteredClips.length }} / {{ clips.length }}</span></div>
            <div class="clip-grid">
              <button v-for="clip in filteredClips" :key="clip.id" class="clip-card" :class="{ selected: selectedClip.id === clip.id }" type="button" @click="selectClip(clip, true)">
                <div class="clip-card-preview" :style="{ '--thumb-accent': clip.accent }">
                  <video v-if="clip.previewUrl" :src="clip.previewUrl" muted preload="metadata"></video>
                  <div v-else class="mini-court"><span class="mini-court-line"></span><i class="mini-player mini-player-a"></i><i class="mini-player mini-player-b"></i><b></b></div>
                  <span class="clip-sequence">{{ String(clip.sequence).padStart(3, '0') }}</span><span class="clip-length">{{ clip.duration }}</span>
                </div>
                <div class="clip-card-copy"><div><strong>{{ clip.name }}</strong><span>{{ clip.capturedAt }}</span></div><span class="clip-status" :class="`clip-status-${clip.status}`"><i></i>{{ clipStatusLabel(clip.status) }}</span></div>
                <div class="clip-card-foot"><span><CircleDot :size="13" /> {{ events.filter((event) => event.clipId === clip.id).length }} events</span><span>{{ clip.confidence ? `AI ${Math.round(clip.confidence * 100)}%` : '等待分析' }}</span></div>
                <button v-if="clip.status === 'failed'" class="retry-button" type="button" title="重新分析" @click.stop="retryClip(clip)"><RefreshCw :size="14" /></button>
              </button>
            </div>
          </section>
        </template>
      </div>
    </main>

    <div v-if="showImport" class="modal-layer" @click.self="showImport = false">
      <section class="modal import-modal" role="dialog" aria-modal="true" aria-labelledby="import-title">
        <div class="modal-header"><div><span class="panel-kicker"><Upload :size="13" /> LOCAL INGEST</span><h2 id="import-title">导入比赛片段</h2><p>支持批量视频，分析结果保留在本机工作区。</p></div><button class="icon-button dark" type="button" title="关闭" @click="showImport = false"><X :size="18" /></button></div>
        <div class="drop-zone" :class="{ dragging: isDragging }" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="onDrop">
          <input ref="fileInput" class="hidden-input" type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/webm" multiple @change="onFileInput" />
          <div class="drop-icon"><CloudUpload :size="24" /></div><strong>拖入视频文件</strong><span>或</span><button class="button button-quiet compact" type="button" @click="triggerFilePicker">从本机选择</button><small>MP4 / MOV / M4V / WebM</small>
        </div>
        <div v-if="pendingFiles.length" class="pending-files"><div class="pending-heading"><span>待导入 {{ pendingFiles.length }} 个文件</span><strong>{{ pendingFileSize }}</strong></div><div class="pending-list"><div v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="pending-file"><FileVideo :size="16" /><span>{{ file.name }}</span><small>{{ (file.size / 1024 / 1024).toFixed(1) }} MB</small><button type="button" title="移除" @click="removePendingFile(index)"><X :size="14" /></button></div></div></div>
        <div class="modal-footer"><span class="modal-local-state"><span class="live-dot"></span> 不上传云端</span><div><button class="button button-quiet" type="button" @click="showImport = false">取消</button><button class="button button-acid" type="button" @click="importPendingFiles"><CloudUpload :size="16" /> 加入分析队列</button></div></div>
      </section>
    </div>

    <div v-if="showPlayerEditor" class="modal-layer" @click.self="showPlayerEditor = false">
      <section class="modal player-modal" role="dialog" aria-modal="true" aria-labelledby="player-title">
        <div class="modal-header"><div><span class="panel-kicker"><UsersRound :size="13" /> IDENTITY CORRECTION</span><h2 id="player-title">修正球员身份</h2><p>更新后会同步到本场关联事件。</p></div><button class="icon-button dark" type="button" title="关闭" @click="showPlayerEditor = false"><X :size="18" /></button></div>
        <div class="player-edit-preview"><span class="player-badge large" :style="{ '--badge-color': playerDraft.color }">{{ playerDraft.number }}</span><div><strong>{{ playerDraft.code }}</strong><small>{{ playerDraft.identityType === 'temporary' ? 'AI 生成的临时身份' : '号码识别身份' }}</small></div><span class="edit-confidence">AI {{ Math.round(playerDraft.confidence * 100) }}%</span></div>
        <div class="form-grid"><label><span>显示名称</span><input v-model="playerDraft.name" type="text" /></label><label><span>本场编号</span><input v-model="playerDraft.number" type="text" /></label><label><span>所属球队</span><select v-model="playerDraft.team"><option value="home">东岸猛禽 · HOME</option><option value="away">北城飞行 · AWAY</option></select></label><label><span>身份状态</span><select v-model="playerDraft.status"><option value="confirmed">已确认</option><option value="candidate">待确认</option></select></label></div>
        <div class="modal-footer"><button class="button button-quiet danger" type="button" @click="showToast('删除身份需要在后端确认')"><Trash2 :size="15" /> 删除身份</button><div><button class="button button-quiet" type="button" @click="showPlayerEditor = false">取消</button><button class="button button-acid" type="button" @click="savePlayer"><Check :size="16" /> 保存修正</button></div></div>
      </section>
    </div>

    <div v-if="showPlayerDetail" class="detail-layer" @click.self="showPlayerDetail = false">
      <aside class="player-detail-drawer" role="dialog" aria-modal="true" aria-labelledby="player-detail-title">
        <div class="drawer-header">
          <div><span class="panel-kicker"><UsersRound :size="13" /> PLAYER PROFILE</span><h2 id="player-detail-title">{{ selectedPlayer.name }}</h2><p>{{ selectedPlayer.teamName }} · {{ selectedPlayer.identityType === 'temporary' ? '本场临时身份' : `号码 ${selectedPlayer.number}` }}</p></div>
          <button class="icon-button dark" type="button" title="关闭球员详情" @click="showPlayerDetail = false"><X :size="18" /></button>
        </div>
        <div class="drawer-player-summary"><span class="player-badge large" :style="{ '--badge-color': selectedPlayer.color }">{{ selectedPlayer.number }}</span><div><strong>{{ selectedPlayer.code }}</strong><small>AI 身份置信度 {{ Math.round(selectedPlayer.confidence * 100) }}% · {{ selectedPlayer.tracks }} tracks</small></div><button class="mini-action muted" type="button" title="修正球员身份" @click="openPlayerEditor(selectedPlayer)"><Settings2 :size="14" /></button></div>
        <div class="drawer-stat-grid"><div><strong>{{ selectedPlayerStats?.pts ?? 0 }}</strong><span>得分</span></div><div><strong>{{ selectedPlayerStats?.fg ?? '0 / 0' }}</strong><span>投篮</span></div><div><strong>{{ selectedPlayerStats?.three ?? '0 / 0' }}</strong><span>三分</span></div><div><strong>{{ selectedPlayerStats?.reb ?? 0 }}</strong><span>篮板</span></div><div><strong>{{ selectedPlayerStats?.ast ?? 0 }}</strong><span>助攻</span></div><div><strong>{{ selectedPlayerStats?.stl ?? 0 }}</strong><span>抢断</span></div></div>
        <div class="drawer-section-heading"><div><span class="panel-kicker"><Sparkles :size="13" /> SCORING HIGHLIGHTS</span><h3>进球集锦 <span>{{ selectedPlayerScoringEvents.length }} 条</span></h3></div><span class="live-update"><span class="live-dot"></span>实时更新</span></div>
        <div v-if="selectedPlayerScoringEvents.length" class="highlight-list"><button v-for="event in selectedPlayerScoringEvents" :key="event.id" class="highlight-item" type="button" @click="openScoringEvent(event)"><span class="highlight-thumb" :class="`highlight-thumb-${event.team}`"><Play :size="16" fill="currentColor" /><small>{{ event.time }}</small></span><span class="highlight-copy"><strong>{{ event.type }}</strong><small>{{ getTeamName(event.team) }} · {{ clips.find((clip) => clip.id === event.clipId)?.name ?? '源片段' }}</small></span><span class="highlight-points">+{{ event.points }}<small>PTS</small></span><ChevronRight :size="15" /></button></div>
        <div v-else class="empty-highlights"><Film :size="19" /><strong>暂无已确认得分集锦</strong><span>分析完成并确认得分事件后，会自动出现在这里。</span></div>
        <div class="drawer-footnote"><CircleAlert :size="14" /> 待确认事件不会计入正式统计，但会在复核后自动更新。</div>
      </aside>
    </div>

    <Transition name="toast"><div v-if="toastMessage" class="toast-message"><CheckCheck :size="16" />{{ toastMessage }}</div></Transition>
  </div>
</template>
