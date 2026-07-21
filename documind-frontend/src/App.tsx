import { useState } from "react";
import { ChatWindow } from "./components/chat/ChatWindow";
import { DocumentList } from "./components/documents/DocumentList";

type Tab = "documents" | "chat";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("documents");

  return (
    <div>
      <nav
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          padding: "20px 0",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500 }}>documind</span>
        <div style={{ display: "flex", gap: 4 }}>
          {(["documents", "chat"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                background: "transparent",
                border: "none",
                borderBottom: activeTab === tab ? "2px solid var(--ink)" : "2px solid transparent",
                color: activeTab === tab ? "var(--ink)" : "var(--muted)",
                padding: "6px 2px",
                cursor: "pointer",
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </nav>

      <main style={{ padding: "24px 0" }}>
        {activeTab === "documents" ? <DocumentList /> : <ChatWindow />}
      </main>
    </div>
  );
}
