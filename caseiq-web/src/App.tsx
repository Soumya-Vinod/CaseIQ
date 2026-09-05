import { useState } from "react";
import styles from "./App.module.css";
import { Footer } from "./components/Footer";
import { Sidebar, type Tab } from "./components/Sidebar";
import { BrowseByActPage } from "./pages/BrowseByActPage";
import { CognizabilityPage } from "./pages/CognizabilityPage";
import { ComplaintPage } from "./pages/ComplaintPage";
import { NewsPage } from "./pages/NewsPage";
import { PoliceStationsPage } from "./pages/PoliceStationsPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { QueryPage } from "./pages/QueryPage";
import { RightsOnArrestPage } from "./pages/RightsOnArrestPage";
import { SectionLookupPage } from "./pages/SectionLookupPage";
import { SituationGuidesPage } from "./pages/SituationGuidesPage";
import { TermsPage } from "./pages/TermsPage";

// Terms/Privacy are reachable only from the footer, not the primary eight-
// tab nav (Sidebar.tsx's NAV_ITEMS is a deliberate, curated list -- see
// docs/caseiq-industry-readiness.md). `null` means "show whichever tab is
// selected"; switching tabs from the sidebar always clears this, so nav
// never leaves a stale legal page showing under a newly-selected tab.
type LegalPage = "privacy" | "terms" | null;

function App() {
  const [tab, setTab] = useState<Tab>("ask");
  const [legalPage, setLegalPage] = useState<LegalPage>(null);

  function handleTabChange(t: Tab) {
    setLegalPage(null);
    setTab(t);
  }

  return (
    <div className={styles.shell}>
      <Sidebar tab={tab} onTabChange={handleTabChange} />
      <main className={styles.content}>
        {legalPage === "privacy" && <PrivacyPage onBack={() => setLegalPage(null)} />}
        {legalPage === "terms" && <TermsPage onBack={() => setLegalPage(null)} />}

        {legalPage === null && (
          <>
            {tab === "ask" && <QueryPage />}
            {tab === "lookup" && <SectionLookupPage />}
            {tab === "browse" && <BrowseByActPage />}
            {tab === "arrest" && <CognizabilityPage />}
            {tab === "rights" && <RightsOnArrestPage />}
            {tab === "guides" && <SituationGuidesPage />}
            {tab === "complaint" && <ComplaintPage />}
            {tab === "news" && <NewsPage />}
            {tab === "stations" && <PoliceStationsPage />}
          </>
        )}

        <Footer
          onOpenPrivacy={() => setLegalPage("privacy")}
          onOpenTerms={() => setLegalPage("terms")}
        />
      </main>
    </div>
  );
}

export default App;
