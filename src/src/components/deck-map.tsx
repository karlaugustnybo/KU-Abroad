import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DeckGL, type DeckGLRef } from '@deck.gl/react'
import { ScatterplotLayer } from '@deck.gl/layers'
import { WebMercatorViewport, type MapViewState, type PickingInfo } from '@deck.gl/core'
import { Map } from 'react-map-gl/maplibre'
import type { StyleSpecification } from 'maplibre-gl'
import { Crosshair, Minus, Plus, TriangleAlert, X } from 'lucide-react'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Button } from '~/components/ui/button'
import type { InstitutionSummary } from '~/lib/types'
import { loadInstitutionDetails } from '~/utils/dataset'

const MIN_ZOOM = -1
const MAX_ZOOM = 18
const WORLD_VIEW: MapViewState = { longitude: 0, latitude: 0, zoom: 1.15, pitch: 0, bearing: 0, minZoom: MIN_ZOOM, maxZoom: MAX_ZOOM }
const RENDER_PIXEL_RATIO = 2
const BASEMAP_STYLE_URL = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const CONFIGURED_BASEMAP_URL = import.meta.env.VITE_BASEMAP_URL?.trim()
const LOW_RES_TILE_URL = CONFIGURED_BASEMAP_URL?.replace('{ratio}', '') ?? 'https://tiles-a.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt'
const OMITTED_SOURCE_LAYERS = new Set(['aeroway', 'building', 'housenumber', 'poi', 'transportation', 'transportation_name'])
let basemapStylePromise: Promise<StyleSpecification> | null = null
const basemapPreloadImages: HTMLImageElement[] = []
let savedView: MapViewState | null = null
const LOW_RES_SOURCE = CONFIGURED_BASEMAP_URL
  ? { type: 'raster' as const, tiles: [LOW_RES_TILE_URL], tileSize: 256, maxzoom: 1, attribution: '&copy; OpenStreetMap contributors &copy; CARTO' }
  : { type: 'vector' as const, tiles: [LOW_RES_TILE_URL], maxzoom: 1, attribution: '&copy; OpenStreetMap contributors &copy; CARTO' }
// The detailed CARTO source supplies the same credit once it is available.
const FULL_STYLE_LOW_RES_SOURCE = { ...LOW_RES_SOURCE, attribution: undefined }
const BACKGROUND_LAYER = { id: 'background', type: 'background' as const, paint: { 'background-color': '#f4f1eb' } }
const LOW_RES_LAYERS: StyleSpecification['layers'] = CONFIGURED_BASEMAP_URL
  ? [{ id: 'low-res-basemap', type: 'raster', source: 'low-res-basemap', paint: { 'raster-fade-duration': 0 } }]
  : [
      { id: 'low-res-water', type: 'fill', source: 'low-res-basemap', 'source-layer': 'water', paint: { 'fill-color': '#d4dadc' } },
      { id: 'low-res-boundaries', type: 'line', source: 'low-res-basemap', 'source-layer': 'boundary', filter: ['==', 'admin_level', 2], paint: { 'line-color': '#dcc9cb', 'line-width': 0.5 } },
    ]
const INITIAL_BASEMAP_STYLE: StyleSpecification = { version: 8, sources: { 'low-res-basemap': LOW_RES_SOURCE }, layers: [BACKGROUND_LAYER, ...LOW_RES_LAYERS] }

function retinaRasterTileUrl(url: string): string {
  if (url.includes('{ratio}')) return url.replace('{ratio}', '@2x')
  return url.replace(/\.(png|jpe?g|webp)(?=\?|$)/i, '@2x.$1')
}

function rasterBasemapStyle(url: string): StyleSpecification {
  return {
    version: 8,
    sources: {
      'low-res-basemap': FULL_STYLE_LOW_RES_SOURCE,
      basemap: {
        type: 'raster',
        tiles: [retinaRasterTileUrl(url)],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      },
    },
    layers: [BACKGROUND_LAYER, ...LOW_RES_LAYERS,
      {
        id: 'basemap',
        type: 'raster',
        source: 'basemap',
        paint: {
          'raster-opacity': 1,
          'raster-fade-duration': 220,
          'raster-resampling': 'linear',
        },
      },
    ],
  }
}

