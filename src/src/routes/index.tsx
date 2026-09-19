import { createFileRoute } from '@tanstack/react-router'
import { DashboardPending, DashboardShell } from '~/components/dashboard-shell'
import { validateFilters } from '~/lib/exchange'
import { getExplorerIndex } from '~/utils/dataset'

export const Route = createFileRoute('/')({
  component: Home,
  pendingComponent: DashboardPending,
  validateSearch: validateFilters,
  loader: async () => {
    const index = await getExplorerIndex()
    return { index }
  },
})

function Home() {
  const { index } = Route.useLoaderData()
  return <DashboardShell index={index} view="table" />
}
