import { describe, expect, it } from 'vitest'
import { dataOnlyLine, percentileNote, rankPhaseRows, renderPhaseRow } from './phaseRender.js'

const FRAMED = {
  dish_component_a: 'ROSEMARY',
  dish_component_b: 'KOREAN MINT',
  render_mode: 'framed',
  frame_id: 'fat_phase_phenol_terpene_carrier',
  sentence: 'Both sit in the fat phase. Guaiacols and terpenes are both fat-soluble.',
  bucket: 'fat_phase',
  a_group: 'Hydrocarbons',
  b_group: 'Phenols',
  a_group_share: 0.34,
  b_group_share: 0.27,
  a_group_percentile: 95.0,
  b_group_percentile: 92.0,
}

const DATA_ONLY = {
  dish_component_a: 'ACEROLA (Malpighia)',
  dish_component_b: 'NECTARINE',
  render_mode: 'data_only',
  frame_id: null,
  bucket: 'fat_leaning',
  a_group: 'Esters',
  b_group: 'Esters',
  a_group_share: 0.3022,
  b_group_share: 0.3359,
  a_group_percentile: 78.8,
  b_group_percentile: 82.8,
  a_group_baseline_median: 0.1303,
}

describe('phase render path', () => {
  it('renders an authored sentence verbatim', () => {
    const r = renderPhaseRow(FRAMED)
    expect(r.mode).toBe('framed')
    expect(r.sentence).toBe(FRAMED.sentence)
  })

  it('NEVER supplies a sentence for a data_only row', () => {
    // The anchor this protects: a generic default would leave the chef an
    // alert they cannot interpret, which is worse than showing nothing.
    const r = renderPhaseRow(DATA_ONLY)
    expect(r.mode).toBe('data_only')
    expect(r.sentence).toBeNull()
  })

  it('treats a framed row with no sentence as data_only', () => {
    const r = renderPhaseRow({ ...FRAMED, sentence: null })
    expect(r.mode).toBe('data_only')
    expect(r.sentence).toBeNull()
  })

  it('states the facts for a data_only row without asserting a consequence', () => {
    const line = dataOnlyLine(renderPhaseRow(DATA_ONLY))
    expect(line).toContain('30%')
    expect(line).toContain('esters')
    expect(line).toContain('Acerola')
  })

  it('gives no data line when there are no numbers', () => {
    const bare = { ...DATA_ONLY, a_group_share: null, b_group_share: null }
    expect(dataOnlyLine(renderPhaseRow(bare))).toBeNull()
  })

  it('names a percentile only when it is genuinely unusual', () => {
    expect(percentileNote(95)).toBe('top 5% of corpus')
    expect(percentileNote(78.8)).toBeNull()
    expect(percentileNote(null)).toBeNull()
  })

  it('ranks framed rows above data_only', () => {
    const ranked = rankPhaseRows([DATA_ONLY, FRAMED])
    expect(ranked[0].mode).toBe('framed')
  })
})
