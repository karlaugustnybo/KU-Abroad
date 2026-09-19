export type GradeRequirement =
  | { kind: 'none' }
  | { kind: 'minimum'; value: number }
  | { kind: 'unknown' }

export const GRADE_NONE = 0
export const GRADE_UNKNOWN = -1

const GRADE_FIELDS = [
  'GPA for undergraduate admission',
  'GPA for graduate admission',
  'Minimum GPA for admission',
  'Grade requirements',
]

const NONE_PATTERN = /no[^.\n]{0,30}requirement|\bnone\b|not applicable|\bn\/?a\b|all students can apply|no minimum/i
const SCALE_NOISE = /\d+(?:[.,]\d+)?\s*[-–]?\s*points?\s+(?:grading\s+|grade\s+)?scale/gi
const URL_NOISE = /https?:\/\/\S+/gi
const FOREIGN_SCALE = /ects|austrian|american|cgpa|us gpa/i
const UNIT_NOISE = /\d+(?:[.,]\d+)?\s*(?:years?|months?|weeks?|hours?|ects|credits?|%)/i
const FRACTION_NOISE = /^\s*(?:\/|of\b|out\s+of\b)\s*4(?:[.,]\d{1,2})?\b/i
const NUMBER_PATTERN = /\d+(?:[.,]\d+)?/g
const WINDOW = 36

export function parseGradeRequirement(text?: string | null): GradeRequirement {
  const cleaned = (text ?? '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').replace(URL_NOISE, ' ').replace(SCALE_NOISE, ' scale ').trim()
  if (!cleaned) return { kind: 'unknown' }
  const candidates: number[] = []
  for (const match of cleaned.matchAll(NUMBER_PATTERN)) {
    const value = Number(match[0].replace(',', '.'))
    const start = match.index ?? 0
    const end = start + match[0].length
    if (!(value > 0 && value <= 12)) continue
    if (UNIT_NOISE.test(cleaned.slice(start, end + 12))) continue
    if (FRACTION_NOISE.test(cleaned.slice(end, end + 12))) continue
    if (FOREIGN_SCALE.test(cleaned.slice(Math.max(0, start - WINDOW), end + WINDOW))) continue
    candidates.push(Math.round(value * 10) / 10)
  }
  if (!candidates.length) return NONE_PATTERN.test(cleaned) ? { kind: 'none' } : { kind: 'unknown' }
  if (NONE_PATTERN.test(cleaned)) return { kind: 'minimum', value: Math.max(...candidates) }
  return { kind: 'minimum', value: candidates[0] }
}

export function aggregateGradeRequirement(details?: Record<string, string> | null): GradeRequirement {
  const minimums: number[] = []
  let none = false
  for (const field of GRADE_FIELDS) {
    const parsed = parseGradeRequirement(details?.[field])
    if (parsed.kind === 'minimum') minimums.push(parsed.value)
    else if (parsed.kind === 'none') none = true
  }
  if (minimums.length) return { kind: 'minimum', value: Math.max(...minimums) }
  return none ? { kind: 'none' } : { kind: 'unknown' }
}

export function encodeGradeRequirement(requirement: GradeRequirement): number {
  if (requirement.kind === 'none') return GRADE_NONE
  if (requirement.kind === 'minimum') return Math.round(requirement.value * 10) / 10
  return GRADE_UNKNOWN
}

export function decodeGradeRequirement(code: number | undefined): GradeRequirement {
  if (code == null || code < 0) return { kind: 'unknown' }
  if (code === GRADE_NONE) return { kind: 'none' }
  return { kind: 'minimum', value: code }
}

export function meetsRequirement(code: number | undefined, average: number, includeUnknown: boolean): boolean {
  const requirement = decodeGradeRequirement(code)
  if (requirement.kind === 'none') return true
  if (requirement.kind === 'unknown') return includeUnknown
  return requirement.value <= average
}

export function formatGrade(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)
}
