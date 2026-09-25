import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { ClientOnly, Link, useLocation, useNavigate, useSearch } from '@tanstack/react-router'
import { Columns3, ExternalLink, Keyboard, List, Loader2, Map as MapIcon, SlidersHorizontal, Star } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '~/components/ui/dialog'
import { FilterBar } from '~/components/filter-bar'
import { InstitutionTable, InstitutionTableSkeleton } from '~/components/institution-table'
import { InstitutionPopup } from '~/components/institution-popup'
import { ShortlistComparison } from '~/components/shortlist-comparison'
import { EMPTY_FILTERS, PORTAL_URL, selectInstitutions, validateFilters, type Filters } from '~/lib/exchange'
import { useFavorites } from '~/lib/collections'
import type { ExplorerIndex, InstitutionSummary } from '~/lib/types'
import { cn } from '~/lib/utils'

const loadDeckMap = () => import('~/components/deck-map')
const DeckMap = lazy(loadDeckMap)
const warmDeckMap = () => { void loadDeckMap().then(module => module.preloadBasemapStyle()).catch(() => undefined) }
const CONTINENTS = ['Africa', 'Asia', 'Australia/Oceania', 'Europe', 'North America', 'South America']

export function DashboardShell({ index }: { index: ExplorerIndex }) {
  const view = useLocation({ select: location => location.pathname === '/map' ? 'map' as const : 'table' as const })
  const rawSearch = useSearch({ strict: false })
  const filters = useMemo(() => validateFilters(rawSearch), [rawSearch])
  const navigate = useNavigate()
  const [detailDismissed, setDetailDismissed] = useState(false)
  const [selectionOverride, setSelectionOverride] = useState<InstitutionSummary | null | undefined>(undefined)
  const [helpOpen, setHelpOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [mapInitialized, setMapInitialized] = useState(view === 'map')
  const { favorites, favoritesOnly, setFavoritesOnly, toggle: toggleFavorite, has: isFavorite } = useFavorites()
  const result = useMemo(() => selectInstitutions(index, filters), [index, filters])
  const visible = useMemo(() => favoritesOnly ? result.institutions.filter(institution => favorites.includes(institution.id)) : result.institutions, [result, favoritesOnly, favorites])
  const routeSelected = result.institutions.find(institution => institution.id === filters.selected) ?? null
  const selected = selectionOverride === undefined ? routeSelected : selectionOverride
  const countries = useMemo(() => [...new Set(index.institutions.filter(institution => !filters.continent || institution.continent === filters.continent).map(institution => institution.country))].sort(), [index.institutions, filters.continent])
  const maxPlaces = useMemo(() => Math.max(0, ...(index.agreementPlaces ?? [])), [index.agreementPlaces])
  const mapped = visible.filter(institution => institution.lat != null && institution.lon != null).length
  const pageCount = Math.max(1, Math.ceil(visible.length / 25))
  const hasResults = result.status !== 'unavailable' && visible.length > 0

  const changeFilters = useCallback((next: Filters, replace = true) => {
    void navigate({ to: view === 'map' ? '/map' : '/', search: next, replace })
  }, [navigate, view])
  const showTable = useCallback(() => {
    void navigate({ to: '/', search: filters })
  }, [navigate, filters])
  const showMap = useCallback(() => {
    void navigate({ to: '/map', search: filters })
  }, [navigate, filters])
  const select = useCallback((institution: InstitutionSummary) => {
    flushSync(() => {
      setDetailDismissed(false)
      setSelectionOverride(institution)
    })
    changeFilters({ ...filters, selected: institution.id }, false)
  }, [changeFilters, filters])
  useEffect(() => {
    if (selectionOverride === undefined) return
    if (filters.selected === (selectionOverride?.id ?? '')) setSelectionOverride(undefined)
  }, [filters.selected, selectionOverride])
  useEffect(() => {
    if (filters.selected && !routeSelected) changeFilters({ ...filters, selected: '' })
    else if (filters.page > pageCount) changeFilters({ ...filters, page: pageCount })
  }, [filters, routeSelected, pageCount, changeFilters])
  useEffect(() => {
    if (mapInitialized) return
    if (view === 'map') {
      setMapInitialized(true)
      return
    }

    // Let the table paint before starting WebGL, tile requests, and the map bundle.
    let cancelled = false
    let idleId: number | undefined
    let timeoutId: number | undefined
    const frameId = window.requestAnimationFrame(() => {
      const initialize = () => { if (!cancelled) setMapInitialized(true) }
      if (typeof window.requestIdleCallback === 'function') idleId = window.requestIdleCallback(initialize, { timeout: 2000 })
      else timeoutId = window.setTimeout(initialize, 0)
    })
    return () => {
      cancelled = true
      window.cancelAnimationFrame(frameId)
      if (idleId !== undefined) window.cancelIdleCallback(idleId)
      if (timeoutId !== undefined) window.clearTimeout(timeoutId)
    }
  }, [mapInitialized, view])

  useEffect(() => {
    const isTypingTarget = (target: EventTarget | null) => {
      const element = target as HTMLElement | null
      if (!element || typeof element.tagName !== 'string') return false
      const tag = element.tagName
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || element.isContentEditable
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (isTypingTarget(event.target)) {
        if (event.key === 'Escape') (event.target as HTMLElement).blur()
        return
      }
      if (event.key === '?') {
        event.preventDefault()
        setHelpOpen(true)
      } else if (event.key === '/') {
        event.preventDefault()
        document.getElementById('institution-search')?.focus()
      } else if (event.key === 't' || event.key === 'T') {
        if (view !== 'table') showTable()
      } else if (event.key === 'm' || event.key === 'M') {
        if (view !== 'map') showMap()
      } else if (event.key === 'ArrowLeft' && view === 'table' && filters.page > 1) {
        event.preventDefault()
        changeFilters({ ...filters, page: filters.page - 1 })
      } else if (event.key === 'ArrowRight' && view === 'table' && filters.page < pageCount) {
        event.preventDefault()
        changeFilters({ ...filters, page: filters.page + 1 })
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [view, filters, pageCount, changeFilters, showTable, showMap])

  const selectedAgreementIds = selected?.matchingAgreementIds.map(id => index.agreementIds[id]).filter(Boolean) ?? []
  return <div className="min-h-screen bg-[#f7f8fa]">
    <header className="border-b bg-background">
      <div className="mx-auto flex max-w-[90rem] items-center justify-between gap-5 px-4 py-4 sm:px-6 lg:px-8">
        <Link to="/" search={EMPTY_FILTERS} className="text-lg font-semibold tracking-tight text-[#18212b]">KU Abroad</Link>
        <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary">Official KU portal<ExternalLink className="size-3.5" /></a>
      </div>
    </header>
    <main className="mx-auto max-w-[90rem] space-y-5 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <h1 className="text-2xl font-semibold tracking-tight text-[#18212b] sm:text-3xl">Explore partner universities</h1>
        <nav aria-label="Result view" className="grid grid-cols-2 rounded-lg border bg-card p-1 shadow-xs">
          <Link to="/" search={filters} className={cn('inline-flex h-8 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium', view === 'table' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground')}><List className="size-4" />Table</Link>
          <Link to="/map" search={filters} onPointerEnter={warmDeckMap} onFocus={warmDeckMap} className={cn('inline-flex h-8 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium', view === 'map' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground')}><MapIcon className="size-4" />Map</Link>
        </nav>
      </div>
      <FilterBar filters={filters} onChange={changeFilters} countries={countries} continents={CONTINENTS} academicYears={index.academicYears} studyFields={index.studyFields} programs={index.programs ?? []} studyLevels={index.studyLevels ?? []} maxPlaces={maxPlaces} yearAttention={result.status === 'overview'} />
      <div className="flex flex-wrap items-center justify-between gap-2 border-y py-3 text-sm">
        <p><span className="font-semibold tabular-nums text-foreground">{visible.length}</span> destination{visible.length === 1 ? '' : 's'}{favoritesOnly && <span className="text-muted-foreground"> · favorites only</span>}{view === 'map' && <span className="text-muted-foreground"> · {mapped} mapped</span>}</p>
        <div className="flex items-center gap-1.5">
          <button type="button" aria-pressed={favoritesOnly} title={favoritesOnly ? 'Show all destinations' : 'Show favorites only'} onClick={() => setFavoritesOnly(!favoritesOnly)} className={cn('inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium', favoritesOnly ? 'border-amber-300 bg-amber-50 text-amber-900' : 'bg-card text-muted-foreground hover:text-foreground')}>
            <Star className={cn('size-3.5', favoritesOnly ? 'fill-amber-400 text-amber-400' : favorites.length > 0 && 'fill-amber-200 text-amber-500')} />Favorites{favorites.length > 0 && <span className="tabular-nums">({favorites.length})</span>}
          </button>
          <button type="button" onClick={() => { const currentIds = new Set(index.institutions.map(institution => institution.id)); setCompareIds(favorites.filter(id => currentIds.has(id)).slice(0, 3)); setCompareOpen(true) }} className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"><Columns3 className="size-3.5" />Compare</button>
          <button type="button" aria-label="Keyboard shortcuts" title="Keyboard shortcuts (?)" onClick={() => setHelpOpen(true)} className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"><Keyboard className="size-3.5" /><span className="hidden sm:inline">Shortcuts</span></button>
        </div>
      </div>
      <div className="relative">
        {result.status === 'unavailable' ? <EmptyState title="Data unavailable" description="Try another academic year or study field, or check the official KU portal." />
          : favoritesOnly && favorites.length === 0 ? <EmptyState title="No favorites yet" description="Tap the star next to any institution to pin it here for later comparison." actionLabel="Show all destinations" onClear={() => setFavoritesOnly(false)} />
          : visible.length === 0 ? <EmptyState title="No destinations match" description="Remove one or more filters to broaden your search." onClear={() => changeFilters(EMPTY_FILTERS)} />
          : view === 'table' ? <InstitutionTable institutions={visible} filters={filters} onChange={changeFilters} onSelect={select} favorites={favorites} onToggleFavorite={toggleFavorite} />
          : null}
        <MapExperience initialized={mapInitialized} active={view === 'map' && hasResults} institutions={visible} routeSelected={routeSelected} index={index} initiallyDismissed={detailDismissed} isFavorite={isFavorite} onToggleFavorite={toggleFavorite} onSelectStart={() => setDetailDismissed(false)} onSelectUrl={institution => changeFilters({ ...filters, selected: institution.id }, false)} onClearUrl={() => changeFilters({ ...filters, selected: '' })} onShowTable={showTable} />
      </div>
    </main>
    <footer className="border-t bg-background">
      <div className="mx-auto flex max-w-[90rem] flex-col items-center justify-between gap-3 px-4 py-4 text-xs text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
        <p>Made by Karl August Krogh Nybo</p>
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
          <a href="https://github.com/karlaugustnybo/KU-Abroad" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-foreground">
            <ExternalLink className="size-3" />GitHub repo
          </a>
          <a href="https://github.com/karlaugustnybo/KU-Abroad/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-foreground">
            <ExternalLink className="size-3" />CC0 1.0 License
          </a>
        </div>
      </div>
    </footer>
    {view === 'table' ? <InstitutionPopup institution={selected} agreementIds={selectedAgreementIds} open={selected !== null && !detailDismissed} isFavorite={selected ? isFavorite(selected.id) : false} onToggleFavorite={selected ? () => toggleFavorite(selected.id) : undefined} onOpenChange={open => { if (!open) { flushSync(() => setSelectionOverride(null)); changeFilters({ ...filters, selected: '' }) } }} onShowMap={() => { setDetailDismissed(true); void navigate({ to: '/map', search: filters }) }} /> : null}
    <ShortlistComparison open={compareOpen} onOpenChange={setCompareOpen} index={index} favorites={favorites} selectedIds={compareIds} onSelectedIdsChange={setCompareIds} onRemoveFavorite={toggleFavorite} academicYear={filters.academicYear} studyField={filters.studyField} />
    <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
      <DialogContent>
        <DialogHeader><DialogTitle>Keyboard shortcuts</DialogTitle><DialogDescription>Navigate KU Abroad without touching the mouse.</DialogDescription></DialogHeader>
        <ul className="space-y-2 text-sm">
          {[['/', 'Focus the search field'], ['t', 'Switch to table view'], ['m', 'Switch to map view'], ['← / →', 'Previous / next table page'], ['?', 'Open this help']].map(([keys, label]) => <li key={keys} className="flex items-center justify-between gap-4"><span className="text-muted-foreground">{label}</span><kbd className="rounded-md border bg-muted px-2 py-0.5 font-mono text-xs">{keys}</kbd></li>)}
        </ul>
      </DialogContent>
    </Dialog>
  </div>
}

interface MapExperienceProps {
  initialized: boolean
  active: boolean
  institutions: InstitutionSummary[]
  routeSelected: InstitutionSummary | null
  index: ExplorerIndex
  initiallyDismissed: boolean
  isFavorite: (id: string) => boolean
  onToggleFavorite: (id: string) => void
  onSelectStart: () => void
  onSelectUrl: (institution: InstitutionSummary) => void
  onClearUrl: () => void
  onShowTable: () => void
}

function MapExperience({ initialized, active, institutions, routeSelected, index, initiallyDismissed, isFavorite, onToggleFavorite, onSelectStart, onSelectUrl, onClearUrl, onShowTable }: MapExperienceProps) {
  const [selectionOverride, setSelectionOverride] = useState<InstitutionSummary | null | undefined>(undefined)
  const [dismissed, setDismissed] = useState(initiallyDismissed)
  const selectionSerial = useRef(0)
  const selected = selectionOverride === undefined ? routeSelected : selectionOverride
  const agreementIds = selected?.matchingAgreementIds.map(id => index.agreementIds[id]).filter(Boolean) ?? []

  const select = useCallback((institution: InstitutionSummary, clickStartedAt: number) => {
    const serial = ++selectionSerial.current
    const handlerStartedAt = performance.now()
    flushSync(() => {
      onSelectStart()
      setDismissed(false)
      setSelectionOverride(institution)
    })
    const committedAt = performance.now()
    window.requestAnimationFrame(() => {
      const firstFrameAt = performance.now()
      window.requestAnimationFrame(() => {
        if (import.meta.env.DEV) console.debug(`[map-popup] ${JSON.stringify({
          dispatchMs: +(handlerStartedAt - clickStartedAt).toFixed(1),
          commitMs: +(committedAt - handlerStartedAt).toFixed(1),
          firstFrameMs: +(firstFrameAt - clickStartedAt).toFixed(1),
          nextFrameMs: +(performance.now() - clickStartedAt).toFixed(1),
        })}`)
        window.setTimeout(() => {
          if (selectionSerial.current === serial) onSelectUrl(institution)
        }, 0)
      })
    })
  }, [onSelectStart, onSelectUrl])

  useEffect(() => () => { selectionSerial.current++ }, [])

  useEffect(() => {
    if (selectionOverride === undefined) return
    if ((selectionOverride?.id ?? '') === (routeSelected?.id ?? '')) setSelectionOverride(undefined)
  }, [routeSelected?.id, selectionOverride])

  return <>
    <div aria-hidden={!active} inert={!active} className={cn('map-frame relative h-[calc(100vh-22rem)] min-h-[28rem] overflow-hidden bg-card p-px shadow-xs', !active && 'pointer-events-none absolute left-[-10000px] top-0 w-full opacity-0')}>
      {initialized && <ClientOnly fallback={<MapLoading />}><Suspense fallback={<MapLoading />}><DeckMap active={active} focusSelected={active && initiallyDismissed} institutions={institutions} selected={routeSelected} onSelect={select} onShowTable={onShowTable} /></Suspense></ClientOnly>}
    </div>
    <InstitutionPopup institution={selected} agreementIds={agreementIds} open={active && selected !== null && !dismissed && !initiallyDismissed} isFavorite={selected ? isFavorite(selected.id) : false} onToggleFavorite={selected ? () => onToggleFavorite(selected.id) : undefined} onOpenChange={open => { if (!open) { selectionSerial.current++; flushSync(() => setSelectionOverride(null)); onClearUrl() } }} onShowMap={() => setDismissed(true)} />
  </>
}

function MapLoading() { return <div className="flex h-full items-center justify-center text-sm text-muted-foreground"><Loader2 className="mr-2 size-4 animate-spin" />Loading map…</div> }

function EmptyState({ title, description, actionLabel = 'Clear filters', onClear }: { title: string; description: string; actionLabel?: string; onClear?: () => void }) {
  return <div className="rounded-lg border border-dashed bg-card px-6 py-14 text-center"><SlidersHorizontal className="mx-auto size-6 text-muted-foreground" /><h2 className="mt-3 font-medium">{title}</h2><p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>{onClear && <Button variant="outline" className="mt-4" onClick={onClear}>{actionLabel}</Button>}</div>
}

export function DashboardPending() {
  return <div className="min-h-screen bg-[#f7f8fa]">
    <header className="border-b bg-background">
      <div className="mx-auto flex max-w-[90rem] items-center justify-between gap-5 px-4 py-4 sm:px-6 lg:px-8">
        <span className="text-lg font-semibold tracking-tight text-[#18212b]">KU Abroad</span>
      </div>
    </header>
    <main className="mx-auto max-w-[90rem] space-y-5 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="h-9 w-72 animate-pulse rounded-lg bg-muted" />
      <div className="h-10 animate-pulse rounded-lg bg-muted" />
      <InstitutionTableSkeleton rows={3} />
    </main>
  </div>
}
