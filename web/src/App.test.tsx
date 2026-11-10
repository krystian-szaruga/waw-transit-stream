import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children?: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Polyline: ({ positions }: { positions: unknown[] }) => (
    <div data-testid="map-polyline" data-points={positions.length} />
  ),
  CircleMarker: ({ children, center }: { children?: ReactNode; center: [number, number] }) => (
    <div data-testid="map-marker" data-center={center.join(',')}>
      {children}
    </div>
  ),
  Marker: ({ children, position }: { children?: ReactNode; position: [number, number] }) => (
    <div data-testid="map-bus" data-position={position.join(',')}>
      {children}
    </div>
  ),
  Tooltip: ({ children }: { children?: ReactNode }) => <span>{children}</span>,
  useMap: () => ({ setView: () => {}, fitBounds: () => {} }),
}))

const stopResponses = [
  { id: '1001', name: 'Plac Zawiszy', lat: 52.2255, lon: 20.995 },
  { id: '1002', name: 'Centrum', lat: 52.2297, lon: 21.0122 },
  { id: '1003', name: 'Rondo Daszyńskiego', lat: 52.229, lon: 20.982 },
  { id: '2001', name: 'Bitwa Warszawska', lat: 52.218, lon: 20.99 },
  { id: '2002', name: 'Bitwa Warszawska', lat: 52.219, lon: 20.991 },
]

const departureResponses = [
  {
    stop_id: '1002',
    line: '175',
    direction: 'Chomiczówka',
    trip_id: 't1',
    stop_sequence: 2,
    vehicle_next_sequence: 2,
    vehicle_id: '1:2001',
    scheduled: '2026-11-09T10:32:00+01:00',
    predicted: '2026-11-09T10:32:45+01:00',
    minutes: 2,
    delay_sec: 45,
    live: true,
  },
  {
    stop_id: '1002',
    line: '9',
    direction: 'Gocław',
    trip_id: 't2',
    stop_sequence: 3,
    vehicle_next_sequence: 3,
    vehicle_id: '2:3001',
    scheduled: '2026-11-09T10:35:00+01:00',
    predicted: '2026-11-09T10:38:00+01:00',
    minutes: 5,
    delay_sec: 180,
    live: true,
  },
  {
    stop_id: '1002',
    line: '175',
    direction: 'Lotnisko',
    trip_id: 't3',
    stop_sequence: 2,
    vehicle_next_sequence: null,
    vehicle_id: null,
    scheduled: '2026-11-09T10:39:00+01:00',
    predicted: null,
    minutes: 9,
    delay_sec: null,
    live: false,
  },
  {
    stop_id: '1002',
    line: '175',
    direction: 'Ahead test',
    trip_id: 't4',
    stop_sequence: 3,
    vehicle_next_sequence: 1,
    vehicle_id: '1:2001',
    scheduled: '2026-11-09T10:50:00+01:00',
    predicted: '2026-11-09T10:50:00+01:00',
    minutes: 12,
    delay_sec: 0,
    live: true,
  },
]

