export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface Document {
  id: number;
  file: string;
  original_filename: string;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  uploaded_at: string;
}
