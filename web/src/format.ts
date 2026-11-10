import type { Departure } from './api'

export function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Warsaw',
  })
}

export function serviceDate(value: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Warsaw',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}

export function formatDelay(delaySec: number | null): string {
  if (delaySec === null) return 'scheduled'
  const minutes = Math.round(delaySec / 60)
  if (minutes === 0) return 'on time'
  return minutes > 0 ? `delayed +${minutes} min` : `early ${Math.abs(minutes)} min`
}

export function delayClass(delaySec: number | null): string {
  if (delaySec === null) return 'scheduled'
  if (delaySec > 120) return 'late'
  if (delaySec < -60) return 'early'
  return 'ok'
}

export function minutesLabel(minutes: number): string {
  if (minutes < 0) return 'departed'
  return minutes === 0 ? 'now' : `${minutes} min`
}

export function scheduledLabel(item: Departure): string | null {
  if (item.scheduledMinutes < 0) return null
  return minutesLabel(item.scheduledMinutes)
}
