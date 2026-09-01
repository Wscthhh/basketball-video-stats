import type { Clip } from './types'

const statusLabels: Record<string, string> = {
  queued: '排队中',
  processing: '分析中',
  review: '待复核',
  ready: '已完成',
  failed: '失败',
  interrupted: '已中断',
  running: '分析中',
  completed: '已完成',
}

export function statusLabel(status?: string) {
  return statusLabels[status ?? ''] ?? '暂无任务'
}

export function clipSource(clip: Clip) {
  if (clip.teamSource === 'manual') return '人工指定'
  if (clip.teamSource === 'ai') return 'AI 归属'
  return '待判断'
}

export function clipTeamStatus(clip: Clip) {
  if (clip.teamSource === 'manual' || clip.teamConfirmed === true) return '已确认'
  if (clip.teamSource === 'ai') return 'AI 归属'
  return '待确认'
}

export function clipTeamStatusClass(clip: Clip) {
  if (clip.teamSource === 'manual' || clip.teamConfirmed === true) return 'confirmed'
  if (clip.teamSource === 'ai') return 'ai'
  return 'pending'
}

export function formatSeconds(value?: number | null) {
  if (value == null) return '--:--'
  const minutes = Math.floor(value / 60).toString().padStart(2, '0')
  const seconds = Math.floor(value % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}
