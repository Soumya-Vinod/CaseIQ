import { useState } from "react";
import styles from "./App.module.css";
import { AppHeader } from "./components/AppHeader";
import { BrowseByActPage } from "./pages/BrowseByActPage";
import { CognizabilityPage } from "./pages/CognizabilityPage";
import { ComplaintPage } from "./pages/ComplaintPage";
import { NewsPage } from "./pages/NewsPage";
import { PoliceStationsPage } from "./pages/PoliceStationsPage";
import { QueryPage } from "./pages/QueryPage";
import { SectionLookupPage } from "./pages/SectionLookupPage";

type Tab = "ask" | "lookup" | "browse" | "arrest" | "complaint" | "news" | "stations";

const TABS: { id: Tab; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "lookup", label: "Look up a section" },
  { id: "browse", label: "Browse by act" },
  { id: "arrest", label: "Arrest & bail" },
  { id: "complaint", label: "File a complaint" },
  { id: "news", label: "News" },
  { id: "stations", label: "Nearby Stations" },
];

function App() {
  const [tab, setTab] = useState<Tab>("ask");

  return (
    <>
      <AppHeader />
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
      {tab === "arrest" && <CognizabilityPage />}
      {tab === "complaint" && <ComplaintPage />}
      {tab === "news" && <NewsPage />}
      {tab === "stations" && <PoliceStationsPage />}
    </>
  );
}

export default App;
