// UI translations served by Frappe (each app's locale/<lang>.po, compiled at build).
// Usage: __('Save'), __('{0} tasks', [count]), __('Open', null, 'Task status').
let messages = {}

export const lang = (typeof window !== 'undefined' && (window.lang || document.documentElement.lang)) || 'en'

export function __(message, replace, context) {
  if (typeof message !== 'string') return message
  let text = (context && messages[`${message}:${context}`]) || messages[message] || message
  if (replace && typeof replace === 'object') {
    text = text.replace(/\{(\d+)\}/g, (match, index) => (replace[index] ?? match))
  }
  return text
}

export async function loadTranslations() {
  document.documentElement.lang = lang
  if (!lang || lang === 'en' || lang.startsWith('en-')) return
  try {
    const response = await fetch(`/api/method/nesscale_sign.api.translations.get_translations?lang=${encodeURIComponent(lang)}`, {
      credentials: 'same-origin',
    })
    const data = await response.json()
    messages = data.message || {}
  } catch {
    messages = {}
  }
}

export const translationPlugin = {
  install(app) {
    app.config.globalProperties.__ = __
  },
}

if (typeof window !== 'undefined') window.__ = __
