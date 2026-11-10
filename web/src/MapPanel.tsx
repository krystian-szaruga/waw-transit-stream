import { useEffect, useMemo, useRef } from 'react'
import { divIcon } from 'leaflet'
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { ShapePoint, TripStop, Vehicle } from './api'
import { stopPhase } from './stops'
import { MAP_COLORS } from './theme'

function busIcon(line: string, color: string) {
  return divIcon({
    className: 'bus-marker',
    html: `<span class="bus-marker-badge" style="background:${color}">${escapeHtml(line)}</span>`,
    iconSize: [36, 44],
    iconAnchor: [18, 42],
  })
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => `&#${character.charCodeAt(0)};`)
}

function MapFocus({
  positions,
  vehicle,
}: {
  positions: [number, number][]
  vehicle: Vehicle | null
}) {
  const map = useMap()
  const vehicleFocused = useRef(false)
  const routeFocused = useRef(false)
  const vehicleLat = vehicle?.lat ?? null
  const vehicleLon = vehicle?.lon ?? null

  useEffect(() => {
    if (vehicleLat !== null && vehicleLon !== null) {
      if (vehicleFocused.current) return
      vehicleFocused.current = true
      map.setView([vehicleLat, vehicleLon], 16)
      return
    }
    if (routeFocused.current || positions.length < 2) return
    routeFocused.current = true
    map.fitBounds(positions, { padding: [28, 28] })
  }, [map, positions, vehicleLat, vehicleLon])

  return null
}

export function MapPanel({
  tripId,
  shape,
  stops,
  referenceSequence,
  ourSequence,
  vehicle,
  color,
}: {
  tripId: string
  shape: ShapePoint[]
  stops: TripStop[]
  referenceSequence: number | null
  ourSequence: number | null
  vehicle: Vehicle | null
  color: string
}) {
  const positions: [number, number][] =
    shape.length > 1
      ? shape.map((point) => [point.lat, point.lon])
      : stops.map((stop) => [stop.lat, stop.lon])
  const center: [number, number] = positions[Math.floor(positions.length / 2)] ?? [52.2297, 21.0122]
  const vehicleLine = vehicle?.line ?? ''
  const vehicleIcon = useMemo(() => busIcon(vehicleLine, color), [vehicleLine, color])

  return (
    <section className="map-panel" aria-label="Trip map">
      <MapContainer key={tripId} center={center} zoom={13} className="trip-map">
        <MapFocus positions={positions} vehicle={vehicle} />
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />
        {positions.length > 1 && (
          <Polyline positions={positions} pathOptions={{ color, weight: 5, opacity: 0.85 }} />
        )}
        {stops.map((stop) => {
          const ours = stop.sequence === ourSequence
          const phase = stopPhase(stop.sequence, referenceSequence, ourSequence)
          const current = phase === 'current'
          const passed = phase === 'past'
          const stopColor = ours
            ? MAP_COLORS.ours
            : current
              ? MAP_COLORS.next
              : passed
                ? MAP_COLORS.passed
                : phase === 'ahead'
                  ? MAP_COLORS.ahead
                  : MAP_COLORS.future
          const strokeColor = ours && current ? MAP_COLORS.next : stopColor
          return (
            <CircleMarker
              key={`${stop.sequence}-${stop.name}`}
              center={[stop.lat, stop.lon]}
              radius={ours || current ? 9 : 6}
              pathOptions={{
                color: strokeColor,
                fillColor: stopColor,
                fillOpacity: passed ? 0.6 : ours && !current ? 0.35 : 1,
                weight: ours || current ? 4 : 2,
              }}
            >
              <Tooltip>{ours ? `${stop.name} (your stop)` : stop.name}</Tooltip>
            </CircleMarker>
          )
        })}
        {vehicle !== null && (
          <Marker position={[vehicle.lat, vehicle.lon]} icon={vehicleIcon} />
        )}
      </MapContainer>
    </section>
  )
}
