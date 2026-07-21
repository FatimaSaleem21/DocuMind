import { useCallback, useEffect, useState } from "react";
import { listDocuments } from "../api/documents";
import type { Document } from "../types/document";

const POLL_INTERVAL_MS = 3000;

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    const data = await listDocuments();
    setDocuments(data);
  }, []);

  useEffect(() => {
    refetch().finally(() => setLoading(false));

    const interval = setInterval(refetch, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refetch]);

  return { documents, refetch, loading };
}
