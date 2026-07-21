import { useRef, useState } from "react";
import { uploadDocument } from "../../api/documents";

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
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        style={{
          width: "100%",
          background: "transparent",
          border: "1px dashed var(--rule)",
          borderRadius: 8,
          padding: 14,
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          color: "#5F5A4E",
          cursor: "pointer",
        }}
      >
        {uploading ? "uploading…" : "+ add document"}
      </button>
      <input ref={inputRef} type="file" accept=".pdf" onChange={handleFileSelect} style={{ display: "none" }} />
      {error && (
        <p role="alert" style={{ color: "var(--failed)", fontSize: 13, marginTop: 8 }}>
          {error}
        </p>
      )}
    </div>
  );
}
