import styles from './DetailsSections.module.css';

interface Props {
  surveyYear: string;
  topics: string[];
}

export function AssumptionsSection({ surveyYear, topics }: Props) {
  const topicsText = topics.length ? topics.join(', ') : '—';
  return (
    <div className={styles.section}>
      <div className={styles.label}>Assumptions</div>
      <div className={styles.kvRow}>
        <div className={styles.kvLabel}>Survey scope</div>
        <div className={styles.kvValue}>U.S. national, {surveyYear}</div>
        <div className={styles.kvNote}>de Beaumont / ASTHO</div>
      </div>
      <div className={styles.kvRow}>
        <div className={styles.kvLabel}>Topics</div>
        <div className={styles.kvValue}>{topicsText}</div>
        <div className={styles.kvNote}>matches taxonomy</div>
      </div>
    </div>
  );
}
