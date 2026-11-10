import { useMemo } from 'react'
import type { StopGroup } from './stops'

export function SearchPanel({
  query,
  groups,
  onQueryChange,
  onSelect,
}: {
  query: string
  groups: StopGroup[]
  onQueryChange: (query: string) => void
  onSelect: (group: StopGroup) => void
}) {
  const matchingStops = useMemo(
    () =>
      query.trim() === ''
        ? []
        : groups
            .filter((item) => item.name.toLowerCase().includes(query.trim().toLowerCase()))
            .slice(0, 20),
    [query, groups],
  )

  return (
    <section className="search-panel">
      <div className="search">
        <input
          type="search"
          placeholder="Search stop"
          aria-label="Search stop"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
        />
        {matchingStops.length > 0 && (
          <ul className="search-results" aria-label="Stop results">
            {matchingStops.map((item) => (
              <li key={item.name}>
                <button type="button" onClick={() => onSelect(item)}>
                  {item.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
