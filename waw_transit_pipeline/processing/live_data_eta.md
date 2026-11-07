# Trip matcher: problem and fix

## Problem

Matched delays piled up at the edge of ±900 s:

- max delays: 899.86, 898.75, 898.04, ...
- min delays: -898.78, -897.12, ... (all `is_layover = true`)

### Root causes

1. **Hard cap.** `max_abs_delay_sec = 900` rejected any match with a larger delay,
   so a bus that was really 20 minutes late got no trip, or a neighbouring trip.
2. **Cap applied after `argmin`.** The best segment was chosen first and rejected
   afterwards, hiding other valid segments of the same trip.
3. **Time-only matching.** `trip.xy` holds the stop coordinates. A brigade serves the
   same stops once per cycle, so `dist_m` is about the same for all its trips and only
   `|delay|` decides. Vehicles between two scheduled visits land near half a cycle
   (about 900 s) from the nearest one, which created the wall.
4. **Cheap trip flipping.** Hysteresis was 25 cost units, so the match jumped between
   trips and delays jumped with it.
5. **`is_layover = delay < -180`** also flagged early buses mid-route, and did not
   separate depot vehicles from terminus waiting.
6. **Duplicated pings** (same vehicle and timestamp) came straight from the source.
7. **Inactive vehicles in the output:** old vehicles from 2024 that keep sending a
   stale timestamp, and depot vehicles pinging every 15 s while parked.

## Changes

### `_Config`
- Removed `fit_window_sec`, `max_abs_delay_sec`, `hysteresis_m`.
- Added `early_penalty = 3.0` and `finish_frac = 0.98`.
- `early_tol_sec` and `late_tol_sec` only limit which trips are *candidates*.
  They no longer reject results.

### `_fit`
- Plausibility (delay bounds and `max_dist_m`) is applied **before** `argmin`.
- Being early on a segment other than the first costs `early_penalty` times more.
  A bus halfway between two visits is now matched as "late for the previous trip"
  rather than "early for the next trip".
- Returns `finished` (on the last segment, `t >= finish_frac`), `seg` and `t`.

### `match`
- Incumbent trip is kept until it is finished, so a 20 or 40 minute delay no longer
  causes a switch to another trip.
- Only a new vehicle, a lost trip or a finished trip triggers a new best-cost choice.

### `Match`
- New fields: `finished`, `seg`, `t`.
- New property `waiting`: first segment, `t < 0.05`, `delay_sec < 0`.

### `_to_frame`
- `is_layover` comes from `Match.waiting` instead of `delay < -180`.

### `match_batch`
- Drops duplicate pings on `(vehicle_type, vehicle_number, time)`.

### `TripMatchStage.transform`
- Keeps only pings from the last 3 minutes (removes the 2024 vehicles).
- Drops `is_layover` rows (vehicles waiting at the terminus).
- Depot vehicles have no candidate trip (too far from the route, `max_dist_m`),
  so `trip_id` is null and they are filtered out.

## What "active" means now

| Case | Result |
|---|---|
| Stale timestamp (2024 vehicles) | removed by the freshness filter |
| Parked in the depot | no candidate within `max_dist_m`, removed |
| Waiting at the terminus | `is_layover = true`, removed from the live view |
| Late by any amount | active, keeps its trip until finished |

There is no fixed delay threshold anywhere in the active logic.

## Requirements

- `spark.sql.session.timeZone = Europe/Warsaw` (already set in `SparkSessionContext`).
- The `Time` column must be a `TimestampType`, otherwise the freshness filter
  compares text. If it is a string, add
  `live.withColumn(WarsawLiveCol.TIME, F.to_timestamp(F.col(WarsawLiveCol.TIME)))`
  before filtering.

## Bug fixed last: `TypeError: Match.__init__() takes from 5 to 7 positional arguments but 8 were given`

`_fit` passed `t` to `Match`, but `Match` in `core` had no `t` field.
Fix: add `t: float = 0.0` to `Match` and restart the Spark job (executors cache
the old class).

## Known limitations

- The first ping of a vehicle, or the first after a 30 minute gap, is still a
  time-proximity guess. The incumbent logic corrects it afterwards.
- A bus stuck in traffic on the route is still active, but a vehicle with no
  movement check is not filtered by speed.
