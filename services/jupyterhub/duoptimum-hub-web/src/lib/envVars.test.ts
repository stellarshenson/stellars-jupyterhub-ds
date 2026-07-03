import { describe, it, expect } from 'vitest'
import { isReservedEnvName, envNameError, envVarsHaveErrors } from './envVars'

const reserved = { names: ['DOCKER_HOST', 'JUPYTERLAB_TIMEZONE'], prefixes: ['JUPYTERHUB_', 'CPU_'] }

describe('isReservedEnvName', () => {
  it('flags an exact reserved name', () => {
    expect(isReservedEnvName('DOCKER_HOST', reserved)).toBe(true)
  })
  it('flags a reserved prefix', () => {
    expect(isReservedEnvName('JUPYTERHUB_API_TOKEN', reserved)).toBe(true)
    expect(isReservedEnvName('CPU_SHARES', reserved)).toBe(true)
  })
  it('allows a normal name', () => {
    expect(isReservedEnvName('MY_VAR', reserved)).toBe(false)
  })
  it('ignores surrounding whitespace', () => {
    expect(isReservedEnvName('  DOCKER_HOST  ', reserved)).toBe(true)
  })
  it('is false when no reserved set is supplied or name is blank', () => {
    expect(isReservedEnvName('DOCKER_HOST')).toBe(false)
    expect(isReservedEnvName('', reserved)).toBe(false)
  })
})

describe('envNameError', () => {
  it('accepts a valid unique non-reserved name', () => {
    expect(envNameError('MY_VAR', ['MY_VAR'], reserved)).toBeNull()
  })
  it('returns null for a blank row (dropped server-side)', () => {
    expect(envNameError('   ', ['   '], reserved)).toBeNull()
  })
  it('rejects an invalid name', () => {
    expect(envNameError('1BAD', ['1BAD'], reserved)).toMatch(/Invalid/)
    expect(envNameError('has space', ['has space'], reserved)).toMatch(/Invalid/)
  })
  it('rejects a reserved name', () => {
    expect(envNameError('JUPYTERHUB_X', ['JUPYTERHUB_X'], reserved)).toMatch(/Reserved/)
  })
  it('rejects a duplicate name', () => {
    expect(envNameError('A', ['A', 'A'], reserved)).toMatch(/Duplicate/)
  })
})

describe('envVarsHaveErrors', () => {
  it('is false for a clean set', () => {
    expect(envVarsHaveErrors([{ name: 'A' }, { name: 'B' }], reserved)).toBe(false)
  })
  it('is false with blank rows only', () => {
    expect(envVarsHaveErrors([{ name: '' }, { name: '  ' }], reserved)).toBe(false)
  })
  it('is true when a row is reserved / invalid / duplicate', () => {
    expect(envVarsHaveErrors([{ name: 'DOCKER_HOST' }], reserved)).toBe(true)
    expect(envVarsHaveErrors([{ name: '1BAD' }], reserved)).toBe(true)
    expect(envVarsHaveErrors([{ name: 'A' }, { name: 'A' }], reserved)).toBe(true)
  })
})
