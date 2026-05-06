import { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

function money(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(numberValue)
}

function miles(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '—'
  return `${numberValue.toFixed(1)} mi`
}

function minutesToHuman(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '—'
  const totalMinutes = Math.max(0, Math.round(numberValue))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours <= 0) return `${minutes} min`
  return `${hours}h ${minutes}m`
}

function FitBounds({ bounds }) {
  const map = useMap()

  useEffect(() => {
    if (!bounds) return
    map.fitBounds(bounds, { padding: [24, 24] })
  }, [map, bounds])

  return null
}

export default function App() {
  const [startLocation, setStartLocation] = useState('Dallas, TX')
  const [endLocation, setEndLocation] = useState('Los Angeles, CA')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  const routeLine = data?.route?.geometry
  const routeCoordinates = useMemo(() => {
    const coords = routeLine?.coordinates
    if (!Array.isArray(coords)) return []
    // OSRM GeoJSON coordinates are [lon, lat]
    return coords
      .map((p) => {
        if (!Array.isArray(p) || p.length < 2) return null
        const lon = Number(p[0])
        const lat = Number(p[1])
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
        return [lat, lon]
      })
      .filter(Boolean)
  }, [routeLine])

  const mapBounds = useMemo(() => {
    if (routeCoordinates.length >= 2) return routeCoordinates
    const bbox = data?.route?.bbox
    if (!Array.isArray(bbox) || bbox.length !== 4) return null
    const [minLon, minLat, maxLon, maxLat] = bbox.map(Number)
    if (![minLon, minLat, maxLon, maxLat].every(Number.isFinite)) return null
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ]
  }, [data, routeCoordinates])

  const startMarker = routeCoordinates.length ? routeCoordinates[0] : null
  const endMarker = routeCoordinates.length ? routeCoordinates[routeCoordinates.length - 1] : null

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    setData(null)

    try {
      const res = await fetch('/api/fuel-routes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_location: startLocation,
          end_location: endLocation,
          include_geometry_coordinates: true,
        }),
      })

      const json = await res.json().catch(() => null)
      if (!res.ok) {
        const message = json?.error || `Request failed (${res.status})`
        throw new Error(message)
      }
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between gap-4">
          <div className="text-left">
            <h1 className="text-lg font-semibold tracking-tight">FuelSpotter</h1>
            <p className="text-sm text-slate-400">Route + optimal fuel stops (USA)</p>
          </div>
          <div className="text-sm text-slate-400">Backend: <span className="text-slate-200">/api/fuel-routes/</span></div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 grid grid-cols-1 lg:grid-cols-5 gap-4">
        <section className="lg:col-span-2 space-y-4">
          <form onSubmit={submit} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left">
            <div className="grid grid-cols-1 gap-3">
              <label className="block">
                <div className="text-xs font-medium text-slate-300">Start location</div>
                <input
                  value={startLocation}
                  onChange={(e) => setStartLocation(e.target.value)}
                  placeholder="e.g. Dallas, TX"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </label>
              <label className="block">
                <div className="text-xs font-medium text-slate-300">End location</div>
                <input
                  value={endLocation}
                  onChange={(e) => setEndLocation(e.target.value)}
                  placeholder="e.g. Los Angeles, CA"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </label>
              <button
                type="submit"
                disabled={loading || !startLocation.trim() || !endLocation.trim()}
                className="inline-flex items-center justify-center rounded-lg bg-slate-200 px-3 py-2 text-sm font-semibold text-slate-900 disabled:opacity-50"
              >
                {loading ? 'Planning…' : 'Plan fuel stops'}
              </button>
              {error ? (
                <div className="rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-2 text-sm text-rose-200">
                  {error}
                </div>
              ) : null}
            </div>
          </form>

          <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left">
            <h2 className="text-sm font-semibold">Summary</h2>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-slate-400">Distance</div>
                <div className="font-medium">{miles(data?.route?.distance_miles)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Duration</div>
                <div className="font-medium">{minutesToHuman(data?.route?.estimated_duration_minutes)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Fuel cost</div>
                <div className="font-medium">{money(data?.summary?.total_fuel_cost)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Stops</div>
                <div className="font-medium">{data?.summary?.total_stops ?? '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Vehicle range</div>
                <div className="font-medium">{data?.summary?.vehicle?.max_range_miles ? `${data.summary.vehicle.max_range_miles} mi` : '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Mileage</div>
                <div className="font-medium">{data?.summary?.vehicle?.mileage_mpg ? `${data.summary.vehicle.mileage_mpg} mpg` : '—'}</div>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-left">
            <h2 className="text-sm font-semibold">Fuel stops</h2>
            {Array.isArray(data?.fuel_stops) && data.fuel_stops.length ? (
              <ol className="mt-3 space-y-3">
                {data.fuel_stops.map((s) => (
                  <li key={s.stop_number} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold">Stop {s.stop_number}</div>
                        <div className="text-xs text-slate-400">
                          {s?.location?.city}, {s?.location?.state}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-slate-400">Cost</div>
                        <div className="text-sm font-semibold">{money(s?.fuel?.cost)}</div>
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-300">
                      <div>
                        <span className="text-slate-500">Price/gal:</span> {s?.station?.price_per_gallon ?? '—'}
                      </div>
                      <div>
                        <span className="text-slate-500">Gallons:</span> {s?.fuel?.gallons_filled ?? '—'}
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500">Station:</span> {s?.station?.name || '—'}
                        {s?.station?.address ? ` — ${s.station.address}` : ''}
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500">Distance from start:</span> {miles(s?.distance_from_start_miles)}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-2 text-sm text-slate-400">No route planned yet.</p>
            )}
          </section>
        </section>

        <section className="lg:col-span-3 rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Map</h2>
            <div className="text-xs text-slate-400">
              {routeCoordinates.length ? `${routeCoordinates.length} points` : 'Submit to render route'}
            </div>
          </div>

          <div className="h-[520px]">
            <MapContainer
              center={[39.8283, -98.5795]}
              zoom={4}
              className="h-full w-full text-slate-200"
              scrollWheelZoom
            >
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {mapBounds ? <FitBounds bounds={mapBounds} /> : null}

              {routeCoordinates.length ? (
                <Polyline positions={routeCoordinates} pathOptions={{ color: 'currentColor', weight: 4 }} />
              ) : null}

              {startMarker ? (
                <Marker position={startMarker}>
                  <Popup>Start</Popup>
                </Marker>
              ) : null}
              {endMarker ? (
                <Marker position={endMarker}>
                  <Popup>End</Popup>
                </Marker>
              ) : null}

              {Array.isArray(data?.fuel_stops)
                ? data.fuel_stops
                  .filter((s) => Number.isFinite(Number(s?.location?.lat)) && Number.isFinite(Number(s?.location?.lng)))
                  .map((s) => (
                    <Marker key={`stop-${s.stop_number}`} position={[Number(s.location.lat), Number(s.location.lng)]}>
                      <Popup>
                        <div className="text-sm font-semibold">Stop {s.stop_number}</div>
                        <div className="text-xs">{s?.location?.city}, {s?.location?.state}</div>
                        <div className="text-xs">Cost: {money(s?.fuel?.cost)}</div>
                      </Popup>
                    </Marker>
                  ))
                : null}
            </MapContainer>
          </div>
        </section>
      </main>
    </div>
  )
}
