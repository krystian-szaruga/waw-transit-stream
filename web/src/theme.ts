export type ThemeName = 'light' | 'dark'

export type Palette = {
  background: string
  surface: string
  surfaceAlt: string
  surfaceRaised: string
  surfaceHover: string
  border: string
  borderStrong: string
  borderSubtle: string
  text: string
  textSoft: string
  textMuted: string
  textDim: string
  accent: string
  yellow: string
  wine: string
  ok: string
  okBright: string
  late: string
  early: string
  danger: string
  dangerBg: string
  dangerText: string
  selectedBg: string
  scheduledBg: string
  yellowWash: string
  ahead: string
  mapFilter: string
}

export const PALETTES: Record<ThemeName, Palette> = {
  dark: {
    background: '#0d1117',
    surface: '#0f141c',
    surfaceAlt: '#0b1017',
    surfaceRaised: '#131a24',
    surfaceHover: '#151b25',
    border: '#1b2230',
    borderStrong: '#2a3442',
    borderSubtle: '#151b25',
    text: '#e6edf3',
    textSoft: '#c9d1d9',
    textMuted: '#9aa4b2',
    textDim: '#6b7684',
    accent: '#4c7be1',
    yellow: '#ffd43b',
    wine: '#ae3ec9',
    ok: '#2f9e44',
    okBright: '#51cf66',
    late: '#ff922b',
    early: '#74c0fc',
    danger: '#d6336c',
    dangerBg: '#2b1219',
    dangerText: '#ffc9d6',
    selectedBg: '#16202f',
    scheduledBg: 'rgba(255, 255, 255, 0.015)',
    yellowWash: 'rgba(255, 212, 59, 0.06)',
    ahead: '#4b5563',
    mapFilter: 'invert(1) hue-rotate(180deg) brightness(0.92) contrast(0.9) saturate(0.7)',
  },
  light: {
    background: '#f5f7fa',
    surface: '#ffffff',
    surfaceAlt: '#f7f9fc',
    surfaceRaised: '#ffffff',
    surfaceHover: '#f3f6fa',
    border: '#d8dee7',
    borderStrong: '#c2cad6',
    borderSubtle: '#e6ebf1',
    text: '#1b2230',
    textSoft: '#1b2230',
    textMuted: '#5b6675',
    textDim: '#8a94a2',
    accent: '#4c7be1',
    yellow: '#d99e00',
    wine: '#ae3ec9',
    ok: '#2f9e44',
    okBright: '#2f9e44',
    late: '#d97706',
    early: '#1971c2',
    danger: '#d6336c',
    dangerBg: '#ffe9ef',
    dangerText: '#a61e4d',
    selectedBg: '#eef4ff',
    scheduledBg: 'rgba(15, 20, 28, 0.02)',
    yellowWash: 'rgba(217, 158, 0, 0.12)',
    ahead: '#8a94a2',
    mapFilter: 'none',
  },
}

export const MAP_COLORS = {
  passed: '#9aa4b2',
  ahead: '#4b5563',
  future: '#4c7be1',
  next: '#ffd43b',
  ours: '#ae3ec9',
  busRing: '#ffffff',
  busText: '#ffffff',
}

export const CSS_VARIABLES: Record<Exclude<keyof Palette, 'mapFilter'>, string> = {
  background: '--c-bg',
  surface: '--c-surface',
  surfaceAlt: '--c-surface-alt',
  surfaceRaised: '--c-surface-raised',
  surfaceHover: '--c-surface-hover',
  border: '--c-border',
  borderStrong: '--c-border-strong',
  borderSubtle: '--c-border-subtle',
  text: '--c-text',
  textSoft: '--c-text-soft',
  textMuted: '--c-text-muted',
  textDim: '--c-text-dim',
  accent: '--c-accent',
  yellow: '--c-yellow',
  wine: '--c-wine',
  ok: '--c-ok',
  okBright: '--c-ok-bright',
  late: '--c-late',
  early: '--c-early',
  danger: '--c-danger',
  dangerBg: '--c-danger-bg',
  dangerText: '--c-danger-text',
  selectedBg: '--c-selected-bg',
  scheduledBg: '--c-scheduled-bg',
  yellowWash: '--c-yellow-wash',
  ahead: '--c-ahead',
}

export function applyTheme(theme: ThemeName, root: HTMLElement): void {
  const palette = PALETTES[theme]
  root.dataset.theme = theme
  root.style.colorScheme = theme
  for (const [key, variable] of Object.entries(CSS_VARIABLES)) {
    root.style.setProperty(variable, palette[key as keyof typeof CSS_VARIABLES])
  }
  root.style.setProperty('--c-map-filter', palette.mapFilter)
}
