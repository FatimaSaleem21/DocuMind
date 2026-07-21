import styles from "./UserMessage.module.css";

export function UserMessage({ content }: { content: string }) {
  return (
    <div className={styles.wrapper}>
      <span className={styles.bubble}>{content}</span>
    </div>
  );
}
