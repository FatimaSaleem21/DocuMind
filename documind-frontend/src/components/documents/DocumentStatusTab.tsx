import type { DocumentStatus } from "../../types/document";
import styles from "./DocumentStatusTab.module.css";

const STATUS_COLOR: Record<DocumentStatus, string> = {
  ready: "var(--verified)",
  processing: "var(--pending)",
  pending: "var(--pending)",
  failed: "var(--failed)",
};

export { STATUS_COLOR };

export function DocumentStatusTab({ status }: { status: DocumentStatus }) {
  return <span className={`${styles.tab} ${styles[status]}`}>{status}</span>;
}
