import clsx from "clsx";
import styles from "./AnswerReceipt.module.css";

export function AnswerReceipt({
  content,
  sources,
  isError,
}: {
  content: string;
  sources?: number[];
  isError?: boolean;
}) {
  return (
    <div className={styles.wrapper}>
      <div className={clsx(styles.card, isError && styles.cardError)}>
        <p className={clsx(styles.content, isError && styles.contentError)}>{content}</p>
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
