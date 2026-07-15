import { Answer } from '../api';
import { SourceRow } from './SourceRow';
import { AssumptionsSection } from './AssumptionsSection';
import { CalculationsSection } from './CalculationsSection';
import styles from './DetailsCard.module.css';

export function DetailsCard({ answer, defaultOpen = false }: { answer: Answer; defaultOpen?: boolean }) {
  const { sources, full_answer } = answer;
  const year = sources.survey_year || '2024';
  const file = sources.source_file || 'phwins_2024.json';

  return (
    <details className={styles.card} open={defaultOpen}>
      <summary>Details</summary>
      <div className={styles.body}>
        <SourceRow surveyYear={year} sourceFile={file} />
        <AssumptionsSection surveyYear={year} topics={sources.topics ?? []} />
        {full_answer && <CalculationsSection fullAnswer={full_answer} />}
      </div>
    </details>
  );
}
