import styles from "./AnswerReceipt.module.css";

export function AnswerReceipt({ content, sources }: { content: string; sources?: number[] }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <p className={styles.content}>{content}</p>
        {sources && sources.length > 0 && (
          <div className={styles.sourcesRow}>
            <span className={styles.sourcesLabel}>sources</span>
            <div className={styles.sourceChips}>
              {sources.map((p) => (
                <span key={p} className={styles.sourceChip}>
                  p.{p}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
