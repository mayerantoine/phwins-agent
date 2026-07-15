import { useState } from 'react';
import styles from './ReasoningToggle.module.css';

export function ReasoningToggle({ reasoning }: { reasoning: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.btn}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? 'Hide reasoning' : 'Show reasoning'}
        </button>
      </div>
      {visible && <pre className={styles.block}>{reasoning}</pre>}
    </>
  );
}
