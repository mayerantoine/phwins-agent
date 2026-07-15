import { useState } from 'react';
import { ask } from './api';
import { AppHeader } from './components/AppHeader';
import { Composer } from './components/Composer';
import { Conversation, Turn } from './components/Conversation';
import styles from './App.module.css';

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState(false);
  const [prefill, setPrefill] = useState<string | undefined>();

  async function handleAsk(question: string) {
    setTurns((t) => [...t, { question }]);
    setPending(true);
    try {
      const answer = await ask(question);
      setTurns((t) => {
        const next = [...t];
        next[next.length - 1] = { question, answer };
        return next;
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setTurns((t) => {
        const next = [...t];
        next[next.length - 1] = { question, error: msg };
        return next;
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.app}>
      <AppHeader />
      <Conversation
        turns={turns}
        pending={pending}
        onPickExample={(q) => setPrefill(q + ' ' /* trigger even for duplicates */)}
      />
      <Composer onSubmit={handleAsk} pending={pending} value={prefill} />
    </div>
  );
}
