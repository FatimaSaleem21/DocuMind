import { useState } from "react";
import clsx from "clsx";
import styles from "./MessageInput.module.css";

export function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (question: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const canSend = !disabled && value.trim().length > 0;

  function submit() {
    const question = value.trim();
    if (!question || disabled) return;
    onSend(question);
    setValue("");
  }

  return (
    <div className={styles.row}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        disabled={disabled}
        placeholder="ask a question about your documents…"
        className={styles.input}
      />
      <button
        onClick={submit}
        disabled={!canSend}
        className={clsx(styles.send, canSend ? styles.sendActive : styles.sendDisabled)}
      >
        send
      </button>
    </div>
  );
}
