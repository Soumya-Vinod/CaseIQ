import { useEffect, useRef, useState } from "react";
import {
  ArrestIcon,
  AskIcon,
  BrowseIcon,
  ChevronIcon,
  CloseIcon,
  ComplaintIcon,
  LookupIcon,
  MenuIcon,
  NewsIcon,
  RightsIcon,
  StationsIcon,
} from "./icons";
import styles from "./Sidebar.module.css";

export type Tab =
  | "ask"
  | "lookup"
  | "browse"
  | "arrest"
  | "rights"
  | "complaint"
  | "news"
  | "stations";

const NAV_ITEMS: { id: Tab; label: string; Icon: typeof AskIcon }[] = [
  { id: "ask", label: "Ask", Icon: AskIcon },
  { id: "lookup", label: "Look up a section", Icon: LookupIcon },
  { id: "browse", label: "Browse by act", Icon: BrowseIcon },
  { id: "arrest", label: "Arrest & bail", Icon: ArrestIcon },
  { id: "rights", label: "Your rights", Icon: RightsIcon },
  { id: "complaint", label: "File a complaint", Icon: ComplaintIcon },
  { id: "news", label: "News", Icon: NewsIcon },
  { id: "stations", label: "Nearby stations", Icon: StationsIcon },
];

const COLLAPSE_KEY = "caseiq_sidebar_collapsed";

/**
 * One nav, two very different renderings of the same list -- a persistent,
 * collapsible-to-icons rail on desktop; an off-canvas drawer behind a
 * hamburger on mobile, never a cramped vertical strip squeezed into a
 * phone width. Which markup is visually active is pure CSS (media query),
 * but the drawer needs real interaction behaviour a rail doesn't: focus
 * moves in on open, Escape closes it, focus returns to the button that
 * opened it, and picking a destination closes it -- same accessibility
 * shape as SectionDetailSheet's bottom sheet, because an off-canvas panel
 * over the page has the same failure modes a modal does.
 */
export function Sidebar({ tab, onTabChange }: { tab: Tab; onTabChange: (t: Tab) => void }) {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  function toggleCollapsed() {
    setCollapsed((v) => {
      const next = !v;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        /* per-viewer convenience only -- fine to lose silently */
      }
      return next;
    });
  }

  function selectTab(t: Tab) {
    onTabChange(t);
    setDrawerOpen(false);
  }

  // Drawer accessibility: focus in on open, trap Tab, Escape closes,
  // restore focus to the hamburger on close. Mirrors SectionDetailSheet's
  // own effect almost exactly -- an off-canvas panel over page content is
  // the same class of overlay a bottom sheet is.
  useEffect(() => {
    if (!drawerOpen) return;
    const nav = drawerRef.current;
    nav?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setDrawerOpen(false);
        return;
      }
      if (e.key !== "Tab" || !nav) return;
      const focusables = nav.querySelectorAll<HTMLElement>(
        'button, [href], [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
      menuButtonRef.current?.focus();
    };
  }, [drawerOpen]);

  const navContent = (
    <>
      <div className={styles.brandRow}>
        <span className={styles.mark} aria-hidden="true">
          §
        </span>
        {!collapsed && (
          <span className={styles.wordmark}>
            Case<span className={styles.wordmarkAccent}>IQ</span>
          </span>
        )}
      </div>

      <ul className={styles.navList}>
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={`${styles.navItem} ${tab === item.id ? styles.navItemActive : ""}`}
              onClick={() => selectTab(item.id)}
              aria-current={tab === item.id ? "page" : undefined}
              title={collapsed ? item.label : undefined}
              aria-label={item.label}
            >
              <item.Icon className={styles.navIcon} />
              <span className={styles.navLabel}>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>

      <button
        type="button"
        className={styles.collapseToggle}
        onClick={toggleCollapsed}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <ChevronIcon className={collapsed ? undefined : styles.collapseIconOpen} />
        {!collapsed && <span>Collapse</span>}
      </button>
    </>
  );

  return (
    <>
      {/* Mobile-only slim top bar -- CSS-hidden on desktop. */}
      <div className={styles.mobileBar}>
        <button
          ref={menuButtonRef}
          type="button"
          className={styles.menuButton}
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={drawerOpen}
        >
          <MenuIcon />
        </button>
        <span className={styles.mobileBrand}>
          Case<span className={styles.wordmarkAccent}>IQ</span>
        </span>
      </div>

      {/* Desktop rail -- CSS-hidden on mobile. */}
      <nav
        className={`${styles.rail} ${collapsed ? styles.railCollapsed : ""}`}
        aria-label="Main"
      >
        {navContent}
      </nav>

      {/* Mobile drawer -- rendered always, visibility/transform driven by
          drawerOpen so the closing transition can run instead of the node
          just vanishing. Backdrop click closes it, same as the sheet. */}
      {drawerOpen && (
        <div className={styles.backdrop} onClick={() => setDrawerOpen(false)} />
      )}
      <nav
        ref={drawerRef}
        className={`${styles.drawer} ${drawerOpen ? styles.drawerOpen : ""}`}
        aria-label="Main"
        aria-hidden={!drawerOpen}
        tabIndex={-1}
      >
        <div className={styles.drawerHeader}>
          <span className={styles.mobileBrand}>
            Case<span className={styles.wordmarkAccent}>IQ</span>
          </span>
          <button
            type="button"
            className={styles.closeButton}
            onClick={() => setDrawerOpen(false)}
            aria-label="Close menu"
          >
            <CloseIcon />
          </button>
        </div>
        <ul className={styles.navList}>
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={`${styles.navItem} ${tab === item.id ? styles.navItemActive : ""}`}
                onClick={() => selectTab(item.id)}
                aria-current={tab === item.id ? "page" : undefined}
                aria-label={item.label}
              >
                <item.Icon className={styles.navIcon} />
                <span className={styles.navLabel}>{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
