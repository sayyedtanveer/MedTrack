import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { QueryProvider } from './QueryProvider'

describe('QueryProvider', () => {
  it('renders children without crashing', () => {
    const { getByText } = render(
      <QueryProvider>
        <div>hello</div>
      </QueryProvider>
    )

    expect(getByText('hello')).toBeTruthy()
  })
})
