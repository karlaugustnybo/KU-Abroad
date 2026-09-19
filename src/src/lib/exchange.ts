import type { ExplorerIndex, InstitutionSummary } from './types'
import { meetsRequirement } from './grade'

export const PORTAL_URL = 'https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01'
export type SortKey = 'name' | 'country' | 'city' | 'agreements'
export type SortDirection = 'asc' | 'desc'

export interface Filters {
  query: string
  continent: string
  country: string
  academicYear: string
  studyField: string
  program: string
  studyLevel: string
  minPlaces: string
  languageInfo: string
  housingInfo: string
  scholarshipInfo: string
  maxGrade: string
  gradeUnknown: string
  sort: SortKey
  direction: SortDirection
  page: number
  selected: string
}

export const EMPTY_FILTERS: Filters = {
  query: '', continent: '', country: '', academicYear: '', studyField: '', program: '', studyLevel: '', minPlaces: '',
  languageInfo: '', housingInfo: '', scholarshipInfo: '', maxGrade: '', gradeUnknown: '',
  sort: 'name', direction: 'asc', page: 1, selected: '',
}
const sortKeys = new Set<SortKey>(['name', 'country', 'city', 'agreements'])

export function validateFilters(search: Record<string, unknown>): Filters {
  const string = (key: keyof Filters) => typeof search[key] === 'string' ? search[key] as string : ''
  const sort = string('sort') as SortKey
  const page = Number(search.page)
  const grade = Number(search.maxGrade)
  const minPlaces = Number(search.minPlaces)
  const studyLevel = string('studyLevel')
  const filters: Filters = {
    query: string('query'), continent: string('continent'), country: string('country'), academicYear: string('academicYear'), studyField: string('studyField'),
    program: string('program'),
    studyLevel: ['bachelor', 'master', 'doctoral'].includes(studyLevel) ? studyLevel : '',
    minPlaces: Number.isInteger(minPlaces) && minPlaces > 0 && minPlaces <= 1_000 ? String(minPlaces) : '',
    languageInfo: string('languageInfo') === 'yes' ? 'yes' : '',
    housingInfo: string('housingInfo') === 'yes' ? 'yes' : '',
    scholarshipInfo: string('scholarshipInfo') === 'yes' ? 'yes' : '',
    maxGrade: Number.isFinite(grade) && grade > 0 && grade <= 12 ? String(grade) : '',
    gradeUnknown: string('gradeUnknown') === 'exclude' ? 'exclude' : '',
    sort: sortKeys.has(sort) ? sort : 'name', direction: string('direction') === 'desc' ? 'desc' : 'asc',
    page: Number.isInteger(page) && page > 0 ? page : 1, selected: string('selected'),
  }
  if (!filters.academicYear) filters.studyField = ''
  return filters
}

const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

export function selectInstitutions(index: ExplorerIndex, filters: Filters) {
  let institutions: InstitutionSummary[] = index.institutions.map(institution => ({ ...institution, matchingAgreementIds: institution.agreementIds }))
  let status: 'overview' | 'available' | 'unavailable' = 'overview'
  let collectedAt = index.generatedAt
  if (filters.academicYear) {
    const result = index.queries.find(query => query.academicYear === filters.academicYear && query.studyField === (filters.studyField || null))
    if (!result || result.status !== 'success') {
      status = 'unavailable'
      institutions = []
    } else {
      status = 'available'
      collectedAt = result.collectedAt
      institutions = result.matches.map(([institutionIndex, agreementIds]) => ({ ...index.institutions[institutionIndex], matchingAgreementIds: agreementIds })).filter(institution => institution.id)
    }
  }
  const levelBit = filters.studyLevel === 'bachelor' ? 1 : filters.studyLevel === 'master' ? 2 : filters.studyLevel === 'doctoral' ? 4 : 0
  const requiredFeatures = (filters.languageInfo ? 1 : 0) | (filters.housingInfo ? 2 : 0) | (filters.scholarshipInfo ? 4 : 0)
  const hasAgreementFilters = Boolean(filters.program || levelBit || filters.minPlaces || requiredFeatures || filters.maxGrade)
  if (hasAgreementFilters) {
    const average = Number(filters.maxGrade)
    const includeUnknown = filters.gradeUnknown !== 'exclude'
    institutions = institutions.map(institution => ({
      ...institution,
      matchingAgreementIds: institution.matchingAgreementIds.filter(id =>
        (!filters.program || index.agreementPrograms?.[id] === filters.program) &&
        (!levelBit || Boolean((index.agreementStudyLevels?.[id] ?? 0) & levelBit)) &&
        (!filters.minPlaces || (index.agreementPlaces?.[id] ?? -1) >= Number(filters.minPlaces)) &&
        (!requiredFeatures || ((index.agreementFeatures?.[id] ?? 0) & requiredFeatures) === requiredFeatures) &&
        (!filters.maxGrade || meetsRequirement(index.gradeRequirements?.[id], average, includeUnknown))
      ),
    })).filter(institution => institution.matchingAgreementIds.length > 0)
  }
  const query = normalize(filters.query.trim())
  institutions = institutions.filter(institution =>
    (!filters.continent || institution.continent === filters.continent) &&
    (!filters.country || institution.country === filters.country) &&
    (!query || normalize(`${institution.name} ${institution.city} ${institution.country} ${institution.continent}`).includes(query)))
  return { institutions, status, collectedAt }
}

export function activeFilterCount(filters: Filters) {
  return [filters.academicYear, filters.studyField, filters.continent, filters.country, filters.program, filters.studyLevel,
    filters.minPlaces, filters.languageInfo, filters.housingInfo, filters.scholarshipInfo, filters.maxGrade, filters.gradeUnknown].filter(Boolean).length
}

export function summarize(institutions: { country: string; continent: string; agreements: unknown[]; lat?: number; lon?: number }[]) {
  const countries: Record<string, number> = {}
  const continents: Record<string, number> = {}
  for (const institution of institutions) {
    countries[institution.country] = (countries[institution.country] ?? 0) + 1
    continents[institution.continent] = (continents[institution.continent] ?? 0) + 1
  }
  return {
    totalInstitutions: institutions.length,
    withAgreements: institutions.filter(institution => institution.agreements.length > 0).length,
    withCoordinates: institutions.filter(institution => institution.lat != null && institution.lon != null).length,
    totalAgreements: institutions.reduce((sum, institution) => sum + institution.agreements.length, 0),
    totalCountries: Object.keys(countries).length,
    continents,
    topCountries: Object.entries(countries).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([country, count]) => ({ country, count })),
  }
}
