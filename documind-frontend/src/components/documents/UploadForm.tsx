import { useRef, useState } from "react";
import { uploadDocument } from "../../api/documents";
import styles from "./UploadForm.module.css";

export function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(file);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div>
      <button onClick={() => inputRef.current?.click()} disabled={uploading} className={styles.button}>
        {uploading ? "uploading…" : "+ add document"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        className={styles.hiddenInput}
      />
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
