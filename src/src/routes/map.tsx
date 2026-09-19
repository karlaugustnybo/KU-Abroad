import { createFileRoute } from '@tanstack/react-router';
import { DashboardPending, DashboardShell } from '~/components/dashboard-shell';
import { getExplorerIndex } from '~/utils/dataset';
import { validateFilters } from '~/lib/exchange';
export const Route = createFileRoute('/map')({
  validateSearch: validateFilters,
  component: MapPage,
  pendingComponent: DashboardPending,
  loader: async () => ({ index: await getExplorerIndex() }),
});
function MapPage() {
  const { index } = Route.useLoaderData();
  return <DashboardShell index={index} view="map" />;
}
