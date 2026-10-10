import { mockApi } from '../test/helpers'
import { api, ApiError, describeDetail, jobsQuery } from './api'
import { DEFAULT_FILTERS } from './filters'

describe('describeDetail', () => {
  it('uses string details as they are', () => {
    expect(describeDetail('No AI provider available', 'fallback')).toBe('No AI provider available')
  })
  it('turns FastAPI validation lists into one sentence', () => {
    const detail = [{ loc: ['body', 'companies'], msg: "unknown source 'workday'" }, { loc: ['body', 'minimum_score'], msg: 'too big' }]
    expect(describeDetail(detail, 'fallback')).toBe("companies: unknown source 'workday'. minimum_score: too big")
  })
  it('falls back when there is nothing usable', () => {
    expect(describeDetail(undefined, 'fallback')).toBe('fallback')
    expect(describeDetail([], 'fallback')).toBe('fallback')
  })
})

describe('requests', () => {
  it('explains an unreachable backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed to fetch')))
    await expect(api.stats()).rejects.toMatchObject({ status: 0, detail: expect.stringContaining('./scripts/start.sh') })
  })

  it('surfaces the backend detail and status', async () => {
    mockApi({ 'POST /api/jobs/9/analyze': () => new Response(JSON.stringify({ detail: 'no AI provider available' }), { status: 503 }) })
    const error = await api.scoreJob(9, false).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 503, detail: 'no AI provider available' })
  })

  it('gives a generic message when the error body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 500 })))
    await expect(api.stats()).rejects.toMatchObject({ status: 500, detail: 'The backend answered 500.' })
  })
})

describe('jobsQuery', () => {
  const params = (patch = {}, offset = 0) => new URLSearchParams(jobsQuery({ ...DEFAULT_FILTERS, ...patch }, offset))

  it('sends sensible defaults', () => {
    const p = params()
    expect(p.get('sort')).toBe('score')
    expect(p.get('limit')).toBe('30')
    expect(p.get('offset')).toBe('0')
    expect(p.has('decision')).toBe(false)
    expect(p.has('min_score')).toBe(false)
  })

  it('maps every filter to the backend parameter', () => {
    const p = params({ q: ' swift ', status: 'saved', fit: '80', where: 'remote', sort: 'new', all: true }, 60)
    expect(Object.fromEntries(p)).toMatchObject({
      q: 'swift', decision: 'saved', min_score: '80', workplace: 'remote', sort: 'newest', include_filtered: 'true', offset: '60',
    })
  })

  it('maps "not scored" to scored=false instead of a minimum', () => {
    const p = params({ fit: 'unscored' })
    expect(p.get('scored')).toBe('false')
    expect(p.has('min_score')).toBe(false)
  })

  it('maps rejected and all statuses', () => {
    expect(params({ status: 'rejected' }).get('decision')).toBe('rejected')
    expect(params({ status: 'all' }).get('decision')).toBe('all')
  })
})
