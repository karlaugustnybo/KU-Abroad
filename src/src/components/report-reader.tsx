import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '~/components/ui/accordion'
import { Button } from '~/components/ui/button'
import { EMPTY_FILTERS, PORTAL_URL } from '~/lib/exchange'
import { loadReport, safeReportLink, type ReportDetail } from '~/lib/reports'

export function ReportReader({ reportId }: { reportId: string }) {
  const [loaded, setLoaded] = useState<{ id: string; report: ReportDetail } | null>(null)
  const [error, setError] = useState(false)
  const [expanded, setExpanded] = useState<string[]>([])

  useEffect(() => {
    let current = true
    setError(false)
    loadReport(reportId).then(report => {
      if (!current) return
      setLoaded({ id: reportId, report })
      setExpanded(report.sections.length ? ['section-0'] : [])
      setError(false)
    }).catch(() => { if (current) setError(true) })
    return () => { current = false }
  }, [reportId])

  const report = loaded?.id === reportId ? loaded.report : null
  const allSectionIds = report?.sections.map((_, index) => `section-${index}`) ?? []
  return <div className="min-h-screen bg-[#f7f8fa]">
    <header className="border-b bg-background"><div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
      <Link to="/" search={EMPTY_FILTERS} className="text-lg font-semibold tracking-tight text-[#18212b]">KU Abroad</Link>
      <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary">Official KU portal<ExternalLink className="size-3.5" /></a>
    </div></header>
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
      {error ? <div className="rounded-lg border bg-background p-8"><h1 className="text-xl font-semibold">Report unavailable</h1><p className="mt-2 text-sm text-muted-foreground">This report could not be loaded. Try again later or return to the destinations.</p><Button asChild variant="outline" className="mt-5"><Link to="/" search={EMPTY_FILTERS}>Explore destinations</Link></Button></div>
      : !report ? <div role="status" className="flex items-center gap-2 py-20 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Loading report…</div>
      : <>
        <Link to="/" search={{ ...EMPTY_FILTERS, selected: report.institutionId }} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-primary"><ArrowLeft className="size-4" />Back to institution</Link>
        <div className="mt-7 border-b pb-7"><p className="text-sm font-medium text-primary">{report.questionnaireType || 'Student report'}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-[#18212b] sm:text-4xl">{report.institutionName}</h1><p className="mt-3 text-sm text-muted-foreground">{[report.academicYear, report.studyField].filter(Boolean).join(' · ')}</p></div>
        <div className="flex flex-wrap items-center justify-between gap-3 py-5"><p className="text-sm text-muted-foreground">Choose the topics you want to read.</p><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => setExpanded(allSectionIds)}>Expand all</Button><Button size="sm" variant="outline" onClick={() => setExpanded([])}>Collapse all</Button></div></div>
        <Accordion type="multiple" value={expanded} onValueChange={setExpanded} className="gap-2">
          {report.sections.map((section, index) => <AccordionItem key={`section-${index}`} value={`section-${index}`} className="rounded-lg border bg-background px-4 sm:px-5">
            <AccordionTrigger className="gap-4 py-4 hover:no-underline"><span className="min-w-0 flex-1 text-base font-semibold">{section.title}</span><span className="w-7 shrink-0 text-right text-xs font-normal tabular-nums text-muted-foreground" aria-label={`${section.questions.length} questions`}>{section.questions.length}</span></AccordionTrigger>
            <AccordionContent className="pb-4"><div className="divide-y">{section.questions.map((item, questionIndex) => <div key={questionIndex} className="py-4 first:pt-0 last:pb-0">
              <h2 className="text-sm font-medium leading-relaxed">{item.question}</h2>
              <p className="mt-1.5 whitespace-pre-wrap break-words text-sm leading-7 text-muted-foreground">{item.answer || 'No answer provided.'}</p>
              {item.links.length > 0 && <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">{item.links.map((link, linkIndex) => {
                const safe = safeReportLink(link)
                return safe && <a key={`${linkIndex}-${safe}`} href={safe} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline"><ExternalLink className="size-3.5" />Source link {linkIndex + 1}</a>
              })}</div>}
            </div>)}</div></AccordionContent>
          </AccordionItem>)}
        </Accordion>
        <p className="mt-8 border-t pt-5 text-xs text-muted-foreground">Student questionnaire from the KU Mobility-Online portal. Experiences describe a previous academic year and may differ from current exchange options.</p>
      </>}
    </main>
  </div>
}
