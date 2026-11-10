import { THEMES, type Theme } from './useTheme'

function themeLabel(theme: Theme): string {
  if (theme === 'auto') return 'Auto'
  return theme === 'light' ? 'Light' : 'Dark'
}

export function ThemeToggle({
  theme,
  onChange,
}: {
  theme: Theme
  onChange: (theme: Theme) => void
}) {
  return (
    <div className="theme-toggle" role="group" aria-label="Theme">
      {THEMES.map((option) => (
        <button
          key={option}
          type="button"
          className={theme === option ? 'theme-option active' : 'theme-option'}
          aria-pressed={theme === option}
          onClick={() => onChange(option)}
        >
          {themeLabel(option)}
        </button>
      ))}
    </div>
  )
}
