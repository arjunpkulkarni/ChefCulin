import { llmChat } from '../api.js'

const MAX_ROUNDS = 6

/**
 * Shared tool-calling loop. Tools run in the browser; OpenAI is proxied via /api/llm/chat.
 *
 * @param {{
 *   system: string,
 *   user: string,
 *   tools: object[],
 *   handleTool: (name: string, args: object) => Promise<any>,
 *   extraSystem?: string,
 * }} opts
 * @returns {Promise<{ options: object[], rationale: string, raw: string }>}
 */
export async function runAgent({ system, user, tools, handleTool, extraSystem = '' }) {
  const messages = [
    { role: 'system', content: extraSystem ? `${system}\n\n${extraSystem}` : system },
    { role: 'user', content: user },
  ]

  for (let round = 0; round < MAX_ROUNDS; round += 1) {
    const data = await llmChat({
      messages,
      tools,
      tool_choice: 'auto',
      temperature: 0.2,
    })

    const choice = data?.choices?.[0]?.message
    if (!choice) throw new Error('Empty LLM response')

    const toolCalls = choice.tool_calls
    if (toolCalls?.length) {
      messages.push({
        role: 'assistant',
        content: choice.content || null,
        tool_calls: toolCalls,
      })
      for (const call of toolCalls) {
        const name = call.function?.name
        let args = {}
        try {
          args = JSON.parse(call.function?.arguments || '{}')
        } catch {
          args = {}
        }
        let result
        try {
          result = await handleTool(name, args)
        } catch (err) {
          result = { error: err?.message || String(err) }
        }
        messages.push({
          role: 'tool',
          tool_call_id: call.id,
          content: JSON.stringify(result),
        })
      }
      continue
    }

    const raw = (choice.content || '').trim()
    return parseAgentResult(raw)
  }

  throw new Error('Agent exceeded tool-call rounds without a final answer')
}

/** @public for tests */
export function parseAgentResult(raw) {
  const jsonText = extractJson(raw)
  let parsed
  try {
    parsed = JSON.parse(jsonText)
  } catch {
    return { options: [], rationale: raw || 'Could not parse agent response', raw }
  }
  const options = Array.isArray(parsed.options) ? parsed.options : []
  return {
    options: options.map(normalizeOption).filter(Boolean),
    rationale: typeof parsed.rationale === 'string' ? parsed.rationale : '',
    raw,
  }
}

function normalizeOption(o) {
  if (!o || typeof o !== 'object') return null
  const id = o.id || o.record_id
  if (!id) return null
  return {
    id: String(id),
    title: String(o.title || o.item || id),
    subtitle: String(o.subtitle || ''),
    score: typeof o.score === 'number' ? o.score : Number(o.score) || 0,
  }
}

function extractJson(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i)
  if (fenced) return fenced[1].trim()
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start >= 0 && end > start) return text.slice(start, end + 1)
  return text
}

/**
 * Plain chat (no tools) — Brainstorm.
 */
export async function runChat({ system, messages, temperature = 0.6 }) {
  const data = await llmChat({
    messages: [{ role: 'system', content: system }, ...messages],
    temperature,
  })
  const content = data?.choices?.[0]?.message?.content
  if (!content) throw new Error('Empty LLM response')
  return content.trim()
}
