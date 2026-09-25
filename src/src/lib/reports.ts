import reportCounts from '~/assets/data/report-counts.json'

export interface ReportSummary {
  id: string
  institutionId: string
  academicYear: string | null
  studyField: string | null
  questionnaireType: string | null
}

export interface ReportQuestion {
  question: string
  answer: string | null
  links: string[]
}

export interface ReportDetail extends ReportSummary {
  institutionName: string
  sections: { title: string; questions: ReportQuestion[] }[]
}

const base = `/reports/${reportCounts.runId}`
const institutionIdPattern = /^inst-[a-f0-9]{24}$/
const reportIdPattern = /^report-[a-f0-9]{24}$/

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error(`Report data unavailable (${response.status})`)
  return response.json() as Promise<T>
}

const listingRequests = new Map<string, Promise<ReportSummary[]>>()

export function loadInstitutionReports(institutionId: string): Promise<ReportSummary[]> {
  if (!institutionIdPattern.test(institutionId)) return Promise.reject(new Error('Invalid institution ID'))
  const cached = listingRequests.get(institutionId)
  if (cached) return cached
  const request = fetchJson<ReportSummary[]>(`${base}/institutions/${institutionId}.json`)
    .then(value => {
      if (!Array.isArray(value) || value.some(item => item.institutionId !== institutionId)) {
        throw new Error('Invalid report list')
      }
      return value
    })
    .catch(error => {
      listingRequests.delete(institutionId)
      throw error
    })
  listingRequests.set(institutionId, request)
  return request
}

export async function loadReport(reportId: string): Promise<ReportDetail> {
  if (!reportIdPattern.test(reportId)) throw new Error('Invalid report ID')
  const value = await fetchJson<ReportDetail>(`${base}/items/${reportId}.json`)
  if (value.id !== reportId || !institutionIdPattern.test(value.institutionId) || !Array.isArray(value.sections)) {
    throw new Error('Invalid report data')
  }
  return value
}

export function safeReportLink(value: string): string | null {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}
