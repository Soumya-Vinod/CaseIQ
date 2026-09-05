/**
 * Minimal line icons for the sidebar nav -- hand-drawn inline SVG, not an
 * icon-library import, same reasoning as AppHeader's own typographic mark:
 * this app's visual language is deliberately not generic-SaaS iconography.
 * One consistent stroke style (24x24 viewBox, 1.75px stroke, round caps/
 * joins, currentColor so they inherit the sidebar's own text/gold colour
 * per active state) rather than mixed weights from mixed sources.
 */
import type { SVGProps } from "react";

function Icon({ children, ...props }: SVGProps<SVGSVGElement> & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function AskIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M4 5.5A2 2 0 0 1 6 3.5h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-4 4v-4H6a2 2 0 0 1-2-2z" />
      <path d="M9 9.5h6M9 12.5h4" />
    </Icon>
  );
}

export function LookupIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="M20 20l-4.8-4.8" />
    </Icon>
  );
}

export function BrowseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M4 5h16M4 12h16M4 19h10" />
    </Icon>
  );
}

export function ArrestIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
      <path d="M9.5 12l1.8 1.8L14.5 10" />
    </Icon>
  );
}

export function ComplaintIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M7 3.5h7l3 3v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-16a1 1 0 0 1 1-1z" />
      <path d="M14 3.5v3h3M9 13l1.5 1.5L15 10" />
    </Icon>
  );
}

export function NewsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="5" width="17" height="14" rx="1" />
      <path d="M7 9h6M7 12.5h6M7 16h3" />
      <path d="M17 9v7" />
    </Icon>
  );
}

export function StationsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M12 21s7-6.5 7-11.5A7 7 0 0 0 5 9.5C5 14.5 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.5" />
    </Icon>
  );
}

export function GuidesIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M6 4.5h11.5v14.5a1 1 0 0 1-1 1H7.5A1.5 1.5 0 0 1 6 18.5z" />
      <path d="M6 4.5A1.5 1.5 0 0 1 7.5 3H16" />
      <path d="M9 8.5h6M9 12h4" />
      <path d="M6 18.5a1.5 1.5 0 0 1 1.5-1.5H16" />
    </Icon>
  );
}

export function RightsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M6 4h9l3 3v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
      <path d="M15 4v3h3" />
      <path d="M8 11h8M8 14h8M8 17h5" />
    </Icon>
  );
}

export function ChevronIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M9 6l6 6-6 6" />
    </Icon>
  );
}

export function MenuIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </Icon>
  );
}

export function CloseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Icon {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Icon>
  );
}
