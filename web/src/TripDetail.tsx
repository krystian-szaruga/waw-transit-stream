import type { RefObject } from 'react'
import type { Departure, TripStop } from './api'
import { stopPhase } from './stops'
import { TripStopItem } from './TripStopItem'

export function TripDetail({
  departure,
  stops,
  loading,
  error,
  referenceSequence,
  stopName,
  showPast,
  onTogglePast,
  onClose,
  containerRef,
}: {
  departure: Departure
  stops: TripStop[]
  loading: boolean
  error: string | null
  referenceSequence: number | null
  stopName: string
  showPast: boolean
  onTogglePast: () => void
  onClose: () => void
  containerRef: RefObject<HTMLDivElement | null>
}) {
  const pastStops =
    referenceSequence === null
      ? []
      : stops.filter((stop) => stop.sequence < referenceSequence)
  const currentStop =
    referenceSequence === null
      ? null
      : stops.find((stop) => stop.sequence === referenceSequence) ?? null
  const futureStops =
    referenceSequence === null
      ? stops
      : stops.filter((stop) => stop.sequence > referenceSequence)
  const firstStop = stops.length > 0 ? stops[0] : null
  const hiddenPastStops = pastStops.filter((stop) => stop.sequence !== firstStop?.sequence)
  const liveDelay = departure.live ? departure.delaySec : null
  const isSelected = (stop: TripStop) => stop.sequence === departure.stopSequence

  return (
    <div className="trip-detail" ref={containerRef}>
      <div className="trip-detail-header">
        <div>
          <h2>
            {departure.line} → {departure.direction}
          </h2>
          {departure.vehicleNextSequence === null && (
            <p className="muted">
              Not started yet
              {departure.scheduledMinutes > 0
                ? ` · passes ${stopName} in ${departure.scheduledMinutes} min`
                : ''}
            </p>
          )}
        </div>
        <button type="button" className="back" onClick={onClose}>
          Close
        </button>
      </div>
      {loading ? (
        <div className="loading" role="status">
          <span className="spinner" />
          Loading trip stops…
        </div>
      ) : error !== null ? (
        <p className="empty-row">{error}</p>
      ) : (
        <ol className="trip-stops" aria-label="Trip stops">
          {firstStop !== null &&
            referenceSequence !== null &&
            firstStop.sequence < referenceSequence && (
              <TripStopItem
                key={`${firstStop.sequence}-${firstStop.name}`}
                stop={firstStop}
                phase="past"
                selected={isSelected(firstStop)}
                delaySec={liveDelay}
              />
            )}
          {hiddenPastStops.length > 0 && (
            <li className="trip-stop past-toggle">
              <button type="button" className="past-button" onClick={onTogglePast}>
                {showPast ? 'Hide stops' : '…'}
              </button>
            </li>
          )}
          {showPast &&
            hiddenPastStops.map((stop) => (
              <TripStopItem
                key={`${stop.sequence}-${stop.name}`}
                stop={stop}
                phase="past"
                selected={isSelected(stop)}
                delaySec={liveDelay}
              />
            ))}
          {currentStop !== null && (
            <TripStopItem
              key={`${currentStop.sequence}-${currentStop.name}`}
              stop={currentStop}
              phase="current"
              selected={isSelected(currentStop)}
              delaySec={liveDelay}
            />
          )}
          {futureStops.map((stop) => (
            <TripStopItem
              key={`${stop.sequence}-${stop.name}`}
              stop={stop}
              phase={stopPhase(stop.sequence, referenceSequence, departure.stopSequence)}
              selected={isSelected(stop)}
              delaySec={liveDelay}
            />
          ))}
        </ol>
      )}
    </div>
  )
}
