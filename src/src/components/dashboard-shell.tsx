import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { flushSync } from 'react-dom'
import { ClientOnly, Link, useNavigate, useSearch } from '@tanstack/react-router'
import { ExternalLink, List, Loader2, Map as MapIcon, SlidersHorizontal } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { FilterBar } from '~/components/filter-bar'
import { InstitutionTable } from '~/components/institution-table'
import { InstitutionPopup } from '~/components/institution-popup'
import { EMPTY_FILTERS, PORTAL_URL, selectInstitutions, validateFilters, type Filters } from '~/lib/exchange'
import type { ExplorerIndex, InstitutionSummary } from '~/lib/types'
import { cn } from '~/lib/utils'

const loadDeckMap = () => import('~/components/deck-map')
const DeckMap = lazy(loadDeckMap)
const CONTINENTS = ['Africa', 'Asia', 'Australia/Oceania', 'Europe', 'North America', 'South America']

export function DashboardShell({ index, view }: { index: ExplorerIndex; view: 'table' | 'map' }) {
  const rawSearch = useSearch({ strict: false })
  const filters = useMemo(() => validateFilters(rawSearch), [rawSearch])
  const navigate = useNavigate()
  const [detailDismissed, setDetailDismissed] = useState(false)
  const [selectionOverride, setSelectionOverride] = useState<InstitutionSummary | null | undefined>(undefined)
  const result = useMemo(() => selectInstitutions(index, filters), [index, filters])
  const routeSelected = result.institutions.find(institution => institution.id === filters.selected) ?? null
  const selected = selectionOverride === undefined ? routeSelected : selectionOverride
  const countries = useMemo(() => [...new Set(index.institutions.filter(institution => !filters.continent || institution.continent === filters.continent).map(institution => institution.country))].sort(), [index.institutions, filters.continent])
  const maxPlaces = useMemo(() => Math.max(0, ...(index.agreementPlaces ?? [])), [index.agreementPlaces])
  const mapped = result.institutions.filter(institution => institution.lat != null && institution.lon != null).length
  const pageCount = Math.max(1, Math.ceil(result.institutions.length / 25))

  const changeFilters = useCallback((next: Filters, replace = true) => {
    void navigate({ to: view === 'map' ? '/map' : '/', search: next, replace })
  }, [navigate, view])
  const showTable = useCallback(() => {
    void navigate({ to: '/', search: filters })
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
    if (view !== 'table') return

    let idleId: number | undefined
    let fallbackId: number | undefined
    let cancelled = false
    const preload = () => {
      if (cancelled) return
      const warmMapBundle = () => {
        void loadDeckMap()
          .then(module => module.preloadBasemapStyle())
          .catch(() => undefined)
      }
      const requestIdle = window.requestIdleCallback
      if (requestIdle) {
        idleId = requestIdle(warmMapBundle, { timeout: 3_000 })
      } else {
        fallbackId = window.setTimeout(warmMapBundle, 250)
      }
    }

    if (document.readyState === 'complete') preload()
    else window.addEventListener('load', preload, { once: true })

    return () => {
      cancelled = true
      window.removeEventListener('load', preload)
      if (idleId !== undefined) window.cancelIdleCallback(idleId)
      if (fallbackId !== undefined) window.clearTimeout(fallbackId)
    }
  }, [view])

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
          <Link to="/map" search={filters} className={cn('inline-flex h-8 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium', view === 'map' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground')}><MapIcon className="size-4" />Map</Link>
        </nav>
      </div>
      <FilterBar filters={filters} onChange={changeFilters} countries={countries} continents={CONTINENTS} academicYears={index.academicYears} studyFields={index.studyFields} programs={index.programs ?? []} studyLevels={index.studyLevels ?? []} maxPlaces={maxPlaces} />
      <div className="border-y py-3 text-sm">
        <p><span className="font-semibold tabular-nums text-foreground">{result.institutions.length}</span> destination{result.institutions.length === 1 ? '' : 's'}{view === 'map' && <span className="text-muted-foreground"> · {mapped} mapped</span>}</p>
      </div>
      {result.status === 'unavailable' ? <EmptyState title="Data unavailable" description="Try another academic year or study field, or check the official KU portal." />
        : result.institutions.length === 0 ? <EmptyState title="No destinations match" description="Remove one or more filters to broaden your search." onClear={() => changeFilters(EMPTY_FILTERS)} />
        : view === 'table' ? <InstitutionTable institutions={result.institutions} filters={filters} onChange={changeFilters} onSelect={select} />
        : <MapExperience institutions={result.institutions} routeSelected={routeSelected} index={index} initiallyDismissed={detailDismissed} onSelectUrl={institution => changeFilters({ ...filters, selected: institution.id }, false)} onClearUrl={() => changeFilters({ ...filters, selected: '' })} onShowTable={showTable} />}
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
    {view === 'table' ? <InstitutionPopup institution={selected} agreementIds={selectedAgreementIds} open={selected !== null && !detailDismissed} onOpenChange={open => { if (!open) { flushSync(() => setSelectionOverride(null)); changeFilters({ ...filters, selected: '' }) } }} onShowMap={() => { setDetailDismissed(true); void navigate({ to: '/map', search: filters }) }} /> : null}
  </div>
}

interface MapExperienceProps {
  institutions: InstitutionSummary[]
  routeSelected: InstitutionSummary | null
  index: ExplorerIndex
  initiallyDismissed: boolean
  onSelectUrl: (institution: InstitutionSummary) => void
  onClearUrl: () => void
  onShowTable: () => void
}

function MapExperience({ institutions, routeSelected, index, initiallyDismissed, onSelectUrl, onClearUrl, onShowTable }: MapExperienceProps) {
  const [selectionOverride, setSelectionOverride] = useState<InstitutionSummary | null | undefined>(undefined)
  const [dismissed, setDismissed] = useState(initiallyDismissed)
  const selected = selectionOverride === undefined ? routeSelected : selectionOverride
  const agreementIds = selected?.matchingAgreementIds.map(id => index.agreementIds[id]).filter(Boolean) ?? []

  const select = useCallback((institution: InstitutionSummary) => {
    const selectionStartedAt = performance.now()
    flushSync(() => {
      setDismissed(false)
      setSelectionOverride(institution)
    })
    window.requestAnimationFrame(() => {
      if (import.meta.env.DEV) console.debug(`[map-popup] ready for paint in ${(performance.now() - selectionStartedAt).toFixed(1)}ms`)
      window.setTimeout(() => onSelectUrl(institution), 0)
    })
  }, [onSelectUrl])

  useEffect(() => {
    if (selectionOverride === undefined) return
    if ((selectionOverride?.id ?? '') === (routeSelected?.id ?? '')) setSelectionOverride(undefined)
  }, [routeSelected?.id, selectionOverride])

  return <>
    <div className="h-[calc(100vh-22rem)] min-h-[28rem] overflow-hidden rounded-xl border bg-card shadow-xs">
      <ClientOnly fallback={<MapLoading />}><Suspense fallback={<MapLoading />}><DeckMap institutions={institutions} selected={routeSelected} onSelect={select} onShowTable={onShowTable} /></Suspense></ClientOnly>
    </div>
    <InstitutionPopup institution={selected} agreementIds={agreementIds} open={selected !== null && !dismissed} onOpenChange={open => { if (!open) { flushSync(() => setSelectionOverride(null)); onClearUrl() } }} onShowMap={() => setDismissed(true)} />
  </>
}

function MapLoading() { return <div className="flex h-full items-center justify-center text-sm text-muted-foreground"><Loader2 className="mr-2 size-4 animate-spin" />Loading map…</div> }

function EmptyState({ title, description, onClear }: { title: string; description: string; onClear?: () => void }) {
  return <div className="rounded-lg border border-dashed bg-card px-6 py-14 text-center"><SlidersHorizontal className="mx-auto size-6 text-muted-foreground" /><h2 className="mt-3 font-medium">{title}</h2><p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>{onClear && <Button variant="outline" className="mt-4" onClick={onClear}>Clear filters</Button>}</div>
}
