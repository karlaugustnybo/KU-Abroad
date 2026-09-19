import { useEffect, useState } from 'react'
import { Bookmark, Check, ChevronsUpDown, Filter, Search, X } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { Checkbox } from '~/components/ui/checkbox'
import { Input } from '~/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '~/components/ui/popover'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '~/components/ui/sheet'
import { Slider } from '~/components/ui/slider'
import { formatGrade } from '~/lib/grade'
import { activeFilterCount, EMPTY_FILTERS, type Filters } from '~/lib/exchange'
import { useSavedSearches } from '~/lib/collections'
import { cn } from '~/lib/utils'

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
  countries: string[]
  continents: string[]
  academicYears: string[]
  studyFields: string[]
  programs: string[]
  studyLevels: ('bachelor' | 'master' | 'doctoral')[]
  maxPlaces: number
  yearAttention?: boolean
}

interface OptionPickerProps {
  id: string
  label: string
  value: string
  allLabel: string
  options: { value: string; label: string }[]
  onValueChange: (value: string) => void
  searchable?: boolean
  disabled?: boolean
  attention?: boolean
}

function OptionPicker({ id, label, value, allLabel, options, onValueChange, searchable = false, disabled = false, attention = false }: OptionPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const matches = options.filter(option => option.label.toLowerCase().includes(query.toLowerCase()))
  const selectedLabel = options.find(option => option.value === value)?.label
  const flagged = attention && !value
  return <div className="space-y-1.5">
    <label className="text-xs font-medium text-foreground" id={`${id}-label`}>{label}</label>
    <Popover open={open} onOpenChange={value => { setOpen(value); if (value) setQuery('') }}>
      <PopoverTrigger asChild>
        <Button variant="outline" aria-labelledby={`${id}-label`} aria-expanded={open} disabled={disabled} className="h-10 w-full justify-between px-3 font-normal">
          <span className={cn('truncate', !value && (flagged ? 'font-medium text-primary' : 'text-muted-foreground'))}>{selectedLabel || allLabel}</span><ChevronsUpDown className="text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] min-w-0 p-2" align="start">
        {searchable && <Input autoFocus aria-label={`Search ${label.toLowerCase()}`} placeholder={`Search ${label.toLowerCase()}…`} value={query} onChange={event => setQuery(event.target.value)} />}
        <div className={cn('max-h-64 overflow-y-auto', searchable && 'mt-2')}>
          {[{ value: '', label: allLabel }, ...matches].map(option =>
            <button key={option.value} type="button" className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => { onValueChange(option.value); setOpen(false) }}>
              <Check className={cn('size-4 shrink-0 text-primary', value !== option.value && 'opacity-0')} /><span className="min-w-0 truncate">{option.label}</span>
            </button>)}
          {!matches.length && query && <p className="p-4 text-center text-sm text-muted-foreground">No matching options</p>}
        </div>
      </PopoverContent>
    </Popover>
  </div>
}

function GradeFilter({ filters, onChange }: Pick<FilterBarProps, 'filters' | 'onChange'>) {
  const value = filters.maxGrade ? Number(filters.maxGrade) : 0
  return <div className="space-y-1.5">
    <label className="text-xs font-medium" id="grade-requirement-label">Grade requirement (Danish scale)</label>
    <div className="flex h-10 items-center gap-3 rounded-md border bg-transparent px-3">
      <Slider value={[value]} min={0} max={12} step={0.5} aria-labelledby="grade-requirement-label" onValueChange={values => onChange({ ...filters, maxGrade: values[0] > 0 ? String(values[0]) : '', page: 1, selected: '' })} />
      <span className="w-14 shrink-0 text-right text-sm tabular-nums text-muted-foreground">{value > 0 ? `≤ ${formatGrade(value)}` : 'Any'}</span>
    </div>
    <label className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
      <Checkbox checked={filters.gradeUnknown !== 'exclude'} onCheckedChange={checked => onChange({ ...filters, gradeUnknown: checked ? '' : 'exclude', page: 1, selected: '' })} />
      Include unclear grade requirements
    </label>
  </div>
}

function PlacesFilter({ filters, maxPlaces, onChange }: Pick<FilterBarProps, 'filters' | 'maxPlaces' | 'onChange'>) {
  const value = Math.min(Number(filters.minPlaces) || 0, maxPlaces)
  return <div className="space-y-1.5">
    <label className="text-xs font-medium" id="available-places-label">Available places</label>
    <div className="flex h-10 items-center gap-3 rounded-md border bg-transparent px-3">
      <Slider value={[value]} min={0} max={maxPlaces} step={1} disabled={maxPlaces < 1} aria-labelledby="available-places-label" onValueChange={values => onChange({ ...filters, minPlaces: values[0] > 0 ? String(values[0]) : '', page: 1, selected: '' })} />
      <span className="w-16 shrink-0 text-right text-sm tabular-nums text-muted-foreground">{value > 0 ? `≥ ${value}` : 'Any'}</span>
    </div>
  </div>
}

