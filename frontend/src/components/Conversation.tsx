import { useLayoutEffect, useRef } from 'react';
import { Answer } from '../api';
import { QuestionBubble } from './QuestionBubble';
import { AnswerBlock } from './AnswerBlock';
import styles from './Conversation.module.css';

export interface Turn {
  question: string;
  answer?: Answer;
  error?: string;
}

interface Props {
  turns: Turn[];
  pending: boolean;
  onPickExample: (q: string) => void;
}

const EXAMPLES = [
  'What percent of workers are experiencing burnout?',
  'How satisfied is the public health workforce with their job?',
  'What share of workers are considering leaving in the next year?',
];

export function Conversation({ turns, pending, onPickExample }: Props) {
  const chatRef = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = chatRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, pending]);

  return (
    <main ref={chatRef} className={styles.chat}>
      <div className={styles.inner} aria-live="polite">
        {turns.length === 0 && !pending && (
          <div className={styles.empty}>
            <p className={styles.emptyLead}>
              Ask a plain-English question about the U.S. public health workforce.
              Answers are grounded in PH WINS 2024.
            </p>
            <div className={styles.chips}>
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  type="button"
                  className={styles.chip}
                  onClick={() => onPickExample(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i}>
            <QuestionBubble text={t.question} />
            {t.error ? (
              <div className={styles.error}>Error: {t.error}</div>
            ) : t.answer ? (
              <AnswerBlock answer={t.answer} />
            ) : null}
          </div>
        ))}

        {pending && <div className={styles.pending}>…thinking</div>}
      </div>
    </main>
  );
}
