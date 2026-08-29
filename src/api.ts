import type { Clip, EventRecord, Health, Match, Run, Workspace } from './types'

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
  upload: (id: string, files: File[]) => { const body = new FormData(); files.forEach((file) => body.append('files', file)); return request<{ accepted: Clip[]; skipped: string[] }>(`/api/matches/${encodeURIComponent(id)}/clips`, { method: 'POST', body }) },
  analyze: (id: string, clipIds: string[]) => request<Run>(`/api/matches/${encodeURIComponent(id)}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clipIds, device: 'auto' }) }),
  task: (id: string) => request<Run>(`/api/tasks/${encodeURIComponent(id)}`),
  updateEvent: (id: string, body: Partial<Pick<EventRecord, 'status' | 'playerId' | 'teamId' | 'type' | 'shotType' | 'points'>>) => request<EventRecord>(`/api/events/${encodeURIComponent(id)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  addEvent: (matchId: string, body: Record<string, unknown>) => request<EventRecord>(`/api/matches/${encodeURIComponent(matchId)}/events`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  updatePlayer: (id: string, body: Record<string, unknown>) => request('/api/players/' + encodeURIComponent(id), { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  mergePlayers: (matchId: string, sourcePlayerId: string, targetPlayerId: string) => request(`/api/matches/${encodeURIComponent(matchId)}/players/merge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sourcePlayerId, targetPlayerId }) }),
  highlights: (id: string) => request<EventRecord[]>('/api/players/' + encodeURIComponent(id) + '/highlights'),
}