function FeatureToggle({ label, checked, onCheckedChange }: { label: string; checked: boolean; onCheckedChange: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 text-xs text-muted-foreground">
    <Checkbox checked={checked} onCheckedChange={value => onCheckedChange(value === true)} />{label}
  </label>
}

function FilterControls({ filters, onChange, countries, continents, academicYears, studyFields, programs, studyLevels, maxPlaces, yearAttention = false }: FilterBarProps) {
  const update = (change: Partial<Filters>) => onChange({ ...filters, ...change, page: 1, selected: '' })
  const levelLabels = { bachelor: "Bachelor's", master: "Master's / postgraduate", doctoral: 'PhD / doctoral' }
  return <div className="space-y-4">
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <OptionPicker id="academic-year" label="Academic year" value={filters.academicYear} allLabel={yearAttention && !filters.academicYear ? 'Pick an academic year' : 'General overview'} options={academicYears.map(value => ({ value, label: value }))} attention={yearAttention} onValueChange={academicYear => onChange({ ...filters, academicYear, studyField: '', page: 1, selected: '' })} />
      <OptionPicker id="study-field" label="Study field" value={filters.studyField} allLabel="All study fields" options={studyFields.map(value => ({ value, label: value }))} searchable disabled={!filters.academicYear} onValueChange={studyField => update({ studyField })} />
      <OptionPicker id="continent" label="Continent" value={filters.continent} allLabel="All continents" options={continents.map(value => ({ value, label: value }))} onValueChange={continent => update({ continent, country: '' })} />
      <OptionPicker id="country" label="Country" value={filters.country} allLabel="All countries" options={countries.map(value => ({ value, label: value }))} searchable onValueChange={country => update({ country })} />
    </div>
    <div className="border-t pt-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <OptionPicker id="exchange-programme" label="Exchange programme" value={filters.program} allLabel="All programmes" options={programs.map(value => ({ value, label: value }))} onValueChange={program => update({ program })} />
        <OptionPicker id="study-level" label="Study level" value={filters.studyLevel} allLabel="All study levels" options={studyLevels.map(value => ({ value, label: levelLabels[value] }))} onValueChange={studyLevel => update({ studyLevel })} />
        <PlacesFilter filters={filters} maxPlaces={maxPlaces} onChange={onChange} />
        <GradeFilter filters={filters} onChange={onChange} />
      </div>
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-3 border-t pt-4">
        <span className="w-full text-xs font-medium text-foreground sm:w-auto">Information provided</span>
        <FeatureToggle label="Language requirements" checked={filters.languageInfo === 'yes'} onCheckedChange={checked => update({ languageInfo: checked ? 'yes' : '' })} />
        <FeatureToggle label="Housing" checked={filters.housingInfo === 'yes'} onCheckedChange={checked => update({ housingInfo: checked ? 'yes' : '' })} />
        <FeatureToggle label="Scholarships" checked={filters.scholarshipInfo === 'yes'} onCheckedChange={checked => update({ scholarshipInfo: checked ? 'yes' : '' })} />
      </div>
    </div>
  </div>
}

function SavedSearches({ filters, onChange }: Pick<FilterBarProps, 'filters' | 'onChange'>) {
  const { searches, save, remove } = useSavedSearches()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  return <Popover open={open} onOpenChange={value => { setOpen(value); if (value) setName('') }}>
    <PopoverTrigger asChild>
      <Button variant="outline" className="h-10 gap-2" aria-label="Saved searches" title="Saved searches">
        <Bookmark className="size-4" /><span className="hidden sm:inline">Saved</span>{searches.length > 0 && <span className="rounded-full bg-primary px-1.5 text-xs text-primary-foreground">{searches.length}</span>}
      </Button>
    </PopoverTrigger>
    <PopoverContent className="w-80 p-3" align="end">
      <p className="text-xs font-medium">Save this search</p>
      <div className="mt-2 flex gap-2">
        <Input aria-label="Name for saved search" placeholder="e.g. Biology in Japan" value={name} onChange={event => setName(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && name.trim()) { save(name, filters); setName('') } }} />
        <Button disabled={!name.trim()} onClick={() => { save(name, filters); setName('') }}>Save</Button>
      </div>
      {searches.length > 0 ? <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto">
        {searches.map(search => <li key={search.id} className="group flex items-center gap-1 rounded-md hover:bg-muted">
          <button type="button" className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm" title={`Apply “${search.name}”`} onClick={() => { onChange({ ...search.filters, page: 1, selected: '' }); setOpen(false) }}>
            <span className="block truncate font-medium">{search.name}</span>
            <span className="block truncate text-xs text-muted-foreground">{[search.filters.academicYear, search.filters.studyField, search.filters.country || search.filters.continent, search.filters.query].filter(Boolean).join(' · ') || 'All destinations'}</span>
          </button>
          <button type="button" aria-label={`Delete saved search “${search.name}”`} onClick={() => remove(search.id)} className="rounded p-1.5 text-muted-foreground opacity-0 hover:text-destructive focus-visible:opacity-100 focus-visible:outline-none group-hover:opacity-100"><X className="size-3.5" /></button>
        </li>)}
      </ul> : <p className="mt-3 text-xs text-muted-foreground">No saved searches yet. Name the current filter combination to reuse it later.</p>}
    </PopoverContent>
  </Popover>
}

