import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import 'leaflet/dist/leaflet.css'
import type { Departure, ShapePoint, TripStop } from './api'
import { loadTripShape, loadTripStops } from './api'
import { DepartureRow } from './DepartureRow'
import { serviceDate } from './format'
import { MapPanel } from './MapPanel'
import { SearchPanel } from './SearchPanel'
import { groupStops, sameIds, type StopGroup } from './stops'
import { ThemeToggle } from './ThemeToggle'
import { TripDetail } from './TripDetail'
import { useLiveTransit } from './useLiveTransit'
import { useTheme } from './useTheme'

function App() {
  const { theme, setTheme } = useTheme()
  const [selectedGroup, setSelectedGroup] = useState<StopGroup | null>(null)
  const [stopQuery, setStopQuery] = useState('')
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null)
  const [tripStops, setTripStops] = useState<TripStop[]>([])
  const [tripShape, setTripShape] = useState<ShapePoint[]>([])
  const [tripLoading, setTripLoading] = useState(false)
  const [tripError, setTripError] = useState<string | null>(null)
  const [showPast, setShowPast] = useState(false)
  const tripDetailRef = useRef<HTMLDivElement | null>(null)
  const stopIds = useMemo(() => selectedGroup?.stopIds ?? [], [selectedGroup])
  const { stops, departures, vehicles, departuresLoading, status, error, socketError, version, retry } =
    useLiveTransit(stopIds)

  const stopGroups = useMemo(() => groupStops(stops), [stops])
  const statusHint = [socketError, version !== null ? `Timetable v${version}` : null]
    .filter((item) => item !== null && item !== '')
    .join(' · ')
  const hasLiveData = vehicles.length > 0 || departures.some((item) => item.live)
  const connectionStatus = status === 'live' && !hasLiveData ? 'connected' : status
  const statusDot =
    connectionStatus === 'live'
      ? 'dot'
      : connectionStatus === 'offline'
        ? 'dot offline'
        : 'dot waiting'

  useEffect(() => {
    setSelectedGroup((current) => {
      if (current === null || stopGroups.length === 0) return current
      const fresh = stopGroups.find((group) => group.name === current.name)
      if (fresh === undefined) return null
      return sameIds(fresh.stopIds, current.stopIds) ? current : fresh
    })
  }, [stopGroups])

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
  const referenceSequence = selectedTrip === null ? null : selectedTrip.vehicleNextSequence
  const ourSequence = selectedTrip === null ? null : selectedTrip.stopSequence
  const tripVehicle = useMemo(() => {
    if (selectedTripId === null) return null
    const vehicleId = selectedTrip?.vehicleId ?? null
    return (
      vehicles.find((item) => vehicleId !== null && item.id === vehicleId) ??
      vehicles.find((item) => item.tripId === selectedTripId) ??
      null
    )
  }, [vehicles, selectedTripId, selectedTrip?.vehicleId])
  const selectedTripDate = selectedTrip === null ? null : serviceDate(selectedTrip.scheduled)

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
    if (selectedTripId === null) return
    let cancelled = false
    setTripShape([])
    loadTripShape(selectedTripId)
      .then((items) => {
        if (!cancelled) setTripShape(items)
      })
      .catch(() => {
        if (!cancelled) setTripShape([])
      })
    return () => {
      cancelled = true
    }
  }, [selectedTripId])

  useEffect(() => {
    const element = tripDetailRef.current
    if (
      selectedTripId !== null &&
      element !== null &&
      typeof element.scrollIntoView === 'function'
    ) {
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
        </nav>

        <div className="topbar-actions">
          <ThemeToggle theme={theme} onChange={setTheme} />
          <div className="status" title={statusHint}>
            <span className={statusDot} />
            {connectionStatus}
          </div>
        </div>
      </header>

      <main className="content">
        <SearchPanel
          query={stopQuery}
          groups={stopGroups}
          onQueryChange={setStopQuery}
          onSelect={selectStop}
        />

        {selectedGroup === null ? (
          error !== null ? (
            <section className="error-card" role="alert">
              <h2>Could not load transit data</h2>
              <p className="muted">{error}</p>
              <button type="button" className="back" onClick={retry}>
                Retry
              </button>
            </section>
          ) : (
            <section className="empty">
              <h1>Live departures</h1>
              <p>Select a stop to see upcoming departures.</p>
            </section>
          )
        ) : (
          <div className={selectedTrip === null ? 'workspace' : 'workspace with-map'}>
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
                <button
                  type="button"
                  className="back"
                  onClick={() => {
                    setSelectedGroup(null)
                    setSelectedTripId(null)
                  }}
                >
                  ← Change stop
                </button>
              </div>

              {selectedTrip !== null && (
                <TripDetail
                  departure={selectedTrip}
                  stops={tripStops}
                  loading={tripLoading}
                  error={tripError}
                  referenceSequence={referenceSequence}
                  stopName={selectedGroup.name}
                  showPast={showPast}
                  onTogglePast={() => setShowPast((value) => !value)}
                  onClose={() => setSelectedTripId(null)}
                  containerRef={tripDetailRef}
                />
              )}

              {departuresLoading ? (
                <div className="loading" role="status">
                  <span className="spinner" />
                  Loading departures…
                </div>
              ) : error !== null && sortedDepartures.length === 0 ? (
                <div className="error-card inline" role="alert">
                  <p className="muted">{error}</p>
                  <button type="button" className="back" onClick={retry}>
                    Retry
                  </button>
                </div>
              ) : (
                <>
                  {error !== null && (
                    <div className="refresh-warning" role="status">
                      Couldn't refresh
                      <button type="button" className="link-button" onClick={retry}>
                        Retry
                      </button>
                    </div>
                  )}
                  {sortedDepartures.length === 0 ? (
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
                </>
              )}
            </section>
            {selectedTrip !== null && (
              <MapPanel
                tripId={selectedTrip.tripId}
                shape={tripShape}
                stops={tripStops}
                referenceSequence={referenceSequence}
                ourSequence={ourSequence}
                vehicle={tripVehicle}
                color={selectedTrip.color}
                delaySec={selectedTrip.live ? selectedTrip.delaySec : null}
              />
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