const responseBodies: Record<string, unknown> = {
  '/api/lines': [
    { name: '175', vehicle_type: 1 },
    { name: '9', vehicle_type: 2 },
  ],
  '/api/vehicles': [],
  '/api/stops': stopResponses,
  '/api/stops/1002/departures': departureResponses,
  '/api/stops/2001/departures': [
    {
      stop_id: '2001',
      line: '1',
      direction: 'Centrum',
      trip_id: 'b1',
      vehicle_id: '2:1',
      scheduled: '2026-11-09T10:33:00+01:00',
      predicted: '2026-11-09T10:33:00+01:00',
      scheduled_minutes: 3,
      minutes: 3,
      delay_sec: 0,
      live: true,
    },
  ],
  '/api/trips/t1/stops': [
    { sequence: 1, name: 'Start', scheduled: '2026-11-09T10:30:00+01:00', lat: 52.23, lon: 20.99 },
    { sequence: 2, name: 'Centrum', scheduled: '2026-11-09T10:32:00+01:00', lat: 52.231, lon: 21.0 },
    { sequence: 3, name: 'End', scheduled: '2026-11-09T10:40:00+01:00', lat: 52.24, lon: 21.01 },
  ],
  '/api/trips/t1/shape': [
    { sequence: 0, lat: 52.2295, lon: 20.989 },
    { sequence: 1, lat: 52.23, lon: 20.99 },
    { sequence: 2, lat: 52.235, lon: 21.005 },
    { sequence: 3, lat: 52.24, lon: 21.01 },
  ],
  '/api/trips/t2/stops': [
    { sequence: 1, name: 'Start', scheduled: '2026-11-09T10:30:00+01:00', lat: 52.23, lon: 20.99 },
    { sequence: 2, name: 'Middle', scheduled: '2026-11-09T10:32:00+01:00', lat: 52.232, lon: 21.0 },
    { sequence: 3, name: 'Gocław', scheduled: '2026-11-09T10:35:00+01:00', lat: 52.235, lon: 21.01 },
    { sequence: 4, name: 'End', scheduled: '2026-11-09T10:40:00+01:00', lat: 52.24, lon: 21.02 },
  ],
  '/api/trips/t3/stops': [
    { sequence: 1, name: 'Lotnisko', scheduled: '2026-11-09T10:39:00+01:00', lat: 52.16, lon: 20.96 },
    { sequence: 2, name: 'End', scheduled: '2026-11-09T10:45:00+01:00', lat: 52.17, lon: 20.97 },
  ],
  '/api/trips/t4/stops': [
    { sequence: 1, name: 'First', scheduled: '2026-11-09T10:40:00+01:00', lat: 52.22, lon: 20.98 },
    { sequence: 2, name: 'Ahead stop', scheduled: '2026-11-09T10:44:00+01:00', lat: 52.225, lon: 20.985 },
    { sequence: 3, name: 'Centrum', scheduled: '2026-11-09T10:50:00+01:00', lat: 52.231, lon: 21.0 },
    { sequence: 4, name: 'After ours', scheduled: '2026-11-09T10:55:00+01:00', lat: 52.24, lon: 21.01 },
  ],
  '/api/stops/2002/departures': [
    {
      stop_id: '2002',
      line: '2',
      direction: 'Lotnisko',
      trip_id: 'b2',
      vehicle_id: '2:2',
      scheduled: '2026-11-09T10:37:00+01:00',
      predicted: '2026-11-09T10:37:00+01:00',
      scheduled_minutes: 7,
      minutes: 7,
      delay_sec: 0,
      live: true,
    },
  ],
}

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  readonly url: string
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  send(): void {}

  close(): void {
    this.onclose?.(new CloseEvent('close'))
  }
}

function vehicleAt(tripId: string, lat: number, lon: number) {
  return {
    id: '1:2001',
    type: 1,
    number: '2001',
    line: '175',
    brigade: '3',
    trip_id: tripId,
    delay_sec: 45,
    status: 'MATCHED',
    next_stop: 'Centrum',
    lat,
    lon,
  }
}

async function renderApp() {
  render(<App />)
  await screen.findByRole('heading', { name: 'Live departures' })
}

async function selectCentrum() {
  const user = userEvent.setup()
  await user.type(screen.getByRole('searchbox', { name: 'Search stop' }), 'centrum')
  const results = screen.getByRole('list', { name: 'Stop results' })
  await user.click(within(results).getByRole('button', { name: 'Centrum' }))
  await screen.findByRole('heading', { name: 'Centrum' })
  await screen.findByRole('list', { name: 'Departures' })
  return user
}

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname
    const body = responseBodies[path]
    if (body === undefined) {
      return { ok: false, status: 404, json: async () => ({}) } as Response
    }
    return { ok: true, status: 200, json: async () => body } as Response
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
  delete document.documentElement.dataset.theme
})