function preloadInitialTiles() {
  if (basemapPreloadImages.length || typeof window === 'undefined') return
  for (let x = 0; x <= 1; x += 1) {
    for (let y = 0; y <= 1; y += 1) {
      const url = LOW_RES_TILE_URL.replace('{z}', '1').replace('{x}', String(x)).replace('{y}', String(y))
      if (CONFIGURED_BASEMAP_URL) {
        const image = new Image()
        image.decoding = 'async'
        image.src = url
        basemapPreloadImages.push(image)
      } else {
        void fetch(url, { cache: 'force-cache' }).catch(() => undefined)
      }
    }
  }
}

export function preloadBasemapStyle(): Promise<StyleSpecification> {
  if (!basemapStylePromise) {
    preloadInitialTiles()
    if (CONFIGURED_BASEMAP_URL) {
      basemapStylePromise = Promise.resolve(rasterBasemapStyle(CONFIGURED_BASEMAP_URL))
      return basemapStylePromise
    }

    basemapStylePromise = fetch(BASEMAP_STYLE_URL, { cache: 'force-cache' })
      .then(response => {
        if (!response.ok) throw new Error(`Unable to load the basemap style (${response.status})`)
        return response.json() as Promise<StyleSpecification>
      })
      .then(style => ({
        ...style,
        sources: { ...style.sources, 'low-res-basemap': FULL_STYLE_LOW_RES_SOURCE },
        layers: [BACKGROUND_LAYER, ...LOW_RES_LAYERS, ...style.layers.filter(layer => {
          if (layer.type === 'background') return false
          const sourceLayer = 'source-layer' in layer ? layer['source-layer'] : undefined
          return !sourceLayer || !OMITTED_SOURCE_LAYERS.has(sourceLayer)
        })],
      }))
      .catch(error => {
        basemapStylePromise = null
        throw error
      })
  }
  return basemapStylePromise
}

interface Props {
  active: boolean
  focusSelected: boolean
  institutions: InstitutionSummary[]
  selected: InstitutionSummary | null
  onSelect: (institution: InstitutionSummary, clickStartedAt: number) => void
  onShowTable: () => void
}

function fitView(institutions: InstitutionSummary[], width = 900, height = 650): MapViewState {
  const points = institutions.filter(institution => institution.lat != null && institution.lon != null)
  if (!points.length) return WORLD_VIEW
  if (points.length === 1) return { ...WORLD_VIEW, longitude: points[0].lon!, latitude: points[0].lat!, zoom: 5 }
  const longitudes = points.map(point => point.lon!)
  const latitudes = points.map(point => point.lat!)
  const viewport = new WebMercatorViewport({ width, height }).fitBounds([
    [Math.min(...longitudes), Math.min(...latitudes)],
    [Math.max(...longitudes), Math.max(...latitudes)],
  ], { padding: 56, maxZoom: 7 })
  return { longitude: viewport.longitude, latitude: viewport.latitude, zoom: viewport.zoom, bearing: 0, pitch: 0, minZoom: MIN_ZOOM, maxZoom: MAX_ZOOM }
}

function worldView(width = 900): MapViewState {
  const paddedWidth = Math.max(width - 32, 256)
  return { ...WORLD_VIEW, zoom: Math.max(MIN_ZOOM, Math.log2(paddedWidth / 512)) }
}

