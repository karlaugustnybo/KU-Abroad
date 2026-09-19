import { describe, expect, test } from 'bun:test'
import { aggregateGradeRequirement, encodeGradeRequirement, meetsRequirement, parseGradeRequirement } from './grade'

describe('grade requirement parsing', () => {
  test('reads Danish scale minimums', () => {
    expect(parseGradeRequirement('7 (Danish scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('7\xa0(Danish scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('4 on the Danish scale')).toEqual({ kind: 'minimum', value: 4 })
    expect(parseGradeRequirement('6,5')).toEqual({ kind: 'minimum', value: 6.5 })
    expect(parseGradeRequirement('7.0 (according to the Danish grading scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('a minimum of 8')).toEqual({ kind: 'minimum', value: 8 })
    expect(parseGradeRequirement('>7 (Danish scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('GPA of min. 7 (on the Danish scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('Undergraduate students should have a GPA of at least 9 (Danish scale) to get accepted as exchange students at CALTECH.')).toEqual({ kind: 'minimum', value: 9 })
    expect(parseGradeRequirement('Minimum 7.2 on the Danish 7-point scale (equivalent to a GPA of 3.1 on a 4-point scale).')).toEqual({ kind: 'minimum', value: 7.2 })
    expect(parseGradeRequirement('The host university requires a GPA minimum of 7.0 (Danish 7-point scale).')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement("7 (Danish scale) equivalent to 3.00 (American scale out of 4.0).")).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('7 (Danish scale) *Law: 8.5 (Danish scale)')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('10 (Danish scale) Law students apply for undergraduate (JD studies) - minimum GPA: 9')).toEqual({ kind: 'minimum', value: 10 })
    expect(parseGradeRequirement("'Studentereksamensbevis' with an overall grade of 7.3 - 7.9 or above. (12 point scale) and a grade in English of 7 or above.")).toEqual({ kind: 'minimum', value: 7.3 })
    expect(parseGradeRequirement('7 (Danish grading scale) with no grades below 4. Students with grades below 7 may find it difficult to secure modules.')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('GPA requirement is 4.8 on the Danish national grading scale. If you are appointed a spot for this agreement with a GPA higher than 4.8 but your GPA gets scaled down to a lower GPA than 4.8 in the period until the host universitys application deadline, there is a risk that your application will be rejected by the host university and your exchange stay will not be possible.')).toEqual({ kind: 'minimum', value: 4.8 })
  })

  test('recognizes agreements without grade requirements', () => {
    const texts = [
      'N/A', 'NA', 'n/a', 'None', 'No requirements', 'No requirements.', 'No GPA requirement', 'No GPA requirements.',
      'No stated requirement', 'No specified requirements', 'No specified requirements. Good academic standing',
      'Not applicable', 'All students can apply', 'The host university has no minimum GPA requirement.',
      'N/A - the agreement is only open to BA students',
      'No specified requirements. Students are normally expected to have completed 2 years of undergraduate study by the start of the exchange, and be in good academic standing at their home institution.',
      'All students can apply. Admission at UNIS depends on how many students applying for the program at UNIS. If more students than places apply students with the highest grades will be admitted.',
    ]
    for (const text of texts) expect(parseGradeRequirement(text)).toEqual({ kind: 'none' })
  })

  test('a stated requirement wins over a no-requirement phrase', () => {
    expect(parseGradeRequirement('No requirements except for Engineering which requires a GPA of 7.')).toEqual({ kind: 'minimum', value: 7 })
    expect(parseGradeRequirement('For students on mandatory stay No GPA requirement All other students applying All other students must have a cumulative grade point average of 7.0 on the Danish grading scale. If you are appointed a spot for this agreement with a GPA higher than 7.0 but your GPA gets scaled down to a lower GPA than 7.0 in the period until the host universitys application deadline, your application may be rejected by the host university and your exchange stay will not be possible.')).toEqual({ kind: 'minimum', value: 7 })
  })

  test('foreign grading scales stay unknown', () => {
    const texts = [
      'Desired grade point average: ≤ 2.0 (referring to Austrian Grade 2.0)',
      'For graduate and PhD students minimum CGPA of 3.00/4.00',
      'For undergraduate students minimum CGPA of 2.50/4.00',
      '*Law students must have a min. GPA of 8.0 on ECTS scale *Students applying for the Faculty of Business and Economics must have a minimum grade average of B average/CGPA 3.0/ Satisfactory level (aprox. 7.0 on ECTS scale)',
      'You must check the GPA requirement for each school, however most schools demand a GPA of 3.0 of 4.0 = approx. minimum 7 (C) on the ECTS scale.',
      'Students must have already completed their first year of study at their home university in order to attend the exchange programme at CityU. Students are expected to be in good academic standing at their home institution.',
      'Not open to undergraduate students',
      'Some faculties/departments might have specific requirements.',
    ]
    for (const text of texts) expect(parseGradeRequirement(text)).toEqual({ kind: 'unknown' })
  })

  test('URLs never become grades', () => {
    expect(parseGradeRequirement('For students going on mandatory stay please go to KUnet to find more information about course load: https://kunet.ku.dk/studie/sider/RedirectToTopic.aspx?topicId=315959c7-23f2-45a1-9b7f-6d7f52f40e34#144411_noPictureOnTop_content (https://kunet.ku.dk/studie/sider/RedirectToTopic.aspx?topicId=315959c7-23f2-45a1-9b7f-6d7f52f40e34#144411_noPictureOnTop_content)')).toEqual({ kind: 'unknown' })
    expect(parseGradeRequirement('')).toEqual({ kind: 'unknown' })
    expect(parseGradeRequirement(undefined)).toEqual({ kind: 'unknown' })
  })

  test('aggregates fields conservatively', () => {
    expect(aggregateGradeRequirement({ 'GPA for undergraduate admission': '7 (Danish scale)', 'GPA for graduate admission': 'N/A' })).toEqual({ kind: 'minimum', value: 7 })
    expect(aggregateGradeRequirement({ 'GPA for undergraduate admission': '4 (Danish scale)', 'GPA for graduate admission': '7 (Danish scale)' })).toEqual({ kind: 'minimum', value: 7 })
    expect(aggregateGradeRequirement({ 'GPA for undergraduate admission': 'N/A', 'GPA for graduate admission': 'None' })).toEqual({ kind: 'none' })
    expect(aggregateGradeRequirement({})).toEqual({ kind: 'unknown' })
    expect(aggregateGradeRequirement({ 'Grade requirements': 'GPA requirement is 4.8 on the Danish national grading scale.' })).toEqual({ kind: 'minimum', value: 4.8 })
  })

  test('encodes and checks eligibility', () => {
    expect(encodeGradeRequirement({ kind: 'none' })).toBe(0)
    expect(encodeGradeRequirement({ kind: 'unknown' })).toBe(-1)
    expect(encodeGradeRequirement({ kind: 'minimum', value: 7.5 })).toBe(7.5)
    expect(meetsRequirement(0, 4, false)).toBe(true)
    expect(meetsRequirement(7, 7.5, false)).toBe(true)
    expect(meetsRequirement(7.5, 7, false)).toBe(false)
    expect(meetsRequirement(-1, 7, false)).toBe(false)
    expect(meetsRequirement(-1, 7, true)).toBe(true)
    expect(meetsRequirement(undefined, 7, true)).toBe(true)
    expect(meetsRequirement(7.2, 7.5, false)).toBe(true)
  })
})
