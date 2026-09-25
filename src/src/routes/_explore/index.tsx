import { createFileRoute } from '@tanstack/react-router'
import { validateFilters } from '~/lib/exchange'

export const Route = createFileRoute('/_explore/')({
  component: () => null,
  validateSearch: validateFilters,
})
