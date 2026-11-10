import type { Stop } from './api'

export type StopGroup = {
  name: string
  stopIds: string[]
}

export type StopPhase = 'past' | 'ahead' | 'current' | 'future'

export function groupStops(stops: Stop[]): StopGroup[] {
  const groups = new Map<string, string[]>()
  for (const stop of stops) {
    const ids = groups.get(stop.name) ?? []
    ids.push(stop.id)
    groups.set(stop.name, ids)
  }
  return [...groups.entries()].map(([name, stopIds]) => ({ name, stopIds }))
}

export function sameIds(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false
  return left.every((id, index) => id === right[index])
}

export function stopPhase(
  sequence: number,
  referenceSequence: number | null,
  ourSequence: number | null,
): StopPhase {
  if (referenceSequence !== null && sequence < referenceSequence) return 'past'
  if (referenceSequence !== null && sequence === referenceSequence) return 'current'
  if (ourSequence !== null && sequence < ourSequence) return 'ahead'
  return 'future'
}
