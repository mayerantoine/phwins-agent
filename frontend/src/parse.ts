export type CalcBlock =
  | { kind: 'row'; label: string; value: string; note: string }
  | { kind: 'prose'; text: string; note: string };

// Split full_answer into per-line blocks. Bulleted or short numeric lines
// become label/value rows; longer sentences become prose paragraphs. A 95% CI
// substring is peeled off into a right-side note.
export function parseCalcBlocks(fullAnswer: string): CalcBlock[] {
  const lines = fullAnswer.split(/\n+/).map((l) => l.trim()).filter(Boolean);
  return lines.map<CalcBlock>((line) => {
    const isBullet = /^[-*•·]\s+/.test(line);
    const clean = line.replace(/^[-*•·]\s*/, '');

    const ciMatch = clean.match(/\(?\s*95%\s*CI[^)]*\)?/i);
    const note = ciMatch ? ciMatch[0].replace(/^\(|\)$/g, '').trim() : '';
    let body = ciMatch ? clean.replace(ciMatch[0], '').trim() : clean;
    body = body.replace(/[,;]\s*$/, '').trim();

    const m = body.match(/^([^:—–]{1,80})[:—–]\s*(.+)$/);
    if (m) {
      const label = m[1].trim();
      const value = m[2].trim();
      const isShortValue = value.length <= 40 || /^[\d.,%\s\-–—<>≈~]+$/.test(value);
      if (isBullet || isShortValue) {
        return { kind: 'row', label, value, note };
      }
    }
    return { kind: 'prose', text: body, note };
  });
}
