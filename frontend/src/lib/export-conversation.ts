interface ExportMessage {
  role: string
  content: string | null
  created_time?: string
  metadata?: {
    agent_id?: number
    agent_name?: string
    role?: string
    is_final?: boolean
  } | null
}

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')

function renderMessage(msg: ExportMessage): string {
  const meta = msg.metadata
  const time = msg.created_time ? new Date(msg.created_time).toLocaleString() : ''

  if (msg.role === 'user') {
    return `<div class="msg user"><div class="bubble user-bg"><div class="label">You ${time ? `· ${time}` : ''}</div>${esc(msg.content || '')}</div></div>`
  }

  if (meta?.role === 'agent') {
    const name = meta.agent_name || 'Agent'
    return `<details class="agent" open><summary class="agent-header">🤖 ${esc(name)} ${time ? `<span class="time">· ${time}</span>` : ''}</summary><div class="agent-body">${esc(msg.content || '')}</div></details>`
  }

  if (meta?.is_final) {
    const roleLabel = meta.role === 'coordinator' ? '📋 Coordinator Summary' : '📋 Aggregator Summary'
    return `<div class="msg ai"><div class="bubble summary-bg"><div class="label">${roleLabel} ${time ? `· ${time}` : ''}</div>${esc(msg.content || '')}</div></div>`
  }

  return `<div class="msg ai"><div class="bubble ai-bg"><div class="label">AI ${time ? `· ${time}` : ''}</div>${esc(msg.content || '')}</div></div>`
}

const CSS = `
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:0 auto;padding:24px;background:#fff;color:#1f2937}
h1{font-size:20px;border-bottom:1px solid #e5e7eb;padding-bottom:12px}
.msg{display:flex;margin-bottom:16px}
.msg.user{justify-content:flex-end}
.msg.ai{justify-content:flex-start}
.bubble{max-width:75%;padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.6;white-space:pre-wrap;word-break:break-word}
.user-bg{background:#2563eb;color:#fff}
.ai-bg{background:#f3f4f6;color:#1f2937}
.summary-bg{background:#eef2ff;color:#1e3a5f;border:1px solid #c7d2fe}
.label{font-weight:600;margin-bottom:4px;font-size:12px;opacity:0.7}
.agent{margin-bottom:12px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}
.agent-header{padding:8px 12px;font-size:13px;font-weight:600;cursor:pointer;background:#f9fafb;display:flex;align-items:center;gap:6px;list-style:none}
.agent-header::-webkit-details-marker{display:none}
.agent-header .time{font-weight:400;opacity:0.6}
.agent-body{padding:10px 16px;font-size:14px;line-height:1.6;white-space:pre-wrap;word-break:break-word;background:#fff;border-top:1px solid #e5e7eb}
.footer{text-align:center;font-size:12px;color:#9ca3af;margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb}
@media print{body{padding:0}.agent-body{display:block!important}}
`

export function downloadConversationHtml(title: string, messages: ExportMessage[]) {
  const sorted = [...messages].sort((a, b) => {
    const aFinal = a.metadata?.is_final ? 1 : 0
    const bFinal = b.metadata?.is_final ? 1 : 0
    if (aFinal !== bFinal) return aFinal - bFinal
    return 0
  })

  const body = sorted.map(renderMessage).join('\n')

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>${esc(title)}</title>
<style>${CSS}</style>
</head>
<body>
<h1>${esc(title)}</h1>
${body}
<div class="footer">Exported from OpenArma · ${new Date().toLocaleString()}</div>
</body>
</html>`

  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_')}.html`
  a.click()
  URL.revokeObjectURL(url)
}
