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
  openFolder: [id: string]
  deleteMatch: [id: string]
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
      <div v-for="item in matches" :key="item.id" class="match-menu-row">
        <button type="button" :class="{ active: item.id === match?.id }" @click="selectMatch(item.id)">{{ item.name }}</button>
        <button class="match-action-button" type="button" title="打开比赛存储文件夹" :aria-label="`打开${item.name}存储文件夹`" @click="emit('openFolder', item.id)"><FolderOpen :size="14" /></button>
        <button class="match-action-button match-delete-button" type="button" title="删除本场比赛" :aria-label="`删除${item.name}`" @click="emit('deleteMatch', item.id)"><Trash2 :size="14" /></button>
      </div>
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
.match-menu-row{display:grid;grid-template-columns:minmax(0,1fr) 30px 30px;gap:4px;align-items:center}.match-menu-row>button:first-child{min-width:0;overflow:hidden;text-align:left;text-overflow:ellipsis;white-space:nowrap}.match-action-button{display:grid;width:30px;height:30px;padding:0;place-items:center;color:#8f9e94;background:#18221e;border:1px solid var(--line);border-radius:4px}.match-action-button:hover{color:var(--acid);border-color:var(--acid)}.match-delete-button:hover{color:#ff9f91;border-color:#87473e;background:#321b18}
</style>