describe('App', () => {
  it('when nothing is selected then the timetable prompt is shown', async () => {
    await renderApp()

    expect(screen.getByText('Select a stop to see upcoming departures.')).toBeInTheDocument()
  })

  it('when a stop is selected then departures are listed by time', async () => {
    await renderApp()
    await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')

    expect(within(rows[0]).getByText('Chomiczówka')).toBeInTheDocument()
    expect(rows[0]).toHaveTextContent('Scheduled:')
    expect(rows[0]).toHaveTextContent('2 min')
    expect(within(rows[1]).getByText('Gocław')).toBeInTheDocument()
    expect(within(rows[2]).getByText('Lotnisko')).toBeInTheDocument()
  })

  it('when a departure is live then the predicted time and delay are shown', async () => {
    await renderApp()
    await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')

    expect(within(rows[0]).getByText('delayed +1 min')).toBeInTheDocument()
    expect(rows[0]).toHaveTextContent('Live:')
    expect(rows[0]).toHaveTextContent('10:32')
  })

  it('when a departure has no prediction then it is marked as schedule only', async () => {
    await renderApp()
    await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')

    expect(within(rows[2]).getByText('scheduled')).toBeInTheDocument()
  })

  it('when a departure is clicked then trip stops are shown and a second click hides them', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[0]).getByText('Chomiczówka'))

    const stops = await screen.findByRole('list', { name: 'Trip stops' })
    expect(within(stops).getByText('Start')).toBeInTheDocument()
    expect(within(stops).getByText('Centrum')).toBeInTheDocument()
    expect(within(stops).getAllByText('10:32').length).toBeGreaterThan(0)
    expect(within(stops).getByText('End')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '175 → Chomiczówka' })).toBeInTheDocument()

    await user.click(within(rows[0]).getByText('Chomiczówka'))

    expect(screen.queryByRole('list', { name: 'Trip stops' })).not.toBeInTheDocument()
  })

  it('when a trip has stops before the first one then the first is shown and the rest expand', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[1]).getByText('Gocław'))

    const stops = await screen.findByRole('list', { name: 'Trip stops' })
    expect(within(stops).getByText('Start')).toBeInTheDocument()
    expect(within(stops).queryByText('Middle')).not.toBeInTheDocument()
    expect(within(stops).getByText('Gocław')).toBeInTheDocument()

    await user.click(within(stops).getByRole('button', { name: '…' }))

    expect(within(stops).getByText('Middle')).toBeInTheDocument()
    expect(within(stops).getByText('10:38')).toBeInTheDocument()
  })

  it('when a trip is selected then the map draws its road shape, stops and the live vehicle', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[0]).getByText('Chomiczówka'))
    await screen.findByRole('list', { name: 'Trip stops' })

    const socket = FakeWebSocket.instances[0]
    await act(async () => {
      socket.onmessage?.({
        data: JSON.stringify({ type: 'snapshot', vehicles: [vehicleAt('t1', 52.2321, 21.0012)] }),
      } as MessageEvent<string>)
    })

    const map = await screen.findByRole('region', { name: 'Trip map' })
    expect(within(map).getByTestId('map-polyline')).toHaveAttribute('data-points', '4')
    expect(within(map).getAllByTestId('map-marker')).toHaveLength(3)
    expect(within(map).getByTestId('map-bus')).toBeInTheDocument()
    expect(within(map).getByText('Centrum (your stop)')).toBeInTheDocument()

    await act(async () => {
      socket.onmessage?.({
        data: JSON.stringify({ type: 'update', vehicles: [vehicleAt('t1', 52.2345, 21.0055)] }),
      } as MessageEvent<string>)
    })

    expect(within(map).getByTestId('map-bus')).toHaveAttribute('data-position', '52.2345,21.0055')
  })

  it('when a trip has not started yet then no stop is marked as past and a notice is shown', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[2]).getByText('Lotnisko'))

    const stops = await screen.findByRole('list', { name: 'Trip stops' })
    expect((await within(stops).findByText('Lotnisko')).closest('li')).toHaveClass('ahead')
    expect(within(stops).getByText('End').closest('li')).toHaveClass('future')
    expect(screen.getByText('Not started yet · passes Centrum in 9 min')).toBeInTheDocument()
  })

  it('when a theme is chosen then the document switches and the choice is remembered', async () => {
    await renderApp()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Light' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(window.localStorage.getItem('theme')).toBe('light')

    await user.click(screen.getByRole('button', { name: 'Dark' }))
    expect(document.documentElement.dataset.theme).toBe('dark')

    await user.click(screen.getByRole('button', { name: 'Auto' }))
    expect(window.localStorage.getItem('theme')).toBe('auto')
  })

  it('when the bus is before our stop then stops it still has to pass are marked ahead', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[3]).getByText('Ahead test'))

    const stops = await screen.findByRole('list', { name: 'Trip stops' })
    expect((await within(stops).findByText('Ahead stop')).closest('li')).toHaveClass('ahead')
    expect(within(stops).getByText('After ours').closest('li')).toHaveClass('future')
    expect(within(stops).getByText('Centrum').closest('li')).toHaveClass('selected')
  })

  it('when our stop is the next one then it is highlighted with a yellow ring', async () => {
    await renderApp()
    const user = await selectCentrum()

    const departures = screen.getByRole('list', { name: 'Departures' })
    const rows = within(departures).getAllByRole('listitem')
    await user.click(within(rows[0]).getByText('Chomiczówka'))

    const stops = await screen.findByRole('list', { name: 'Trip stops' })
    const centrum = (await within(stops).findByText('Centrum')).closest('li')
    expect(centrum).toHaveClass('current')
    expect(centrum).toHaveClass('selected')
  })

  it('when the stop search is typed then matching stops are offered', async () => {
    await renderApp()

    const user = userEvent.setup()
    await user.type(screen.getByRole('searchbox', { name: 'Search stop' }), 'plac')

    const results = screen.getByRole('list', { name: 'Stop results' })
    expect(within(results).getByRole('button', { name: 'Plac Zawiszy' })).toBeInTheDocument()
  })

  it('when platforms share a name then one result aggregates their departures', async () => {
    await renderApp()

    const user = userEvent.setup()
    await user.type(screen.getByRole('searchbox', { name: 'Search stop' }), 'bitwa')
    const results = screen.getByRole('list', { name: 'Stop results' })
    const buttons = within(results).getAllByRole('button')

    expect(buttons).toHaveLength(1)
    await user.click(buttons[0])
    await screen.findByRole('list', { name: 'Departures' })

    expect(screen.getByRole('heading', { name: 'Bitwa Warszawska' })).toBeInTheDocument()
    expect(screen.getByText('Upcoming departures · 2 platforms')).toBeInTheDocument()
    expect(screen.getByText('Centrum')).toBeInTheDocument()
    expect(screen.getByText('Lotnisko')).toBeInTheDocument()
  })

  it('when the selected stop is cleared then the prompt returns', async () => {
    await renderApp()
    const user = await selectCentrum()

    await user.click(screen.getByRole('button', { name: '← Change stop' }))

    expect(screen.getByText('Select a stop to see upcoming departures.')).toBeInTheDocument()
  })

  it('when the backend request fails then the error is shown', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) }) as Response))

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed with status 500')
  })

  it('when a new timetable version arrives then stops are refetched and the selected stop follows its name', async () => {
    const previousStops = responseBodies['/api/stops']
    await renderApp()
    await selectCentrum()

    responseBodies['/api/stops'] = [
      { id: '9002', name: 'Centrum', lat: 52.2297, lon: 21.0122 },
      { id: '1001', name: 'Plac Zawiszy', lat: 52.2255, lon: 20.995 },
    ]
    responseBodies['/api/stops/9002/departures'] = [
      {
        stop_id: '9002',
        line: '175',
        direction: 'Chomiczówka',
        trip_id: 't9',
        stop_sequence: 2,
        vehicle_next_sequence: 2,
        vehicle_id: '1:2001',
        scheduled: '2026-11-09T10:32:00+01:00',
        predicted: null,
        minutes: 2,
        delay_sec: null,
        live: false,
      },
    ]

    const socket = FakeWebSocket.instances[0]
    const fetchMock = vi.mocked(fetch)
    const callsBefore = fetchMock.mock.calls.length

    await act(async () => {
      socket.onmessage?.({
        data: JSON.stringify({ type: 'snapshot', vehicles: [], version: 2 }),
      } as MessageEvent<string>)
    })

    await waitFor(() => {
      expect(
        fetchMock.mock.calls
          .slice(callsBefore)
          .some(([input]) => String(input).includes('/api/stops/9002/departures')),
      ).toBe(true)
    })
    expect(
      fetchMock.mock.calls.slice(callsBefore).some(([input]) => String(input).endsWith('/api/stops')),
    ).toBe(true)
    expect(screen.getByRole('heading', { name: 'Centrum' })).toBeInTheDocument()
    expect(screen.getByTitle('Timetable v2')).toBeInTheDocument()

    responseBodies['/api/stops'] = previousStops
    delete responseBodies['/api/stops/9002/departures']
  })
})
