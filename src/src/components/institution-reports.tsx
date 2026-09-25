import { useEffect, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { FileText, Loader2 } from 'lucide-react'
import { Button } from '~/components/ui/button'
import { loadInstitutionReports, type ReportSummary } from '~/lib/reports'

const PAGE_SIZE = 20

export function InstitutionReports({ institutionId, reportCount }: { institutionId: string; reportCount: number }) {
  const [listing, setListing] = useState<ReportSummary[] | null>(null)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [year, setYear] = useState('')
  const [field, setField] = useState('')
  const [limit, setLimit] = useState(PAGE_SIZE)

  useEffect(() => {
    let current = true
    if (reportCount === 0) return () => { current = false }
    loadInstitutionReports(institutionId).then(value => {
      if (current) { setListing(value); setError(false) }
    }).catch(() => { if (current) setError(true) })
    return () => { current = false }
  }, [institutionId, reportCount, retry])

  const years = useMemo(() => [...new Set((listing ?? []).map(item => item.academicYear).filter((value): value is string => Boolean(value)))].sort().reverse(), [listing])
  const fields = useMemo(() => [...new Set((listing ?? []).filter(item => !year || item.academicYear === year).map(item => item.studyField).filter((value): value is string => Boolean(value)))].sort(), [listing, year])
  const filtered = useMemo(() => (listing ?? []).filter(item => (!year || item.academicYear === year) && (!field || item.studyField === field)), [listing, year, field])

  if (!reportCount) return <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">No student reports are available for this institution.</p>
  if (error) return <div className="rounded-lg border border-destructive/30 p-5 text-sm"><p>Reports could not be loaded.</p><Button variant="outline" className="mt-3" onClick={() => { setError(false); setRetry(value => value + 1) }}>Try again</Button></div>
  if (!listing) return <p className="flex items-center gap-2 py-8 text-sm text-muted-foreground" role="status"><Loader2 className="size-4 animate-spin" />Loading reports…</p>

  return <div className="space-y-4 pb-8">
    <p className="text-sm text-muted-foreground">Student experiences from previous academic years. Report filters are separate from the exchange options you selected.</p>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="grid gap-1.5 text-xs font-medium">Academic year
        <select className="h-10 rounded-md border bg-background px-3 text-sm font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" value={year} onChange={event => { setYear(event.target.value); setField(''); setLimit(PAGE_SIZE) }}>
          <option value="">All years</option>{years.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
      <label className="grid gap-1.5 text-xs font-medium">Study field
        <select className="h-10 rounded-md border bg-background px-3 text-sm font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" value={field} onChange={event => { setField(event.target.value); setLimit(PAGE_SIZE) }}>
          <option value="">All study fields</option>{fields.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
    </div>
    <p className="text-xs text-muted-foreground" aria-live="polite">{filtered.length} report{filtered.length === 1 ? '' : 's'} found</p>
    {filtered.length ? <ul className="divide-y border-y">
      {filtered.slice(0, limit).map(item => <li key={item.id}>
        <Link to="/reports/$reportId" params={{ reportId: item.id }} className="group flex items-start gap-3 py-3.5 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0"><span className="block text-sm font-medium group-hover:text-primary group-hover:underline">{item.questionnaireType || 'Student report'}</span><span className="mt-0.5 block text-xs text-muted-foreground">{[item.academicYear, item.studyField].filter(Boolean).join(' · ')}</span></span>
        </Link>
      </li>)}
    </ul> : <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">No reports match these filters.</p>}
    {limit < filtered.length && <Button variant="outline" className="w-full" onClick={() => setLimit(value => value + PAGE_SIZE)}>Show more reports</Button>}
  </div>
}
