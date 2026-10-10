import { render, screen, waitFor } from '@testing-library/react'
import { setReducedMotion } from '../../test/setup'
import { AnimatedNumber } from './AnimatedNumber'

describe('AnimatedNumber', () => {
  it('shows the value at once when the user prefers reduced motion', () => {
    render(<AnimatedNumber value={42} />)
    expect(screen.getByLabelText('42')).toHaveTextContent('42')
  })

  it('counts up to the value otherwise', async () => {
    setReducedMotion(false)
    render(<AnimatedNumber value={42} durationMs={60} />)
    await waitFor(() => expect(screen.getByLabelText('42')).toHaveTextContent('42'))
  })

  it('travels from the old value to the new one', async () => {
    setReducedMotion(false)
    const { rerender } = render(<AnimatedNumber value={10} durationMs={40} />)
    await waitFor(() => expect(screen.getByLabelText('10')).toHaveTextContent('10'))
    rerender(<AnimatedNumber value={25} durationMs={40} />)
    await waitFor(() => expect(screen.getByLabelText('25')).toHaveTextContent('25'))
  })
})
