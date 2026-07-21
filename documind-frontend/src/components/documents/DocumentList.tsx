import { useDocuments } from "../../hooks/useDocuments";
import { DocumentRow } from "./DocumentRow";
import { UploadForm } from "./UploadForm";
import styles from "./DocumentList.module.css";

export function DocumentList() {
  const { documents, refetch } = useDocuments();

  return (
    <div>
      <div className={styles.subtitle}>
        index — {documents.length} document{documents.length === 1 ? "" : "s"}
      </div>
      <UploadForm onUploaded={refetch} />
      <div className={styles.list}>
        {documents.length === 0 ? (
          <div className={styles.empty}>no documents yet</div>
        ) : (
          documents.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
        )}
      </div>
    </div>
  );
}
