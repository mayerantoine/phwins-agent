export interface Sources {
  survey_year: string;
  source_file: string;
  topics: string[];
}

export interface Answer {
  direct_answer: string;
  full_answer: string;
  synthesis: string;
  reasoning: string;
  sources: Sources;
}

export async function ask(question: string): Promise<Answer> {
  const r = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
