import { bandFor, DIMENSIONS, formatSalary, plural, relativeTime, sourceName } from './format'

describe('bandFor', () => {
  it.each([
    [100, 'excellent'],
    [90, 'excellent'],
    [89, 'strong'],
    [80, 'strong'],
    [79, 'worth'],
    [70, 'worth'],
    [69, 'weak'],
    [60, 'weak'],
    [59, 'poor'],
    [0, 'poor'],
  ])('scores %i as %s', (score, key) => {
    expect(bandFor(score).key).toBe(key)
  })

  it('glows only for strong fits and better', () => {
    expect(bandFor(80).glow).toBe(true)
    expect(bandFor(79).glow).toBe(false)
  })
})

describe('DIMENSIONS', () => {
  it('weights add up to 100, like the backend', () => {
    expect(DIMENSIONS.reduce((sum, dim) => sum + dim.weight, 0)).toBe(100)
  })
  it('lists seven parts in the backend order', () => {
    expect(DIMENSIONS.map((d) => d.key)).toEqual(['technical', 'experience', 'seniority', 'location', 'authorization', 'role', 'domain'])
  })
})

describe('formatSalary', () => {
  it('formats ranges with a currency symbol', () => {
    expect(formatSalary(150000, 190000, 'USD')).toBe('$150k to $190k')
    expect(formatSalary(70000, 90000, 'GBP')).toBe('£70k to £90k')
  })
  it('handles a single value, unknown currencies and no salary', () => {
    expect(formatSalary(120000, null, 'USD')).toBe('$120k')
    expect(formatSalary(100000, 120000, 'PKR')).toBe('PKR 100k to PKR 120k')
    expect(formatSalary(null, null, 'USD')).toBeNull()
  })
})

describe('relativeTime', () => {
  const now = Date.parse('2026-10-09T12:00:00Z')
  it('describes recent and older times', () => {
    expect(relativeTime('2026-10-09T11:59:40Z', now)).toBe('just now')
    expect(relativeTime('2026-10-09T11:30:00Z', now)).toBe('30 min ago')
    expect(relativeTime('2026-10-09T09:00:00Z', now)).toBe('3 h ago')
    expect(relativeTime('2026-10-07T12:00:00Z', now)).toBe('2 d ago')
  })
  it('treats timestamps without a zone as UTC, like the backend sends them', () => {
    expect(relativeTime('2026-10-09T09:00:00', now)).toBe('3 h ago')
  })
  it('returns nothing for missing or broken input', () => {
    expect(relativeTime(null, now)).toBe('')
    expect(relativeTime('not a date', now)).toBe('')
  })
})

describe('small helpers', () => {
  it('plural and sourceName', () => {
    expect(plural(1, 'job')).toBe('job')
    expect(plural(2, 'job')).toBe('jobs')
    expect(plural(2, 'source had a problem', 'sources had problems')).toBe('sources had problems')
    expect(sourceName('greenhouse')).toBe('Greenhouse')
  })
})
