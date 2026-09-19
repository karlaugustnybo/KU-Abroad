import { describe, expect, test } from 'bun:test'
import { selectInstitutions, validateFilters } from './exchange'
import type { ExplorerIndex } from './types'

const index: ExplorerIndex = {
  version: 'test', generatedAt: '2026-09-19T00:00:00Z', sourceUrl: 'https://example.com',
  coverage: { expectedQueries: 2, successfulQueries: 1, status: 'incomplete' },
  academicYears: ['2026/2027'], studyFields: ['Biology'], agreementIds: ['a1', 'a2', 'a3'], gradeRequirements: [7, 0, -1],
  programs: ['Erasmus student', 'Bilateral exchange student'], studyLevels: ['bachelor', 'master'],
  agreementPrograms: ['Erasmus student', 'Bilateral exchange student', 'Erasmus student'],
  agreementPlaces: [2, 6, 1], agreementStudyLevels: [1, 3, 2], agreementFeatures: [3, 6, 1],
  institutions: [
    { id: 'one', name: 'Alpha University', country: 'France', city: 'Paris', continent: 'Europe', lat: 48, lon: 2, agreementCount: 2, reportCount: 0, cooperationCount: 0, multilateralCount: 0, agreementIds: [0, 1] },
    { id: 'two', name: 'Beta College', country: 'Japan', city: 'Tokyo', continent: 'Asia', agreementCount: 1, reportCount: 0, cooperationCount: 0, multilateralCount: 0, agreementIds: [2] },
    { id: 'three', name: 'Gamma Institute', country: 'France', city: 'Lyon', continent: 'Europe', agreementCount: 1, reportCount: 0, cooperationCount: 0, multilateralCount: 0, agreementIds: [0] },
  ],
  queries: [{ academicYear: '2026/2027', studyField: 'Biology', status: 'success', collectedAt: '2026-09-19T00:00:00Z', matches: [[0, [1]], [2, [0]]] }],
}

describe('explorer filtering', () => {
  test('preserves exact agreement membership', () => {
    const filters = validateFilters({ academicYear: '2026/2027', studyField: 'Biology' })
    const result = selectInstitutions(index, filters)
    expect(result.institutions.map(institution => [institution.id, institution.matchingAgreementIds])).toEqual([['one', [1]], ['three', [0]]])
  })

  test('combines query, location and exchange filters', () => {
    const filters = validateFilters({ academicYear: '2026/2027', studyField: 'Biology', continent: 'Europe', country: 'France', query: 'Lyon' })
    expect(selectInstitutions(index, filters).institutions.map(institution => institution.id)).toEqual(['three'])
  })

  test('distinguishes unavailable verified data from a valid empty result', () => {
    expect(selectInstitutions(index, validateFilters({ academicYear: '2027/2028' })).status).toBe('unavailable')
    const validEmpty = selectInstitutions(index, validateFilters({ academicYear: '2026/2027', studyField: 'Biology', query: 'missing' }))
    expect(validEmpty.status).toBe('available')
    expect(validEmpty.institutions).toHaveLength(0)
  })

  test('normalizes invalid URL values and requires a year for study field', () => {
    expect(validateFilters({ page: '-4', sort: 'unknown', direction: 'sideways', studyField: 'Biology' })).toEqual({
      query: '', continent: '', country: '', academicYear: '', studyField: '', program: '', studyLevel: '', minPlaces: '',
      languageInfo: '', housingInfo: '', scholarshipInfo: '', maxGrade: '', gradeUnknown: '', sort: 'name', direction: 'asc', page: 1, selected: '',
    })
    expect(validateFilters({ maxGrade: '99' }).maxGrade).toBe('')
    expect(validateFilters({ maxGrade: '0' }).maxGrade).toBe('')
    expect(validateFilters({ maxGrade: '7.5' }).maxGrade).toBe('7.5')
    expect(validateFilters({ gradeUnknown: 'exclude' }).gradeUnknown).toBe('exclude')
    expect(validateFilters({ gradeUnknown: 'weird' }).gradeUnknown).toBe('')
  })

  test('applies the maximum grade requirement', () => {
    expect(selectInstitutions(index, validateFilters({ maxGrade: '7' })).institutions.map(institution => institution.id)).toEqual(['one', 'two', 'three'])
    expect(selectInstitutions(index, validateFilters({ maxGrade: '6.5' })).institutions.map(institution => institution.id)).toEqual(['one', 'two'])
    expect(selectInstitutions(index, validateFilters({ maxGrade: '6.5', gradeUnknown: 'exclude' })).institutions.map(institution => institution.id)).toEqual(['one'])
    expect(selectInstitutions(index, validateFilters({ maxGrade: '7', gradeUnknown: 'exclude' })).institutions.map(institution => institution.id)).toEqual(['one', 'three'])
  })

  test('grade requirement respects verified agreement matches', () => {
    const filters = validateFilters({ academicYear: '2026/2027', studyField: 'Biology', maxGrade: '6.5' })
    expect(selectInstitutions(index, filters).institutions.map(institution => institution.id)).toEqual(['one'])
  })

  test('combines agreement metadata filters and narrows matching agreements', () => {
    const result = selectInstitutions(index, validateFilters({
      program: 'Bilateral exchange student', studyLevel: 'master', minPlaces: '5', housingInfo: 'yes', scholarshipInfo: 'yes',
    }))
    expect(result.institutions.map(institution => [institution.id, institution.matchingAgreementIds])).toEqual([['one', [1]]])
  })

  test('applies agreement filters after verified academic matches', () => {
    const result = selectInstitutions(index, validateFilters({ academicYear: '2026/2027', studyField: 'Biology', studyLevel: 'master' }))
    expect(result.institutions.map(institution => [institution.id, institution.matchingAgreementIds])).toEqual([['one', [1]]])
  })

  test('retains institutions without coordinates in table results', () => {
    expect(selectInstitutions(index, validateFilters({ query: 'Gamma' })).institutions[0].lat).toBeUndefined()
  })
})
