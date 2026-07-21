export function AnswerReceipt({ content, sources }: { content: string; sources?: number[] }) {
  return (
    <div style={{ maxWidth: "82%", marginBottom: 28 }}>
      <div style={{ border: "1px dashed #A9A398", borderRadius: 6, padding: "16px 18px 0", position: "relative" }}>
        <div
          style={{
            position: "absolute",
            top: -1,
            left: 12,
            right: 12,
            height: 1,
            background: "repeating-linear-gradient(90deg, var(--paper) 0 6px, transparent 6px 12px)",
          }}
        />
        <p style={{ fontSize: 14, lineHeight: 1.6 }}>{content}</p>
        {sources && sources.length > 0 && (
          <div
            style={{
              borderTop: "1px dashed #A9A398",
              margin: "14px 0 0",
              padding: "10px 0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.08em", color: "#8A857A" }}>
              sources
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              {sources.map((p) => (
                <span
                  key={p}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--verified)",
                    background: "var(--verified-bg)",
                    padding: "2px 8px",
                    borderRadius: 4,
                  }}
                >
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
