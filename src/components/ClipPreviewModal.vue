<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Trash2, X } from 'lucide-vue-next'
import { clipSource, statusLabel } from '../presentation'
import type { Clip, Team } from '../types'
import TeamColorSwatch from './TeamColorSwatch.vue'

const props = defineProps<{ clip: Clip; homeTeam?: Team; awayTeam?: Team; busy: boolean; reviewClips?: Clip[] }>()
const emit = defineEmits<{
  close: []
  confirmTeam: [teamId: string | null]
  saveTeam: [teamId: string | null]
  startReassign: []
  cancelReassign: []
  deleteClip: []
  navigate: [direction: -1 | 1]
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const selectedTeamId = ref<string | null>(props.clip.teamId ?? null)
const editingTeam = ref(!props.clip.teamId)
const teamConfirmed = computed(() => props.clip.teamSource === 'manual')
const reviewIndex = computed(() => (props.reviewClips ?? []).findIndex((clip) => clip.id === props.clip.id))
const inReviewQueue = computed(() => reviewIndex.value >= 0)
const canNavigatePrevious = computed(() => reviewIndex.value > 0)
const canNavigateNext = computed(() => reviewIndex.value >= 0 && reviewIndex.value < (props.reviewClips?.length ?? 0) - 1)
const assignedTeamName = computed(() => {
  const homeTeam = props.homeTeam
  const awayTeam = props.awayTeam
  if (homeTeam && props.clip.teamId === homeTeam.id) return homeTeam.name
  if (awayTeam && props.clip.teamId === awayTeam.id) return awayTeam.name
  return '待判断'
})

function selectTeam(teamId: string | null) {
  selectedTeamId.value = teamId
}

function startReassign() {
  editingTeam.value = true
  selectedTeamId.value = props.clip.teamId ?? null
  emit('startReassign')
}

function cancelReassign() {
  editingTeam.value = false
  selectedTeamId.value = props.clip.teamId ?? null
  emit('cancelReassign')
}

watch(() => props.clip.id, () => {
  selectedTeamId.value = props.clip.teamId ?? null
  editingTeam.value = !props.clip.teamId
})

onMounted(() => void videoRef.value?.play().catch(() => undefined))

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft' && canNavigatePrevious.value) emit('navigate', -1)
  if (event.key === 'ArrowRight' && canNavigateNext.value) emit('navigate', 1)
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <div class="modal-layer highlight-player-layer" @click.self="$emit('close')">
    <section class="modal highlight-player-modal">
      <div class="modal-header">
        <div><span class="panel-kicker">CLIP PREVIEW</span><h2>{{ clip.name }}</h2><p>{{ statusLabel(clip.status) }} · {{ clipSource(clip) }}</p></div>
        <button class="icon-button dark" type="button" title="关闭" @click="$emit('close')"><X :size="18" /></button>
      </div>
      <div v-if="inReviewQueue" class="clip-review-navigation">
        <button class="icon-button dark" type="button" title="上一个待确认片段" :disabled="busy || !canNavigatePrevious" @click="emit('navigate', -1)"><ChevronLeft :size="18" /></button>
        <span>{{ reviewIndex + 1 }} / {{ reviewClips?.length }}</span>
        <button class="icon-button dark" type="button" title="下一个待确认片段" :disabled="busy || !canNavigateNext" @click="emit('navigate', 1)"><ChevronRight :size="18" /></button>
      </div>
       <div class="highlight-player-video">
         <video v-if="clip.previewUrl" ref="videoRef" controls playsinline :src="clip.previewUrl"></video>
         <div v-else class="professional-empty"><strong>该片段暂无可播放预览</strong></div>
       </div>
       <div class="highlight-player-meta"><span>片段状态 {{ statusLabel(clip.status) }}</span><span class="assigned-team"><TeamColorSwatch :color="clip.teamId === homeTeam?.id ? homeTeam?.color : clip.teamId === awayTeam?.id ? awayTeam?.color : null" />球队归属 {{ assignedTeamName }}</span></div>
       <div class="clip-detail-actions">
         <div class="clip-detail-team-label"><span class="panel-kicker">片段归属</span><strong>{{ assignedTeamName }}</strong></div>
         <template v-if="!teamConfirmed">
           <div class="team-assignment-editor">
             <div class="team-choice" aria-label="选择片段归属">
             <button v-if="homeTeam?.id" type="button" :disabled="busy" :class="{ selected: selectedTeamId === homeTeam.id }" @click="selectTeam(homeTeam.id)"><TeamColorSwatch :color="homeTeam.color" />{{ homeTeam.name }}</button>
             <button v-if="awayTeam?.id" type="button" :disabled="busy" :class="{ selected: selectedTeamId === awayTeam.id }" @click="selectTeam(awayTeam.id)"><TeamColorSwatch :color="awayTeam.color" />{{ awayTeam.name }}</button>
               <button type="button" :disabled="busy" :class="{ selected: selectedTeamId === null }" @click="selectTeam(null)">待判断</button>
             </div>
             <button class="button button-acid" type="button" :disabled="busy" @click="emit('confirmTeam', selectedTeamId)">确认归属</button>
           </div>
         </template>
         <template v-else-if="!editingTeam">
           <button class="button button-quiet" type="button" :disabled="busy" @click="startReassign">修正归属</button>
         </template>
         <template v-else>
           <div class="team-assignment-editor">
             <div class="team-choice" aria-label="修正片段归属">
               <button v-if="homeTeam?.id" type="button" :disabled="busy" :class="{ selected: selectedTeamId === homeTeam.id }" @click="selectTeam(homeTeam.id)"><TeamColorSwatch :color="homeTeam.color" />{{ homeTeam.name }}</button>
               <button v-if="awayTeam?.id" type="button" :disabled="busy" :class="{ selected: selectedTeamId === awayTeam.id }" @click="selectTeam(awayTeam.id)"><TeamColorSwatch :color="awayTeam.color" />{{ awayTeam.name }}</button>
               <button type="button" :disabled="busy" :class="{ selected: selectedTeamId === null }" @click="selectTeam(null)">待判断</button>
             </div>
             <div class="team-assignment-actions">
               <button class="button button-acid" type="button" :disabled="busy" @click="emit('saveTeam', selectedTeamId)">保存修正</button>
               <button class="button button-quiet" type="button" :disabled="busy" @click="cancelReassign">取消修正</button>
             </div>
           </div>
         </template>
         <button class="button button-danger" type="button" :disabled="busy" @click="emit('deleteClip')"><Trash2 :size="15" /> 删除片段</button>
       </div>
    </section>
  </div>
</template>

<style scoped>
.clip-review-navigation{display:flex;align-items:center;justify-content:center;gap:12px;margin:14px 0 2px;color:#a9b8aa;font-size:12px}.clip-review-navigation .icon-button:disabled{cursor:not-allowed;opacity:.35}.clip-detail-actions{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;padding-top:18px}.clip-detail-team-label{display:grid;gap:5px;margin-right:auto}.clip-detail-team-label strong{color:#dfe9df;font-size:12px}.team-assignment-editor{display:grid;justify-items:end;gap:10px}.team-assignment-actions{display:flex;gap:7px}.button-danger{color:#ffd7cf;background:#301815;border:1px solid #8d3f34}.button-danger:hover{color:#fff;background:#a33d30;border-color:#c95849}.team-choice button:disabled{cursor:not-allowed;opacity:.45}.team-choice button{display:inline-flex;align-items:center;gap:6px}
@media(max-width:760px){.clip-detail-actions{align-items:stretch;flex-direction:column}.button-danger{width:100%}}
</style>
