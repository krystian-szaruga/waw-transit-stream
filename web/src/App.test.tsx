import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('when nothing is selected then the hint and every vehicle are shown', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Pick a point on the map' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(5)
  })

  it('when a vehicle on the map is clicked then its details are shown', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Vehicle 175 2001' }))

    expect(screen.getByRole('heading', { name: 'Centrum' })).toBeInTheDocument()
    expect(screen.getByText('+1 min')).toBeInTheDocument()
    expect(screen.getByText('2026-11-06:175:1:0830')).toBeInTheDocument()
  })

  it('when a stop on the map is clicked then its departures are listed by time', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Stop Centrum' }))

    expect(document.querySelector('.stop-marker.selected')).not.toBeNull()

    const departures = screen.getAllByRole('listitem')
    expect(within(departures[0]).getByText('in 2 min')).toBeInTheDocument()
    expect(within(departures[1]).getByText('in 5 min')).toBeInTheDocument()
    expect(within(departures[2]).getByText('in 9 min')).toBeInTheDocument()
  })

  it('when a line chip is clicked then only that line keeps vehicles', async () => {
    const user = userEvent.setup()
    render(<App />)

    const topbar = screen.getByRole('banner')
    await user.click(within(topbar).getByRole('button', { name: '9' }))

    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Vehicle 9 3001' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Vehicle 175 2001' })).not.toBeInTheDocument()
  })

  it('when a stop name is typed then matching stops are offered and can be selected', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByRole('searchbox', { name: 'Search stop' }), 'plac')
    const results = screen.getByRole('list', { name: 'Stop results' })
    await user.click(within(results).getByRole('button', { name: 'Plac Zawiszy' }))

    expect(screen.getByRole('heading', { name: 'Plac Zawiszy' })).toBeInTheDocument()
    expect(screen.getByText('in 3 min')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search stop' })).toHaveValue('')
  })

  it('when back is clicked after selecting a stop then the hint returns', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Stop Centrum' }))
    await user.click(screen.getByRole('button', { name: '← Back' }))

    expect(screen.getByRole('heading', { name: 'Pick a point on the map' })).toBeInTheDocument()
  })

  it('when a vehicle in the list is clicked then the hint is replaced by its details', async () => {
    const user = userEvent.setup()
    render(<App />)

    const list = screen.getByRole('list', { name: 'Vehicles' })
    await user.click(within(list).getByText('Dw. Centralny'))

    expect(screen.getByRole('heading', { name: 'Dw. Centralny' })).toBeInTheDocument()
    expect(screen.getByText('+10 min')).toBeInTheDocument()
  })
})
