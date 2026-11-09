import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

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
    stop_sequence: 1,
    vehicle_next_sequence: null,
    vehicle_id: null,
    scheduled: '2026-11-09T10:39:00+01:00',
    predicted: null,
    minutes: 9,
    delay_sec: null,
    live: false,
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
    { sequence: 1, name: 'Start', scheduled: '2026-11-09T10:30:00+01:00' },
    { sequence: 2, name: 'Centrum', scheduled: '2026-11-09T10:32:00+01:00' },
    { sequence: 3, name: 'End', scheduled: '2026-11-09T10:40:00+01:00' },
  ],
  '/api/trips/t2/stops': [
    { sequence: 1, name: 'Start', scheduled: '2026-11-09T10:30:00+01:00' },
    { sequence: 2, name: 'Middle', scheduled: '2026-11-09T10:32:00+01:00' },
    { sequence: 3, name: 'Gocław', scheduled: '2026-11-09T10:35:00+01:00' },
    { sequence: 4, name: 'End', scheduled: '2026-11-09T10:40:00+01:00' },
  ],
  '/api/trips/t3/stops': [
    { sequence: 1, name: 'Lotnisko', scheduled: '2026-11-09T10:39:00+01:00' },
    { sequence: 2, name: 'End', scheduled: '2026-11-09T10:45:00+01:00' },
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
})
