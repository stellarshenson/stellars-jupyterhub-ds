import { describe, it, expect } from 'vitest'
import { hasVolumes } from './volumes'
import type { Volume } from '../services/types'

describe('hasVolumes', () => {
  it('returns false when the user has no volumes (gates the Manage-volumes action OFF)', () => {
    expect(hasVolumes([])).toBe(false)
    expect(hasVolumes(undefined)).toBe(false)
    expect(hasVolumes(null)).toBe(false)
  })
  it('returns true when the user has one or more volumes', () => {
    expect(hasVolumes([{} as Volume])).toBe(true)
    expect(hasVolumes([{} as Volume, {} as Volume])).toBe(true)
  })
})
