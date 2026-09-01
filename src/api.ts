import type { Clip, ClipCollections, EventRecord, Health, Match, Run, TeamHighlightExport, TeamTrainingStatus, Workspace } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    let detail = `API ${response.status}`
    try { detail = (await response.json()).detail ?? detail } catch { /* non JSON error */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/api/health'),
  matches: () => request<Match[]>('/api/matches'),
  createMatch: (body: Omit<Match, 'id'>) => request<Match>('/api/matches', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  workspace: (id: string) => request<Workspace>(`/api/matches/${encodeURIComponent(id)}/workspace`),
  clipCollections: (id: string) => request<ClipCollections>(`/api/matches/${encodeURIComponent(id)}/clips/collections`),
  upload: (id: string, files: File[]) => { const body = new FormData(); files.forEach((file) => body.append('files', file)); return request<{ accepted: Clip[]; skipped: string[] }>(`/api/matches/${encodeURIComponent(id)}/clips`, { method: 'POST', body }) },
  analyze: (id: string, clipIds: string[]) => request<Run>(`/api/matches/${encodeURIComponent(id)}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clipIds, device: 'auto' }) }),
  task: (id: string) => request<Run>(`/api/tasks/${encodeURIComponent(id)}`),
  updateEvent: (id: string, body: Pick<EventRecord, 'status'> & Partial<Pick<EventRecord, 'teamId' | 'playerId'>>) => request<EventRecord>(`/api/events/${encodeURIComponent(id)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  updateClipTeam: (id: string, teamId: string | null) => request<Clip>(`/api/clips/${encodeURIComponent(id)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ teamId }) }),
  deleteClip: (id: string) => request<{ id: string; deleted: boolean }>(`/api/clips/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  downloadClipUrl: (id: string) => `/api/clips/${encodeURIComponent(id)}/download`,
  teamHighlights: (id: string) => request<TeamHighlightExport[]>(`/api/matches/${encodeURIComponent(id)}/team-highlights`),
  generateTeamHighlight: (matchId: string, teamId: string) => request<TeamHighlightExport>(`/api/matches/${encodeURIComponent(matchId)}/team-highlights/${encodeURIComponent(teamId)}/generate`, { method: 'POST' }),
  teamTrainingStatus: (id: string) => request<TeamTrainingStatus>(`/api/matches/${encodeURIComponent(id)}/team-classifier/training-status`),
  trainTeamClassifier: (id: string) => request<TeamTrainingStatus>(`/api/matches/${encodeURIComponent(id)}/team-classifier/train`, { method: 'POST' }),
}
