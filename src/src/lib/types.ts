export interface AgreementRow {
  id: string
  partner: string
  hostCountry: string
  portalUrl?: string | null
  details?: Record<string, string> | null
}

export interface PartnerDetails {
  name: string
  code: string | null
  additionalDescription: string | null
  country: string | null
  description: string | null
  ectsConverter: string | null
  semesterDates: string | null
  academicCalendar: string | null
  facultyContact: string | null
  housingContact: string | null
  comment: string | null
  documents: { label: string; url: string }[]
}

export interface Institution {
  id: string
  name: string
  continent: string
  country: string
  city: string
  lat?: number
  lon?: number
  agreementCount: number
  cooperationCount: number
  multilateralCount: number
  reportCount: number
  eventCount: number
  agreements: AgreementRow[]
  partnerDetails?: PartnerDetails
}

export interface InstitutionSummary extends Omit<Institution, 'agreements' | 'partnerDetails' | 'eventCount'> {
  agreementIds: number[]
  matchingAgreementIds: number[]
}

export type QueryMatch = [institutionIndex: number, agreementIndexes: number[]]

export interface ExplorerQuery {
  academicYear: string
  studyField: string | null
  status: 'success' | 'error' | 'pending'
  collectedAt: string
  matches: QueryMatch[]
}

export interface ExplorerIndex {
  version: string
  generatedAt: string
  sourceUrl: string
  coverage: { expectedQueries: number; successfulQueries: number; status: 'complete' | 'incomplete' }
  academicYears: string[]
  studyFields: string[]
  programs?: string[]
  studyLevels?: ('bachelor' | 'master' | 'doctoral')[]
  agreementIds: string[]
  gradeRequirements?: number[]
  agreementPrograms?: string[]
  agreementPlaces?: number[]
  agreementStudyLevels?: number[]
  agreementFeatures?: number[]
  institutions: Omit<InstitutionSummary, 'matchingAgreementIds'>[]
  queries: ExplorerQuery[]
}

export interface InstitutionDetails extends Institution {
  datasetVersion: string
}

export interface ExchangeQuery {
  academicYear: string
  studyField: string | null
  status: 'success' | 'error' | 'pending'
  collectedAt: string
  matches: { institutionId: string; agreementIds: string[]; method?: string; sourceRef?: string }[]
}

export interface ExchangeData {
  runId: string
  academicYears: string[]
  studyFields: string[]
  collectedAt: string
  sourceUrl: string
  coverage: ExplorerIndex['coverage']
  queries: ExchangeQuery[]
}

export interface Dataset {
  exchange?: ExchangeData
  institutions: Institution[]
  generatedAt: string
  stats: unknown
}

export interface SummaryStats {
  totalInstitutions: number
  withAgreements: number
  withCoordinates: number
  totalAgreements: number
  totalCountries: number
  continents: Record<string, number>
  topCountries: { country: string; count: number }[]
}
