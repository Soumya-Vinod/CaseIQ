import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { SectionDetailOut } from "../api/types";
import { ACT_LABELS } from "../utils/acts";
import { JudicialStatusBadge } from "./JudicialStatusBadge";
import { OFFENCE_ATTR_ACTS, OffenceAttributesBlock } from "./OffenceAttributesBlock";
import styles from "./SectionDetailSheet.module.css";

const DISMISS_DRAG_PX = 80;

/**
 * A bottom sheet, not a centred dialog -- deliberately, since the demo is a
 * phone browser and a centred modal either traps content that can't fit or
 * lets the page behind it scroll along with it. Three ways to dismiss (tap
 * outside, swipe down, a visible close button), because relying on just one
 * is exactly the class of thing modals get wrong.
 *
 * Fetches its own detail (GET /knowledge/sections/{act}/{section}) rather
 * than trusting whatever truncated snippet triggered it -- the sources
 * panel and browse list only ever show a 300-char preview; this is the one
 * place the FULL text, version history, and judicial status all live
 * together, which is the entire point of building it.
 *
 * Content order is deliberate, not incidental (see the render body below):
 * act/section/title, then judicial status (before anything else, since it
 * changes whether the rest even applies), then offence attributes, then
 * the full text, then in-force/version, then history collapsed by default.
 */
export function SectionDetailSheet({
  act,
  section,
  triggerEl,
  onClose,
}: {
  act: string;
  section: string;
  triggerEl: HTMLElement | null;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<SectionDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);

  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef<number | null>(null);
  // Mirrors dragOffset synchronously. touchend reading React state directly
  // is unreliable here -- when touchmove and touchend fire back-to-back
  // (exactly how a real swipe ends), touchend's closure can still see the
  // pre-update value if React hasn't committed the last setDragOffset yet.
  // A ref sidesteps that render-timing race entirely.
  const dragOffsetRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const { data, error: apiError } = await api.GET(
          "/api/v1/knowledge/sections/{act}/{section_number}",
          { params: { path: { act, section_number: section } } },
        );
        if (cancelled) return;
        if (apiError) {
          setError("Could not load this section. Please try again.");
          return;
        }
        setDetail(data);
      } catch {
        if (!cancelled) setError("Could not reach the server. Check your connection and try again.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [act, section]);

  // Body scroll lock -- the page behind the sheet must not scroll while
  // it's open, only the sheet's own content. Runs once per open/close
  // lifecycle (this component mounts on open, unmounts on close).
  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, []);

  // Focus in on open, trap Tab while open, Escape to close, restore focus
  // to the triggering element on close -- all four in one effect since
  // they share the same mount/unmount lifecycle. Deliberately run once per
  // mount/unmount (== once per open/close) -- see the empty deps array
  // below; this component itself mounts on open and unmounts on close, so
  // "once per mount" already means "once per open".
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const restoreTo = triggerEl ?? (document.activeElement as HTMLElement | null);
    // Focus the sheet's own container (tabIndex=-1 below), not straight to
    // the close button -- a screen reader announces the dialog's
    // aria-label first this way, not "Close button" with no context.
    sheetRef.current?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !sheetRef.current) return;
      const focusables = sheetRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
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
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      restoreTo?.focus?.();
    };
  }, []);

  function handleTouchStart(e: React.TouchEvent) {
    dragStartY.current = e.touches[0].clientY;
  }
  function handleTouchMove(e: React.TouchEvent) {
    if (dragStartY.current == null) return;
    const delta = e.touches[0].clientY - dragStartY.current;
    const clamped = delta > 0 ? delta : 0;
    dragOffsetRef.current = clamped;
    setDragOffset(clamped);
  }
  function handleTouchEnd() {
    if (dragOffsetRef.current > DISMISS_DRAG_PX) {
      onClose();
    } else {
      dragOffsetRef.current = 0;
      setDragOffset(0);
    }
    dragStartY.current = null;
  }

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div
        ref={sheetRef}
        className={styles.sheet}
        style={dragOffset ? { transform: `translateY(${dragOffset}px)` } : undefined}
        role="dialog"
        aria-modal="true"
        aria-label={`${act} Section ${section} — details`}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className={styles.dragHandleRow}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className={styles.dragHandle} aria-hidden="true" />
        </div>

        <header className={styles.sheetHeader}>
          <div className={styles.locus}>
            <span className={styles.act}>{act}</span>
            <span className={styles.sectionNo}>§ {section}</span>
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        <div className={styles.sheetBody}>
          {loading && <p className={styles.loading}>Loading section…</p>}
          {error && <div className={styles.errorBox}>{error}</div>}

          {detail && (
            <>
              <p className={styles.actFullName}>{ACT_LABELS[detail.act] ?? detail.act}</p>
              {detail.title && <h2 className={styles.title}>{detail.title}</h2>}

              {detail.judicial_status && (
                <div className={styles.statusRow}>
                  <JudicialStatusBadge status={detail.judicial_status} />
                </div>
              )}

              {OFFENCE_ATTR_ACTS.has(detail.act) && (
                <OffenceAttributesBlock attrs={detail.offence_attributes} />
              )}

              <p className={styles.sectionLabel}>Full text</p>
              <p className={styles.text}>{detail.section_text}</p>

              <div className={styles.metaRow}>
                {detail.valid_from && <span>In force from {detail.valid_from}</span>}
                {detail.valid_to && <span>until {detail.valid_to}</span>}
                {detail.version_no != null && <span>Version {detail.version_no}</span>}
              </div>

              {detail.previous_version && (
                <div className={styles.historySection}>
                  <button
                    type="button"
                    className={styles.historyToggle}
                    aria-expanded={historyOpen}
                    onClick={() => setHistoryOpen((v) => !v)}
                  >
                    {historyOpen ? "Hide" : "Show"} version history {historyOpen ? "▲" : "▼"}
                  </button>
                  {historyOpen && (
                    <div className={styles.historyBody}>
                      <p className={styles.historyMeta}>
                        Version {detail.previous_version.version_no} — in force{" "}
                        {detail.previous_version.valid_from}
                        {detail.previous_version.valid_to
                          ? ` to ${detail.previous_version.valid_to}`
                          : ""}
                      </p>
                      <p className={styles.text}>{detail.previous_version.section_text}</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
