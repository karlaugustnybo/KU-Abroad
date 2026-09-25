import { createFileRoute } from '@tanstack/react-router'
import { ReportReader } from '~/components/report-reader'

export const Route = createFileRoute('/reports/$reportId')({
  component: ReportPage,
  head: () => ({ meta: [{ title: 'Student report · KU Abroad' }] }),
})

function ReportPage() {
  const { reportId } = Route.useParams()
  return <ReportReader reportId={reportId} />
}
