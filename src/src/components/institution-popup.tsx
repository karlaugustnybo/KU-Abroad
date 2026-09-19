import { startTransition, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AlertCircle, ExternalLink, FileText, Loader2, Map, MapPin, Star } from 'lucide-react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '~/components/ui/accordion'
import { Badge } from '~/components/ui/badge'
import { Button } from '~/components/ui/button'
import { Separator } from '~/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '~/components/ui/sheet'
import { loadInstitutionDetails } from '~/utils/dataset'
import { aggregateGradeRequirement, formatGrade } from '~/lib/grade'
import { PORTAL_URL } from '~/lib/exchange'
import { cn } from '~/lib/utils'
import type { AgreementRow, InstitutionDetails, InstitutionSummary } from '~/lib/types'

interface Props {
  institution: InstitutionSummary | null
  agreementIds: string[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onShowMap: () => void
  isFavorite?: boolean
  onToggleFavorite?: () => void
}

function Linkify({ text }: { text: string }) {
  const parts: ReactNode[] = []
  const expression = /([^\n]+?)\s*\((https?:\/\/[^\s)]+)\)|\b(https?:\/\/[^\s]+)/g
  let cursor = 0
  let match: RegExpExecArray | null
  while ((match = expression.exec(text))) {
    if (match.index > cursor) parts.push(text.slice(cursor, match.index))
    const url = match[2] || match[3]
    const label = match[1]?.trim() || url.replace(/^https?:\/\//, '')
    parts.push(<a key={`${match.index}-${url}`} href={url} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2 hover:text-primary/80">{label}</a>)
    cursor = match.index + match[0].length
  }
  if (cursor < text.length) parts.push(text.slice(cursor))
  return <>{parts}</>
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return <div className="grid gap-1 border-b py-3 last:border-0 sm:grid-cols-[9rem_1fr]"><dt className="text-xs font-medium text-muted-foreground">{label}</dt><dd className="whitespace-pre-wrap text-sm leading-relaxed"><Linkify text={value} /></dd></div>
}

function GradeBadge({ details }: { details?: Record<string, string> | null }) {
  const requirement = aggregateGradeRequirement(details)
  const label = requirement.kind === 'none' ? 'No grade requirement'
    : requirement.kind === 'minimum' ? `Min. grade average ${formatGrade(requirement.value)} (Danish scale)`
    : 'Grade requirement unclear'
  const variant = requirement.kind === 'minimum' ? 'default' : requirement.kind === 'none' ? 'secondary' : 'outline'
  return <Badge variant={variant} className="mt-3">{label}</Badge>
}

function Agreement({ agreement }: { agreement: AgreementRow }) {
  const title = agreement.details?.['Agreement name'] || agreement.partner
  return <AccordionItem value={agreement.id} className="rounded-lg border px-4 not-last:border-b">
    <AccordionTrigger className="gap-3 py-4 hover:no-underline"><span><span className="block font-medium">{title}</span><span className="mt-1 block text-xs font-normal text-muted-foreground">{agreement.hostCountry}</span></span></AccordionTrigger>
    <AccordionContent className="pb-4"><GradeBadge details={agreement.details} /><dl>{Object.entries(agreement.details ?? {}).filter(([, value]) => value).map(([label, value]) => <DetailRow key={label} label={label} value={value} />)}</dl>
      <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"><ExternalLink className="size-4" />Open the KU Mobility-Online portal</a>
    </AccordionContent>
  </AccordionItem>
}

export function InstitutionPopup({ institution, agreementIds, open, onOpenChange, onShowMap, isFavorite = false, onToggleFavorite }: Props) {
  const [loaded, setLoaded] = useState<{ institutionId: string; details: InstitutionDetails } | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    let current = true
    setError(false)
    if (!open || !institution) return () => { current = false }
    loadInstitutionDetails(institution.id).then(value => {
      if (!current) return
      window.requestAnimationFrame(() => startTransition(() => {
        if (current) setLoaded({ institutionId: institution.id, details: value })
      }))
    }).catch(() => { if (current) setError(true) })
    return () => { current = false }
  }, [institution?.id, open])
  const details = loaded && loaded.institutionId === institution?.id ? loaded.details : null
  const agreements = useMemo(() => details?.agreements.filter(agreement => agreementIds.includes(agreement.id)) ?? [], [details, agreementIds])
  return <Sheet open={open} onOpenChange={onOpenChange}>
    {open && <SheetContent instant className="w-full sm:w-[min(92vw,42rem)]">
      <SheetHeader><SheetTitle>{institution?.name || 'Institution details'}</SheetTitle><SheetDescription className="flex items-center gap-1"><MapPin className="size-3.5" />{institution && [institution.city, institution.country].filter(Boolean).join(', ')}</SheetDescription></SheetHeader>
      {!institution ? null : error ? <div className="m-5 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm"><div className="flex items-center gap-2 font-medium"><AlertCircle className="size-4 text-destructive" />Details could not be loaded</div><p className="mt-1 text-muted-foreground">Close this panel and try again.</p></div>
        : !details ? <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground"><Loader2 className="mr-2 size-4 animate-spin" />Loading details…</div>
        : <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-8">
          <div className="flex flex-wrap gap-2 py-4">{institution.lat != null && institution.lon != null && <Button variant="outline" onClick={onShowMap}><Map />Show on map</Button>}{onToggleFavorite && <Button variant="outline" aria-pressed={isFavorite} onClick={onToggleFavorite}><Star className={cn(isFavorite && 'fill-amber-400 text-amber-400')} />{isFavorite ? 'Saved' : 'Save'}</Button>}<Button asChild variant="outline"><a href={PORTAL_URL} target="_blank" rel="noopener noreferrer"><ExternalLink />Official KU portal</a></Button></div>
          {details.partnerDetails && <section><h3 className="text-sm font-semibold">Institution information</h3><dl className="mt-2"><DetailRow label="Institution code" value={details.partnerDetails.code} /><DetailRow label="Description" value={details.partnerDetails.description} /><DetailRow label="Semester dates" value={details.partnerDetails.semesterDates} /><DetailRow label="Academic calendar" value={details.partnerDetails.academicCalendar} /><DetailRow label="ECTS converter" value={details.partnerDetails.ectsConverter} /><DetailRow label="Faculty contact" value={details.partnerDetails.facultyContact} /><DetailRow label="Housing contact" value={details.partnerDetails.housingContact} /><DetailRow label="Comment" value={details.partnerDetails.comment} /></dl>
            {!!details.partnerDetails.documents.length && <div className="mt-3 space-y-2">{details.partnerDetails.documents.map(document => <a key={document.url} href={document.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-primary hover:underline"><FileText className="size-4" />{document.label}</a>)}</div>}
          </section>}
          <Separator className="my-5" />
          <section><div className="flex items-baseline justify-between gap-4"><h3 className="text-sm font-semibold">Matching agreements</h3><span className="text-xs text-muted-foreground">{agreements.length} found</span></div>
            {agreements.length ? <Accordion type="multiple" className="mt-3 gap-2">{agreements.map(agreement => <Agreement key={agreement.id} agreement={agreement} />)}</Accordion> : <p className="mt-3 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No agreements match the current academic selection.</p>}
          </section>
        </div>}
    </SheetContent>}
  </Sheet>
}
