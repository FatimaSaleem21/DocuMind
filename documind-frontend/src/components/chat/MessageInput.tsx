import { useState } from "react";

export function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (question: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit() {
    const question = value.trim();
    if (!question || disabled) return;
    onSend(question);
    setValue("");
  }

  return (
    <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        disabled={disabled}
        placeholder="ask a question about your documents…"
        style={{
          flex: 1,
          fontFamily: "var(--font-sans)",
          fontSize: 14,
          padding: "10px 12px",
          border: "1px solid var(--rule)",
          borderRadius: 6,
          background: "var(--paper)",
          color: "var(--ink)",
        }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          padding: "0 16px",
          border: "1px solid var(--rule)",
          borderRadius: 6,
          background: "transparent",
          color: "var(--ink)",
          cursor: disabled || !value.trim() ? "default" : "pointer",
          opacity: disabled || !value.trim() ? 0.5 : 1,
        }}
      >
        send
      </button>
    </div>
  );
}
