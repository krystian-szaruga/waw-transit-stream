import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import type { Departure, Stop, TripStop } from './api'
import { loadTripStops } from './api'
import { useLiveTransit } from './useLiveTransit'

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Warsaw',
  })
}

function serviceDate(value: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Warsaw',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}

function formatDelay(delaySec: number | null): string {
  if (delaySec === null) return 'scheduled'
  const minutes = Math.round(delaySec / 60)
  if (minutes === 0) return 'on time'
  return minutes > 0 ? `delayed +${minutes} min` : `early ${Math.abs(minutes)} min`
}

function delayClass(delaySec: number | null): string {
  if (delaySec === null) return 'scheduled'
  if (delaySec > 120) return 'late'
  if (delaySec < -60) return 'early'
  return 'ok'
}

function minutesLabel(minutes: number): string {
  if (minutes < 0) return 'departed'
  return minutes === 0 ? 'now' : `${minutes} min`
}

function scheduledLabel(item: Departure): string | null {
  if (item.scheduledMinutes < 0) return null
  return minutesLabel(item.scheduledMinutes)
}

function DepartureRow({
  item,
  selected,
  onSelect,
}: {
  item: Departure
  selected: boolean
  onSelect: (item: Departure) => void
}) {
  const predicted = item.predicted
  const live = predicted !== null
  return (
    <li
      className={`${live ? 'departure live' : 'departure scheduled'} selectable${selected ? ' selected' : ''}`}
      tabIndex={0}
      onClick={() => onSelect(item)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(item)
        }
      }}
    >
      <span className="line-badge" style={{ background: item.color }}>
        {item.line}
      </span>
      <div className="departure-main">
        <span className="direction">{item.direction || 'Unknown direction'}</span>
        <span className="timing">
          <span className="timing-label">Scheduled:</span> {formatTime(item.scheduled)}
          {scheduledLabel(item) !== null ? ` (${scheduledLabel(item)})` : ''}
        </span>
        {predicted !== null && (
          <span className="timing live">
            <span className="timing-label">Live:</span> {formatTime(predicted)}
            {` (${minutesLabel(item.minutes)})`}
          </span>
        )}
      </div>
      <span className={`delay ${delayClass(item.delaySec)}`}>
        {live ? formatDelay(item.delaySec) : 'scheduled'}
      </span>
    </li>
  )
}

function TripStopItem({
  stop,
  state,
  selected,
  delaySec,
}: {
  stop: TripStop
  state: 'past' | 'current' | 'future'
  selected: boolean
  delaySec: number | null
}) {
  const predicted =
    state === 'past' || delaySec === null
      ? null
      : new Date(new Date(stop.scheduled).getTime() + delaySec * 1000)
  return (
    <li className={`trip-stop ${state}${selected ? ' selected' : ''}`}>
      <span className="trip-stop-name">{stop.name}</span>
      <span className="trip-stop-time">
        {formatTime(stop.scheduled)}
        {predicted !== null && <span className="trip-stop-live">{formatTime(predicted.toISOString())}</span>}
      </span>
    </li>
  )
}

