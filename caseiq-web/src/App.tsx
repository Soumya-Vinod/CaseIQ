import { useState } from "react";
import styles from "./App.module.css";
import { AccountPage } from "./pages/AccountPage";
import { Footer } from "./components/Footer";
import { Sidebar, type Tab } from "./components/Sidebar";
import { AuthProvider } from "./contexts/AuthContext";
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

// Terms/Privacy/Account are reachable only from the footer, not the primary
// eight-tab nav (Sidebar.tsx's NAV_ITEMS is a deliberate, curated list --
// see docs/caseiq-industry-readiness.md). `null` means "show whichever tab
// is selected"; switching tabs from the sidebar always clears this, so nav
// never leaves a stale footer page showing under a newly-selected tab.
// Account joined this group in Phase B (checklist item 6) rather than
// becoming a ninth sidebar tab -- worth revisiting once conversation
// history (Phase C) makes being logged in a frequent action, not an
// occasional one; see AccountPage's own docstring.
type FooterPage = "privacy" | "terms" | "account" | null;

function App() {
  const [tab, setTab] = useState<Tab>("ask");
  const [footerPage, setFooterPage] = useState<FooterPage>(null);

  function handleTabChange(t: Tab) {
    setFooterPage(null);
    setTab(t);
  }

  return (
    <AuthProvider>
      <div className={styles.shell}>
        <Sidebar tab={tab} onTabChange={handleTabChange} />
        <main className={styles.content}>
          {footerPage === "privacy" && <PrivacyPage onBack={() => setFooterPage(null)} />}
          {footerPage === "terms" && <TermsPage onBack={() => setFooterPage(null)} />}
          {footerPage === "account" && (
            <AccountPage
              onBack={() => setFooterPage(null)}
              onGoToAsk={() => {
                setFooterPage(null);
                setTab("ask");
              }}
            />
          )}

          {footerPage === null && (
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
            onOpenPrivacy={() => setFooterPage("privacy")}
            onOpenTerms={() => setFooterPage("terms")}
            onOpenAccount={() => setFooterPage("account")}
          />
        </main>
      </div>
    </AuthProvider>
  );
}

export default App;
