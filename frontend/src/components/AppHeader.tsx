import styles from './AppHeader.module.css';

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <span className={styles.traffic}>
          <span className={styles.r} />
          <span className={styles.y} />
          <span className={styles.g} />
        </span>
        <span className={styles.title}>PH WINS 2024 Q&amp;A</span>
      </div>
    </header>
  );
}