export function FilterBar(props: FilterBarProps) {
  const { filters, onChange } = props
  const [search, setSearch] = useState(filters.query)
  useEffect(() => setSearch(filters.query), [filters.query])
  useEffect(() => {
    if (search === filters.query) return
    const timeout = window.setTimeout(() => onChange({ ...filters, query: search, page: 1, selected: '' }), 150)
    return () => window.clearTimeout(timeout)
  }, [search, filters, onChange])
  const count = activeFilterCount(filters)
  const chips = [
    ['academicYear', filters.academicYear], ['studyField', filters.studyField], ['continent', filters.continent], ['country', filters.country],
    ['program', filters.program], ['studyLevel', filters.studyLevel ? ({ bachelor: "Bachelor's", master: "Master's / postgraduate", doctoral: 'PhD / doctoral' }[filters.studyLevel]) : ''],
    ['minPlaces', filters.minPlaces ? `At least ${filters.minPlaces} places` : ''],
    ['languageInfo', filters.languageInfo ? 'Language requirements provided' : ''],
    ['housingInfo', filters.housingInfo ? 'Housing information provided' : ''],
    ['scholarshipInfo', filters.scholarshipInfo ? 'Scholarship information provided' : ''],
    ['maxGrade', filters.maxGrade ? `Requires ≤ ${formatGrade(Number(filters.maxGrade))}` : ''],
    ['gradeUnknown', filters.gradeUnknown === 'exclude' ? 'Unclear grade requirements excluded' : ''],
  ] as const
  const clear = () => onChange({ ...EMPTY_FILTERS, query: filters.query })
  return <div className="space-y-3">
    <div className="flex gap-2">
      <div className="relative flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><Input id="institution-search" aria-label="Search institutions" placeholder="Search institution, city or country (press /)" value={search} onChange={event => setSearch(event.target.value)} className="h-10 bg-card pl-9" /></div>
      <SavedSearches filters={filters} onChange={onChange} />
      <Sheet><SheetTrigger asChild><Button variant="outline" className="h-10 gap-2 md:hidden"><Filter />Filters{count > 0 && <span className="rounded-full bg-primary px-1.5 text-xs text-primary-foreground">{count}</span>}</Button></SheetTrigger>
        <SheetContent side="bottom"><SheetHeader><SheetTitle>Filter destinations</SheetTitle><SheetDescription className="sr-only">Filter exchange destinations</SheetDescription></SheetHeader><div className="min-h-0 flex-1 overflow-y-auto p-5"><FilterControls {...props} /><Button variant="outline" className="mt-5 w-full" onClick={clear}>Clear filters</Button></div></SheetContent>
      </Sheet>
    </div>
    <div className="hidden rounded-lg border bg-card p-4 md:block"><FilterControls {...props} /></div>
    {chips.some(([, value]) => value) && <div className="flex flex-wrap items-center gap-2" aria-label="Active filters">
      {chips.filter(([, value]) => value).map(([key, value]) => <button key={key} type="button" className="inline-flex items-center gap-1 rounded-full border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground" onClick={() => onChange({ ...filters, [key]: '', ...(key === 'academicYear' ? { studyField: '' } : {}), page: 1, selected: '' })}>{value}<X className="size-3" /></button>)}
      <button type="button" className="text-xs font-medium text-primary hover:underline" onClick={clear}>Clear filters</button>
    </div>}
  </div>
}
