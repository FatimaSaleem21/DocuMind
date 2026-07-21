export function UserMessage({ content }: { content: string }) {
  return (
    <p
      style={{
        textAlign: "right",
        fontSize: 14,
        color: "var(--muted)",
        marginBottom: 20,
      }}
    >
      {content}
    </p>
  );
}
