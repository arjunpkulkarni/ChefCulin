/**
 * Direct OpenAI Chat Completions from the browser (Vite env).
 * Set VITE_OPENAI_API_KEY in .env — no backend proxy.
 */

const OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
const DEFAULT_MODEL = 'gpt-4o-mini'

function readEnv(name) {
  if (typeof import.meta !== 'undefined' && import.meta.env?.[name]) {
    return String(import.meta.env[name]).trim()
  }
  if (typeof process !== 'undefined' && process.env?.[name]) {
    return String(process.env[name]).trim()
  }
  return ''
}

/** API key: VITE_OPENAI_API_KEY in dev; OPENAI_API_KEY for Vitest live runs. */
export function openaiApiKey() {
  return readEnv('VITE_OPENAI_API_KEY') || readEnv('OPENAI_API_KEY')
}

export function openaiConfigured() {
  return Boolean(openaiApiKey())
}

export function defaultModel() {
  return readEnv('VITE_OPENAI_MODEL') || readEnv('OPENAI_MODEL') || DEFAULT_MODEL
}

/**
 * @param {object} body — OpenAI chat completions body (messages, tools, temperature, …)
 */
export async function llmChat(body) {
  const key = openaiApiKey()
  if (!key) {
    throw new Error('VITE_OPENAI_API_KEY is not set — add it to .env in the project root')
  }

  const payload = {
    model: defaultModel(),
    ...body,
  }

  const res = await fetch(OPENAI_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`OpenAI ${res.status}${detail ? `: ${detail.slice(0, 400)}` : ''}`)
  }

  return res.json()
}
