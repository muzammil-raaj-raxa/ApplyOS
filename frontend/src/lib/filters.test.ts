import { applyFilters, DEFAULT_FILTERS, hasActiveFilters, parseFilters } from './filters'

const params = (query: string) => new URLSearchParams(query)

describe('parseFilters', () => {
  it('uses defaults for an empty address', () => {
    expect(parseFilters(params(''))).toEqual(DEFAULT_FILTERS)
  })
  it('reads valid values and ignores nonsense', () => {
    expect(parseFilters(params('status=saved&fit=80&where=remote&sort=new&all=1&q=swift'))).toEqual({
      q: 'swift', status: 'saved', fit: '80', where: 'remote', sort: 'new', all: true,
    })
    expect(parseFilters(params('status=banana&fit=12&where=moon&sort=random'))).toEqual(DEFAULT_FILTERS)
  })
})

describe('applyFilters', () => {
  it('writes changes and drops values that equal the default', () => {
    const next = applyFilters(params('fit=80'), { where: 'remote', fit: 'any' })
    expect(next.toString()).toBe('where=remote')
  })
  it('keeps unrelated parameters such as the open job', () => {
    const next = applyFilters(params('job=7'), { status: 'saved' })
    expect(next.get('job')).toBe('7')
    expect(next.get('status')).toBe('saved')
  })
  it('clears the search text and the include-filtered flag', () => {
    expect(applyFilters(params('q=abc&all=1'), { q: '', all: false }).toString()).toBe('')
  })
})

describe('hasActiveFilters', () => {
  it('is false for defaults and true when anything differs', () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false)
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, fit: '90' })).toBe(true)
  })
})
