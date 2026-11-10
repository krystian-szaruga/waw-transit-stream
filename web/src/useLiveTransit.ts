import { useEffect, useRef, useState } from 'react'
import {
  loadDepartures,
  loadLines,
  loadStops,
  loadVehicles,
  toVehicle,
  type Departure,
  type Line,
  type Stop,
  type Vehicle,
} from './api'

export type ConnectionStatus = 'connecting' | 'live' | 'offline'

export type TransitData = {
  lines: Line[]
  stops: Stop[]
  vehicles: Vehicle[]
  departures: Departure[]
  departuresLoading: boolean
  status: ConnectionStatus
  error: string | null
  socketError: string | null
  version: number | null
  retry: () => void
}

export function useLiveTransit(stopIds: string[]): TransitData {
  const [lines, setLines] = useState<Line[]>([])
  const [stops, setStops] = useState<Stop[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [departureState, setDepartureState] = useState<DepartureState | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [requestError, setRequestError] = useState<string | null>(null)
  const [socketError, setSocketError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const [retryCount, setRetryCount] = useState(0)
  const [version, setVersion] = useState<number | null>(null)
  const versionRef = useRef<number | null>(null)
  const stopKey = stopIds.join(',')

  useEffect(() => {
    let cancelled = false
    Promise.all([loadLines(), loadStops(), loadVehicles()])
      .then(([loadedLines, loadedStops, loadedVehicles]) => {
        if (cancelled) return
        setLines(loadedLines)
        setStops(loadedStops)
        setVehicles(loadedVehicles)
        setRequestError(null)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setRequestError(errorMessage(reason))
      })
    return () => {
      cancelled = true
    }
  }, [version, retryCount])

  useEffect(() => {
    let socket: WebSocket | null = null
    let retryTimer: number | undefined
    let attempt = 0
    let stopped = false

    const connect = () => {
      socket = new WebSocket(WS_URL)
      socket.onopen = () => {
        attempt = 0
        setStatus('live')
        setSocketError(null)
        socket?.send(JSON.stringify({ type: 'subscribe', line: null, stop_id: null }))
      }
      socket.onmessage = (event: MessageEvent<string>) => {
        const message = parseMessage(event.data)
        if (message === null) return
        setVehicles(message.vehicles.map(toVehicle))
        if (typeof message.version === 'number' && versionRef.current !== message.version) {
          versionRef.current = message.version
          setVersion(message.version)
        }
        setRevision((value) => value + 1)
      }
      socket.onerror = () => {
        setSocketError('WebSocket connection failed')
      }
      socket.onclose = (event: CloseEvent) => {
        if (stopped) return
        setStatus('offline')
        setSocketError(`WebSocket closed (${event.code})`)
        attempt += 1
        retryTimer = window.setTimeout(() => {
          setStatus('connecting')
          connect()
        }, Math.min(1000 * 2 ** (attempt - 1), 30000))
      }
    }

    connect()
    return () => {
      stopped = true
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
      socket?.close()
    }
  }, [])

  useEffect(() => {
    if (stopIds.length === 0) return
    let cancelled = false
    Promise.all(stopIds.map((stopId) => loadDepartures(stopId)))
      .then((groups) => {
        if (!cancelled) {
          setDepartureState({ stopKey, items: mergeDepartures(groups.flat()) })
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) setRequestError(errorMessage(reason))
      })
    return () => {
      cancelled = true
    }
  }, [stopKey, revision, retryCount])

  const departures = departureState?.stopKey === stopKey ? departureState.items : []
  const departuresLoading =
    stopIds.length > 0 && departureState?.stopKey !== stopKey && requestError === null
  const retry = () => setRetryCount((value) => value + 1)
  const error = requestError
  return { lines, stops, vehicles, departures, departuresLoading, status, error, socketError, version, retry }
}

function parseMessage(raw: string): LiveMessage | null {
  try {
    const data: unknown = JSON.parse(raw)
    if (typeof data !== 'object' || data === null) return null
    const message = data as Partial<LiveMessage>
    if (message.type !== 'snapshot' && message.type !== 'update') return null
    if (!Array.isArray(message.vehicles)) return null
    return message as LiveMessage
  } catch {
    return null
  }
}

function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : 'Unable to load transit data'
}

function mergeDepartures(items: Departure[]): Departure[] {
  const unique = new Map<string, Departure>()
  for (const item of items) {
    const key = `${item.tripId}|${item.scheduled}`
    const current = unique.get(key)
    if (current === undefined || (!current.live && item.live)) {
      unique.set(key, item)
    }
  }
  return [...unique.values()].sort(
    (a, b) => new Date(a.scheduled).getTime() - new Date(b.scheduled).getTime(),
  )
}

type LiveMessage = {
  type: 'snapshot' | 'update'
  vehicles: LiveVehicle[]
  version?: number | null
}

type DepartureState = {
  stopKey: string
  items: Departure[]
}

type LiveVehicle = {
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

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss' : 'ws'

const WS_URL =
  import.meta.env.VITE_WS_BASE_URL ??
  (import.meta.env.DEV
    ? `${WS_PROTOCOL}://${window.location.hostname}:8000/ws`
    : `${WS_PROTOCOL}://${window.location.host}/ws`)
