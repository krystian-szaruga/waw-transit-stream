import { useEffect, useState } from 'react'
import { applyTheme, type ThemeName } from './theme'

export type Theme = 'auto' | ThemeName

export const THEMES: Theme[] = ['auto', 'light', 'dark']

const THEME_KEY = 'theme'

export function useTheme(): {
  theme: Theme
  resolved: ThemeName
  setTheme: (theme: Theme) => void
} {
  const [theme, setTheme] = useState<Theme>(() => storedTheme())
  const [systemDark, setSystemDark] = useState(() => prefersDark())

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    query.addEventListener('change', listener)
    return () => query.removeEventListener('change', listener)
  }, [])

  const resolved: ThemeName = theme === 'auto' ? (systemDark ? 'dark' : 'light') : theme

  useEffect(() => {
    window.localStorage.setItem(THEME_KEY, theme)
    applyTheme(resolved, document.documentElement)
  }, [theme, resolved])

  return { theme, resolved, setTheme }
}

function storedTheme(): Theme {
  const stored = window.localStorage.getItem(THEME_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'auto' ? stored : 'auto'
}

function prefersDark(): boolean {
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : true
}
