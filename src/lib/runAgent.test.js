import { describe, expect, it } from 'vitest'
import { parseAgentResult } from './runAgent.js'

describe('runAgent parse', () => {
  it('parses bare JSON options', () => {
    const r = parseAgentResult(
      '{"options":[{"id":"R0001","title":"Acarajé","subtitle":"Brazil — Core","score":4}],"rationale":"ok"}'
    )
    expect(r.options).toHaveLength(1)
    expect(r.options[0].id).toBe('R0001')
    expect(r.rationale).toBe('ok')
  })

  it('strips markdown fences', () => {
    const r = parseAgentResult('```json\n{"options":[],"rationale":"none"}\n```')
    expect(r.options).toEqual([])
    expect(r.rationale).toBe('none')
  })
})
