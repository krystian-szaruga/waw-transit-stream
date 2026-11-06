export type Vehicle = {
  id: string
  type: number
  number: string
  line: string
  brigade: string
  tripId: string
  delaySec: number
  status: 'matched' | 'layover'
  nextStop: string
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

export type Departure = {
  stopId: string
  line: string
  direction: string
  minutes: number
  delaySec: number
  color: string
}

export const lines = [
  { name: '175', color: '#e8590c' },
  { name: '9', color: '#1971c2' },
  { name: 'S1', color: '#2f9e44' },
]

export const vehicles: Vehicle[] = [
  {
    id: '1:2001',
    type: 1,
    number: '2001',
    line: '175',
    brigade: '3',
    tripId: '2026-11-06:175:1:0830',
    delaySec: 45,
    status: 'matched',
    nextStop: 'Centrum',
    lat: 52.2312,
    lon: 21.0068,
    color: '#e8590c',
  },
  {
    id: '1:2002',
    type: 1,
    number: '2002',
    line: '175',
    brigade: '5',
    tripId: '2026-11-06:175:1:0850',
    delaySec: -20,
    status: 'matched',
    nextStop: 'Plac Zawiszy',
    lat: 52.2262,
    lon: 20.9975,
    color: '#e8590c',
  },
  {
    id: '2:3001',
    type: 2,
    number: '3001',
    line: '9',
    brigade: '1',
    tripId: '2026-11-06:9:1:0845',
    delaySec: 180,
    status: 'matched',
    nextStop: 'Rondo Daszyńskiego',
    lat: 52.2286,
    lon: 20.9852,
    color: '#1971c2',
  },
  {
    id: '2:3002',
    type: 2,
    number: '3002',
    line: '9',
    brigade: '2',
    tripId: '2026-11-06:9:1:0905',
    delaySec: 0,
    status: 'matched',
    nextStop: 'Most Poniatowskiego',
    lat: 52.2338,
    lon: 21.032,
    color: '#1971c2',
  },
  {
    id: '1:2003',
    type: 1,
    number: '2003',
    line: 'S1',
    brigade: '7',
    tripId: '2026-11-06:S1:1:0900',
    delaySec: 600,
    status: 'layover',
    nextStop: 'Dw. Centralny',
    lat: 52.2278,
    lon: 21.0005,
    color: '#2f9e44',
  },
]

export const stops: Stop[] = [
  { id: '1001', name: 'Plac Zawiszy', lat: 52.2255, lon: 20.995 },
  { id: '1002', name: 'Centrum', lat: 52.2297, lon: 21.0122 },
  { id: '1003', name: 'Rondo Daszyńskiego', lat: 52.229, lon: 20.982 },
  { id: '1004', name: 'Most Poniatowskiego', lat: 52.235, lon: 21.035 },
  { id: '1005', name: 'Dw. Centralny', lat: 52.2285, lon: 21.003 },
]

export const departures: Departure[] = [
  { stopId: '1002', line: '175', direction: 'Chomiczówka', minutes: 2, delaySec: 45, color: '#e8590c' },
  { stopId: '1002', line: '9', direction: 'Gocław', minutes: 5, delaySec: 180, color: '#1971c2' },
  { stopId: '1002', line: '175', direction: 'Lotnisko', minutes: 9, delaySec: -20, color: '#e8590c' },
  { stopId: '1001', line: '175', direction: 'Chomiczówka', minutes: 3, delaySec: 45, color: '#e8590c' },
  { stopId: '1001', line: 'S1', direction: 'Piaseczno', minutes: 7, delaySec: 600, color: '#2f9e44' },
  { stopId: '1003', line: '9', direction: 'Gocław', minutes: 1, delaySec: 180, color: '#1971c2' },
  { stopId: '1004', line: '9', direction: 'Praga', minutes: 4, delaySec: 0, color: '#1971c2' },
  { stopId: '1005', line: 'S1', direction: 'Legionowo', minutes: 6, delaySec: 600, color: '#2f9e44' },
]
