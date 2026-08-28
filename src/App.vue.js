import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { ArrowDownRight, ArrowUpRight, Bell, Check, CheckCheck, ChevronDown, ChevronRight, CircleAlert, CircleDot, ClipboardCheck, CloudUpload, Cpu, Download, Ellipsis, FileDown, FileVideo, Film, Gauge, LayoutDashboard, ListFilter, Pause, Play, Plus, RefreshCw, ScanLine, Search, Settings2, Sparkles, Target, Trash2, Upload, UsersRound, X, } from 'lucide-vue-next';
const navItems = [
    { key: 'overview', label: '比赛总览', meta: '01', icon: LayoutDashboard },
    { key: 'review', label: '复核队列', meta: '12', icon: ClipboardCheck },
    { key: 'players', label: '球员身份', meta: '10', icon: UsersRound },
    { key: 'clips', label: '片段库', meta: '300', icon: Film },
];
const baseClips = [
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
];
const players = ref([
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
]);
const clips = ref(baseClips);
const events = ref([
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
]);
const baseStatRows = [
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
];
const activeTab = ref('overview');
const activeClipId = ref('clip-031');
const statsTab = ref('players');
const clipSearch = ref('');
const clipFilter = ref('all');
const isAnalyzing = ref(false);
const analysisProgress = ref(0);
const processedClipCount = ref(284);
const totalClipCount = ref(300);
const currentSeconds = ref(7.4);
const isPlaying = ref(false);
const playbackRate = ref(1);
const videoRef = ref(null);
const fileInput = ref(null);
const pendingFiles = ref([]);
const showImport = ref(false);
const showPlayerEditor = ref(false);
const showPlayerDetail = ref(false);
const selectedPlayerId = ref('p-home-12');
const isDragging = ref(false);
const toastMessage = ref('');
const toastTimer = ref();
const analysisTimer = ref();
const objectUrls = ref([]);
const engineMode = ref('CUDA 已就绪');
const engineDetail = ref('CPU fallback 可用');
const backendOnline = ref(false);
const playerDraft = reactive({ ...players.value[0] });
const fallbackClip = baseClips[0];
const selectedClip = computed(() => clips.value.find((clip) => clip.id === activeClipId.value) ?? clips.value[0] ?? fallbackClip);
const selectedEvents = computed(() => events.value.filter((event) => event.clipId === selectedClip.value.id));
const selectedPlayer = computed(() => players.value.find((player) => player.id === selectedPlayerId.value) ?? players.value[0]);
const selectedPlayerStats = computed(() => statRows.value.find((row) => row.playerId === selectedPlayerId.value) ?? statRows.value[0]);
const selectedPlayerScoringEvents = computed(() => events.value.filter((event) => event.playerId === selectedPlayerId.value && event.points > 0 && event.status !== 'ignored'));
const pendingEventCount = computed(() => events.value.filter((event) => event.status === 'pending').length);
const confirmedEventCount = computed(() => events.value.filter((event) => event.status === 'confirmed').length);
const analyzedProgress = computed(() => Math.round((processedClipCount.value / totalClipCount.value) * 100));
const viewTitle = computed(() => {
    const titles = {
        overview: '比赛总览',
        review: '复核队列',
        players: '球员身份',
        clips: '片段库',
    };
    return titles[activeTab.value];
});
const filteredClips = computed(() => {
    const query = clipSearch.value.trim().toLowerCase();
    return clips.value.filter((clip) => {
        const matchesQuery = !query || clip.name.toLowerCase().includes(query) || String(clip.sequence).includes(query);
        const matchesFilter = clipFilter.value === 'all' || clip.status === clipFilter.value;
        return matchesQuery && matchesFilter;
    });
});
const statRows = computed(() => baseStatRows);
const pendingFileSize = computed(() => {
    const bytes = pendingFiles.value.reduce((sum, file) => sum + file.size, 0);
    if (!bytes)
        return '0 MB';
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
});
const teamTotals = computed(() => [
    {
        team: 'home',
        name: '东岸猛禽',
        score: 42,
        fg: '17 / 34',
        three: '5 / 14',
        reb: 21,
        ast: 10,
    },
    {
        team: 'away',
        name: '北城飞行',
        score: 38,
        fg: '15 / 36',
        three: '6 / 18',
        reb: 19,
        ast: 12,
    },
]);
function showToast(message) {
    toastMessage.value = message;
    if (toastTimer.value)
        window.clearTimeout(toastTimer.value);
    toastTimer.value = window.setTimeout(() => {
        toastMessage.value = '';
    }, 2800);
}
async function apiRequest(path, init) {
    const response = await fetch(path, init);
    if (!response.ok)
        throw new Error(`API ${response.status}`);
    return response.json();
}
async function checkBackend() {
    try {
        const health = await apiRequest('/api/health');
        backendOnline.value = true;
        engineMode.value = health.cuda ? 'CUDA 已就绪' : 'CPU fallback';
        engineDetail.value = health.ffmpeg ? 'FFmpeg 媒体处理可用' : '未检测到 FFmpeg';
    }
    catch {
        backendOnline.value = false;
        engineMode.value = '演示模式';
        engineDetail.value = '启动本地服务后可接入分析';
    }
}
function setTab(tab) {
    activeTab.value = tab;
}
function selectClip(clip, openReview = false) {
    activeClipId.value = clip.id;
    currentSeconds.value = clip.id === 'clip-031' ? 7.4 : 3.2;
    isPlaying.value = false;
    if (videoRef.value) {
        videoRef.value.pause();
        videoRef.value.currentTime = currentSeconds.value;
    }
    if (openReview)
        activeTab.value = 'review';
}
function toggleVideo() {
    if (videoRef.value) {
        if (videoRef.value.paused) {
            void videoRef.value.play();
        }
        else {
            videoRef.value.pause();
        }
    }
    else {
        isPlaying.value = !isPlaying.value;
    }
}
function updatePlaying(value) {
    isPlaying.value = value;
}
function updateCurrentTime(event) {
    const target = event.target;
    currentSeconds.value = target.currentTime;
}
function seekVideo() {
    if (videoRef.value)
        videoRef.value.currentTime = currentSeconds.value;
}
function changePlaybackRate(rate) {
    playbackRate.value = rate;
    if (videoRef.value)
        videoRef.value.playbackRate = rate;
}
function formatTime(seconds) {
    const wholeSeconds = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(wholeSeconds / 60);
    const remainder = wholeSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}
