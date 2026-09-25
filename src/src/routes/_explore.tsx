import { createFileRoute, Outlet } from '@tanstack/react-router'
import { DashboardPending, DashboardShell } from '~/components/dashboard-shell'
import { getExplorerIndex } from '~/utils/dataset'

export const Route = createFileRoute('/_explore')({
  loader: async () => ({ index: await getExplorerIndex() }),
  pendingComponent: DashboardPending,
  component: ExploreLayout,
})

function ExploreLayout() {
  const { index } = Route.useLoaderData()
  return <><DashboardShell index={index} /><Outlet /></>
}
