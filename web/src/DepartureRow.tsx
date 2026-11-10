import type { Departure } from './api'
import { delayClass, formatDelay, formatTime, minutesLabel, scheduledLabel } from './format'

export function DepartureRow({
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
