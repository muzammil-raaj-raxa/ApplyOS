import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { makeJob } from '../../test/fixtures'
import { mockApi, renderApp } from '../../test/helpers'

const jobs = { 'GET /api/jobs': { total: 1, items: [makeJob()] } }

describe('Shell', () => {
  it('has the dock with every place you can go', async () => {
    mockApi(jobs)
    renderApp('/')
    const dock = screen.getByRole('navigation', { name: 'Main' })
    expect(within(dock).getByRole('link', { name: 'Today' })).toBeInTheDocument()
    expect(within(dock).getByRole('link', { name: 'Jobs' })).toBeInTheDocument()
    expect(within(dock).getByRole('link', { name: 'Sources' })).toBeInTheDocument()
    expect(within(dock).getByRole('link', { name: 'Today' })).toHaveAttribute('aria-current', 'page')
  })

  it('moves between pages from the dock', async () => {
    mockApi(jobs)
    renderApp('/')
    await userEvent.click(screen.getByRole('link', { name: 'Jobs' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Jobs' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Sources' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Sources' })).toBeInTheDocument()
  })

  it('sends unknown addresses to Today', async () => {
    mockApi(jobs)
    renderApp('/nowhere')
    expect(screen.getByRole('link', { name: 'Today' })).toHaveAttribute('aria-current', 'page')
  })

  it('opens the command palette with Ctrl+K and closes it with Escape', async () => {
    mockApi(jobs)
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    expect(await screen.findByRole('dialog', { name: 'Commands' })).toBeInTheDocument()
    expect(screen.getByText('Go to Jobs')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Commands' })).not.toBeInTheDocument())
  })

  it('filters commands as you type and runs the highlighted one', async () => {
    const api = mockApi(jobs)
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    await userEvent.type(await screen.findByLabelText('Command'), 'saved{Enter}')
    expect(await screen.findByRole('heading', { level: 1, name: 'Jobs' })).toBeInTheDocument()
    await waitFor(() => expect(api.called('GET', '/api/jobs').some((c) => c.search.get('decision') === 'saved')).toBe(true))
  })

  it('turns free text into a job search', async () => {
    const api = mockApi(jobs)
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    await userEvent.type(await screen.findByLabelText('Command'), 'swift')
    expect(screen.getByText('Search jobs for "swift"')).toBeInTheDocument()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(api.called('GET', '/api/jobs').some((c) => c.search.get('q') === 'swift')).toBe(true), { timeout: 2000 })
  })

  it('moves the highlight with the arrow keys', async () => {
    mockApi(jobs)
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    await screen.findByLabelText('Command')
    await userEvent.keyboard('{ArrowDown}{Enter}')
    expect(await screen.findByRole('heading', { level: 1, name: 'Jobs' })).toBeInTheDocument()
  })

  it('runs real actions from the palette', async () => {
    const api = mockApi({
      ...jobs,
      'POST /api/jobs/search': { fetched: 0, new: 0, relevant: 0, filtered_out: 0, already_known: 0, cross_source_duplicates: 0, parse_failures: 0, errors: [] },
    })
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    await userEvent.type(await screen.findByLabelText('Command'), 'find{Enter}')
    await waitFor(() => expect(api.called('POST', '/api/jobs/search')).toHaveLength(1))
  })

  it('says when no command matches', async () => {
    mockApi(jobs)
    renderApp('/')
    await userEvent.keyboard('{Control>}k{/Control}')
    await userEvent.type(await screen.findByLabelText('Command'), '   ')
    expect(screen.getByText('Go to Today')).toBeInTheDocument()
  })

  it('the status orb explains what needs fixing', async () => {
    mockApi(jobs)
    renderApp('/')
    await userEvent.click(screen.getByRole('button', { name: 'System status' }))
    const popover = await screen.findByRole('dialog', { name: 'System status' })
    await waitFor(() => expect(popover).toHaveTextContent('Running, with one thing to fix'))
    expect(popover).toHaveTextContent('Not running, or the model in OLLAMA_MODEL is not installed.')
  })

  it('the status orb says plainly when the backend is down', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')))
    renderApp('/')
    await userEvent.click(screen.getByRole('button', { name: 'System status' }))
    const popover = await screen.findByRole('dialog', { name: 'System status' })
    await waitFor(() => expect(popover).toHaveTextContent('Needs attention'))
    expect(popover).toHaveTextContent('./scripts/start.sh')
  })
})
