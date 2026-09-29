// PDF transcripts are read in the browser with pdf.js, and the text goes to the same parser as a pasted .txt.
// (The server build reads PDFs with pdfplumber; that library has no Pyodide build, so the static site cannot.)
const MAX_PAGES = 30
const SAME_LINE = 3  // points: text on one printed line can differ slightly in height

type Item = { str: string; x: number; y: number; w: number }

export async function pdfToText(file: Blob): Promise<string> {
  const [pdfjs, worker] = await Promise.all([import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.mjs?url')])
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default
  const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) })
  const doc = await task.promise
  try {
    if (doc.numPages > MAX_PAGES) throw new Error(`transcript PDF has ${doc.numPages} pages; the limit is ${MAX_PAGES}`)
    const pages: string[] = []
    for (let n = 1; n <= doc.numPages; n++) {
      const content = await (await doc.getPage(n)).getTextContent()
      const items: Item[] = content.items.flatMap(i => 'str' in i && i.str.trim()
        ? [{ str: i.str, x: i.transform[4], y: i.transform[5], w: i.width }] : [])
      pages.push(toLines(items))
    }
    return pages.join('\n')
  } finally { void task.destroy() }
}

/** Top to bottom, left to right; a wide gap between two pieces of a line becomes two spaces. */
function toLines(items: Item[]): string {
  const rows: Item[][] = []
  for (const it of [...items].sort((a, b) => b.y - a.y)) {
    const row = rows.find(r => Math.abs(r[0].y - it.y) <= SAME_LINE)
    if (row) row.push(it); else rows.push([it])
  }
  return rows.map(row => {
    row.sort((a, b) => a.x - b.x)
    return row.reduce((line, it, i) => {
      if (!i) return it.str.trim()
      const prev = row[i - 1], gap = it.x - (prev.x + prev.w)
      return line + (gap > 1 ? ' ' : '') + it.str.trim()
    }, '')
  }).join('\n')
}
