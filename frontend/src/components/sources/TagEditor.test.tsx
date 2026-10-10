import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { TagEditor } from './TagEditor'

function Harness({ initial = ['stripe'], validate }: { initial?: string[]; validate?: (v: string) => string | null }) {
  const [values, setValues] = useState(initial)
  return <TagEditor label="Greenhouse" values={values} onChange={setValues} validate={validate} />
}

describe('TagEditor', () => {
  it('adds a chip on Enter and on comma', async () => {
    render(<Harness />)
    const input = screen.getByLabelText('Greenhouse')
    await userEvent.type(input, 'airbnb{Enter}')
    await userEvent.type(input, 'figma,')
    expect(screen.getByText('airbnb')).toBeInTheDocument()
    expect(screen.getByText('figma')).toBeInTheDocument()
    expect(input).toHaveValue('')
  })

  it('adds what you typed when you click away', async () => {
    render(<Harness />)
    await userEvent.type(screen.getByLabelText('Greenhouse'), 'linear')
    await userEvent.tab()
    expect(screen.getByText('linear')).toBeInTheDocument()
  })

  it('refuses a duplicate, ignoring case', async () => {
    render(<Harness />)
    await userEvent.type(screen.getByLabelText('Greenhouse'), 'STRIPE{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('"STRIPE" is already in the list.')
    expect(screen.getAllByText(/stripe/i)).toHaveLength(2) // the chip and the message
  })

  it('shows the validation message and keeps the text so it can be fixed', async () => {
    render(<Harness validate={(v) => (v.includes(' ') ? 'No spaces, please.' : null)} />)
    const input = screen.getByLabelText('Greenhouse')
    await userEvent.type(input, 'two words{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('No spaces, please.')
    expect(input).toHaveValue('two words')
  })

  it('removes a chip with its button', async () => {
    render(<Harness initial={['stripe', 'airbnb']} />)
    await userEvent.click(screen.getByRole('button', { name: 'Remove stripe' }))
    expect(screen.queryByText('stripe')).not.toBeInTheDocument()
    expect(screen.getByText('airbnb')).toBeInTheDocument()
  })

  it('Backspace on an empty field removes the last chip', async () => {
    render(<Harness initial={['stripe', 'airbnb']} />)
    await userEvent.click(screen.getByLabelText('Greenhouse'))
    await userEvent.keyboard('{Backspace}')
    expect(screen.queryByText('airbnb')).not.toBeInTheDocument()
    expect(screen.getByText('stripe')).toBeInTheDocument()
  })
})
