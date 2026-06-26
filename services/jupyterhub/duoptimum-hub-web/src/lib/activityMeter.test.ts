import { describe, it, expect } from 'vitest'
import { litBars, meterTone } from './activityMeter'

describe('litBars', () => {
  it('lights EXACTLY zero bars for zero activity', () => {
    expect(litBars(0)).toBe(0)
  })
  it('clamps negative to zero bars', () => {
    expect(litBars(-5)).toBe(0)
  })
  it('lights at least one bar for any positive value', () => {
    expect(litBars(1)).toBe(1)
    expect(litBars(9)).toBe(1)
  })
  it('scales 0-100 across five bars and caps at five', () => {
    expect(litBars(20)).toBe(1)
    expect(litBars(50)).toBe(3)
    expect(litBars(100)).toBe(5)
    expect(litBars(150)).toBe(5)
  })
})

describe('meterTone', () => {
  it('zero bars -> no tone (empty meter)', () => {
    expect(meterTone(0)).toBe('')
  })
  it('one bar -> low (pale red)', () => {
    expect(meterTone(1)).toBe('low')
  })
  it('two or three bars -> idle (orange)', () => {
    expect(meterTone(2)).toBe('idle')
    expect(meterTone(3)).toBe('idle')
  })
  it('four or five bars -> default (no class)', () => {
    expect(meterTone(4)).toBe('')
    expect(meterTone(5)).toBe('')
  })
})
