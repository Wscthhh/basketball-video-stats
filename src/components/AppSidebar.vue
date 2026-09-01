<script setup lang="ts">
import { ref } from 'vue'
import { Activity, CheckCheck, ChevronDown, Cpu, Film, FolderOpen, Plus, ScanLine, Trash2 } from 'lucide-vue-next'
import type { Health, Match, TabKey } from '../types'

defineProps<{
  tab: TabKey
  matches: Match[]
  match: Match | null
  health: Health | null
  readyModels: string
  pendingCount: number
  clipCount: number
}>()

const emit = defineEmits<{
  selectTab: [tab: TabKey]
  selectMatch: [id: string]
  createMatch: []
  openFolder: []
  deleteMatch: []
}>()

const showMatchMenu = ref(false)

function selectMatch(id: string) {
  showMatchMenu.value = false
  emit('selectMatch', id)
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand-lockup">
      <div class="brand-mark"><ScanLine :size="20" /></div>
      <div><strong>COURTTRACE</strong><span>LOCAL SCOUTING DESK</span></div>
    </div>
    <div class="sidebar-section-label">当前比赛</div>
    <button v-if="match" class="match-switcher" type="button" @click="showMatchMenu = !showMatchMenu">
      <span class="match-badge">◎</span>
      <span class="match-copy">
        <strong><em v-if="match.isTest" class="test-tag">TEST</em>{{ match.name }}</strong>
        <small>{{ match.venue || '未填写场地' }}</small>
      </span>
      <ChevronDown :size="16" />
    </button>
    <div v-if="showMatchMenu" class="match-menu">
      <button v-for="item in matches" :key="item.id" type="button" :class="{ active: item.id === match?.id }" @click="selectMatch(item.id)">
        {{ item.name }}
      </button>
      <button type="button" @click="emit('openFolder')"><FolderOpen :size="14" /> 打开存储文件夹</button>
      <button class="match-danger" type="button" @click="emit('deleteMatch')"><Trash2 :size="14" /> 删除本场比赛</button>
    </div>
    <button class="sidebar-create-button" type="button" @click="emit('createMatch')">
      <Plus :size="15" /> 创建比赛
    </button>
    <nav class="primary-nav">
      <button class="nav-item" :class="{ active: tab === 'overview' }" type="button" @click="emit('selectTab', 'overview')">
        <Activity :size="18" /><span>比赛总览</span><em></em>
      </button>
      <button class="nav-item" :class="{ active: tab === 'review' }" type="button" @click="emit('selectTab', 'review')">
        <CheckCheck :size="18" /><span>复核队列</span><em>{{ pendingCount }}</em>
      </button>
      <button class="nav-item" :class="{ active: tab === 'clips' }" type="button" @click="emit('selectTab', 'clips')">
        <Film :size="18" /><span>片段库</span><em>{{ clipCount }}</em>
      </button>
    </nav>
    <div class="sidebar-spacer"></div>
    <div class="engine-card">
      <div class="engine-card-top"><span class="live-dot"></span><span>本地推理引擎</span><Cpu :size="15" /></div>
      <strong>{{ health?.analyzer?.mode || '未连接' }}</strong>
      <small>{{ health?.analyzer?.ready ? '模型已就绪' : '模型未就绪' }}<template v-if="readyModels"> · {{ readyModels }}</template></small>
    </div>
  </aside>
</template>

<style scoped>
.match-menu button{display:flex;align-items:center;gap:7px}.match-menu .match-danger{color:#ff9f91}.match-menu .match-danger:hover{color:#ffd1c9;background:#321b18}
</style>
