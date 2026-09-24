import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Check, ExternalLink, Loader2, Star } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '~/components/ui/dialog'
import { aggregateGradeRequirement, formatGrade } from '~/lib/grade'
import { PORTAL_URL } from '~/lib/exchange'
import type { AgreementRow, ExplorerIndex, InstitutionDetails } from '~/lib/types'
import { loadInstitutionDetails } from '~/utils/dataset'

const MAX_COMPARE = 4
const LANGUAGE_FIELDS = ['Accepted proof of language proficiency (required AFTER nomination)', 'Language requirements']
type ListedInstitution = ExplorerIndex['institutions'][number]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  index: ExplorerIndex
  favorites: string[]
  selectedIds: string[]
  onSelectedIdsChange: (ids: string[]) => void
  onRemoveFavorite: (id: string) => void
  academicYear: string
  studyField: string
}

function firstValue(agreement: AgreementRow, fields: string[]): string {
  return fields.map(field => agreement.details?.[field]?.trim()).find(Boolean) ?? ''
}

function LongText({ value }: { value: string }) {
  if (!value) return <span className="text-muted-foreground">Not provided</span>
  if (value.length <= 180) return <span className="whitespace-pre-wrap">{value}</span>
  return <details className="group"><summary className="cursor-pointer list-none text-left focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="group-open:hidden">{value.slice(0, 175).trimEnd()}… <span className="font-medium text-primary">Read more</span></span><span className="hidden font-medium text-primary group-open:inline">Show less</span></summary><p className="mt-1 whitespace-pre-wrap">{value}</p></details>
}

function AgreementValues({ agreements, valueFor }: { agreements: AgreementRow[]; valueFor: (agreement: AgreementRow) => string }) {
  if (!agreements.length) return <span className="text-muted-foreground">No matching agreements</span>
  const values = agreements.map(agreement => ({
    id: agreement.id,
    name: agreement.details?.['Agreement name']?.trim() || agreement.partner,
    value: valueFor(agreement),
  }))
  if (values.every(item => !item.value)) return <span className="text-muted-foreground">Not provided</span>
  return <ul className="space-y-2">{values.map(item => <li key={item.id} className="border-b border-border/60 pb-2 last:border-0 last:pb-0">{agreements.length > 1 && <span className="mb-0.5 block text-xs font-medium text-muted-foreground">{item.name}</span>}<LongText value={item.value} /></li>)}</ul>
}

function gradeText(agreement: AgreementRow): string {
  const grade = aggregateGradeRequirement(agreement.details)
  return grade.kind === 'minimum' ? `At least ${formatGrade(grade.value)} on the Danish scale` : grade.kind === 'none' ? 'No minimum listed' : ''
}

function studyLevels(agreement: AgreementRow): string {
  const fields = agreement.details ?? {}
  const levels = [
    fields.Bachelor === 'Yes' && "Bachelor's",
    fields['Second cycle/Master/Postgraduate'] === 'Yes' && "Master's",
    fields['Third cycle/Phd/Doctoral'] === 'Yes' && 'PhD',
  ].filter(Boolean)
  return levels.join(', ')
}

