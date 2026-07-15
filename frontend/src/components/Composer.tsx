import { KeyboardEvent, useEffect, useRef, useState } from 'react';
import styles from './Composer.module.css';

interface Props {
  onSubmit: (question: string) => void;
  pending: boolean;
  value?: string;
}

export function Composer({ onSubmit, pending, value }: Props) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  // Allow parent to prefill the composer (used by empty-state example chips).
  useEffect(() => {
    if (value !== undefined) {
      setText(value);
      ref.current?.focus();
    }
  }, [value]);

  // Auto-grow up to 260px.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 260) + 'px';
  }, [text]);

  function submit() {
    const q = text.trim();
    if (!q || pending) return;
    onSubmit(q);
    setText('');
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className={styles.composer}>
      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          ref={ref}
          className={styles.textarea}
          rows={3}
          placeholder="Ask about the U.S. public health workforce…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          required
        />
        <button className={styles.button} type="submit" disabled={pending}>
          {pending ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </div>
  );
}
