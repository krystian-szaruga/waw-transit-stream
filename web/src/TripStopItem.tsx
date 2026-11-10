import type { TripStop } from './api'
import { formatTime } from './format'
import type { StopPhase } from './stops'

export function TripStopItem({
  stop,
  phase,
  selected,
  delaySec,
}: {
  stop: TripStop
  phase: StopPhase
  selected: boolean
  delaySec: number | null
}) {
  const predicted =
    phase === 'past' || delaySec === null
      ? null
      : new Date(new Date(stop.scheduled).getTime() + delaySec * 1000)
  return (
    <li className={`trip-stop ${phase}${selected ? ' selected' : ''}`}>
      <span className="trip-stop-name">{stop.name}</span>
      <span className="trip-stop-time">
        {formatTime(stop.scheduled)}
        {predicted !== null && (
          <span className="trip-stop-live">{formatTime(predicted.toISOString())}</span>
        )}
      </span>
    </li>
  )
}
