import { useEffect, useMemo, useState } from "react"

export function VideoNotes({
    value,
    onChange,
}: {
    value: string
    onChange: (value: string) => void
}) {
    const [editing, setEditing] = useState(value.length === 0)
    const [draft, setDraft] = useState(value)
    const [saved, setSaved] = useState(true)
    const html = useMemo(() => markdownToHtml(draft), [draft])

    useEffect(() => {
        setDraft(value)
        setSaved(true)
        setEditing(value.length === 0)
    }, [value])

    const save = () => {
        onChange(draft)
        setSaved(true)
    }

    return (
        <section className="space-y-3 pt-6">
            <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-bold">Notes</h3>
                <span className="text-xs text-muted-foreground">{saved ? "Saved to database" : "Unsaved changes"}</span>
                <button
                    type="button"
                    onClick={() => setEditing((current) => !current)}
                    className="rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                >
                    {editing ? "Preview" : "Edit"}
                </button>
                <button
                    type="button"
                    onClick={save}
                    disabled={saved}
                    className="rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground disabled:opacity-45"
                >
                    Save
                </button>
            </div>
            {editing ? (
                <textarea
                    value={draft}
                    onChange={(event) => {
                        setDraft(event.target.value)
                        setSaved(event.target.value === value)
                    }}
                    placeholder="Write notes in Markdown..."
                    className="min-h-36 w-full resize-y rounded-md border border-border bg-background p-3 text-sm leading-6 outline-none focus:border-primary/55"
                />
            ) : draft.trim() ? (
                <div
                    className="space-y-2 text-sm leading-6 text-muted-foreground [&_code]:rounded-md [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-foreground [&_em]:text-foreground/80 [&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-foreground [&_h3]:font-bold [&_h3]:text-foreground [&_h4]:font-semibold [&_h4]:text-foreground [&_li]:ml-4 [&_li]:list-disc [&_strong]:font-semibold [&_strong]:text-foreground"
                    dangerouslySetInnerHTML={{ __html: html }}
                />
            ) : (
                <p className="text-sm text-muted-foreground">No notes yet.</p>
            )}
        </section>
    )
}

function markdownToHtml(markdown: string) {
    const lines = markdown.split(/\r?\n/)
    const html: string[] = []
    let inList = false
    for (const line of lines) {
        const text = line.trim()
        if (!text) {
            if (inList) {
                html.push("</ul>")
                inList = false
            }
            continue
        }
        if (text.startsWith("### ")) {
            if (inList) {
                html.push("</ul>")
                inList = false
            }
            html.push(`<h4>${inline(text.slice(4))}</h4>`)
            continue
        }
        if (text.startsWith("## ")) {
            if (inList) {
                html.push("</ul>")
                inList = false
            }
            html.push(`<h3>${inline(text.slice(3))}</h3>`)
            continue
        }
        if (text.startsWith("# ")) {
            if (inList) {
                html.push("</ul>")
                inList = false
            }
            html.push(`<h2>${inline(text.slice(2))}</h2>`)
            continue
        }
        if (/^[-*]\s+/.test(text)) {
            if (!inList) {
                html.push("<ul>")
                inList = true
            }
            html.push(`<li>${inline(text.replace(/^[-*]\s+/, ""))}</li>`)
            continue
        }
        if (inList) {
            html.push("</ul>")
            inList = false
        }
        html.push(`<p>${inline(text)}</p>`)
    }
    if (inList) html.push("</ul>")
    return html.join("")
}

function inline(value: string) {
    return escapeHtml(value)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([^*]+)\*/g, "<em>$1</em>")
}

function escapeHtml(value: string) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;")
}
