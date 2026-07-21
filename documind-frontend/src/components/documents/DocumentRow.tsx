import type { Document } from "../../types/document";
import { DocumentStatusTab, STATUS_CONFIG } from "./DocumentStatusTab";

export function DocumentRow({ doc }: { doc: Document }) {
  const meta =
    doc.status === "failed"
      ? doc.error_message
      : doc.status === "ready"
        ? `${doc.page_count} pages`
        : "processing…";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderTop: "1px solid var(--rule)" }}>
      <div style={{ width: 4, height: 32, borderRadius: 2, background: STATUS_CONFIG[doc.status].color }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14 }}>{doc.original_filename}</div>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: doc.status === "failed" ? "var(--failed)" : "var(--muted)",
          }}
        >
          {meta}
        </div>
      </div>
      <DocumentStatusTab status={doc.status} />
    </div>
  );
}
