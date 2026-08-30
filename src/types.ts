export type TabKey = 'overview' | 'review' | 'players' | 'clips'
export type EventStatus = 'pending' | 'confirmed' | 'ignored'
export type EventType = 'attempt' | 'make'
export type ShotType = 'freeThrow' | 'twoPoint' | 'threePoint'

export interface Team { id?: string; name: string; color: string; side?: 'home' | 'away' }
export interface Match { id: string; name: string; playedAt?: string; venue?: string; isTest?: boolean; homeTeam: Team; awayTeam: Team }
export interface Clip { id: string; name: string; sequence?: number; durationSeconds?: number; duration?: number; status?: string; confidence?: number; createdAt?: string; sizeBytes?: number; previewUrl?: string; teamId?: string | null; teamSource?: 'ai' | 'manual' | 'unresolved' | string; teamConfidence?: number; teamEvidence?: string }
export interface ClipCollection { team?: Team; clips: Clip[] }
export interface ClipCollections { home: ClipCollection; away: ClipCollection; unresolved: Clip[] }
export interface Player { id: string; name: string; displayName?: string; coverUrl?: string | null; number?: string | null; numberConfidence?: number; numberSource?: string | null; numberCandidates?: Array<{ number: string; votes: number; confidence: number }>; code?: string; teamId?: string | null; team?: 'home' | 'away'; identityType?: string; color?: string | null; confidence?: number; tracks?: number; tracksCount?: number; status?: string }
export interface EventRecord { id: string; clipId?: string; seconds?: number; time?: string; type: EventType | string; shotType?: ShotType | null; shotTypeConfidence?: number; shotTypeSource?: string | null; courtX?: number | null; courtY?: number | null; homographyConfidence?: number; releaseFrame?: number | null; description?: string; playerId?: string | null; teamId?: string | null; teamSource?: 'ai' | 'manual' | 'unassigned' | string; status: EventStatus; points?: number | null; confidence?: number; confirmedBy?: string | null; confirmationRule?: string | null; highlightStart?: number | null; highlightEnd?: number | null; previewUrl?: string }
export interface ScoringEvent extends EventRecord { type: 'make' }
export interface ScoringTeamGroup { team?: Team; events: ScoringEvent[] }
export interface ScoringResponse { home: ScoringTeamGroup; away: ScoringTeamGroup; unassigned: ScoringEvent[] }
export interface StatRow { playerId: string | null; teamId?: string | null; name?: string; code?: string; attempts: number; makes: number; points: number; freeThrowAttempts: number; freeThrowMakes: number; twoPointAttempts: number; twoPointMakes: number; threePointAttempts: number; threePointMakes: number; unclassifiedAttempts: number; unclassifiedMakes: number }
export interface Run { id: string; status?: string; progress?: number; completed?: number; total?: number; error?: string; details?: Record<string, unknown>; [key: string]: unknown }
export interface Workspace { match: Match; teams: Team[]; players: Player[]; clips: Clip[]; events: EventRecord[]; stats: StatRow[]; runs: Run[] }
export interface Health { analyzer?: { ready?: boolean; mode?: string; ocr?: { ready?: boolean; attempted?: boolean; error?: string }; models?: Record<string, { ready?: boolean; path?: string; task?: string; classes?: string[]; error?: string }> }; [key: string]: unknown }
