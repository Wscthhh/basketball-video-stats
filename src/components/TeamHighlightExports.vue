<script setup lang="ts">
import { Download, Film, LoaderCircle, WandSparkles } from 'lucide-vue-next'
import type { Team, TeamHighlightExport } from '../types'

const props = defineProps<{ homeTeam?: Team; awayTeam?: Team; exports: TeamHighlightExport[]; busy: boolean }>()
defineEmits<{ generate: [teamId: string] }>()

function latest(teamId?: string) {
  return props.exports.find((item) => item.teamId === teamId)
}
</script>

<template>
  <section class="tool-panel team-export-panel">
    <div class="panel-header"><div><div class="panel-kicker">TEAM HIGHLIGHT EXPORTS</div><h2>球队集锦合集</h2></div><span class="highlight-count">包含 AI 归属和已确认片段</span></div>
    <div class="team-export-grid">
      <article v-for="team in [homeTeam, awayTeam]" :key="team?.id" class="team-export-card">
        <div class="team-export-heading"><div><strong>{{ team?.name || '球队' }}</strong><small>确认片段合集</small></div><button class="button button-quiet" type="button" :disabled="busy || !team?.id" @click="$emit('generate', team!.id!)"><WandSparkles :size="15" />{{ latest(team?.id)?.status === 'running' || latest(team?.id)?.status === 'queued' ? '生成中' : '生成合集' }}</button></div>
        <template v-if="latest(team?.id)?.status === 'completed' && latest(team?.id)?.downloadUrl">
          <video class="team-export-video" controls playsinline :src="latest(team?.id)?.downloadUrl ?? undefined"></video>
          <a class="button button-acid team-export-download" :href="latest(team?.id)?.downloadUrl || undefined" download><Download :size="15" />下载合集</a>
        </template>
        <div v-else-if="latest(team?.id)?.status === 'queued' || latest(team?.id)?.status === 'running'" class="professional-empty team-export-empty"><LoaderCircle class="spin" :size="22" /><strong>正在生成 {{ latest(team?.id)?.progress || 0 }}%</strong><span>确认片段正在合并，请稍候。</span></div>
        <div v-else-if="latest(team?.id)?.status === 'failed'" class="professional-empty team-export-empty"><Film :size="22" /><strong>生成失败</strong><span>{{ latest(team?.id)?.error || '请重试' }}</span></div>
        <div v-else class="professional-empty team-export-empty"><Film :size="22" /><strong>暂无合集</strong><span>点击生成，将该球队的确认片段合并为一个视频。</span></div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.team-export-panel{margin-top:18px}.team-export-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border-top:1px solid var(--line)}.team-export-card{min-width:0;padding:18px 20px;border-right:1px solid var(--line)}.team-export-card:last-child{border-right:0}.team-export-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.team-export-heading strong,.team-export-heading small{display:block}.team-export-heading small{margin-top:4px;color:var(--muted);font-size:10px}.team-export-video{display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#050806;border:1px solid var(--line);border-radius:4px}.team-export-download{margin-top:10px}.team-export-empty{min-height:145px;padding:18px}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:760px){.team-export-grid{grid-template-columns:1fr}.team-export-card{border-right:0;border-bottom:1px solid var(--line)}.team-export-card:last-child{border-bottom:0}}
</style>
