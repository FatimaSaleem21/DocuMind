import { useState } from "react";
import clsx from "clsx";
import styles from "./App.module.css";
import { ChatWindow } from "./components/chat/ChatWindow";
import { DocumentList } from "./components/documents/DocumentList";

type Tab = "documents" | "chat";

const TAB_LABELS: Record<Tab, string> = {
  documents: "Documents",
  chat: "Chat",
};

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("documents");

  return (
    <>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoBadge}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="12" height="12" rx="1.5" stroke="var(--accent-contrast)" strokeWidth="1.3" />
              <line x1="3.5" y1="5" x2="10.5" y2="5" stroke="var(--accent-contrast)" strokeWidth="1.1" />
              <line x1="3.5" y1="7.5" x2="10.5" y2="7.5" stroke="var(--accent-contrast)" strokeWidth="1.1" />
              <line x1="3.5" y1="10" x2="8" y2="10" stroke="var(--accent-contrast)" strokeWidth="1.1" />
            </svg>
          </div>
          <span className={styles.logoText}>
            docu<span className={styles.logoAccent}>mind</span>
          </span>
        </div>
        <nav className={styles.nav}>
          {(["documents", "chat"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(styles.navItem, activeTab === tab && styles.navItemActive)}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </aside>

      <main className={styles.main}>
        <div className={styles.mainInner}>
          <h1 className={styles.pageTitle}>{TAB_LABELS[activeTab]}</h1>
          {activeTab === "documents" ? <DocumentList /> : <ChatWindow />}
        </div>
      </main>
    </>
  );
}
