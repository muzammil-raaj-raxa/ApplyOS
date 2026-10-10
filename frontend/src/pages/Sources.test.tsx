import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { searchProfile } from '../test/fixtures'
import { json, mockApi, renderApp } from '../test/helpers'

describe('Sources page', () => {
  it('shows what ApplyOS is set up to look for', async () => {
    mockApi({})
    renderApp('/sources')
    expect(await screen.findByText('iOS Engineer')).toBeInTheDocument()
    expect(screen.getByText('stripe')).toBeInTheDocument()
    expect(screen.getByText('ramp')).toBeInTheDocument()
    expect(screen.getByText('Principal')).toBeInTheDocument()
    expect(screen.getByText('2 companies across three job boards.', { exact: false })).toBeInTheDocument()
    expect(screen.getByLabelText('Minimum score for a strong fit')).toHaveValue('80')
  })

  it('shows nothing to save until you change something', async () => {
    mockApi({})
    renderApp('/sources')
    await screen.findByText('stripe')
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument()
  })

  it('saves a new company and keeps everything else, including display names', async () => {
    const api = mockApi({ 'PUT /api/search-profile': (_url: URL, init?: RequestInit) => JSON.parse(String(init?.body)) })
    renderApp('/sources')
    await screen.findByText('stripe')
    await userEvent.type(screen.getByLabelText('Greenhouse'), 'airbnb{Enter}')
    expect(await screen.findByText('You have unsaved changes.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.called('PUT', '/api/search-profile')).toHaveLength(1))
    const body = api.called('PUT', '/api/search-profile')[0].body as typeof searchProfile
    expect(body.companies.greenhouse).toEqual(['stripe', 'airbnb'])
    expect(body.companies.ashby).toEqual(['ramp'])
    expect(body.company_names).toEqual({ openai: 'OpenAI' })
    expect(await screen.findByText('Sources saved.')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument())
  })

  it('discards changes', async () => {
    mockApi({})
    renderApp('/sources')
    await screen.findByText('stripe')
    await userEvent.click(screen.getByRole('button', { name: 'Remove stripe' }))
    expect(screen.queryByText('stripe')).not.toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Discard' }))
    expect(await screen.findByText('stripe')).toBeInTheDocument()
  })

  it('rejects a company name that cannot be right, without marking the page changed', async () => {
    mockApi({})
    renderApp('/sources')
    await screen.findByText('stripe')
    await userEvent.type(screen.getByLabelText('Lever'), 'not a slug{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('Use only letters, numbers, dots, dashes and underscores')
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument()
  })

  it('changes the minimum score for a strong fit', async () => {
    const api = mockApi({ 'PUT /api/search-profile': (_url: URL, init?: RequestInit) => JSON.parse(String(init?.body)) })
    renderApp('/sources')
    await screen.findByText('stripe')
    fireEvent.change(screen.getByLabelText('Minimum score for a strong fit'), { target: { value: '90' } })
    await userEvent.click(await screen.findByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.called('PUT', '/api/search-profile')[0]?.body).toMatchObject({ minimum_score: 90 }))
  })

  it('shows the backend message when saving fails', async () => {
    mockApi({
      'PUT /api/search-profile': () => json({ detail: [{ loc: ['body', 'companies'], msg: "unknown source 'workday'" }] }, 422),
    })
    renderApp('/sources')
    await screen.findByText('stripe')
    await userEvent.type(screen.getByLabelText('Greenhouse'), 'airbnb{Enter}')
    await userEvent.click(await screen.findByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText("companies: unknown source 'workday'")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled()
  })

  it('asks you to save before finding jobs', async () => {
    mockApi({})
    renderApp('/sources')
    await screen.findByText('stripe')
    await userEvent.click(screen.getByRole('button', { name: 'Remove stripe' }))
    expect(screen.getByRole('button', { name: 'Find new jobs' })).toBeDisabled()
    expect(screen.getByText('Save your changes first.')).toBeInTheDocument()
  })

  it('shows an error with a retry when the profile cannot load', async () => {
    mockApi({ 'GET /api/search-profile': () => json({ detail: 'search profile file is damaged' }, 500) })
    renderApp('/sources')
    expect(await screen.findByText('search profile file is damaged')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