function DeckMap({ active, focusSelected, institutions, selected, onSelect, onShowTable }: Props) {
  const points = useMemo(() => institutions.filter(institution => institution.lat != null && institution.lon != null), [institutions])
  const [viewState, setViewState] = useState<MapViewState>(() => selected ? { ...WORLD_VIEW, longitude: selected.lon!, latitude: selected.lat!, zoom: 5 } : savedView ?? fitView(points))
  const currentView = useRef(viewState)
  const hoveredIdRef = useRef<string | null>(null)
  const hoverLabelRef = useRef<HTMLDivElement>(null)
  const mapContainer = useRef<HTMLDivElement>(null)
  const deckRef = useRef<DeckGLRef | null>(null)
  const pointerDown = useRef<{ id: number; x: number; y: number } | null>(null)
  const [basemapStyle, setBasemapStyle] = useState<StyleSpecification>(INITIAL_BASEMAP_STYLE)
  const [overlap, setOverlap] = useState<InstitutionSummary[]>([])
  const [mapError, setMapError] = useState(false)
  useEffect(() => {
    let cancelled = false
    void preloadBasemapStyle()
      .then(style => { if (!cancelled) setBasemapStyle(style) })
      .catch(() => { if (!cancelled) setMapError(true) })
    return () => { cancelled = true }
  }, [])
  const rememberView = useCallback((next: MapViewState) => {
    currentView.current = next
    savedView = next
    setViewState(next)
  }, [])
  useEffect(() => {
    if (!active) {
      hoveredIdRef.current = null
      if (hoverLabelRef.current) hoverLabelRef.current.hidden = true
    }
  }, [active])
  useEffect(() => {
    if (!focusSelected || selected?.lat == null || selected.lon == null) return
    rememberView({ ...currentView.current, latitude: selected.lat, longitude: selected.lon, zoom: Math.max(currentView.current.zoom, 5) })
  }, [focusSelected, selected?.id, selected?.lat, selected?.lon, rememberView])
  const moveTo = useCallback((next: MapViewState) => {
    rememberView(next)
  }, [rememberView])
  const resetToWorld = () => moveTo(worldView(mapContainer.current?.clientWidth))
  const handleHover = useCallback((info: PickingInfo<InstitutionSummary>) => {
    const nextId = info.object?.id ?? null
    if (nextId === hoveredIdRef.current) return
    hoveredIdRef.current = nextId
    const label = hoverLabelRef.current
    if (label) {
      label.hidden = !info.object
      if (info.object) {
        label.textContent = info.object.name
        label.style.left = `clamp(8.5rem, ${info.x}px, calc(100% - 8.5rem))`
        label.style.top = `${info.y}px`
        label.style.transform = info.y < 72 ? 'translate(-50%, 0.75rem)' : 'translate(-50%, calc(-100% - 0.75rem))'
      }
    }
    if (info.object) void loadInstitutionDetails(info.object.id).catch(() => undefined)
  }, [])
  const selectHit = useCallback((hit: InstitutionSummary, clickStartedAt: number) => {
    const matches = points.filter(point => Math.abs(point.lon! - hit.lon!) < 0.00001 && Math.abs(point.lat! - hit.lat!) < 0.00001)
    if (matches.length > 1) setOverlap(matches)
    else {
      onSelect(hit, clickStartedAt)
      void loadInstitutionDetails(hit.id).catch(() => undefined)
    }
  }, [points, onSelect])
  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!event.isPrimary || event.button !== 0 || !(event.target instanceof Element) || event.target.closest('button, a, input, [role="button"]')) return
    const bounds = deckRef.current?.deck?.getCanvas()?.getBoundingClientRect()
    if (!bounds || event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) return
    pointerDown.current = { id: event.pointerId, x: event.clientX, y: event.clientY }
  }, [])
  const handlePointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const start = pointerDown.current
    pointerDown.current = null
    if (!start || start.id !== event.pointerId || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 8) return
    const canvas = deckRef.current?.deck?.getCanvas()
    if (!canvas) return
    const bounds = canvas.getBoundingClientRect()
    const picked = (deckRef.current?.pickObject({ x: event.clientX - bounds.left, y: event.clientY - bounds.top }) as PickingInfo<InstitutionSummary> | null)?.object
    if (picked) {
      const hit = picked
      const clickStartedAt = event.timeStamp
      window.setTimeout(() => selectHit(hit, clickStartedAt), 0)
    }
  }, [selectHit])
  const layers = useMemo(() => [new ScatterplotLayer<InstitutionSummary>({
    id: 'institutions', data: points, pickable: true, autoHighlight: true, highlightColor: [80, 32, 44, 255], opacity: 0.88, stroked: true, filled: true,
    radiusUnits: 'pixels', getRadius: 7, radiusMinPixels: 6, radiusMaxPixels: 10,
    lineWidthUnits: 'pixels', getLineWidth: institution => institution.id === selected?.id ? 3 : 1.5,
    getPosition: institution => [institution.lon!, institution.lat!],
    getFillColor: institution => institution.id === selected?.id ? [153, 27, 27] : [24, 33, 43],
    getLineColor: [255, 255, 255],
    onHover: handleHover,
    updateTriggers: { getFillColor: selected?.id, getLineWidth: selected?.id },
  })], [points, selected?.id, handleHover])

  return <div ref={mapContainer} className="map-frame-content relative isolate h-full w-full overflow-hidden" onPointerDownCapture={handlePointerDown} onPointerUpCapture={handlePointerUp} onPointerCancelCapture={() => { pointerDown.current = null }}>
    <DeckGL ref={deckRef} viewState={viewState} controller layers={layers} useDevicePixels={RENDER_PIXEL_RATIO} onViewStateChange={({ viewState: next }) => rememberView(next as MapViewState)} getCursor={({ isDragging, isHovering }) => isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'}>
      <Map mapStyle={basemapStyle} minZoom={MIN_ZOOM} pixelRatio={RENDER_PIXEL_RATIO} fadeDuration={0} maxTileCacheZoomLevels={12} refreshExpiredTiles={false} cancelPendingTileRequestsWhileZooming reuseMaps onError={() => setMapError(true)} />
    </DeckGL>
    <div ref={hoverLabelRef} role="tooltip" hidden className="pointer-events-none absolute z-20 w-max max-w-64 rounded-lg bg-[#18212b] px-2.5 py-2 text-center text-sm font-medium leading-tight text-white shadow-lg" />
    {mapError ? <div role="status" className="absolute bottom-3 left-3 z-10 flex max-w-[calc(100%-1.5rem)] items-center gap-2 rounded-lg border bg-background/95 px-3 py-2 text-xs shadow-sm"><TriangleAlert className="size-4 shrink-0 text-primary" /><span>Basemap unavailable; destinations are still interactive.</span><Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onShowTable}>Table</Button></div> : null}
    <div className="absolute right-3 top-3 flex flex-col gap-1 rounded-lg border bg-background/95 p-1 shadow-sm backdrop-blur">
      <Button variant="ghost" size="icon-sm" aria-label="Zoom in" onClick={() => moveTo({ ...currentView.current, zoom: Math.min(currentView.current.zoom + 1, MAX_ZOOM) })}><Plus /></Button>
      <Button variant="ghost" size="icon-sm" aria-label="Zoom out" onClick={() => moveTo({ ...currentView.current, zoom: Math.max(currentView.current.zoom - 1, MIN_ZOOM) })}><Minus /></Button>
      <Button variant="ghost" size="icon-sm" aria-label="Return to world view" title="Return to world view" onClick={resetToWorld}><Crosshair /></Button>
    </div>
    {!!overlap.length && <div className="absolute bottom-8 left-3 w-[min(22rem,calc(100%-1.5rem))] rounded-lg border bg-background p-3 shadow-lg"><div className="mb-2 flex items-center justify-between"><p className="text-sm font-medium">Choose an institution</p><Button variant="ghost" size="icon-xs" aria-label="Close chooser" onClick={() => setOverlap([])}><X /></Button></div><div className="max-h-48 space-y-1 overflow-y-auto">{overlap.map(institution => <button key={institution.id} type="button" onClick={event => { const clickStartedAt = event.timeStamp; window.setTimeout(() => onSelect(institution, clickStartedAt), 0); setOverlap([]) }} className="block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="font-medium">{institution.name}</span><span className="block text-xs text-muted-foreground">{institution.country}</span></button>)}</div></div>}
  </div>
}

export default memo(DeckMap)
