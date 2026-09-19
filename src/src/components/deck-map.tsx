import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DeckGL } from '@deck.gl/react'
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
const BASEMAP_TILEJSON_URL = 'https://tiles.basemaps.cartocdn.com/vector/carto.streets/v1/tiles.json'
const CONFIGURED_BASEMAP_URL = import.meta.env.VITE_BASEMAP_URL?.trim()
const OMITTED_SOURCE_LAYERS = new Set(['aeroway', 'building', 'housenumber', 'poi', 'transportation', 'transportation_name'])
let basemapStylePromise: Promise<StyleSpecification> | null = null
const basemapPreloadImages: HTMLImageElement[] = []
let savedView: MapViewState | null = null

interface HoverLabel {
  institution: InstitutionSummary
  x: number
  y: number
}

function retinaRasterTileUrl(url: string): string {
  if (url.includes('{ratio}')) return url.replace('{ratio}', '@2x')
  return url.replace(/\.(png|jpe?g|webp)(?=\?|$)/i, '@2x.$1')
}

function rasterBasemapStyle(url: string): StyleSpecification {
  return {
    version: 8,
    sources: {
      basemap: {
        type: 'raster',
        tiles: [retinaRasterTileUrl(url)],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#f4f1eb' } },
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

function preloadInitialRasterTiles(url: string) {
  if (typeof Image === 'undefined' || basemapPreloadImages.length) return
  const template = retinaRasterTileUrl(url)
  for (let x = 0; x <= 1; x += 1) {
    for (let y = 0; y <= 1; y += 1) {
      const image = new Image()
      image.decoding = 'async'
      image.src = template.replace('{z}', '1').replace('{x}', String(x)).replace('{y}', String(y))
      basemapPreloadImages.push(image)
    }
  }
}

export function preloadBasemapStyle(): Promise<StyleSpecification> {
  if (!basemapStylePromise) {
    if (CONFIGURED_BASEMAP_URL) {
      preloadInitialRasterTiles(CONFIGURED_BASEMAP_URL)
      basemapStylePromise = Promise.resolve(rasterBasemapStyle(CONFIGURED_BASEMAP_URL))
      return basemapStylePromise
    }

    void fetch(BASEMAP_TILEJSON_URL, { cache: 'force-cache' }).catch(() => undefined)
    basemapStylePromise = fetch(BASEMAP_STYLE_URL, { cache: 'force-cache' })
      .then(response => {
        if (!response.ok) throw new Error(`Unable to load the basemap style (${response.status})`)
        return response.json() as Promise<StyleSpecification>
      })
      .then(style => ({
        ...style,
        layers: style.layers.filter(layer => {
          const sourceLayer = 'source-layer' in layer ? layer['source-layer'] : undefined
          return !sourceLayer || !OMITTED_SOURCE_LAYERS.has(sourceLayer)
        }),
      }))
      .catch(error => {
        basemapStylePromise = null
        throw error
      })
  }
  return basemapStylePromise
}

interface Props {
  institutions: InstitutionSummary[]
  selected: InstitutionSummary | null
  onSelect: (institution: InstitutionSummary) => void
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

function DeckMap({ institutions, selected, onSelect, onShowTable }: Props) {
  const points = useMemo(() => institutions.filter(institution => institution.lat != null && institution.lon != null), [institutions])
  const [viewState, setViewState] = useState<MapViewState>(() => selected ? { ...WORLD_VIEW, longitude: selected.lon!, latitude: selected.lat!, zoom: 5 } : savedView ?? fitView(points))
  const currentView = useRef(viewState)
  const hoveredIdRef = useRef<string | null>(null)
  const mapContainer = useRef<HTMLDivElement>(null)
  const [basemapStyle, setBasemapStyle] = useState<StyleSpecification | null>(null)
  const [overlap, setOverlap] = useState<InstitutionSummary[]>([])
  const [hovered, setHovered] = useState<HoverLabel | null>(null)
  const hoveredId = hovered?.institution.id ?? null
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
  const moveTo = useCallback((next: MapViewState) => {
    rememberView(next)
  }, [rememberView])
  const resetToWorld = () => moveTo(worldView(mapContainer.current?.clientWidth))
  const handleHover = useCallback((info: PickingInfo<InstitutionSummary>) => {
    const nextId = info.object?.id ?? null
    if (nextId === hoveredIdRef.current) return
    hoveredIdRef.current = nextId
    setHovered(info.object ? { institution: info.object, x: info.x, y: info.y } : null)
    if (info.object) void loadInstitutionDetails(info.object.id).catch(() => undefined)
  }, [])
  const layers = useMemo(() => [new ScatterplotLayer<InstitutionSummary>({
    id: 'institutions', data: points, pickable: true, opacity: 0.88, stroked: true, filled: true,
    radiusUnits: 'pixels', getRadius: institution => institution.id === hoveredId ? 9 : 7, radiusMinPixels: 6, radiusMaxPixels: 10,
    lineWidthUnits: 'pixels', getLineWidth: institution => institution.id === selected?.id || institution.id === hoveredId ? 3 : 1.5,
    getPosition: institution => [institution.lon!, institution.lat!],
    getFillColor: institution => institution.id === selected?.id ? [153, 27, 27] : institution.id === hoveredId ? [80, 32, 44] : [24, 33, 43],
    getLineColor: [255, 255, 255],
    onHover: handleHover,
    onClick: info => {
      if (!info.object) return
      const hit = info.object
      const matches = points.filter(point => Math.abs(point.lon! - hit.lon!) < 0.00001 && Math.abs(point.lat! - hit.lat!) < 0.00001)
      if (matches.length > 1) setOverlap(matches)
      else {
        onSelect(hit)
        void loadInstitutionDetails(hit.id).catch(() => undefined)
      }
    },
    updateTriggers: { getRadius: [hoveredId], getFillColor: [selected?.id, hoveredId], getLineWidth: [selected?.id, hoveredId] },
  })], [points, selected?.id, hoveredId, handleHover, onSelect])

  if (mapError) return <div className="flex h-full flex-col items-center justify-center gap-3 bg-muted/30 p-8 text-center"><TriangleAlert className="size-6 text-primary" /><div><p className="font-medium">The map could not be loaded</p><p className="mt-1 text-sm text-muted-foreground">All destinations remain available in the table.</p></div><Button variant="outline" onClick={onShowTable}>Open table</Button></div>
  if (!basemapStyle) return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading map…</div>

  return <div ref={mapContainer} className="relative isolate h-full w-full overflow-hidden rounded-xl">
    <DeckGL viewState={viewState} controller layers={layers} useDevicePixels={RENDER_PIXEL_RATIO} onViewStateChange={({ viewState: next }) => rememberView(next as MapViewState)} getCursor={({ isDragging, isHovering }) => isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'}>
      <Map mapStyle={basemapStyle} minZoom={MIN_ZOOM} pixelRatio={RENDER_PIXEL_RATIO} fadeDuration={0} maxTileCacheZoomLevels={12} refreshExpiredTiles={false} cancelPendingTileRequestsWhileZooming reuseMaps onError={() => setMapError(true)} />
    </DeckGL>
    {hovered ? <div role="tooltip" className="pointer-events-none absolute z-20 w-max max-w-64 rounded-lg bg-[#18212b] px-2.5 py-2 text-center text-sm font-medium leading-tight text-white shadow-lg" style={{ left: `clamp(8.5rem, ${hovered.x}px, calc(100% - 8.5rem))`, top: hovered.y, transform: hovered.y < 72 ? 'translate(-50%, 0.75rem)' : 'translate(-50%, calc(-100% - 0.75rem))' }}>{hovered.institution.name}</div> : null}
    <div className="absolute right-3 top-3 flex flex-col gap-1 rounded-lg border bg-background/95 p-1 shadow-sm backdrop-blur">
      <Button variant="ghost" size="icon-sm" aria-label="Zoom in" onClick={() => moveTo({ ...currentView.current, zoom: Math.min(currentView.current.zoom + 1, MAX_ZOOM) })}><Plus /></Button>
      <Button variant="ghost" size="icon-sm" aria-label="Zoom out" onClick={() => moveTo({ ...currentView.current, zoom: Math.max(currentView.current.zoom - 1, MIN_ZOOM) })}><Minus /></Button>
      <Button variant="ghost" size="icon-sm" aria-label="Return to world view" title="Return to world view" onClick={resetToWorld}><Crosshair /></Button>
    </div>
    {!!overlap.length && <div className="absolute bottom-8 left-3 w-[min(22rem,calc(100%-1.5rem))] rounded-lg border bg-background p-3 shadow-lg"><div className="mb-2 flex items-center justify-between"><p className="text-sm font-medium">Choose an institution</p><Button variant="ghost" size="icon-xs" aria-label="Close chooser" onClick={() => setOverlap([])}><X /></Button></div><div className="max-h-48 space-y-1 overflow-y-auto">{overlap.map(institution => <button key={institution.id} type="button" onClick={() => { onSelect(institution); setOverlap([]) }} className="block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="font-medium">{institution.name}</span><span className="block text-xs text-muted-foreground">{institution.country}</span></button>)}</div></div>}
  </div>
}

export default memo(DeckMap)