export function ShortlistComparison({ open, onOpenChange, index, favorites, selectedIds, onSelectedIdsChange, onRemoveFavorite, academicYear, studyField }: Props) {
  const [details, setDetails] = useState<Record<string, InstitutionDetails>>({})
  const [errors, setErrors] = useState<string[]>([])
  const institutionsById = useMemo(() => new Map(index.institutions.map(institution => [institution.id, institution])), [index.institutions])
  const saved = favorites.map(id => institutionsById.get(id)).filter((item): item is ListedInstitution => Boolean(item))
  const selected = selectedIds.filter(id => favorites.includes(id) && institutionsById.has(id))
  const query = academicYear ? index.queries.find(item => item.academicYear === academicYear && item.studyField === (studyField || null) && item.status === 'success') : null
  const matchingByIndex = useMemo(() => new Map(query?.matches.map(([institutionIndex, agreementIds]) => [institutionIndex, agreementIds]) ?? []), [query])
  const positions = useMemo(() => new Map(index.institutions.map((institution, position) => [institution.id, position])), [index.institutions])

  useEffect(() => {
    if (!open || !selected.length) return
    let active = true
    const missing = selected.filter(id => !details[id] && !errors.includes(id))
    if (missing.length) {
      void Promise.allSettled(missing.map(id => loadInstitutionDetails(id))).then(results => {
        if (!active) return
        const loaded: Record<string, InstitutionDetails> = {}
        const failed: string[] = []
        results.forEach((result, position) => {
          if (result.status === 'fulfilled') loaded[missing[position]] = result.value
          else failed.push(missing[position])
        })
        if (Object.keys(loaded).length) setDetails(current => ({ ...current, ...loaded }))
        if (failed.length) setErrors(current => [...new Set([...current, ...failed])])
      })
    }
    return () => { active = false }
  }, [open, selected.join('|'), details, errors])

  function toggle(id: string) {
    if (selected.includes(id)) onSelectedIdsChange(selected.filter(value => value !== id))
    else if (selected.length < MAX_COMPARE) onSelectedIdsChange([...selected, id])
  }

  function agreementsFor(id: string): AgreementRow[] {
    const institution = details[id]
    if (!institution) return []
    if (!academicYear) return institution.agreements
    const position = positions.get(id)
    const matching = new Set(position == null ? [] : (matchingByIndex.get(position) ?? []).map(number => index.agreementIds[number]))
    return institution.agreements.filter(agreement => matching.has(agreement.id))
  }

  const rows: { label: string; content: (institution: ListedInstitution, agreements: AgreementRow[]) => ReactNode }[] = [
    { label: 'Location', content: institution => [institution.city, institution.country].filter(Boolean).join(', ') },
    { label: 'Agreements', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => agreement.details?.['Agreement name']?.trim() || agreement.partner} /> },
    { label: 'Places listed', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, ['Total number'])} /> },
    { label: 'Study levels', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={studyLevels} /> },
    { label: 'Grade requirement', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={gradeText} /> },
    { label: 'Language', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, LANGUAGE_FIELDS)} /> },
    { label: 'Housing', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, ['Housing'])} /> },
    { label: 'Scholarships', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, ['Scholarships'])} /> },
    { label: 'Semester dates', content: (institution, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, ['Semester dates', 'Academic calendar']) || details[institution.id]?.partnerDetails?.semesterDates || details[institution.id]?.partnerDetails?.academicCalendar || ''} /> },
    { label: 'Restrictions', content: (_, agreements) => <AgreementValues agreements={agreements} valueFor={agreement => firstValue(agreement, ['Restrictions'])} /> },
  ]

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="flex max-h-[92vh] w-[calc(100%-1rem)] max-w-[90rem] flex-col gap-0 overflow-hidden p-0 sm:max-w-[min(96vw,90rem)]">
      <DialogHeader className="shrink-0 border-b px-5 py-5 pr-12 sm:px-7">
        <DialogTitle className="text-xl font-semibold">Compare saved destinations</DialogTitle>
        <DialogDescription>{academicYear ? `Showing agreements for ${academicYear}${studyField ? ` · ${studyField}` : ''}.` : 'Showing all listed agreements. Choose an academic year in the filters to narrow them.'} Select up to four destinations.</DialogDescription>
      </DialogHeader>
      <div className="min-h-0 overflow-y-auto">
        {saved.length === 0 ? <div className="px-6 py-14 text-center"><Star className="mx-auto size-6 text-muted-foreground" /><p className="mt-3 font-medium">Your shortlist is empty</p><p className="mt-1 text-sm text-muted-foreground">Save destinations with the star, then compare them here.</p></div> : <>
          <div className="border-b px-5 py-4 sm:px-7"><p className="mb-2 text-xs font-medium text-muted-foreground">Saved destinations ({saved.length})</p><div className="flex flex-wrap gap-2">{saved.map(institution => {
            const active = selected.includes(institution.id)
            return <button key={institution.id} type="button" aria-pressed={active} disabled={!active && selected.length >= MAX_COMPARE} onClick={() => toggle(institution.id)} className={`inline-flex max-w-full items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-40 ${active ? 'border-primary bg-primary/8 text-primary' : 'bg-background text-muted-foreground hover:text-foreground'}`}><Check className={`size-3.5 ${active ? '' : 'opacity-0'}`} /><span className="truncate">{institution.name}</span></button>
          })}</div></div>
          {selected.length === 0 ? <p className="px-6 py-12 text-center text-sm text-muted-foreground">Select destinations above to compare them.</p> : <div className="overflow-x-auto" role="region" aria-label="Destination comparison" tabIndex={0}>
            <table className="w-max min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead><tr><th scope="col" className="sticky left-0 z-20 w-36 min-w-36 border-b border-r bg-muted px-4 py-4 align-top text-xs font-medium text-muted-foreground sm:w-44 sm:min-w-44">Compare</th>{selected.map(id => {
                const institution = institutionsById.get(id)!
                return <th scope="col" key={id} className="w-64 min-w-64 border-b border-r bg-muted/60 px-4 py-4 align-top last:border-r-0 sm:w-72 sm:min-w-72"><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold leading-snug text-foreground">{institution.name}</span><button type="button" onClick={() => onRemoveFavorite(id)} aria-label={`Remove ${institution.name} from saved destinations`} title="Remove from saved destinations" className="shrink-0 rounded p-1 text-amber-500 hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><Star className="size-4 fill-amber-400" /></button></div></th>
              })}</tr></thead>
              <tbody>{rows.map(row => <tr key={row.label}><th scope="row" className="sticky left-0 z-10 w-36 min-w-36 border-b border-r bg-background px-4 py-4 align-top text-xs font-medium text-foreground sm:w-44 sm:min-w-44">{row.label}</th>{selected.map(id => {
                const institution = institutionsById.get(id)!
                return <td key={id} className="w-64 min-w-64 border-b border-r px-4 py-4 align-top leading-relaxed last:border-r-0 sm:w-72 sm:min-w-72">{errors.includes(id) ? <span className="text-destructive">Details could not be loaded. <button type="button" className="underline" onClick={() => setErrors(current => current.filter(value => value !== id))}>Retry</button></span> : !details[id] ? <span className="inline-flex items-center gap-2 text-muted-foreground"><Loader2 className="size-3.5 animate-spin" />Loading…</span> : row.content(institution, agreementsFor(id))}</td>
              })}</tr>)}</tbody>
            </table>
          </div>}
          <div className="flex justify-end border-t px-5 py-3 sm:px-7"><Button asChild variant="outline" size="sm"><a href={PORTAL_URL} target="_blank" rel="noopener noreferrer">Check the official KU portal<ExternalLink className="size-3.5" /></a></Button></div>
        </>}
      </div>
    </DialogContent>
  </Dialog>
}
