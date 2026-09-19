import { createServerFn } from '@tanstack/react-start'
import explorerIndex from '~/assets/data/explorer-index.json'
import institutionDetails from '~/assets/data/institution-details.json'
import type { ExplorerIndex, InstitutionDetails } from '~/lib/types'

const index = explorerIndex as unknown as ExplorerIndex
const details = institutionDetails as unknown as Record<string, InstitutionDetails>
const detailCache = new Map<string, InstitutionDetails>()
const detailRequests = new Map<string, Promise<InstitutionDetails>>()

export const getExplorerIndex = createServerFn({ method: 'GET' }).handler(() => index)

export const getInstitutionDetails = createServerFn({ method: 'GET' })
  .validator((input: { institutionId: string }) => {
    if (!/^inst-[a-f0-9]{24}$/.test(input.institutionId)) throw new Error('Invalid institution ID')
    return input
  })
  .handler(({ data }) => {
    const cacheKey = `${index.version}:${data.institutionId}`
    const cached = detailCache.get(cacheKey)
    if (cached) return cached
    const institution = details[data.institutionId]
    if (!institution) throw new Error('Institution not found')
    detailCache.set(cacheKey, institution)
    return institution
  })

export function loadInstitutionDetails(institutionId: string): Promise<InstitutionDetails> {
  const cached = detailRequests.get(institutionId)
  if (cached) return cached

  const request = getInstitutionDetails({ data: { institutionId } }).catch(error => {
    detailRequests.delete(institutionId)
    throw error
  })
  detailRequests.set(institutionId, request)
  return request
}
