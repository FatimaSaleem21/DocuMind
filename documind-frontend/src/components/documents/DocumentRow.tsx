import clsx from "clsx";
import type { Document } from "../../types/document";
import { DocumentStatusTab, STATUS_COLOR } from "./DocumentStatusTab";
import styles from "./DocumentRow.module.css";

export function DocumentRow({ doc }: { doc: Document }) {
  const meta =
    doc.status === "failed"
      ? doc.error_message
      : doc.status === "ready"
        ? `${doc.page_count} pages`
        : "processing…";

  return (
    <div className={styles.row}>
      <div
        className={styles.statusBar}
        style={{ "--status-color": STATUS_COLOR[doc.status] } as React.CSSProperties}
      />
      <div className={styles.info}>
        <div className={styles.filename}>{doc.original_filename}</div>
        <div className={clsx(styles.meta, doc.status === "failed" && styles.metaFailed)}>{meta}</div>
      </div>
      <DocumentStatusTab status={doc.status} />
    </div>
  );
}
