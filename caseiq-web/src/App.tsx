import { useState } from "react";
import styles from "./App.module.css";
import { Sidebar, type Tab } from "./components/Sidebar";
import { BrowseByActPage } from "./pages/BrowseByActPage";
import { CognizabilityPage } from "./pages/CognizabilityPage";
import { ComplaintPage } from "./pages/ComplaintPage";
import { NewsPage } from "./pages/NewsPage";
import { PoliceStationsPage } from "./pages/PoliceStationsPage";
import { QueryPage } from "./pages/QueryPage";
import { RightsOnArrestPage } from "./pages/RightsOnArrestPage";
import { SectionLookupPage } from "./pages/SectionLookupPage";

function App() {
  const [tab, setTab] = useState<Tab>("ask");

  return (
    <div className={styles.shell}>
      <Sidebar tab={tab} onTabChange={setTab} />
      <main className={styles.content}>
        {tab === "ask" && <QueryPage />}
        {tab === "lookup" && <SectionLookupPage />}
        {tab === "browse" && <BrowseByActPage />}
        {tab === "arrest" && <CognizabilityPage />}
        {tab === "rights" && <RightsOnArrestPage />}
        {tab === "complaint" && <ComplaintPage />}
        {tab === "news" && <NewsPage />}
        {tab === "stations" && <PoliceStationsPage />}
      </main>
    </div>
  );
}

export default App;
