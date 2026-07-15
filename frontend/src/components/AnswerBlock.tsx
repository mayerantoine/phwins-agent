import { useState } from 'react';
import { Answer } from '../api';
import { renderInline } from '../markdown';
import { ChartCard } from './ChartCard';
import { DetailsCard } from './DetailsCard';
import { ReasoningToggle } from './ReasoningToggle';
import styles from './AnswerBlock.module.css';

export function AnswerBlock({ answer }: { answer: Answer }) {
  const [copied, setCopied] = useState(false);
  const hasHeadline = Boolean(answer.direct_answer);
  const inScope = answer.is_in_scope !== false;

  async function copyHeadline() {
    if (!answer.direct_answer) return;
    try {
      await navigator.clipboard.writeText(answer.direct_answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard blocked; ignore */
    }
  }

  if (!inScope) {
    return (
      <div>
        <p
          className={styles.synthesis}
          dangerouslySetInnerHTML={{ __html: renderInline(answer.direct_answer) }}
        />
      </div>
    );
  }

  return (
    <div>
      {hasHeadline && (
        <div className={styles.headline}>
          <span dangerouslySetInnerHTML={{ __html: renderInline(answer.direct_answer) }} />
          <span className={styles.info} title="Grounded in PH WINS 2024">ⓘ</span>
          <button
            type="button"
            className={styles.copy}
            onClick={copyHeadline}
            aria-label="Copy answer"
            title={copied ? 'Copied' : 'Copy answer'}
          >
            {copied ? '✓' : '⧉'}
          </button>
        </div>
      )}
      {answer.synthesis && (
        <p
          className={styles.synthesis}
          dangerouslySetInnerHTML={{ __html: renderInline(answer.synthesis) }}
        />
      )}
      {answer.chart && <ChartCard chart={answer.chart} />}
      <DetailsCard answer={answer} defaultOpen={!hasHeadline} />
      {answer.reasoning && <ReasoningToggle reasoning={answer.reasoning} />}
    </div>
  );
}
