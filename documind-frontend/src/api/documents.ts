import { get, post } from "./client";
import type { Document } from "../types/document";

export function listDocuments(): Promise<Document[]> {
  return get<Document[]>("/documents/");
}

export function getDocument(id: number): Promise<Document> {
  return get<Document>(`/documents/${id}/`);
}

export function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return post<Document>("/documents/", formData);
}
