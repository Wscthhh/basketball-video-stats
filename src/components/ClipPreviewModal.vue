<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Trash2, X } from 'lucide-vue-next'
import { clipSource, statusLabel } from '../presentation'
import type { Clip, Team } from '../types'

const props = defineProps<{ clip: Clip; homeTeam?: Team; awayTeam?: Team; busy: boolean }>()
defineEmits<{ close: []; assignTeam: [teamId: string | null]; deleteClip: [] }>()

const videoRef = ref<HTMLVideoElement | null>(null)
const assignedTeamName = computed(() => {
  const homeTeam = props.homeTeam
  const awayTeam = props.awayTeam
  if (homeTeam && props.clip.teamId === homeTeam.id) return homeTeam.name
  if (awayTeam && props.clip.teamId === awayTeam.id) return awayTeam.name
  return '待判断'
})
onMounted(() => void videoRef.value?.play().catch(() => undefined))
</script>

<template>
  <div class="modal-layer highlight-player-layer" @click.self="$emit('close')">
    <section class="modal highlight-player-modal">
      <div class="modal-header">
        <div><span class="panel-kicker">CLIP PREVIEW</span><h2>{{ clip.name }}</h2><p>{{ statusLabel(clip.status) }} · {{ clipSource(clip) }}</p></div>
        <button class="icon-button dark" type="button" title="关闭" @click="$emit('close')"><X :size="18" /></button>
      </div>
      <div class="highlight-player-video">
        <video v-if="clip.previewUrl" ref="videoRef" controls playsinline :src="clip.previewUrl"></video>
        <div v-else class="professional-empty"><strong>该片段暂无可播放预览</strong></div>
      </div>
      <div class="highlight-player-meta"><span>片段状态 {{ statusLabel(clip.status) }}</span><span>球队归属 {{ assignedTeamName }}</span></div>
        <div class="clip-detail-actions">
          <div class="clip-detail-team-label"><span class="panel-kicker">片段归属</span><strong>{{ assignedTeamName }}</strong></div>
          <div class="team-choice" aria-label="调整片段归属">
          <button v-if="homeTeam?.id" type="button" :disabled="busy" :class="{ selected: clip.teamId === homeTeam.id }" @click="$emit('assignTeam', homeTeam.id)">{{ homeTeam.name }}</button>
          <button v-if="awayTeam?.id" type="button" :disabled="busy" :class="{ selected: clip.teamId === awayTeam.id }" @click="$emit('assignTeam', awayTeam.id)">{{ awayTeam.name }}</button>
          <button type="button" :disabled="busy" :class="{ selected: !clip.teamId }" @click="$emit('assignTeam', null)">待判断</button>
        </div>
        <button class="button button-danger" type="button" :disabled="busy" @click="$emit('deleteClip')"><Trash2 :size="15" /> 删除片段</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.clip-detail-actions{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;padding-top:18px}.clip-detail-team-label{display:grid;gap:5px;margin-right:auto}.clip-detail-team-label strong{color:#dfe9df;font-size:12px}.button-danger{color:#ffd7cf;background:#301815;border:1px solid #8d3f34}.button-danger:hover{color:#fff;background:#a33d30;border-color:#c95849}.team-choice button:disabled{cursor:not-allowed;opacity:.45}
@media(max-width:760px){.clip-detail-actions{align-items:stretch;flex-direction:column}.button-danger{width:100%}}
</style>