function App() {
  const [selectedGroup, setSelectedGroup] = useState<StopGroup | null>(null)
  const [stopQuery, setStopQuery] = useState('')
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null)
  const [tripStops, setTripStops] = useState<TripStop[]>([])
  const [tripLoading, setTripLoading] = useState(false)
  const [tripError, setTripError] = useState<string | null>(null)
  const [showPast, setShowPast] = useState(false)
  const tripDetailRef = useRef<HTMLDivElement | null>(null)
  const stopIds = useMemo(() => selectedGroup?.stopIds ?? [], [selectedGroup])
  const { stops, departures, departuresLoading, status, error, version } =
    useLiveTransit(stopIds)

  const stopGroups = useMemo(() => groupStops(stops), [stops])
  const statusHint = [
    error,
    version !== null ? `Timetable v${version}` : null,
  ]
    .filter((item) => item !== null && item !== '')
    .join(' · ')

  useEffect(() => {
    setSelectedGroup((current) => {
      if (current === null || stopGroups.length === 0) return current
      const fresh = stopGroups.find((group) => group.name === current.name)
      if (fresh === undefined) return null
      return sameIds(fresh.stopIds, current.stopIds) ? current : fresh
    })
  }, [stopGroups])
  const matchingStops = useMemo(
    () =>
      stopQuery.trim() === ''
        ? []
        : stopGroups
            .filter((item) => item.name.toLowerCase().includes(stopQuery.trim().toLowerCase()))
            .slice(0, 20),
    [stopQuery, stopGroups],
  )
  const sortedDepartures = useMemo(
    () =>
      [...departures].sort(
        (a, b) => new Date(a.scheduled).getTime() - new Date(b.scheduled).getTime(),
      ),
    [departures],
  )
  const selectedTrip =
    selectedTripId === null
      ? null
      : sortedDepartures.find((item) => item.tripId === selectedTripId) ?? null
  const referenceSequence =
    selectedTrip === null
      ? null
      : selectedTrip.vehicleNextSequence ?? selectedTrip.stopSequence
  const pastStops = useMemo(
    () =>
      referenceSequence === null
        ? []
        : tripStops.filter((stop) => stop.sequence < referenceSequence),
    [tripStops, referenceSequence],
  )
  const currentStop =
    referenceSequence === null
      ? null
      : tripStops.find((stop) => stop.sequence === referenceSequence) ?? null
  const futureStops = useMemo(
    () =>
      referenceSequence === null
        ? []
        : tripStops.filter((stop) => stop.sequence > referenceSequence),
    [tripStops, referenceSequence],
  )
  const liveDelay = selectedTrip?.live ? selectedTrip.delaySec : null
  const firstStop = tripStops.length > 0 ? tripStops[0] : null
  const hiddenPastStops = pastStops.filter((stop) => stop.sequence !== firstStop?.sequence)

  const selectedTripDate =
    selectedTrip === null ? null : serviceDate(selectedTrip.scheduled)

  useEffect(() => {
    if (selectedTripId === null || selectedTripDate === null) return
    let cancelled = false
    setTripLoading(true)
    setTripError(null)
    loadTripStops(selectedTripId, selectedTripDate)
      .then((items) => {
        if (!cancelled) setTripStops(items)
      })
      .catch(() => {
        if (!cancelled) setTripError('Could not load trip stops.')
      })
      .finally(() => {
        if (!cancelled) setTripLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedTripId, selectedTripDate])

  useEffect(() => {
    const element = tripDetailRef.current
    if (selectedTripId !== null && element !== null && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [selectedTripId])

  const toggleTrip = (departure: Departure) => {
    setSelectedTripId((current) => (current === departure.tripId ? null : departure.tripId))
    setShowPast(false)
  }

  const selectStop = (group: StopGroup) => {
    setSelectedGroup(group)
    setSelectedTripId(null)
    setStopQuery('')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Warsaw Transit
          <span className="subtitle">live</span>
        </div>

        <nav className="tabs" aria-label="Views">
          <button type="button" className="tab active">
            Live departures
          </button>
          <button type="button" className="tab" disabled title="Coming soon">
            Timetable
          </button>
          <button type="button" className="tab" disabled title="Coming soon">
            Routes
          </button>
          <button type="button" className="tab" disabled title="Coming soon">
            Map
          </button>
        </nav>

        <div className="status" title={statusHint}>
          <span className={status === 'live' ? 'dot' : 'dot offline'} />
          {status}
        </div>
      </header>

      <main className="content">
        <section className="search-panel">
          <div className="search">
            <input
              type="search"
              placeholder="Search stop"
              aria-label="Search stop"
              value={stopQuery}
              onChange={(event) => setStopQuery(event.target.value)}
            />
            {matchingStops.length > 0 && (
              <ul className="search-results" aria-label="Stop results">
                {matchingStops.map((item) => (
                  <li key={item.name}>
                    <button type="button" onClick={() => selectStop(item)}>
                      {item.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        {selectedGroup === null ? (
          <section className="empty">
            <h1>Live departures</h1>
            <p>Select a stop to see upcoming departures.</p>
          </section>
        ) : (
          <section className="board">
            <div className="board-header">
              <div>
                <h1>{selectedGroup.name}</h1>
                <p className="muted">
                  Upcoming departures
                  {selectedGroup.stopIds.length > 1
                    ? ` · ${selectedGroup.stopIds.length} platforms`
                    : ''}
                </p>
              </div>
              <button type="button" className="back" onClick={() => {
                  setSelectedGroup(null)
                  setSelectedTripId(null)
                }}>
                ← Change stop
              </button>
            </div>

            {selectedTrip !== null && (
              <div className="trip-detail" ref={tripDetailRef}>
                <div className="trip-detail-header">
                  <h2>
                    {selectedTrip.line} → {selectedTrip.direction}
                  </h2>
                  <button type="button" className="back" onClick={() => setSelectedTripId(null)}>
                    Close
                  </button>
                </div>
                {tripLoading ? (
                  <div className="loading" role="status">
                    <span className="spinner" />
                    Loading trip stops…
                  </div>
                ) : tripError !== null ? (
                  <p className="empty-row">{tripError}</p>
                ) : (
                  <ol className="trip-stops" aria-label="Trip stops">
                    {firstStop !== null &&
                      referenceSequence !== null &&
                      firstStop.sequence < referenceSequence && (
                        <TripStopItem
                          key={`${firstStop.sequence}-${firstStop.name}`}
                          stop={firstStop}
                          state="past"
                          selected={firstStop.sequence === selectedTrip?.stopSequence}
                          delaySec={liveDelay}
                        />
                      )}
                    {hiddenPastStops.length > 0 && (
                      <li className="trip-stop past-toggle">
                        <button
                          type="button"
                          className="past-button"
                          onClick={() => setShowPast((value) => !value)}
                        >
                          {showPast ? 'Hide stops' : '…'}
                        </button>
                      </li>
                    )}
                    {showPast &&
                      hiddenPastStops.map((stop) => (
                        <TripStopItem
                          key={`${stop.sequence}-${stop.name}`}
                          stop={stop}
                          state="past"
                          selected={stop.sequence === selectedTrip?.stopSequence}
                          delaySec={liveDelay}
                        />
                      ))}
                    {currentStop !== null && (
                      <TripStopItem
                        key={`${currentStop.sequence}-${currentStop.name}`}
                        stop={currentStop}
                        state="current"
                        selected={currentStop.sequence === selectedTrip?.stopSequence}
                        delaySec={liveDelay}
                      />
                    )}
                    {futureStops.map((stop) => (
                      <TripStopItem
                        key={`${stop.sequence}-${stop.name}`}
                        stop={stop}
                        state="future"
                        selected={stop.sequence === selectedTrip?.stopSequence}
                        delaySec={liveDelay}
                      />
                    ))}
                  </ol>
                )}
              </div>
            )}
            {departuresLoading ? (
              <div className="loading" role="status">
                <span className="spinner" />
                Loading departures…
              </div>
            ) : sortedDepartures.length === 0 ? (
              <p className="empty-row">No departures at this time.</p>
            ) : (
              <ul className="departures" aria-label="Departures">
                {sortedDepartures.map((item) => (
                  <DepartureRow
                    key={`${item.tripId}-${item.scheduled}`}
                    item={item}
                    selected={selectedTrip?.tripId === item.tripId}
                    onSelect={toggleTrip}
                  />
                ))}
              </ul>
            )}

          </section>
        )}
      </main>
    </div>
  )
}

export default App

type StopGroup = {
  name: string
  stopIds: string[]
}

function groupStops(stops: Stop[]): StopGroup[] {
  const groups = new Map<string, string[]>()
  for (const stop of stops) {
    const ids = groups.get(stop.name) ?? []
    ids.push(stop.id)
    groups.set(stop.name, ids)
  }
  return [...groups.entries()].map(([name, stopIds]) => ({ name, stopIds }))
}

function sameIds(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false
  return left.every((id, index) => id === right[index])
}
