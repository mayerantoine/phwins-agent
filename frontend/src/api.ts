export interface Sources {
  survey_year: string;
  source_file: string;
  topics: string[];
}

export interface ChartBar {
  label: string;
  value_pct: number;
  lci: number | null;
  uci: number | null;
  is_highlight: boolean;
  is_group: boolean;
}

export interface Chart {
  title: string;
  subtitle: string;
  caption: string;
  highlight: string | null;
  bars: ChartBar[];
  source: {
    topic: string;
    subtopic: string;
    survey_year: string;
    source_file: string;
  };
}

export interface Answer {
  direct_answer: string;
  full_answer: string;
  synthesis: string;
  reasoning: string;
  sources: Sources;
  chart?: Chart | null;
  is_in_scope?: boolean;
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
