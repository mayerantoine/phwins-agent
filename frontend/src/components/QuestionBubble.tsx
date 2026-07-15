import styles from './QuestionBubble.module.css';

export function QuestionBubble({ text }: { text: string }) {
  return (
    <div className={styles.row}>
      <div className={styles.bubble}>{text}</div>
    </div>
  );
}
