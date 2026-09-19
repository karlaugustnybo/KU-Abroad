import { useMemo } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, MapPin } from 'lucide-react'
import { flexRender } from '@tanstack/react-table'
import { getCoreRowModel, getPaginationRowModel, getSortedRowModel, type LegacyColumnDef, useLegacyTable } from '@tanstack/react-table/legacy'
import { Button } from '~/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '~/components/ui/table'
import type { Filters, SortKey } from '~/lib/exchange'
import type { InstitutionSummary } from '~/lib/types'

interface InstitutionTableProps {
  institutions: InstitutionSummary[]
  filters: Filters
  onChange: (filters: Filters) => void
  onSelect: (institution: InstitutionSummary) => void
}

function SortIcon({ active, descending }: { active: boolean; descending: boolean }) {
  if (!active) return <ArrowUpDown className="size-3.5 opacity-35" />
  return descending ? <ArrowDown className="size-3.5" /> : <ArrowUp className="size-3.5" />
}

export function InstitutionTable({ institutions, filters, onChange, onSelect }: InstitutionTableProps) {
  const columns = useMemo<LegacyColumnDef<InstitutionSummary>[]>(() => [
    { id: 'name', accessorKey: 'name', header: 'Institution', cell: ({ row }) => <button type="button" onClick={() => onSelect(row.original)} className="group text-left focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="font-medium text-foreground group-hover:text-primary group-hover:underline">{row.original.name}</span><span className="mt-1 flex items-center gap-1 text-xs text-muted-foreground sm:hidden"><MapPin className="size-3" />{[row.original.city, row.original.country].filter(Boolean).join(', ')}</span></button> },
    { id: 'country', accessorKey: 'country', header: 'Country' },
    { id: 'city', accessorKey: 'city', header: 'City' },
    { id: 'agreements', accessorFn: row => row.matchingAgreementIds.length, header: 'Agreements' },
  ], [onSelect])
  const table = useLegacyTable({
    data: institutions,
    columns,
    state: {
      sorting: [{ id: filters.sort, desc: filters.direction === 'desc' }],
      pagination: { pageIndex: filters.page - 1, pageSize: 25 },
    },
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getPaginationRowModel: getPaginationRowModel(),
  })
  const pages = Math.max(1, table.getPageCount())
  function sort(key: SortKey) {
    onChange({ ...filters, sort: key, direction: filters.sort === key && filters.direction === 'asc' ? 'desc' : 'asc', page: 1 })
  }
  return <div className="overflow-hidden rounded-lg border bg-card">
    <div className="overflow-x-auto">
      <Table>
        <TableHeader><TableRow className="bg-muted/55 hover:bg-muted/55">
          {table.getHeaderGroups()[0].headers.map(header => {
            const key = header.column.id as SortKey
            return <TableHead key={header.id} className={key === 'city' ? 'hidden md:table-cell' : key === 'country' ? 'hidden sm:table-cell' : key === 'agreements' ? 'w-28 text-right' : ''}>
              <button type="button" onClick={() => sort(key)} className="inline-flex items-center gap-1.5 py-1 font-medium text-foreground focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {flexRender(header.column.columnDef.header, header.getContext())}<SortIcon active={filters.sort === key} descending={filters.direction === 'desc'} />
              </button>
            </TableHead>
          })}
        </TableRow></TableHeader>
        <TableBody>{table.getRowModel().rows.map(row => <TableRow key={row.id}>
          {row.getVisibleCells().map(cell => <TableCell key={cell.id} className={cell.column.id === 'city' ? 'hidden text-muted-foreground md:table-cell' : cell.column.id === 'country' ? 'hidden sm:table-cell' : cell.column.id === 'agreements' ? 'text-right tabular-nums' : ''}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>)}
        </TableRow>)}</TableBody>
      </Table>
    </div>
    <div className="flex items-center justify-between border-t px-4 py-3 text-sm text-muted-foreground">
      <span>Page {Math.min(filters.page, pages)} of {pages}</span>
      <div className="flex gap-1"><Button variant="outline" size="icon-sm" aria-label="Previous page" disabled={filters.page <= 1} onClick={() => onChange({ ...filters, page: filters.page - 1 })}><ChevronLeft /></Button><Button variant="outline" size="icon-sm" aria-label="Next page" disabled={filters.page >= pages} onClick={() => onChange({ ...filters, page: filters.page + 1 })}><ChevronRight /></Button></div>
    </div>
  </div>
}
