import styles from './SourceRow.module.css';

interface Props {
  surveyYear: string;
  sourceFile: string;
}

export function SourceRow({ surveyYear, sourceFile }: Props) {
  return (
    <div className={styles.row}>
      <div className={styles.icon} />
      <div className={styles.text}>
        <div className={styles.title}>Adapted from &ldquo;PH WINS {surveyYear} survey&rdquo;</div>
        <div className={styles.meta}>de Beaumont Foundation / ASTHO · {sourceFile}</div>
      </div>
      <a
        href="#"
        className={styles.open}
        onClick={(e) => e.preventDefault()}
      >
        Open ↗
      </a>
    </div>
  );
}
