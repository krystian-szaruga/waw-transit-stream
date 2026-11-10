export type Vehicle = {
  id: string
  type: number
  number: string
  line: string
  brigade: string
  tripId: string
  delaySec: number
  status: string
  nextStop: string | null
  lat: number
  lon: number
  color: string
}

export type Stop = {
  id: string
  name: string
  lat: number
  lon: number
}

export type Line = {
  name: string
  vehicleType: number
  color: string
}

export type TripStop = {
  sequence: number
  name: string
  scheduled: string
}

export type Departure = {
  stopId: string
  line: string
  direction: string
  tripId: string
  stopSequence: number
  vehicleNextSequence: number | null
  vehicleId: string | null
  scheduled: string
  predicted: string | null
  scheduledMinutes: number
  minutes: number
  delaySec: number | null
  color: string
  live: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

const LINE_COLORS = [
  '#e8590c',
  '#1971c2',
  '#2f9e44',
  '#ae3ec9',
  '#f08c00',
  '#0c8599',
  '#d6336c',
  '#5f3dc4',
]

export function lineColor(line: string): string {
  let hash = 0
  for (const character of line) {
    hash = (hash * 31 + character.charCodeAt(0)) % LINE_COLORS.length
  }
  return LINE_COLORS[hash]
}

export async function loadLines(): Promise<Line[]> {
  const items = await fetchJson<LineResponse[]>('/lines')
  return items.map((item) => ({
    name: item.name,
    vehicleType: item.vehicle_type,
    color: lineColor(item.name),
  }))
}

export async function loadVehicles(): Promise<Vehicle[]> {
  const items = await fetchJson<VehicleResponse[]>('/vehicles')
  return items.map(toVehicle)
}

export async function loadStops(query?: string): Promise<Stop[]> {
  const suffix = query ? `?${new URLSearchParams({ query })}` : ''
  return fetchJson<StopResponse[]>(`/stops${suffix}`)
}

export async function loadTripStops(tripId: string, serviceDate: string): Promise<TripStop[]> {
  const suffix = `?${new URLSearchParams({ date: serviceDate })}`
  return fetchJson<TripStopResponse[]>(`/trips/${encodeURIComponent(tripId)}/stops${suffix}`)
}

export async function loadDepartures(stopId: string, limit = 20): Promise<Departure[]> {
  const suffix = `?${new URLSearchParams({ limit: String(limit) })}`
  const items = await fetchJson<DepartureResponse[]>(`/stops/${encodeURIComponent(stopId)}/departures${suffix}`)
  return items.map((item) => ({
    stopId: item.stop_id,
    line: item.line,
    direction: item.direction,
    tripId: item.trip_id,
    stopSequence: item.stop_sequence,
    vehicleNextSequence: item.vehicle_next_sequence,
    vehicleId: item.vehicle_id,
    scheduled: item.scheduled,
    predicted: item.predicted,
    scheduledMinutes:
      item.scheduled_minutes ?? item.minutes - Math.round((item.delay_sec ?? 0) / 60),
    minutes: item.minutes,
    delaySec: item.delay_sec,
    color: lineColor(item.line),
    live: item.live,
  }))
}

export function toVehicle(item: VehicleResponse): Vehicle {
  return {
    id: item.id,
    type: item.type,
    number: item.number,
    line: item.line,
    brigade: item.brigade,
    tripId: item.trip_id,
    delaySec: item.delay_sec,
    status: item.status,
    nextStop: item.next_stop,
    lat: item.lat,
    lon: item.lon,
    color: lineColor(item.line),
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

type VehicleResponse = {
  id: string
  type: number
  number: string
  line: string
  brigade: string
  trip_id: string
  delay_sec: number
  status: string
  next_stop: string | null
  lat: number
  lon: number
}

type StopResponse = {
  id: string
  name: string
  lat: number
  lon: number
}

type LineResponse = {
  name: string
  vehicle_type: number
}

type TripStopResponse = {
  sequence: number
  name: string
  scheduled: string
}

type DepartureResponse = {
  stop_id: string
  line: string
  direction: string
  trip_id: string
  stop_sequence: number
  vehicle_next_sequence: number | null
  vehicle_id: string | null
  scheduled: string
  predicted: string | null
  scheduled_minutes: number
  minutes: number
  delay_sec: number | null
  live: boolean
}
