import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'
import { departures, lines, stops, vehicles, type Stop, type Vehicle } from './mocks'

function formatDelay(delaySec: number): string {
  const minutes = Math.round(delaySec / 60)
  if (minutes === 0) return 'on time'
  return minutes > 0 ? `+${minutes} min` : `${minutes} min`
}

function delayClass(delaySec: number): string {
  if (delaySec > 120) return 'late'
  if (delaySec < -60) return 'early'
  return 'ok'
}

function vehicleIcon(item: Vehicle, selected: boolean) {
  return L.divIcon({
    className: selected ? 'vehicle-marker selected' : 'vehicle-marker',
    html: `<span role="button" aria-label="Vehicle ${item.line} ${item.number}" style="background:${item.color}">${item.line}</span>`,
    iconSize: [32, 22],
    iconAnchor: [16, 11],
  })
}

function ResizeMap() {
  const map = useMap()

  useEffect(() => {
    map.invalidateSize()
    const timer = window.setTimeout(() => map.invalidateSize(), 0)
    return () => window.clearTimeout(timer)
  }, [map])

  return null
}

function stopIcon(item: Stop, selected: boolean, showLabel: boolean) {
  const label = showLabel ? `<span class="stop-label">${item.name}</span>` : ''
  return L.divIcon({
    className: selected ? 'stop-marker selected' : 'stop-marker',
    html: `<span class="stop-inner" role="button" aria-label="Stop ${item.name}">${label}<span class="stop-dot"></span></span>`,
    iconSize: showLabel ? [150, 34] : [14, 14],
    iconAnchor: showLabel ? [75, 30] : [7, 7],
  })
}

function ZoomWatcher({ onChange }: { onChange: (zoom: number) => void }) {
  const map = useMapEvents({ zoomend: () => onChange(map.getZoom()) })

  useEffect(() => {
    onChange(map.getZoom())
  }, [map, onChange])

  return null
}



function App() {
  const [line, setLine] = useState<string | null>(null)
  const [vehicleId, setVehicleId] = useState<string | null>(null)
  const [stopId, setStopId] = useState<string | null>(null)
  const [stopQuery, setStopQuery] = useState('')
  const [zoom, setZoom] = useState(13)
  const mapRef = useRef<L.Map | null>(null)

  const visible = useMemo(
    () => vehicles.filter((item) => line === null || item.line === line),
    [line],
  )

  const vehicle = vehicles.find((item) => item.id === vehicleId) ?? null
  const stop = stops.find((item) => item.id === stopId) ?? null
  const matchingStops = useMemo(
    () =>
      stopQuery.trim() === ''
        ? []
        : stops.filter((item) => item.name.toLowerCase().includes(stopQuery.trim().toLowerCase())),
    [stopQuery],
  )
  const stopDepartures = useMemo(
    () => departures.filter((item) => item.stopId === stopId).sort((a, b) => a.minutes - b.minutes),
    [stopId],
  )

  useEffect(() => {
    if (stop) mapRef.current?.setView([stop.lat, stop.lon], 15)
    else if (vehicle) mapRef.current?.setView([vehicle.lat, vehicle.lon], 15)
  }, [stop, vehicle])

  const selectVehicle = (id: string) => {
    setVehicleId(id)
    setStopId(null)
  }

  const selectStop = (id: string) => {
    setStopId(id)
    setVehicleId(null)
  }

  const clearSelection = () => {
    setStopId(null)
    setVehicleId(null)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Warsaw Transit
          <span className="subtitle">live</span>
        </div>

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
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      selectStop(item.id)
                      setStopQuery('')
                    }}
                  >
                    {item.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="lines">
          <button
            type="button"
            className={line === null ? 'chip active' : 'chip'}
            onClick={() => setLine(null)}
          >
            All
          </button>
          {lines.map((item) => (
            <button
              key={item.name}
              type="button"
              className={line === item.name ? 'chip active' : 'chip'}
              style={{ borderColor: item.color }}
              onClick={() => setLine(item.name)}
            >
              {item.name}
            </button>
          ))}
        </div>

        <div className="status">
          <span className="dot" />
          live
        </div>
      </header>

      <main className="layout">
        <section className="map" aria-label="Vehicle map">
          <MapContainer
            ref={mapRef}
            center={[52.2297, 21.0122]}
            zoom={13}
            scrollWheelZoom
            className="leaflet-map"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <ResizeMap />
            <ZoomWatcher onChange={setZoom} />

            {stops.map((item) => (
              <Marker
                key={`${item.id}-${stopId === item.id}-${zoom >= 15}`}
                position={[item.lat, item.lon]}
                icon={stopIcon(item, stopId === item.id, zoom >= 15 || stopId === item.id)}
                zIndexOffset={stopId === item.id ? 1000 : 300}
                eventHandlers={{ click: () => selectStop(item.id) }}
              />
            ))}

            {visible.map((item) => (
              <Marker
                key={`${item.id}-${vehicleId === item.id}`}
                position={[item.lat, item.lon]}
                icon={vehicleIcon(item, vehicleId === item.id)}
                eventHandlers={{ click: () => selectVehicle(item.id) }}
              />
            ))}
          </MapContainer>

          <div className="legend">
            {lines.map((item) => (
              <span key={item.name}>
                <i style={{ background: item.color }} />
                {item.name}
              </span>
            ))}
          </div>
        </section>

        <aside className="panel">
          {vehicle ? (
            <div className="details">
              <button type="button" className="back" onClick={clearSelection}>
                ← Back
              </button>
              <div className="row">
                <span className="badge" style={{ background: vehicle.color }}>
                  {vehicle.line}
                </span>
                <span className="muted">brigade {vehicle.brigade}</span>
              </div>
              <h2>{vehicle.nextStop}</h2>
              <p className={delayClass(vehicle.delaySec)}>
                {formatDelay(vehicle.delaySec)}
              </p>
              <dl>
                <dt>Vehicle</dt>
                <dd>
                  {vehicle.type}:{vehicle.number}
                </dd>
                <dt>Trip</dt>
                <dd>{vehicle.tripId}</dd>
                <dt>Status</dt>
                <dd>{vehicle.status}</dd>
              </dl>
            </div>
          ) : stop ? (
            <div className="departures">
              <button type="button" className="back" onClick={clearSelection}>
                ← Back
              </button>
              <h2>{stop.name}</h2>
              <ul>
                {stopDepartures.map((item) => (
                  <li key={`${item.line}-${item.direction}-${item.minutes}`}>
                    <span className="badge" style={{ background: item.color }}>
                      {item.line}
                    </span>
                    <span className="direction">{item.direction}</span>
                    <span className="minutes">in {item.minutes} min</span>
                    <span className={delayClass(item.delaySec)}>{formatDelay(item.delaySec)}</span>
                  </li>
                ))}
                {stopDepartures.length === 0 && <li className="empty">No departures</li>}
              </ul>
            </div>
          ) : (
            <div className="hint">
              <h2>Pick a point on the map</h2>
              <p className="muted">Click a vehicle or a stop.</p>
              <ul className="vehicle-list" aria-label="Vehicles">
                {visible.map((item) => (
                  <li key={item.id} onClick={() => selectVehicle(item.id)}>
                    <span className="badge" style={{ background: item.color }}>
                      {item.line}
                    </span>
                    <span>{item.nextStop}</span>
                    <span className={delayClass(item.delaySec)}>{formatDelay(item.delaySec)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </main>
    </div>
  )
}

export default App
