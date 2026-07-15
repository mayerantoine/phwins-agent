import { parseCalcBlocks } from '../parse';
import { renderInline } from '../markdown';
import styles from './DetailsSections.module.css';

export function CalculationsSection({ fullAnswer }: { fullAnswer: string }) {
  const blocks = parseCalcBlocks(fullAnswer);
  return (
    <div className={styles.section}>
      <div className={styles.label}>Intermediate calculations</div>
      <div className={styles.calc}>
        {blocks.length === 0 ? (
          <div
            className={styles.prose}
            dangerouslySetInnerHTML={{ __html: renderInline(fullAnswer) }}
          />
        ) : (
          blocks.map((b, i) =>
            b.kind === 'row' ? (
              <div key={i} className={styles.kvRow}>
                <div
                  className={styles.kvLabel}
                  dangerouslySetInnerHTML={{ __html: renderInline(b.label) }}
                />
                <div
                  className={styles.kvValue}
                  dangerouslySetInnerHTML={{ __html: renderInline(b.value) }}
                />
                <div className={styles.kvNote}>{b.note}</div>
              </div>
            ) : (
              <div key={i}>
                <div
                  className={styles.prose}
                  dangerouslySetInnerHTML={{ __html: renderInline(b.text) }}
                />
                {b.note && (
                  <div className={`${styles.kvRow} ${styles.kvRowFull}`}>
                    <div className={styles.kvValue} />
                    <div className={styles.kvNote}>{b.note}</div>
                  </div>
                )}
              </div>
            ),
          )
        )}
      </div>
    </div>
  );
}
