import { useDocuments } from "../../hooks/useDocuments";
import { DocumentRow } from "./DocumentRow";
import { UploadForm } from "./UploadForm";

export function DocumentList() {
  const { documents, refetch } = useDocuments();

  return (
    <div>
      <UploadForm onUploaded={refetch} />
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)", margin: "20px 0 8px" }}>
        index — {documents.length} document{documents.length === 1 ? "" : "s"}
      </div>
      {documents.length === 0 ? (
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--muted)", padding: "24px 0" }}>
          no documents yet
        </div>
      ) : (
        documents.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
      )}
    </div>
  );
}
