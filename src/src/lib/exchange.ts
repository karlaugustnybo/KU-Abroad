import type { ExplorerIndex, InstitutionSummary } from './types'
import { meetsRequirement } from './grade'

export const PORTAL_URL = 'https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01'
export type SortKey = 'name' | 'country' | 'city' | 'agreements'
export type SortDirection = 'asc' | 'desc'

// Display names diverge from the portal's raw "Country" / "Host country" values.
// Keep in sync with scripts/portal_data.py COUNTRY_DISPLAY_NAMES.
const COUNTRY_DISPLAY_NAMES: Record<string, string> = {
  'China (Hong Kong)': 'Hong Kong (China)',
  'China (Taiwan)': 'Taiwan',
}

export function displayCountry(country: string): string {
  return COUNTRY_DISPLAY_NAMES[country.trim()] ?? country
}

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
  const rawCountry = string('country')
  const filters: Filters = {
    query: string('query'), continent: string('continent'), country: rawCountry ? displayCountry(rawCountry) : '', academicYear: string('academicYear'), studyField: string('studyField'),
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

export interface SelectionResult {
  institutions: InstitutionSummary[]
  status: 'overview' | 'available' | 'unavailable'
  collectedAt: string
}

// Memoize on the selection-affecting filter fields only, so view-only changes
// (sort, direction, page, selected) return a stable reference and don't
// invalidate downstream useMemo/useEffect dependency arrays.
const selectionCache = new WeakMap<object, { key: string; result: SelectionResult }>()

function selectionKey(filters: Filters): string {
  return JSON.stringify([
    filters.query, filters.continent, filters.country, filters.academicYear, filters.studyField,
    filters.program, filters.studyLevel, filters.minPlaces, filters.languageInfo, filters.housingInfo,
    filters.scholarshipInfo, filters.maxGrade, filters.gradeUnknown,
  ])
}

export function selectInstitutions(index: ExplorerIndex, filters: Filters): SelectionResult {
  const key = selectionKey(filters)
  const cached = selectionCache.get(index)
  if (cached && cached.key === key) return cached.result

  const result = computeSelection(index, filters)
  selectionCache.set(index, { key, result })
  return result
}

function computeSelection(index: ExplorerIndex, filters: Filters): SelectionResult {
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

export function summarize(institutions: { country: string; agreements: unknown[]; lat?: number; lon?: number }[]) {
  const countries = new Set<string>()
  for (const institution of institutions) {
    countries.add(institution.country)
  }
  return {
    totalInstitutions: institutions.length,
    withAgreements: institutions.filter(institution => institution.agreements.length > 0).length,
    withCoordinates: institutions.filter(institution => institution.lat != null && institution.lon != null).length,
    totalAgreements: institutions.reduce((sum, institution) => sum + institution.agreements.length, 0),
    totalCountries: countries.size,
  }
}
