import type { DocumentStatus } from "../../types/document";

const STATUS_CONFIG: Record<DocumentStatus, { color: string; bg: string; label: string }> = {
  ready: { color: "var(--verified)", bg: "var(--verified-bg)", label: "ready" },
  processing: { color: "var(--pending)", bg: "var(--pending-bg)", label: "processing" },
  pending: { color: "var(--pending)", bg: "var(--pending-bg)", label: "pending" },
  failed: { color: "var(--failed)", bg: "var(--failed-bg)", label: "failed" },
};

export { STATUS_CONFIG };

export function DocumentStatusTab({ status }: { status: DocumentStatus }) {
  const { color, bg, label } = STATUS_CONFIG[status];
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color,
        background: bg,
        padding: "3px 8px",
        borderRadius: 4,
      }}
    >
      {label}
    </span>
  );
}
