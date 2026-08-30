import { useState } from "react";
import styles from "./App.module.css";
import { BrowseByActPage } from "./pages/BrowseByActPage";
import { QueryPage } from "./pages/QueryPage";
import { SectionLookupPage } from "./pages/SectionLookupPage";

type Tab = "ask" | "lookup" | "browse";

const TABS: { id: Tab; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "lookup", label: "Look up a section" },
  { id: "browse", label: "Browse by act" },
];

function App() {
  const [tab, setTab] = useState<Tab>("ask");

  return (
    <>
      <nav className={styles.nav} aria-label="Main">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`${styles.tab} ${tab === t.id ? styles.tabActive : ""}`}
            onClick={() => setTab(t.id)}
            aria-current={tab === t.id ? "page" : undefined}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "ask" && <QueryPage />}
      {tab === "lookup" && <SectionLookupPage />}
      {tab === "browse" && <BrowseByActPage />}
    </>
  );
}

export default App;