function clipStatusLabel(status) {
    const labels = {
        ready: '已完成',
        review: '待复核',
        processing: '分析中',
        queued: '排队中',
        failed: '失败',
    };
    return labels[status];
}
function eventStatusLabel(status) {
    const labels = {
        pending: '待确认',
        confirmed: '已确认',
        ignored: '已忽略',
    };
    return labels[status];
}
function getPlayer(playerId) {
    return players.value.find((player) => player.id === playerId);
}
function getPlayerName(playerId) {
    return getPlayer(playerId)?.name ?? '未分配球员';
}
function getTeamName(team) {
    return team === 'home' ? '东岸猛禽' : '北城飞行';
}
function confirmEvent(eventId) {
    const target = events.value.find((event) => event.id === eventId);
    if (!target)
        return;
    target.status = 'confirmed';
    showToast(`${target.type}已计入统计`);
}
function ignoreEvent(eventId) {
    const target = events.value.find((event) => event.id === eventId);
    if (!target)
        return;
    target.status = 'ignored';
    showToast('候选事件已忽略');
}
function confirmAllEvents() {
    const targets = events.value.filter((event) => event.clipId === selectedClip.value.id && event.status === 'pending');
    targets.forEach((event) => {
        event.status = 'confirmed';
    });
    showToast(targets.length ? `${targets.length} 个事件已确认` : '当前片段没有待确认事件');
}
function updateEventPlayer(event) {
    const player = getPlayer(event.playerId);
    if (player)
        event.team = player.team;
    showToast('球员归属已更新');
}
function addManualEvent() {
    const defaultPlayer = players.value[0];
    const newEvent = {
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
    };
    events.value.unshift(newEvent);
    showToast('已添加人工事件');
}
function openPlayerEditor(player) {
    Object.assign(playerDraft, player);
    showPlayerEditor.value = true;
}
function openPlayerDetail(playerId) {
    selectedPlayerId.value = playerId;
    showPlayerDetail.value = true;
}
function openScoringEvent(event) {
    const clip = clips.value.find((item) => item.id === event.clipId);
    if (!clip) {
        showToast('源片段尚未在当前片段库中');
        return;
    }
    showPlayerDetail.value = false;
    selectClip(clip, true);
    currentSeconds.value = event.seconds;
    seekVideo();
}
function savePlayer() {
    const index = players.value.findIndex((player) => player.id === playerDraft.id);
    if (index === -1)
        return;
    players.value[index] = { ...playerDraft, code: `${playerDraft.team === 'home' ? 'H' : 'A'}-${playerDraft.number || playerDraft.code.split('-').at(-1)}` };
    events.value.forEach((event) => {
        if (event.playerId === playerDraft.id)
            event.team = playerDraft.team;
    });
    showPlayerEditor.value = false;
    showToast('球员身份已保存');
}
function triggerFilePicker() {
    fileInput.value?.click();
}
function addPendingFiles(files) {
    const videoFiles = files.filter((file) => file.type.startsWith('video/') || /\.(mp4|mov|m4v|webm)$/i.test(file.name));
    if (!videoFiles.length) {
        showToast('请选择 MP4、MOV、M4V 或 WebM 视频');
        return;
    }
    pendingFiles.value = [...pendingFiles.value, ...videoFiles];
}
function onFileInput(event) {
    const target = event.target;
    addPendingFiles(Array.from(target.files ?? []));
    target.value = '';
}
function onDrop(event) {
    isDragging.value = false;
    addPendingFiles(Array.from(event.dataTransfer?.files ?? []));
}
function removePendingFile(index) {
    pendingFiles.value.splice(index, 1);
}
async function importPendingFiles() {
    if (!pendingFiles.value.length) {
        showToast('先选择要导入的片段');
        return;
    }
    const filesToUpload = [...pendingFiles.value];
    const startSequence = totalClipCount.value + 1;
    try {
        const formData = new FormData();
        filesToUpload.forEach((file) => formData.append('files', file));
        const result = await apiRequest('/api/matches/friendly-game-04/clips', { method: 'POST', body: formData });
        if (result.accepted.length) {
            clips.value = [
                ...result.accepted.map((clip, index) => ({
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
            ];
            totalClipCount.value += result.accepted.length;
            activeClipId.value = result.accepted[0].id;
        }
        pendingFiles.value = [];
        showImport.value = false;
        activeTab.value = 'clips';
        showToast(`${result.accepted.length} 个视频已上传到本地分析队列${result.skipped.length ? `，跳过 ${result.skipped.length} 个` : ''}`);
        void startAnalysis();
        return;
    }
    catch {
        showToast('本地分析服务未启动，已切换为浏览器演示导入');
    }
    const imported = pendingFiles.value.map((file, index) => {
        const previewUrl = URL.createObjectURL(file);
        objectUrls.value.push(previewUrl);
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
        };
    });
    clips.value = [...imported, ...clips.value];
    totalClipCount.value += imported.length;
    activeClipId.value = imported[0].id;
    pendingFiles.value = [];
    showImport.value = false;
    activeTab.value = 'clips';
    showToast(`${imported.length} 个视频已加入分析队列`);
    void startAnalysis();
}
async function startAnalysis() {
    if (isAnalyzing.value)
        return;
    const targets = clips.value.filter((clip) => clip.status === 'queued' || clip.status === 'failed');
    if (!targets.length) {
        showToast('当前没有等待分析的片段');
        return;
    }
    try {
        const task = await apiRequest('/api/matches/friendly-game-04/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clip_ids: targets.map((clip) => clip.id), device: 'auto' }),
        });
        if (task.total) {
            isAnalyzing.value = true;
            analysisProgress.value = 0;
            targets.forEach((clip) => { clip.status = 'processing'; });
            const poll = window.setInterval(async () => {
                try {
                    const current = await apiRequest('/api/tasks/' + task.id);
                    analysisProgress.value = current.progress;
                    if (current.status === 'completed') {
                        window.clearInterval(poll);
                        targets.forEach((clip) => { clip.status = 'review'; clip.confidence = 0.82; });
                        isAnalyzing.value = false;
                        showToast('本地 AI 分析完成，候选事件已进入复核队列');
                    }
                }
                catch {
                    window.clearInterval(poll);
                    isAnalyzing.value = false;
                    showToast('分析任务状态读取失败');
                }
            }, 500);
            return;
        }
    }
    catch {
        showToast('本地服务不可用，使用前端演示队列');
    }
    isAnalyzing.value = true;
    analysisProgress.value = 0;
    targets.forEach((clip) => {
        clip.status = 'processing';
    });
    let tick = 0;
    analysisTimer.value = window.setInterval(() => {
        tick += 1;
        analysisProgress.value = Math.min(100, tick * 12.5);
        const completed = Math.min(targets.length, Math.floor((tick / 8) * targets.length));
        targets.forEach((clip, index) => {
            if (index < completed) {
                clip.status = 'review';
                clip.confidence = 0.76 + (index % 4) * 0.05;
            }
        });
        processedClipCount.value = Math.min(totalClipCount.value, processedClipCount.value + (tick % 2 === 0 ? 1 : 0));
        if (tick >= 8) {
            if (analysisTimer.value)
                window.clearInterval(analysisTimer.value);
            analysisTimer.value = undefined;
            isAnalyzing.value = false;
            analysisProgress.value = 100;
            targets.forEach((clip) => {
                clip.status = 'review';
                if (!clip.confidence)
                    clip.confidence = 0.82;
            });
            processedClipCount.value = Math.min(totalClipCount.value, processedClipCount.value + targets.length);
            showToast('AI 初判完成，候选事件已进入复核队列');
        }
    }, 650);
}
function retryClip(clip) {
    clip.status = 'queued';
    showToast(`${clip.name} 已重新排队`);
}
function exportStats() {
    const header = ['球员', '球队', '得分', '投篮', '三分', '篮板', '助攻', '抢断', '失误'];
    const rows = statRows.value.map((row) => [row.name, row.teamName, row.pts, row.fg, row.three, row.reb, row.ast, row.stl, row.turnovers]);
    const csv = [header, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'courttrace-友谊赛-04-统计.csv';
    link.click();
    URL.revokeObjectURL(url);
    showToast('统计 CSV 已导出');
}
onBeforeUnmount(() => {
    if (analysisTimer.value)
        window.clearInterval(analysisTimer.value);
    if (toastTimer.value)
        window.clearTimeout(toastTimer.value);
    objectUrls.value.forEach((url) => URL.revokeObjectURL(url));
});
onMounted(checkBackend);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "app-shell" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
    ...{ class: "sidebar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand-lockup" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand-mark" },
});
const __VLS_0 = {}.ScanLine;
/** @type {[typeof __VLS_components.ScanLine, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    size: (20),
    strokeWidth: (2.4),
}));
const __VLS_2 = __VLS_1({
    size: (20),
    strokeWidth: (2.4),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "sidebar-section-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: "match-switcher" },
    type: "button",
    title: "切换比赛",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "match-badge" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "match-copy" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
const __VLS_4 = {}.ChevronDown;
/** @type {[typeof __VLS_components.ChevronDown, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    size: (16),
}));
const __VLS_6 = __VLS_5({
    size: (16),
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
__VLS_asFunctionalElement(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({
    ...{ class: "primary-nav" },
    'aria-label': "主导航",
});
for (const [item] of __VLS_getVForSourceType((__VLS_ctx.navItems))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.setTab(item.key);
            } },
        key: (item.key),
        ...{ class: "nav-item" },
        ...{ class: ({ active: __VLS_ctx.activeTab === item.key }) },
        type: "button",
    });
    const __VLS_8 = ((item.icon));
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        size: (18),
        strokeWidth: (__VLS_ctx.activeTab === item.key ? 2.4 : 1.8),
    }));
    const __VLS_10 = __VLS_9({
        size: (18),
        strokeWidth: (__VLS_ctx.activeTab === item.key ? 2.4 : 1.8),
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (item.label);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.em, __VLS_intrinsicElements.em)({});
    (item.meta);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "sidebar-spacer" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "engine-card" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "engine-card-top" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "live-dot" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
const __VLS_12 = {}.Cpu;
/** @type {[typeof __VLS_components.Cpu, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    size: (15),
}));
const __VLS_14 = __VLS_13({
    size: (15),
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.engineMode);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "engine-meter" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ style: {} },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
(__VLS_ctx.backendOnline ? __VLS_ctx.engineDetail : __VLS_ctx.engineDetail);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "sidebar-footer" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: "footer-action" },
    type: "button",
    title: "设置",
});
const __VLS_16 = {}.Settings2;
/** @type {[typeof __VLS_components.Settings2, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    size: (17),
}));
const __VLS_18 = __VLS_17({
    size: (17),
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: "footer-action" },
    type: "button",
    title: "帮助",
});
const __VLS_20 = {}.CircleAlert;
/** @type {[typeof __VLS_components.CircleAlert, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    size: (17),
}));
const __VLS_22 = __VLS_21({
    size: (17),
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.main, __VLS_intrinsicElements.main)({
    ...{ class: "main-shell" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "topbar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "breadcrumb" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
const __VLS_24 = {}.ChevronRight;
/** @type {[typeof __VLS_components.ChevronRight, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    size: (14),
}));
const __VLS_26 = __VLS_25({
    size: (14),
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.viewTitle);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "topbar-actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "connection-state" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: ({ offline: !__VLS_ctx.backendOnline }) },
});
(__VLS_ctx.backendOnline ? __VLS_ctx.engineMode.replace(' 已就绪', '').toUpperCase() : 'DEMO');
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: "icon-button" },
    type: "button",
    title: "通知",
});
const __VLS_28 = {}.Bell;
/** @type {[typeof __VLS_components.Bell, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    size: (18),
}));
const __VLS_30 = __VLS_29({
    size: (18),
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: "icon-button" },
    type: "button",
    title: "更多",
});
const __VLS_32 = {}.Ellipsis;
/** @type {[typeof __VLS_components.Ellipsis, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    size: (19),
}));
const __VLS_34 = __VLS_33({
    size: (19),
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "avatar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "page-content" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "page-heading" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "eyebrow" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "eyebrow-line" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "heading-actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.exportStats) },
    ...{ class: "button button-quiet" },
    type: "button",
});
const __VLS_36 = {}.Download;
/** @type {[typeof __VLS_components.Download, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    size: (16),
}));
const __VLS_38 = __VLS_37({
    size: (16),
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.showImport = true;
        } },
    ...{ class: "button button-acid" },
    type: "button",
});
const __VLS_40 = {}.CloudUpload;
/** @type {[typeof __VLS_components.CloudUpload, ]} */ ;
// @ts-ignore
const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
    size: (17),
}));
const __VLS_42 = __VLS_41({
    size: (17),
}, ...__VLS_functionalComponentArgsRest(__VLS_41));
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "metric-strip" },
    'aria-label': "比赛处理概览",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-cell metric-primary" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "metric-index" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-value" },
});
(__VLS_ctx.processedClipCount);
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
(__VLS_ctx.totalClipCount);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-subline" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "positive" },
});
const __VLS_44 = {}.ArrowUpRight;
/** @type {[typeof __VLS_components.ArrowUpRight, ]} */ ;
// @ts-ignore
const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
    size: (13),
}));
const __VLS_46 = __VLS_45({
    size: (13),
}, ...__VLS_functionalComponentArgsRest(__VLS_45));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-cell" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "metric-index" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-value" },
});
(__VLS_ctx.confirmedEventCount);
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-subline" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "warning" },
});
(__VLS_ctx.pendingEventCount);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-cell" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "metric-index" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-value" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-subline" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "positive" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-cell metric-engine" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "metric-index" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-engine-line" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "status-orbit" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.isAnalyzing ? 'AI 分析中' : '可以开始复核');
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "metric-subline" },
});
(__VLS_ctx.isAnalyzing ? `${Math.round(__VLS_ctx.analysisProgress)}% · 本地队列` : 'AI 初判已完成 94%');
if (__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "workspace-grid" },
        ...{ class: ({ 'workspace-grid-focus': __VLS_ctx.activeTab === 'review' }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "tool-panel review-workspace" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-kicker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "accent-marker" },
    });
    (__VLS_ctx.activeTab === 'review' ? 'AI 复核队列' : '当前片段');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
    (__VLS_ctx.selectedClip.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (String(__VLS_ctx.selectedClip.sequence).padStart(3, '0'));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-header-actions" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "confidence-chip" },
    });
    const __VLS_48 = {}.Sparkles;
    /** @type {[typeof __VLS_components.Sparkles, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        size: (13),
    }));
    const __VLS_50 = __VLS_49({
        size: (13),
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    (Math.round(__VLS_ctx.selectedClip.confidence * 100));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ class: "icon-button dark" },
        type: "button",
        title: "片段选项",
    });
    const __VLS_52 = {}.Ellipsis;
    /** @type {[typeof __VLS_components.Ellipsis, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        size: (18),
    }));
    const __VLS_54 = __VLS_53({
        size: (18),
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "review-layout" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "video-column" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "video-stage" },
    });
    if (__VLS_ctx.selectedClip.previewUrl) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.video, __VLS_intrinsicElements.video)({
            ...{ onPlay: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.selectedClip.previewUrl))
                        return;
                    __VLS_ctx.updatePlaying(true);
                } },
            ...{ onPause: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.selectedClip.previewUrl))
                        return;
                    __VLS_ctx.updatePlaying(false);
                } },
            ...{ onTimeupdate: (__VLS_ctx.updateCurrentTime) },
            ref: "videoRef",
            ...{ class: "source-video" },
            src: (__VLS_ctx.selectedClip.previewUrl),
            playsinline: true,
        });
        /** @type {typeof __VLS_ctx.videoRef} */ ;
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-scene" },
            ...{ class: ({ playing: __VLS_ctx.isPlaying }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-grain" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-line court-line-mid" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-line court-line-key court-line-key-left" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-line court-line-key court-line-key-right" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-arc court-arc-left" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-arc court-arc-right" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-hoop court-hoop-left" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "court-hoop court-hoop-right" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        for (const [player, index] of __VLS_getVForSourceType((__VLS_ctx.players))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (player.id),
                ...{ class: "court-player" },
                ...{ class: (`court-player--${index + 1}`) },
                ...{ style: ({ '--player-color': player.color }) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (player.number.replace('T', ''));
        }
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "ball-track" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "scene-tag scene-tag-top" },
        });
        const __VLS_56 = {}.CircleDot;
        /** @type {[typeof __VLS_components.CircleDot, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            size: (12),
        }));
        const __VLS_58 = __VLS_57({
            size: (12),
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "scene-tag scene-tag-bottom" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "scene-frame-label" },
        });
        (String(__VLS_ctx.selectedClip.sequence).padStart(3, '0'));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "scene-focus-ring" },
        });
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "video-overlay-top" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "rec-dot" },
    });
    (__VLS_ctx.selectedClip.previewUrl ? 'LOCAL FILE' : 'DEMO FRAME');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "video-overlay-bottom" },
    });
    (__VLS_ctx.selectedClip.capturedAt);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.selectedClip.duration);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "video-control-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.toggleVideo) },
        ...{ class: "play-button" },
        type: "button",
        title: (__VLS_ctx.isPlaying ? '暂停' : '播放'),
    });
    if (__VLS_ctx.isPlaying) {
        const __VLS_60 = {}.Pause;
        /** @type {[typeof __VLS_components.Pause, ]} */ ;
        // @ts-ignore
        const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
            size: (18),
            fill: "currentColor",
        }));
        const __VLS_62 = __VLS_61({
            size: (18),
            fill: "currentColor",
        }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    }
    else {
        const __VLS_64 = {}.Play;
        /** @type {[typeof __VLS_components.Play, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            size: (18),
            fill: "currentColor",
        }));
        const __VLS_66 = __VLS_65({
            size: (18),
            fill: "currentColor",
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "time-readout" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.formatTime(__VLS_ctx.currentSeconds));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "scrubber-wrap" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        ...{ onInput: (__VLS_ctx.seekVideo) },
        ...{ class: "scrubber" },
        type: "range",
        min: "0",
        max: "10",
        step: "0.1",
    });
    (__VLS_ctx.currentSeconds);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "scrubber-markers" },
    });
    for (const [event] of __VLS_getVForSourceType((__VLS_ctx.selectedEvents))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            key: (event.id),
            ...{ style: ({ left: `${(event.seconds / 10) * 100}%` }) },
            ...{ class: (`marker-${event.status}`) },
            title: (event.type),
        });
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "speed-control" },
    });
    for (const [rate] of __VLS_getVForSourceType(([0.5, 1, 1.5]))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    __VLS_ctx.changePlaybackRate(rate);
                } },
            key: (rate),
            type: "button",
            ...{ class: ({ selected: __VLS_ctx.playbackRate === rate }) },
        });
        (rate);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ class: "icon-button dark small" },
        type: "button",
        title: "全屏预览",
    });
    const __VLS_68 = {}.Gauge;
    /** @type {[typeof __VLS_components.Gauge, ]} */ ;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
        size: (16),
    }));
    const __VLS_70 = __VLS_69({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "clip-context-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_72 = {}.Film;
    /** @type {[typeof __VLS_components.Film, ]} */ ;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        size: (14),
    }));
    const __VLS_74 = __VLS_73({
        size: (14),
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_76 = {}.Target;
    /** @type {[typeof __VLS_components.Target, ]} */ ;
    // @ts-ignore
    const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
        size: (14),
    }));
    const __VLS_78 = __VLS_77({
        size: (14),
    }, ...__VLS_functionalComponentArgsRest(__VLS_77));
    (__VLS_ctx.selectedEvents.length);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
        ...{ class: "event-review-column" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "event-column-heading" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "panel-kicker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
    (__VLS_ctx.selectedEvents.length);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.confirmAllEvents) },
        ...{ class: "text-button" },
        type: "button",
    });
    const __VLS_80 = {}.CheckCheck;
    /** @type {[typeof __VLS_components.CheckCheck, ]} */ ;
    // @ts-ignore
    const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
        size: (15),
    }));
    const __VLS_82 = __VLS_81({
        size: (15),
    }, ...__VLS_functionalComponentArgsRest(__VLS_81));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "event-list" },
    });
    for (const [event] of __VLS_getVForSourceType((__VLS_ctx.selectedEvents))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.article, __VLS_intrinsicElements.article)({
            key: (event.id),
            ...{ class: "event-item" },
            ...{ class: ([`event-${event.status}`, `team-${event.team}`]) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-item-top" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-type-mark" },
        });
        const __VLS_84 = {}.CircleDot;
        /** @type {[typeof __VLS_components.CircleDot, ]} */ ;
        // @ts-ignore
        const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
            size: (15),
        }));
        const __VLS_86 = __VLS_85({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_85));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-main-copy" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-title-line" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (event.type);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (event.time);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
        (event.description);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "event-confidence" },
        });
        (Math.round(event.confidence * 100));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-item-bottom" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
            ...{ class: "player-select" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "player-swatch" },
            ...{ style: ({ background: __VLS_ctx.getPlayer(event.playerId)?.color ?? '#78827c' }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({
            ...{ onChange: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    __VLS_ctx.updateEventPlayer(event);
                } },
            value: (event.playerId),
            'aria-label': "选择事件球员",
        });
        for (const [player] of __VLS_getVForSourceType((__VLS_ctx.players))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
                key: (player.id),
                value: (player.id),
            });
            (player.name);
            (player.code);
        }
        const __VLS_88 = {}.ChevronDown;
        /** @type {[typeof __VLS_components.ChevronDown, ]} */ ;
        // @ts-ignore
        const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
            size: (13),
        }));
        const __VLS_90 = __VLS_89({
            size: (13),
        }, ...__VLS_functionalComponentArgsRest(__VLS_89));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "event-actions" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "event-status-label" },
        });
        (__VLS_ctx.eventStatusLabel(event.status));
        if (event.status === 'pending') {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!(event.status === 'pending'))
                            return;
                        __VLS_ctx.confirmEvent(event.id);
                    } },
                ...{ class: "mini-action confirm" },
                type: "button",
                title: "确认事件",
            });
            const __VLS_92 = {}.Check;
            /** @type {[typeof __VLS_components.Check, ]} */ ;
            // @ts-ignore
            const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
                size: (14),
            }));
            const __VLS_94 = __VLS_93({
                size: (14),
            }, ...__VLS_functionalComponentArgsRest(__VLS_93));
        }
        if (event.status === 'pending') {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!(event.status === 'pending'))
                            return;
                        __VLS_ctx.ignoreEvent(event.id);
                    } },
                ...{ class: "mini-action ignore" },
                type: "button",
                title: "忽略事件",
            });
            const __VLS_96 = {}.X;
            /** @type {[typeof __VLS_components.X, ]} */ ;
            // @ts-ignore
            const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
                size: (14),
            }));
            const __VLS_98 = __VLS_97({
                size: (14),
            }, ...__VLS_functionalComponentArgsRest(__VLS_97));
        }
        else {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!!(event.status === 'pending'))
                            return;
                        event.status = 'pending';
                    } },
                ...{ class: "mini-action muted" },
                type: "button",
                title: "恢复待确认",
            });
            const __VLS_100 = {}.RefreshCw;
            /** @type {[typeof __VLS_components.RefreshCw, ]} */ ;
            // @ts-ignore
            const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
                size: (13),
            }));
            const __VLS_102 = __VLS_101({
                size: (13),
            }, ...__VLS_functionalComponentArgsRest(__VLS_101));
        }
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.addManualEvent) },
        ...{ class: "manual-event-button" },
        type: "button",
    });
    const __VLS_104 = {}.Plus;
    /** @type {[typeof __VLS_components.Plus, ]} */ ;
    // @ts-ignore
    const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
        size: (16),
    }));
    const __VLS_106 = __VLS_105({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_105));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "review-note" },
    });
    const __VLS_108 = {}.CircleAlert;
    /** @type {[typeof __VLS_components.CircleAlert, ]} */ ;
    // @ts-ignore
    const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
        size: (14),
    }));
    const __VLS_110 = __VLS_109({
        size: (14),
    }, ...__VLS_functionalComponentArgsRest(__VLS_109));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    if (__VLS_ctx.activeTab === 'overview') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
            ...{ class: "overview-rail" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
            ...{ class: "tool-panel identity-panel" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "rail-heading" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "panel-kicker" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'overview'))
                        return;
                    __VLS_ctx.setTab('players');
                } },
            ...{ class: "icon-button dark small" },
            type: "button",
            title: "身份设置",
        });
        const __VLS_112 = {}.Settings2;
        /** @type {[typeof __VLS_components.Settings2, ]} */ ;
        // @ts-ignore
        const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
            size: (15),
        }));
        const __VLS_114 = __VLS_113({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_113));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "identity-list" },
        });
        for (const [player] of __VLS_getVForSourceType((__VLS_ctx.players))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!(__VLS_ctx.activeTab === 'overview'))
                            return;
                        __VLS_ctx.openPlayerEditor(player);
                    } },
                key: (player.id),
                ...{ class: "identity-row" },
                type: "button",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "player-badge" },
                ...{ style: ({ '--badge-color': player.color }) },
            });
            (player.number);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "identity-copy" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (player.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (player.teamName);
            (player.tracks);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "identity-confidence" },
                ...{ class: ({ candidate: player.status === 'candidate' }) },
            });
            (Math.round(player.confidence * 100));
            const __VLS_116 = {}.ChevronRight;
            /** @type {[typeof __VLS_components.ChevronRight, ]} */ ;
            // @ts-ignore
            const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
                size: (14),
                ...{ class: "identity-arrow" },
            }));
            const __VLS_118 = __VLS_117({
                size: (14),
                ...{ class: "identity-arrow" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_117));
        }
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'overview'))
                        return;
                    __VLS_ctx.setTab('players');
                } },
            ...{ class: "rail-link" },
            type: "button",
        });
        const __VLS_120 = {}.ArrowDownRight;
        /** @type {[typeof __VLS_components.ArrowDownRight, ]} */ ;
        // @ts-ignore
        const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
            size: (14),
        }));
        const __VLS_122 = __VLS_121({
            size: (14),
        }, ...__VLS_functionalComponentArgsRest(__VLS_121));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
            ...{ class: "tool-panel queue-panel" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "rail-heading" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "panel-kicker" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        (__VLS_ctx.isAnalyzing ? '分析进行中' : '复核准备度');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "queue-percent" },
        });
        (__VLS_ctx.isAnalyzing ? `${Math.round(__VLS_ctx.analysisProgress)}%` : `${__VLS_ctx.analyzedProgress}%`);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "progress-ring" },
            ...{ style: ({ '--progress': `${__VLS_ctx.isAnalyzing ? __VLS_ctx.analysisProgress : __VLS_ctx.analyzedProgress}%` }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.isAnalyzing ? Math.round(__VLS_ctx.analysisProgress) : __VLS_ctx.analyzedProgress);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "queue-stats" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
        (__VLS_ctx.processedClipCount);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
        (__VLS_ctx.pendingEventCount);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "analysis-live-state" },
        });
        const __VLS_124 = {}.Sparkles;
        /** @type {[typeof __VLS_components.Sparkles, ]} */ ;
        // @ts-ignore
        const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
            size: (15),
        }));
        const __VLS_126 = __VLS_125({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_125));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.isAnalyzing ? 'AI 正在处理...' : '导入后自动分析');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
        (__VLS_ctx.isAnalyzing ? `${Math.round(__VLS_ctx.analysisProgress)}%` : 'AUTO');
    }
    if (__VLS_ctx.activeTab === 'overview') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
            ...{ class: "tool-panel stats-panel" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "panel-header stats-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "panel-kicker" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "accent-marker coral" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stats-header-actions" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "segmented-control" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'overview'))
                        return;
                    __VLS_ctx.statsTab = 'players';
                } },
            type: "button",
            ...{ class: ({ selected: __VLS_ctx.statsTab === 'players' }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'overview'))
                        return;
                    __VLS_ctx.statsTab = 'teams';
                } },
            type: "button",
            ...{ class: ({ selected: __VLS_ctx.statsTab === 'teams' }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ class: "icon-button dark" },
            type: "button",
            title: "筛选",
        });
        const __VLS_128 = {}.ListFilter;
        /** @type {[typeof __VLS_components.ListFilter, ]} */ ;
        // @ts-ignore
        const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
            size: (17),
        }));
        const __VLS_130 = __VLS_129({
            size: (17),
        }, ...__VLS_functionalComponentArgsRest(__VLS_129));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.exportStats) },
            ...{ class: "button button-quiet compact" },
            type: "button",
        });
        const __VLS_132 = {}.FileDown;
        /** @type {[typeof __VLS_components.FileDown, ]} */ ;
        // @ts-ignore
        const __VLS_133 = __VLS_asFunctionalComponent(__VLS_132, new __VLS_132({
            size: (15),
        }));
        const __VLS_134 = __VLS_133({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_133));
        if (__VLS_ctx.statsTab === 'players') {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "table-wrap" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.table, __VLS_intrinsicElements.table)({
                ...{ class: "stats-table" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.thead, __VLS_intrinsicElements.thead)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({
                ...{ class: "player-col" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.tbody, __VLS_intrinsicElements.tbody)({});
            for (const [row] of __VLS_getVForSourceType((__VLS_ctx.statRows))) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({
                    key: (row.playerId),
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
                    ...{ class: "player-col" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                                return;
                            if (!(__VLS_ctx.activeTab === 'overview'))
                                return;
                            if (!(__VLS_ctx.statsTab === 'players'))
                                return;
                            __VLS_ctx.openPlayerDetail(row.playerId);
                        } },
                    ...{ class: "player-cell-button" },
                    type: "button",
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "table-avatar" },
                    ...{ class: (`table-avatar-${row.team}`) },
                });
                (row.name.slice(0, 1));
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
                (row.name);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
                (row.teamName);
                const __VLS_136 = {}.ChevronRight;
                /** @type {[typeof __VLS_components.ChevronRight, ]} */ ;
                // @ts-ignore
                const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
                    size: (14),
                }));
                const __VLS_138 = __VLS_137({
                    size: (14),
                }, ...__VLS_functionalComponentArgsRest(__VLS_137));
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
                    ...{ class: "points-cell" },
                });
                (row.pts);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.fg);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.three);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.reb);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.ast);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.stl);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                (row.turnovers);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
                if (row.trend === 'up') {
                    const __VLS_140 = {}.ArrowUpRight;
                    /** @type {[typeof __VLS_components.ArrowUpRight, ]} */ ;
                    // @ts-ignore
                    const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
                        ...{ class: "trend-up" },
                        size: (16),
                    }));
                    const __VLS_142 = __VLS_141({
                        ...{ class: "trend-up" },
                        size: (16),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_141));
                }
                else if (row.trend === 'down') {
                    const __VLS_144 = {}.ArrowDownRight;
                    /** @type {[typeof __VLS_components.ArrowDownRight, ]} */ ;
                    // @ts-ignore
                    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
                        ...{ class: "trend-down" },
                        size: (16),
                    }));
                    const __VLS_146 = __VLS_145({
                        ...{ class: "trend-down" },
                        size: (16),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_145));
                }
                else {
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                        ...{ class: "trend-flat" },
                    });
                }
            }
        }
        else {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "team-stat-grid" },
            });
            for (const [team] of __VLS_getVForSourceType((__VLS_ctx.teamTotals))) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.article, __VLS_intrinsicElements.article)({
                    key: (team.team),
                    ...{ class: "team-stat-card" },
                    ...{ class: (`team-stat-${team.team}`) },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                    ...{ class: "team-stat-top" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "team-dot" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
                (team.name);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "team-code" },
                });
                (team.team === 'home' ? 'HOME' : 'AWAY');
                __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                    ...{ class: "team-score" },
                });
                (team.score);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
                __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                    ...{ class: "team-stat-line" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (team.fg);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (team.three);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (team.reb);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (team.ast);
            }
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
            ...{ class: "tool-panel full-queue-panel" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "panel-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "panel-kicker" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "accent-marker" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.clips.length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "queue-toolbar" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ class: "icon-button dark small" },
            type: "button",
            title: "筛选",
        });
        const __VLS_148 = {}.ListFilter;
        /** @type {[typeof __VLS_components.ListFilter, ]} */ ;
        // @ts-ignore
        const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
            size: (16),
        }));
        const __VLS_150 = __VLS_149({
            size: (16),
        }, ...__VLS_functionalComponentArgsRest(__VLS_149));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!!(__VLS_ctx.activeTab === 'overview'))
                        return;
                    __VLS_ctx.showImport = true;
                } },
            ...{ class: "button button-acid compact" },
            type: "button",
        });
        const __VLS_152 = {}.Plus;
        /** @type {[typeof __VLS_components.Plus, ]} */ ;
        // @ts-ignore
        const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
            size: (15),
        }));
        const __VLS_154 = __VLS_153({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_153));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "queue-table" },
        });
        for (const [clip] of __VLS_getVForSourceType((__VLS_ctx.clips))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!!(__VLS_ctx.activeTab === 'overview'))
                            return;
                        __VLS_ctx.selectClip(clip);
                    } },
                key: (clip.id),
                ...{ class: "queue-row" },
                ...{ class: ({ selected: __VLS_ctx.selectedClip.id === clip.id }) },
                type: "button",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "queue-number" },
            });
            (String(clip.sequence).padStart(3, '0'));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "queue-thumb" },
                ...{ style: ({ '--thumb-accent': clip.accent }) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "queue-name" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (clip.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (clip.capturedAt);
            (clip.fileSize);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "queue-event-count" },
            });
            (__VLS_ctx.events.filter((event) => event.clipId === clip.id).length);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "clip-status" },
                ...{ class: (`clip-status-${clip.status}`) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
            (__VLS_ctx.clipStatusLabel(clip.status));
            const __VLS_156 = {}.ChevronRight;
            /** @type {[typeof __VLS_components.ChevronRight, ]} */ ;
            // @ts-ignore
            const __VLS_157 = __VLS_asFunctionalComponent(__VLS_156, new __VLS_156({
                size: (16),
            }));
            const __VLS_158 = __VLS_157({
                size: (16),
            }, ...__VLS_functionalComponentArgsRest(__VLS_157));
        }
    }
}
else if (__VLS_ctx.activeTab === 'players') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "tool-panel roster-panel" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-header roster-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-kicker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "accent-marker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                    return;
                if (!(__VLS_ctx.activeTab === 'players'))
                    return;
                __VLS_ctx.showToast('新增球员入口已准备');
            } },
        ...{ class: "button button-acid" },
        type: "button",
    });
    const __VLS_160 = {}.Plus;
    /** @type {[typeof __VLS_components.Plus, ]} */ ;
    // @ts-ignore
    const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
        size: (16),
    }));
    const __VLS_162 = __VLS_161({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_161));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "roster-summary" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "roster-summary-note" },
    });
    const __VLS_164 = {}.CircleAlert;
    /** @type {[typeof __VLS_components.CircleAlert, ]} */ ;
    // @ts-ignore
    const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
        size: (16),
    }));
    const __VLS_166 = __VLS_165({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_165));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "roster-columns" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-roster team-roster-home" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-roster-heading" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "team-color-dot home-dot" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    for (const [player] of __VLS_getVForSourceType((__VLS_ctx.players.filter((item) => item.team === 'home')))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'players'))
                        return;
                    __VLS_ctx.openPlayerEditor(player);
                } },
            key: (player.id),
            ...{ class: "roster-row" },
            type: "button",
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "roster-number" },
            ...{ style: ({ '--roster-color': player.color }) },
        });
        (player.number);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (player.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
        (player.identityType === 'temporary' ? '临时身份' : `号码 ${player.number}`);
        (player.tracks);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "roster-confidence" },
            ...{ class: ({ candidate: player.status === 'candidate' }) },
        });
        (Math.round(player.confidence * 100));
        const __VLS_168 = {}.Settings2;
        /** @type {[typeof __VLS_components.Settings2, ]} */ ;
        // @ts-ignore
        const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
            size: (15),
        }));
        const __VLS_170 = __VLS_169({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_169));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-roster team-roster-away" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "team-roster-heading" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "team-color-dot away-dot" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    for (const [player] of __VLS_getVForSourceType((__VLS_ctx.players.filter((item) => item.team === 'away')))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!(__VLS_ctx.activeTab === 'players'))
                        return;
                    __VLS_ctx.openPlayerEditor(player);
                } },
            key: (player.id),
            ...{ class: "roster-row" },
            type: "button",
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "roster-number" },
            ...{ style: ({ '--roster-color': player.color }) },
        });
        (player.number);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (player.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
        (player.identityType === 'temporary' ? '临时身份' : `号码 ${player.number}`);
        (player.tracks);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "roster-confidence" },
            ...{ class: ({ candidate: player.status === 'candidate' }) },
        });
        (Math.round(player.confidence * 100));
        const __VLS_172 = {}.Settings2;
        /** @type {[typeof __VLS_components.Settings2, ]} */ ;
        // @ts-ignore
        const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
            size: (15),
        }));
        const __VLS_174 = __VLS_173({
            size: (15),
        }, ...__VLS_functionalComponentArgsRest(__VLS_173));
    }
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "tool-panel library-panel" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-header library-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-kicker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "accent-marker" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.totalClipCount);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "library-actions" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "analysis-live-label" },
    });
    const __VLS_176 = {}.Sparkles;
    /** @type {[typeof __VLS_components.Sparkles, ]} */ ;
    // @ts-ignore
    const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
        size: (15),
    }));
    const __VLS_178 = __VLS_177({
        size: (15),
    }, ...__VLS_functionalComponentArgsRest(__VLS_177));
    (__VLS_ctx.isAnalyzing ? 'AI 分析中' : '导入后自动分析');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                    return;
                if (!!(__VLS_ctx.activeTab === 'players'))
                    return;
                __VLS_ctx.showImport = true;
            } },
        ...{ class: "button button-acid" },
        type: "button",
    });
    const __VLS_180 = {}.CloudUpload;
    /** @type {[typeof __VLS_components.CloudUpload, ]} */ ;
    // @ts-ignore
    const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
        size: (16),
    }));
    const __VLS_182 = __VLS_181({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_181));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "library-toolbar" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "search-field" },
    });
    const __VLS_184 = {}.Search;
    /** @type {[typeof __VLS_components.Search, ]} */ ;
    // @ts-ignore
    const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
        size: (16),
    }));
    const __VLS_186 = __VLS_185({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_185));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        type: "search",
        placeholder: "搜索文件名或片段编号",
    });
    (__VLS_ctx.clipSearch);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "filter-pills" },
    });
    for (const [filter] of __VLS_getVForSourceType([['all', '全部'], ['review', '待复核'], ['ready', '已完成'], ['queued', '排队中'], ['failed', '失败']])) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!!(__VLS_ctx.activeTab === 'players'))
                        return;
                    __VLS_ctx.clipFilter = filter[0];
                } },
            key: (filter[0]),
            type: "button",
            ...{ class: ({ active: __VLS_ctx.clipFilter === filter[0] }) },
        });
        (filter[1]);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "library-total" },
    });
    (__VLS_ctx.filteredClips.length);
    (__VLS_ctx.clips.length);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "clip-grid" },
    });
    for (const [clip] of __VLS_getVForSourceType((__VLS_ctx.filteredClips))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                        return;
                    if (!!(__VLS_ctx.activeTab === 'players'))
                        return;
                    __VLS_ctx.selectClip(clip, true);
                } },
            key: (clip.id),
            ...{ class: "clip-card" },
            ...{ class: ({ selected: __VLS_ctx.selectedClip.id === clip.id }) },
            type: "button",
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "clip-card-preview" },
            ...{ style: ({ '--thumb-accent': clip.accent }) },
        });
        if (clip.previewUrl) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.video, __VLS_intrinsicElements.video)({
                src: (clip.previewUrl),
                muted: true,
                preload: "metadata",
            });
        }
        else {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "mini-court" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "mini-court-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
                ...{ class: "mini-player mini-player-a" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
                ...{ class: "mini-player mini-player-b" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
        }
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "clip-sequence" },
        });
        (String(clip.sequence).padStart(3, '0'));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "clip-length" },
        });
        (clip.duration);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "clip-card-copy" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (clip.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (clip.capturedAt);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "clip-status" },
            ...{ class: (`clip-status-${clip.status}`) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({});
        (__VLS_ctx.clipStatusLabel(clip.status));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "clip-card-foot" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        const __VLS_188 = {}.CircleDot;
        /** @type {[typeof __VLS_components.CircleDot, ]} */ ;
        // @ts-ignore
        const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
            size: (13),
        }));
        const __VLS_190 = __VLS_189({
            size: (13),
        }, ...__VLS_functionalComponentArgsRest(__VLS_189));
        (__VLS_ctx.events.filter((event) => event.clipId === clip.id).length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (clip.confidence ? `AI ${Math.round(clip.confidence * 100)}%` : '等待分析');
        if (clip.status === 'failed') {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.activeTab === 'overview' || __VLS_ctx.activeTab === 'review'))
                            return;
                        if (!!(__VLS_ctx.activeTab === 'players'))
                            return;
                        if (!(clip.status === 'failed'))
                            return;
                        __VLS_ctx.retryClip(clip);
                    } },
                ...{ class: "retry-button" },
                type: "button",
                title: "重新分析",
            });
            const __VLS_192 = {}.RefreshCw;
            /** @type {[typeof __VLS_components.RefreshCw, ]} */ ;
            // @ts-ignore
            const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
                size: (14),
            }));
            const __VLS_194 = __VLS_193({
                size: (14),
            }, ...__VLS_functionalComponentArgsRest(__VLS_193));
        }
    }
}
if (__VLS_ctx.showImport) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showImport))
                    return;
                __VLS_ctx.showImport = false;
            } },
        ...{ class: "modal-layer" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "modal import-modal" },
        role: "dialog",
        'aria-modal': "true",
        'aria-labelledby': "import-title",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "modal-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "panel-kicker" },
    });
    const __VLS_196 = {}.Upload;
    /** @type {[typeof __VLS_components.Upload, ]} */ ;
    // @ts-ignore
    const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
        size: (13),
    }));
    const __VLS_198 = __VLS_197({
        size: (13),
    }, ...__VLS_functionalComponentArgsRest(__VLS_197));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
        id: "import-title",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showImport))
                    return;
                __VLS_ctx.showImport = false;
            } },
        ...{ class: "icon-button dark" },
        type: "button",
        title: "关闭",
    });
    const __VLS_200 = {}.X;
    /** @type {[typeof __VLS_components.X, ]} */ ;
    // @ts-ignore
    const __VLS_201 = __VLS_asFunctionalComponent(__VLS_200, new __VLS_200({
        size: (18),
    }));
    const __VLS_202 = __VLS_201({
        size: (18),
    }, ...__VLS_functionalComponentArgsRest(__VLS_201));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ onDragover: (...[$event]) => {
                if (!(__VLS_ctx.showImport))
                    return;
                __VLS_ctx.isDragging = true;
            } },
        ...{ onDragleave: (...[$event]) => {
                if (!(__VLS_ctx.showImport))
                    return;
                __VLS_ctx.isDragging = false;
            } },
        ...{ onDrop: (__VLS_ctx.onDrop) },
        ...{ class: "drop-zone" },
        ...{ class: ({ dragging: __VLS_ctx.isDragging }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        ...{ onChange: (__VLS_ctx.onFileInput) },
        ref: "fileInput",
        ...{ class: "hidden-input" },
        type: "file",
        accept: "video/mp4,video/quicktime,video/x-m4v,video/webm",
        multiple: true,
    });
    /** @type {typeof __VLS_ctx.fileInput} */ ;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drop-icon" },
    });
    const __VLS_204 = {}.CloudUpload;
    /** @type {[typeof __VLS_components.CloudUpload, ]} */ ;
    // @ts-ignore
    const __VLS_205 = __VLS_asFunctionalComponent(__VLS_204, new __VLS_204({
        size: (24),
    }));
    const __VLS_206 = __VLS_205({
        size: (24),
    }, ...__VLS_functionalComponentArgsRest(__VLS_205));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.triggerFilePicker) },
        ...{ class: "button button-quiet compact" },
        type: "button",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    if (__VLS_ctx.pendingFiles.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "pending-files" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "pending-heading" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.pendingFiles.length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.pendingFileSize);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "pending-list" },
        });
        for (const [file, index] of __VLS_getVForSourceType((__VLS_ctx.pendingFiles))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (`${file.name}-${index}`),
                ...{ class: "pending-file" },
            });
            const __VLS_208 = {}.FileVideo;
            /** @type {[typeof __VLS_components.FileVideo, ]} */ ;
            // @ts-ignore
            const __VLS_209 = __VLS_asFunctionalComponent(__VLS_208, new __VLS_208({
                size: (16),
            }));
            const __VLS_210 = __VLS_209({
                size: (16),
            }, ...__VLS_functionalComponentArgsRest(__VLS_209));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (file.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            ((file.size / 1024 / 1024).toFixed(1));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.showImport))
                            return;
                        if (!(__VLS_ctx.pendingFiles.length))
                            return;
                        __VLS_ctx.removePendingFile(index);
                    } },
                type: "button",
                title: "移除",
            });
            const __VLS_212 = {}.X;
            /** @type {[typeof __VLS_components.X, ]} */ ;
            // @ts-ignore
            const __VLS_213 = __VLS_asFunctionalComponent(__VLS_212, new __VLS_212({
                size: (14),
            }));
            const __VLS_214 = __VLS_213({
                size: (14),
            }, ...__VLS_functionalComponentArgsRest(__VLS_213));
        }
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "modal-footer" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "modal-local-state" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "live-dot" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showImport))
                    return;
                __VLS_ctx.showImport = false;
            } },
        ...{ class: "button button-quiet" },
        type: "button",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.importPendingFiles) },
        ...{ class: "button button-acid" },
        type: "button",
    });
    const __VLS_216 = {}.CloudUpload;
    /** @type {[typeof __VLS_components.CloudUpload, ]} */ ;
    // @ts-ignore
    const __VLS_217 = __VLS_asFunctionalComponent(__VLS_216, new __VLS_216({
        size: (16),
    }));
    const __VLS_218 = __VLS_217({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_217));
}
if (__VLS_ctx.showPlayerEditor) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerEditor))
                    return;
                __VLS_ctx.showPlayerEditor = false;
            } },
        ...{ class: "modal-layer" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "modal player-modal" },
        role: "dialog",
        'aria-modal': "true",
        'aria-labelledby': "player-title",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "modal-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "panel-kicker" },
    });
    const __VLS_220 = {}.UsersRound;
    /** @type {[typeof __VLS_components.UsersRound, ]} */ ;
    // @ts-ignore
    const __VLS_221 = __VLS_asFunctionalComponent(__VLS_220, new __VLS_220({
        size: (13),
    }));
    const __VLS_222 = __VLS_221({
        size: (13),
    }, ...__VLS_functionalComponentArgsRest(__VLS_221));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
        id: "player-title",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerEditor))
                    return;
                __VLS_ctx.showPlayerEditor = false;
            } },
        ...{ class: "icon-button dark" },
        type: "button",
        title: "关闭",
    });
    const __VLS_224 = {}.X;
    /** @type {[typeof __VLS_components.X, ]} */ ;
    // @ts-ignore
    const __VLS_225 = __VLS_asFunctionalComponent(__VLS_224, new __VLS_224({
        size: (18),
    }));
    const __VLS_226 = __VLS_225({
        size: (18),
    }, ...__VLS_functionalComponentArgsRest(__VLS_225));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "player-edit-preview" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "player-badge large" },
        ...{ style: ({ '--badge-color': __VLS_ctx.playerDraft.color }) },
    });
    (__VLS_ctx.playerDraft.number);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.playerDraft.code);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    (__VLS_ctx.playerDraft.identityType === 'temporary' ? 'AI 生成的临时身份' : '号码识别身份');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "edit-confidence" },
    });
    (Math.round(__VLS_ctx.playerDraft.confidence * 100));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "form-grid" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        value: (__VLS_ctx.playerDraft.name),
        type: "text",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        value: (__VLS_ctx.playerDraft.number),
        type: "text",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({
        value: (__VLS_ctx.playerDraft.team),
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
        value: "home",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
        value: "away",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({
        value: (__VLS_ctx.playerDraft.status),
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
        value: "confirmed",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
        value: "candidate",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "modal-footer" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerEditor))
                    return;
                __VLS_ctx.showToast('删除身份需要在后端确认');
            } },
        ...{ class: "button button-quiet danger" },
        type: "button",
    });
    const __VLS_228 = {}.Trash2;
    /** @type {[typeof __VLS_components.Trash2, ]} */ ;
    // @ts-ignore
    const __VLS_229 = __VLS_asFunctionalComponent(__VLS_228, new __VLS_228({
        size: (15),
    }));
    const __VLS_230 = __VLS_229({
        size: (15),
    }, ...__VLS_functionalComponentArgsRest(__VLS_229));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerEditor))
                    return;
                __VLS_ctx.showPlayerEditor = false;
            } },
        ...{ class: "button button-quiet" },
        type: "button",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.savePlayer) },
        ...{ class: "button button-acid" },
        type: "button",
    });
    const __VLS_232 = {}.Check;
    /** @type {[typeof __VLS_components.Check, ]} */ ;
    // @ts-ignore
    const __VLS_233 = __VLS_asFunctionalComponent(__VLS_232, new __VLS_232({
        size: (16),
    }));
    const __VLS_234 = __VLS_233({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_233));
}
if (__VLS_ctx.showPlayerDetail) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerDetail))
                    return;
                __VLS_ctx.showPlayerDetail = false;
            } },
        ...{ class: "detail-layer" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
        ...{ class: "player-detail-drawer" },
        role: "dialog",
        'aria-modal': "true",
        'aria-labelledby': "player-detail-title",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "panel-kicker" },
    });
    const __VLS_236 = {}.UsersRound;
    /** @type {[typeof __VLS_components.UsersRound, ]} */ ;
    // @ts-ignore
    const __VLS_237 = __VLS_asFunctionalComponent(__VLS_236, new __VLS_236({
        size: (13),
    }));
    const __VLS_238 = __VLS_237({
        size: (13),
    }, ...__VLS_functionalComponentArgsRest(__VLS_237));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
        id: "player-detail-title",
    });
    (__VLS_ctx.selectedPlayer.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    (__VLS_ctx.selectedPlayer.teamName);
    (__VLS_ctx.selectedPlayer.identityType === 'temporary' ? '本场临时身份' : `号码 ${__VLS_ctx.selectedPlayer.number}`);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerDetail))
                    return;
                __VLS_ctx.showPlayerDetail = false;
            } },
        ...{ class: "icon-button dark" },
        type: "button",
        title: "关闭球员详情",
    });
    const __VLS_240 = {}.X;
    /** @type {[typeof __VLS_components.X, ]} */ ;
    // @ts-ignore
    const __VLS_241 = __VLS_asFunctionalComponent(__VLS_240, new __VLS_240({
        size: (18),
    }));
    const __VLS_242 = __VLS_241({
        size: (18),
    }, ...__VLS_functionalComponentArgsRest(__VLS_241));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-player-summary" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "player-badge large" },
        ...{ style: ({ '--badge-color': __VLS_ctx.selectedPlayer.color }) },
    });
    (__VLS_ctx.selectedPlayer.number);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayer.code);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
    (Math.round(__VLS_ctx.selectedPlayer.confidence * 100));
    (__VLS_ctx.selectedPlayer.tracks);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showPlayerDetail))
                    return;
                __VLS_ctx.openPlayerEditor(__VLS_ctx.selectedPlayer);
            } },
        ...{ class: "mini-action muted" },
        type: "button",
        title: "修正球员身份",
    });
    const __VLS_244 = {}.Settings2;
    /** @type {[typeof __VLS_components.Settings2, ]} */ ;
    // @ts-ignore
    const __VLS_245 = __VLS_asFunctionalComponent(__VLS_244, new __VLS_244({
        size: (14),
    }));
    const __VLS_246 = __VLS_245({
        size: (14),
    }, ...__VLS_functionalComponentArgsRest(__VLS_245));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-stat-grid" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.pts ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.fg ?? '0 / 0');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.three ?? '0 / 0');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.reb ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.ast ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlayerStats?.stl ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-section-heading" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "panel-kicker" },
    });
    const __VLS_248 = {}.Sparkles;
    /** @type {[typeof __VLS_components.Sparkles, ]} */ ;
    // @ts-ignore
    const __VLS_249 = __VLS_asFunctionalComponent(__VLS_248, new __VLS_248({
        size: (13),
    }));
    const __VLS_250 = __VLS_249({
        size: (13),
    }, ...__VLS_functionalComponentArgsRest(__VLS_249));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.selectedPlayerScoringEvents.length);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "live-update" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "live-dot" },
    });
    if (__VLS_ctx.selectedPlayerScoringEvents.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "highlight-list" },
        });
        for (const [event] of __VLS_getVForSourceType((__VLS_ctx.selectedPlayerScoringEvents))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.showPlayerDetail))
                            return;
                        if (!(__VLS_ctx.selectedPlayerScoringEvents.length))
                            return;
                        __VLS_ctx.openScoringEvent(event);
                    } },
                key: (event.id),
                ...{ class: "highlight-item" },
                type: "button",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "highlight-thumb" },
                ...{ class: (`highlight-thumb-${event.team}`) },
            });
            const __VLS_252 = {}.Play;
            /** @type {[typeof __VLS_components.Play, ]} */ ;
            // @ts-ignore
            const __VLS_253 = __VLS_asFunctionalComponent(__VLS_252, new __VLS_252({
                size: (16),
                fill: "currentColor",
            }));
            const __VLS_254 = __VLS_253({
                size: (16),
                fill: "currentColor",
            }, ...__VLS_functionalComponentArgsRest(__VLS_253));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (event.time);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "highlight-copy" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (event.type);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (__VLS_ctx.getTeamName(event.team));
            (__VLS_ctx.clips.find((clip) => clip.id === event.clipId)?.name ?? '源片段');
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "highlight-points" },
            });
            (event.points);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            const __VLS_256 = {}.ChevronRight;
            /** @type {[typeof __VLS_components.ChevronRight, ]} */ ;
            // @ts-ignore
            const __VLS_257 = __VLS_asFunctionalComponent(__VLS_256, new __VLS_256({
                size: (15),
            }));
            const __VLS_258 = __VLS_257({
                size: (15),
            }, ...__VLS_functionalComponentArgsRest(__VLS_257));
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "empty-highlights" },
        });
        const __VLS_260 = {}.Film;
        /** @type {[typeof __VLS_components.Film, ]} */ ;
        // @ts-ignore
        const __VLS_261 = __VLS_asFunctionalComponent(__VLS_260, new __VLS_260({
            size: (19),
        }));
        const __VLS_262 = __VLS_261({
            size: (19),
        }, ...__VLS_functionalComponentArgsRest(__VLS_261));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-footnote" },
    });
    const __VLS_264 = {}.CircleAlert;
    /** @type {[typeof __VLS_components.CircleAlert, ]} */ ;
    // @ts-ignore
    const __VLS_265 = __VLS_asFunctionalComponent(__VLS_264, new __VLS_264({
        size: (14),
    }));
    const __VLS_266 = __VLS_265({
        size: (14),
    }, ...__VLS_functionalComponentArgsRest(__VLS_265));
}
const __VLS_268 = {}.Transition;
/** @type {[typeof __VLS_components.Transition, typeof __VLS_components.Transition, ]} */ ;
// @ts-ignore
const __VLS_269 = __VLS_asFunctionalComponent(__VLS_268, new __VLS_268({
    name: "toast",
}));
const __VLS_270 = __VLS_269({
    name: "toast",
}, ...__VLS_functionalComponentArgsRest(__VLS_269));
__VLS_271.slots.default;
if (__VLS_ctx.toastMessage) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "toast-message" },
    });
    const __VLS_272 = {}.CheckCheck;
    /** @type {[typeof __VLS_components.CheckCheck, ]} */ ;
    // @ts-ignore
    const __VLS_273 = __VLS_asFunctionalComponent(__VLS_272, new __VLS_272({
        size: (16),
    }));
    const __VLS_274 = __VLS_273({
        size: (16),
    }, ...__VLS_functionalComponentArgsRest(__VLS_273));
    (__VLS_ctx.toastMessage);
}
var __VLS_271;
/** @type {__VLS_StyleScopedClasses['app-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-lockup']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-mark']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar-section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['match-switcher']} */ ;
/** @type {__VLS_StyleScopedClasses['match-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['match-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['primary-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-item']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar-spacer']} */ ;
/** @type {__VLS_StyleScopedClasses['engine-card']} */ ;
/** @type {__VLS_StyleScopedClasses['engine-card-top']} */ ;
/** @type {__VLS_StyleScopedClasses['live-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['engine-meter']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar-footer']} */ ;
/** @type {__VLS_StyleScopedClasses['footer-action']} */ ;
/** @type {__VLS_StyleScopedClasses['footer-action']} */ ;
/** @type {__VLS_StyleScopedClasses['main-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['topbar']} */ ;
/** @type {__VLS_StyleScopedClasses['breadcrumb']} */ ;
/** @type {__VLS_StyleScopedClasses['topbar-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['connection-state']} */ ;
/** @type {__VLS_StyleScopedClasses['offline']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['page-content']} */ ;
/** @type {__VLS_StyleScopedClasses['page-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['eyebrow']} */ ;
/** @type {__VLS_StyleScopedClasses['eyebrow-line']} */ ;
/** @type {__VLS_StyleScopedClasses['heading-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-strip']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-index']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-subline']} */ ;
/** @type {__VLS_StyleScopedClasses['positive']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-index']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-subline']} */ ;
/** @type {__VLS_StyleScopedClasses['warning']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-index']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-subline']} */ ;
/** @type {__VLS_StyleScopedClasses['positive']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-engine']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-index']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-engine-line']} */ ;
/** @type {__VLS_StyleScopedClasses['status-orbit']} */ ;
/** @type {__VLS_StyleScopedClasses['metric-subline']} */ ;
/** @type {__VLS_StyleScopedClasses['workspace-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['workspace-grid-focus']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['review-workspace']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['accent-marker']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['confidence-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['review-layout']} */ ;
/** @type {__VLS_StyleScopedClasses['video-column']} */ ;
/** @type {__VLS_StyleScopedClasses['video-stage']} */ ;
/** @type {__VLS_StyleScopedClasses['source-video']} */ ;
/** @type {__VLS_StyleScopedClasses['court-scene']} */ ;
/** @type {__VLS_StyleScopedClasses['playing']} */ ;
/** @type {__VLS_StyleScopedClasses['court-grain']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line-mid']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line-key']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line-key-left']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line-key']} */ ;
/** @type {__VLS_StyleScopedClasses['court-line-key-right']} */ ;
/** @type {__VLS_StyleScopedClasses['court-arc']} */ ;
/** @type {__VLS_StyleScopedClasses['court-arc-left']} */ ;
/** @type {__VLS_StyleScopedClasses['court-arc']} */ ;
/** @type {__VLS_StyleScopedClasses['court-arc-right']} */ ;
/** @type {__VLS_StyleScopedClasses['court-hoop']} */ ;
/** @type {__VLS_StyleScopedClasses['court-hoop-left']} */ ;
/** @type {__VLS_StyleScopedClasses['court-hoop']} */ ;
/** @type {__VLS_StyleScopedClasses['court-hoop-right']} */ ;
/** @type {__VLS_StyleScopedClasses['court-player']} */ ;
/** @type {__VLS_StyleScopedClasses['ball-track']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-tag']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-tag-top']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-tag']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-tag-bottom']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-frame-label']} */ ;
/** @type {__VLS_StyleScopedClasses['scene-focus-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['video-overlay-top']} */ ;
/** @type {__VLS_StyleScopedClasses['rec-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['video-overlay-bottom']} */ ;
/** @type {__VLS_StyleScopedClasses['video-control-row']} */ ;
/** @type {__VLS_StyleScopedClasses['play-button']} */ ;
/** @type {__VLS_StyleScopedClasses['time-readout']} */ ;
/** @type {__VLS_StyleScopedClasses['scrubber-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['scrubber']} */ ;
/** @type {__VLS_StyleScopedClasses['scrubber-markers']} */ ;
/** @type {__VLS_StyleScopedClasses['speed-control']} */ ;
/** @type {__VLS_StyleScopedClasses['selected']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['small']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-context-row']} */ ;
/** @type {__VLS_StyleScopedClasses['event-review-column']} */ ;
/** @type {__VLS_StyleScopedClasses['event-column-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['text-button']} */ ;
/** @type {__VLS_StyleScopedClasses['event-list']} */ ;
/** @type {__VLS_StyleScopedClasses['event-item']} */ ;
/** @type {__VLS_StyleScopedClasses['event-item-top']} */ ;
/** @type {__VLS_StyleScopedClasses['event-type-mark']} */ ;
/** @type {__VLS_StyleScopedClasses['event-main-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['event-title-line']} */ ;
/** @type {__VLS_StyleScopedClasses['event-confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['event-item-bottom']} */ ;
/** @type {__VLS_StyleScopedClasses['player-select']} */ ;
/** @type {__VLS_StyleScopedClasses['player-swatch']} */ ;
/** @type {__VLS_StyleScopedClasses['event-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['event-status-label']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-action']} */ ;
/** @type {__VLS_StyleScopedClasses['confirm']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-action']} */ ;
/** @type {__VLS_StyleScopedClasses['ignore']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-action']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['manual-event-button']} */ ;
/** @type {__VLS_StyleScopedClasses['review-note']} */ ;
/** @type {__VLS_StyleScopedClasses['overview-rail']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['rail-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['small']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-list']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-row']} */ ;
/** @type {__VLS_StyleScopedClasses['player-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['candidate']} */ ;
/** @type {__VLS_StyleScopedClasses['identity-arrow']} */ ;
/** @type {__VLS_StyleScopedClasses['rail-link']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['rail-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-percent']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-stats']} */ ;
/** @type {__VLS_StyleScopedClasses['analysis-live-state']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['accent-marker']} */ ;
/** @type {__VLS_StyleScopedClasses['coral']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-header-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['segmented-control']} */ ;
/** @type {__VLS_StyleScopedClasses['selected']} */ ;
/** @type {__VLS_StyleScopedClasses['selected']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
/** @type {__VLS_StyleScopedClasses['table-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-table']} */ ;
/** @type {__VLS_StyleScopedClasses['player-col']} */ ;
/** @type {__VLS_StyleScopedClasses['player-col']} */ ;
/** @type {__VLS_StyleScopedClasses['player-cell-button']} */ ;
/** @type {__VLS_StyleScopedClasses['table-avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['points-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-up']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-down']} */ ;
/** @type {__VLS_StyleScopedClasses['trend-flat']} */ ;
/** @type {__VLS_StyleScopedClasses['team-stat-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['team-stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['team-stat-top']} */ ;
/** @type {__VLS_StyleScopedClasses['team-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['team-code']} */ ;
/** @type {__VLS_StyleScopedClasses['team-score']} */ ;
/** @type {__VLS_StyleScopedClasses['team-stat-line']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['full-queue-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['accent-marker']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['small']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-table']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-row']} */ ;
/** @type {__VLS_StyleScopedClasses['selected']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-number']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-thumb']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-name']} */ ;
/** @type {__VLS_StyleScopedClasses['queue-event-count']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-status']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['accent-marker']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-summary-note']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-columns']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster-home']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['team-color-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['home-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-row']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-number']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['candidate']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster-away']} */ ;
/** @type {__VLS_StyleScopedClasses['team-roster-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['team-color-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['away-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-row']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-number']} */ ;
/** @type {__VLS_StyleScopedClasses['roster-confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['candidate']} */ ;
/** @type {__VLS_StyleScopedClasses['tool-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['library-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-header']} */ ;
/** @type {__VLS_StyleScopedClasses['library-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['accent-marker']} */ ;
/** @type {__VLS_StyleScopedClasses['library-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['analysis-live-label']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['library-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['search-field']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-pills']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['library-total']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-card']} */ ;
/** @type {__VLS_StyleScopedClasses['selected']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-card-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-court']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-court-line']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-player']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-player-a']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-player']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-player-b']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-sequence']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-length']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-card-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-status']} */ ;
/** @type {__VLS_StyleScopedClasses['clip-card-foot']} */ ;
/** @type {__VLS_StyleScopedClasses['retry-button']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-layer']} */ ;
/** @type {__VLS_StyleScopedClasses['modal']} */ ;
/** @type {__VLS_StyleScopedClasses['import-modal']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-zone']} */ ;
/** @type {__VLS_StyleScopedClasses['dragging']} */ ;
/** @type {__VLS_StyleScopedClasses['hidden-input']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['compact']} */ ;
/** @type {__VLS_StyleScopedClasses['pending-files']} */ ;
/** @type {__VLS_StyleScopedClasses['pending-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['pending-list']} */ ;
/** @type {__VLS_StyleScopedClasses['pending-file']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-local-state']} */ ;
/** @type {__VLS_StyleScopedClasses['live-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-layer']} */ ;
/** @type {__VLS_StyleScopedClasses['modal']} */ ;
/** @type {__VLS_StyleScopedClasses['player-modal']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['player-edit-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['player-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['large']} */ ;
/** @type {__VLS_StyleScopedClasses['edit-confidence']} */ ;
/** @type {__VLS_StyleScopedClasses['form-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-footer']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['danger']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-quiet']} */ ;
/** @type {__VLS_StyleScopedClasses['button']} */ ;
/** @type {__VLS_StyleScopedClasses['button-acid']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-layer']} */ ;
/** @type {__VLS_StyleScopedClasses['player-detail-drawer']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-header']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['icon-button']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-player-summary']} */ ;
/** @type {__VLS_StyleScopedClasses['player-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['large']} */ ;
/** @type {__VLS_StyleScopedClasses['mini-action']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-stat-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-section-heading']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['live-update']} */ ;
/** @type {__VLS_StyleScopedClasses['live-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-list']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-item']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-thumb']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-copy']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-points']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-highlights']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-footnote']} */ ;
/** @type {__VLS_StyleScopedClasses['toast-message']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            ArrowDownRight: ArrowDownRight,
            ArrowUpRight: ArrowUpRight,
            Bell: Bell,
            Check: Check,
            CheckCheck: CheckCheck,
            ChevronDown: ChevronDown,
            ChevronRight: ChevronRight,
            CircleAlert: CircleAlert,
            CircleDot: CircleDot,
            CloudUpload: CloudUpload,
            Cpu: Cpu,
            Download: Download,
            Ellipsis: Ellipsis,
            FileDown: FileDown,
            FileVideo: FileVideo,
            Film: Film,
            Gauge: Gauge,
            ListFilter: ListFilter,
            Pause: Pause,
            Play: Play,
            Plus: Plus,
            RefreshCw: RefreshCw,
            ScanLine: ScanLine,
            Search: Search,
            Settings2: Settings2,
            Sparkles: Sparkles,
            Target: Target,
            Trash2: Trash2,
            Upload: Upload,
            UsersRound: UsersRound,
            X: X,
            navItems: navItems,
            players: players,
            clips: clips,
            events: events,
            activeTab: activeTab,
            statsTab: statsTab,
            clipSearch: clipSearch,
            clipFilter: clipFilter,
            isAnalyzing: isAnalyzing,
            analysisProgress: analysisProgress,
            processedClipCount: processedClipCount,
            totalClipCount: totalClipCount,
            currentSeconds: currentSeconds,
            isPlaying: isPlaying,
            playbackRate: playbackRate,
            videoRef: videoRef,
            fileInput: fileInput,
            pendingFiles: pendingFiles,
            showImport: showImport,
            showPlayerEditor: showPlayerEditor,
            showPlayerDetail: showPlayerDetail,
            isDragging: isDragging,
            toastMessage: toastMessage,
            engineMode: engineMode,
            engineDetail: engineDetail,
            backendOnline: backendOnline,
            playerDraft: playerDraft,
            selectedClip: selectedClip,
            selectedEvents: selectedEvents,
            selectedPlayer: selectedPlayer,
            selectedPlayerStats: selectedPlayerStats,
            selectedPlayerScoringEvents: selectedPlayerScoringEvents,
            pendingEventCount: pendingEventCount,
            confirmedEventCount: confirmedEventCount,
            analyzedProgress: analyzedProgress,
            viewTitle: viewTitle,
            filteredClips: filteredClips,
            statRows: statRows,
            pendingFileSize: pendingFileSize,
            teamTotals: teamTotals,
            showToast: showToast,
            setTab: setTab,
            selectClip: selectClip,
            toggleVideo: toggleVideo,
            updatePlaying: updatePlaying,
            updateCurrentTime: updateCurrentTime,
            seekVideo: seekVideo,
            changePlaybackRate: changePlaybackRate,
            formatTime: formatTime,
            clipStatusLabel: clipStatusLabel,
            eventStatusLabel: eventStatusLabel,
            getPlayer: getPlayer,
            getTeamName: getTeamName,
            confirmEvent: confirmEvent,
            ignoreEvent: ignoreEvent,
            confirmAllEvents: confirmAllEvents,
            updateEventPlayer: updateEventPlayer,
            addManualEvent: addManualEvent,
            openPlayerEditor: openPlayerEditor,
            openPlayerDetail: openPlayerDetail,
            openScoringEvent: openScoringEvent,
            savePlayer: savePlayer,
            triggerFilePicker: triggerFilePicker,
            onFileInput: onFileInput,
            onDrop: onDrop,
            removePendingFile: removePendingFile,
            importPendingFiles: importPendingFiles,
            retryClip: retryClip,
            exportStats: exportStats,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