- To improve the first guess, store the segment index in the Spark state and only
  allow forward progress.
- Check results with a delay histogram: expect a peak near 0 and a long tail to the
  late side, with no wall at ±900.



## ISUES 

# Analiza dopasowania kursów (Trip Matching) – Problem sztucznego opóźnienia (+922s)

## Opis problemu
W trakcie testów replay dla pojazdu **757** (linia **110**) zaobserwowano sytuację, w której autobus stojący fizycznie na przystanku **Perzyńskiego 02** o godzinie **16:50:22** (odległość `dist_m = 6.36`) otrzymywał w wyniku algorytmu status opóźnionego o **922 sekundy** (~15 minut i 22 sekundy), mimo że papierowy rozkład jazdy zakładał odjazd z tego przystanku o godzinie **16:50:00**.

## Przyczyna techniczna (Root Cause)
Problem nie wynika z błędu obliczeniowego wewnątrz funkcji rzutowania geometrii (`_fit`), lecz z **niepoprawnych/kłamliwych danych wejściowych w strumieniu live (API ZTM Warszawa)** dotyczących numeru brygady.

1. **Strumień Live (Ping GPS):**
   Pojazd przysłał w payloadzie informację: `Lines: 110`, `Brigade: 2`, `Time: 16:50:22`.
2. **Baza danych rozkładowych (Lookup):**
   W bazie danych (GTFS/Rozkład) dla linii 110 w tym oknie czasowym istniały dwa niezależne kursy:
   * `TRIP_ID: 2026-10-29:110:PcS:2:1630` -> **Brygada 2** | Odjazd z Perzyńskiego: **16:35:00**
   * `TRIP_ID: 2026-10-29:110:PcS:3:1645` -> **Brygada 3** | Odjazd z Perzyńskiego: **16:50:00**
3. **Zachowanie algorytmu:**
   Metoda `_active_trips` filtruje sztywno bazę danych po kluczu `TripKey(service_date, vehicle_type, line, brigade)`. Ponieważ ping deklarował brygadę **2**, algorytm dostał do dyspozycji wyłącznie kursy brygady 2. Najbliższym czasowo był kurs ze startem o 16:30 (odjazd z Perzyńskiego o 16:35).
4. **Matematyka błędu:**
   Czas rzeczywisty (`16:50:22`) minus czas rozkładowy błędnie przypisanego kursu (`16:35:00`) dał dokładnie **922 sekundy** opóźnienia. Z punktu widzenia geometrii autobus stał idealnie na trasie brygady 2 (ponieważ warianty tras dla obu brygad pokrywają się geograficznie).

## Dlaczego dane live kłamią?
Rozbieżność ta jest powszechną cechą warszawskiego systemu SIP/WTP i wynika z:
* Błędu ludzkiego (kierowca fizycznie realizuje kurs brygady 3 w ramach łączenia linii lub wozu rezerwowego, ale nie zaktualizował numeru zadania w sterowniku pokładowym).
* Znanych opóźnień i błędów synchronizacji wewnątrz centralnej szyny danych ZTM, przez co numery brygad potrafią "zamrażać" na konkretnych wozach.

## Wnioski i rekomendacje architektoniczne
Zawężanie przestrzeni wyszukiwania kandydatów (`_candidates`) wyłącznie do numeru brygady przekazanego w pingu live powoduje podatność systemu na fałszywe anomalie (efekt "widmo-opóźnienia"). 

Aby uodpornić system na ten problem, należy wdrożyć strategię **Fuzzy Brigade Matching**:
1. Modyfikacja `Lookup` i metody `_active_trips`, aby pobierała wszystkie kursy dla danej `line` (linii) i `service_date` (dnia), ignorując sztywny filtr po `ping.brigade`.
2. Pozwolenie funkcji kosztu w `_fit` na naturalne wyłonienie właściwego kursu na podstawie kombinacji najmniejszej odległości geograficznej (`dist_m`) oraz najmniejszego bezwzględnego odchylenia czasu (`delay_sec`). Przy takim podejściu kurs brygady 3 z czasem 16:50 wygrałby konkurencję z kursem brygady 2 z czasem 16:35, dając realne opóźnienie wynoszące ~22 sekundy.
