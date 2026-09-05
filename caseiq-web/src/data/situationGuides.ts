/**
 * Situation guides (checklist item 3) -- grounded walkthroughs for someone
 * who doesn't know what they're entitled to, written for a phone screen and
 * a distressed reader: short sentences, one idea each, meaning before any
 * quoted text. Every `quote` below is a verified, exact substring of the
 * live section_text for that (act, section) -- checked directly against the
 * corpus before this file was written (see docs/evaluation.md's situation-
 * guides entries for the grounding record, including the woman-officer
 * proviso finding and the dropped missing-person guide), never transcribed
 * from memory. If the corpus is ever re-ingested cleanly, tapping "Read the
 * full section" (SectionDetailSheet) always shows the current text; only
 * these short quotes are fixed here.
 *
 * Content shapes are deliberately different, and must keep LOOKING
 * different, not just be labelled differently:
 *   - `entitlements` / `recognition` -- a real right or offence definition,
 *     quoted from the statute. Rendered with an act/section badge and a
 *     bordered quote, same visual language as RightsOnArrestPage's cards.
 *   - `leadCallout` / `practicalTips` -- practical advice this project
 *     verified against an official source, or plain know-how (take someone
 *     with you, stay calm), but NOT a statutory citation. Rendered with a
 *     visibly different border/background and no act/section badge -- see
 *     SituationGuideDetail.module.css's `.practicalBox` vs `.entitlementCard`.
 *
 * Every guide opens with `openingLine` -- one plain sentence saying what the
 * page is for, before any entitlement -- so someone landing from the list
 * page knows in two seconds whether they're in the right place.
 *
 * ARRAY ORDER IS DELIBERATE, not alphabetical or chronological-by-when-
 * written: the two safety-critical guides (domestic cruelty, harassment/
 * stalking) lead the list. No section header or "for women" grouping was
 * added -- see docs/evaluation.md's "standalone women's-provisions surface
 * considered and rejected" entry for why a demographic label was rejected
 * even though ordering wasn't. A distressed person scanning this list on a
 * phone is served by position, not by a category that would also imply the
 * other three guides are for someone else.
 */

export interface GuideEntitlement {
  number: number;
  heading: string;
  /** Paragraphs of plain-language explanation, meaning BEFORE the quote. */
  body: string[];
  quote: string;
  act: string;
  section: string;
  /** Extra visual weight -- for the one entitlement in a guide that's most
   * likely to be unknown, or most consequential if missed. Not every guide
   * needs one, and it does not have to be the first entitlement listed. */
  weighted?: boolean;
}

export interface GuidePracticalTip {
  heading: string;
  items: string[];
}

export interface GuideLeadCallout {
  heading: string;
  /** The provenance disclaimer -- states plainly this isn't a statutory
   * quote, since it sits right next to entitlement cards that are. */
  note: string;
  paragraphs: string[];
}

export interface GuideRecognitionItem {
  label: string;
  quote: string;
  act: string;
  section: string;
}

export interface GuideRefusalStep {
  heading: string;
  body: string;
  act: string;
  section: string;
}

export interface GuideCrossLink {
  /** Phrased by circumstance, not by legal category -- "if the person
   * doing this lives with you or is family", not "related: domestic
   * cruelty". The reader identifies by situation, not by which guide's
   * title matches a label. */
  situationText: string;
  linkLabel: string;
  targetSlug: string;
}

export interface SituationGuide {
  slug: string;
  navLabel: string;
  navSummary: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  /** One plain sentence, rendered before anything else in the body --
   * what this page is for. */
  openingLine: string;
  /** Rendered right after openingLine, before any statutory content --
   * someone in the wrong guide should be able to redirect before reading
   * further, not after. Deliberately not a "related guides" list: at most
   * one, phrased for the specific circumstance that would send a reader
   * to the other guide. */
  crossLink?: GuideCrossLink;
  leadCallout?: GuideLeadCallout;
  /** "Does this match what's happening to you?" -- offence definitions
   * quoted directly, rendered before the procedural entitlements. Optional;
   * only guides where recognising the offence itself isn't obvious need it
   * (harassment/stalking, cruelty) -- theft-by-fraud or an arrest don't. */
  recognition?: { intro: string; items: GuideRecognitionItem[] };
  entitlementsHeading: string;
  entitlementsIntro: string;
  entitlements: GuideEntitlement[];
  /** Each tip renders directly after the entitlement whose `number`
   * matches. A guide can have more than one -- e.g. arrested/detained has
   * a "what to say" for three separate rights. */
  practicalTips?: { afterEntitlement: number; tip: GuidePracticalTip }[];
  refusalHeading: string;
  refusalIntro: string;
  refusalBullets: string[];
  refusalOutro: string;
  refusalSteps: GuideRefusalStep[];
  /** Bottom-of-page notes, in order -- caveats last read, not first, so a
   * reader gets through what they're entitled to before any reason to
   * doubt it (or, for cruelty, before being asked to think about which
   * law's cutover date applies to them). */
  closingNote: string[];
}

export const SITUATION_GUIDES: SituationGuide[] = [
  {
    slug: "domestic-cruelty",
    navLabel: "Cruelty by a husband or his family",
    navSummary:
      "Physical or mental cruelty, or dowry-related harassment, by a husband or his relatives — help first, then what you're entitled to.",
    eyebrow: "Situation guide",
    title: "Cruelty by a husband or his family",
    subtitle: "Help first. Then what counts, what you're entitled to, and what to say.",
    openingLine:
      "This page is for cruelty, threats, or dowry-related harassment by a husband or his relatives.",
    crossLink: {
      situationText: "If this is someone outside your home — a stranger, a coworker, someone following or watching you —",
      linkLabel: "see Reporting harassment or stalking instead",
      targetSlug: "woman-reporting-harassment",
    },
    leadCallout: {
      heading: "If you're in danger right now",
      note: "This is practical safety information, not a quote from the law.",
      paragraphs: [
        "Call 112 (police, fire, medical — any emergency) or 181 (Women's Helpline). Both are free, and both work any time, day or night.",
        "You do not need to have already filed a complaint to call. You do not need to know what you want to happen next. You just need to be safe.",
        "When you're ready — today, or another day — here is what the law says you're entitled to.",
      ],
    },
    recognition: {
      intro:
        "The law names two different things as cruelty — not just physical violence. If either matches what's happening to you, it counts. The law doesn't set a minimum number of times this has to happen — one incident that matches this can already be a crime.",
      items: [
        {
          label:
            "Behaviour meant to push you toward suicide, or that risks serious injury or danger to your health, mental or physical.",
          quote:
            "any wilful conduct which is of such a nature as is likely to drive the woman to commit suicide or to cause grave injury or danger to life, limb or health",
          act: "BNS",
          section: "86",
        },
        {
          label:
            "Being harassed to pressure you or your family into giving money, property, or anything valuable — including dowry demands.",
          quote:
            "harassment of the woman where such harassment is with a view to coercing her … to meet any unlawful demand for any property or valuable security",
          act: "BNS",
          section: "86",
        },
      ],
    },
    entitlementsHeading: "What you're entitled to",
    entitlementsIntro:
      "A husband or any relative of his who does this can be punished with up to three years in prison, plus a fine. Here's what happens when you report it.",
    entitlements: [
      {
        number: 1,
        heading: "Any police station must take your complaint.",
        body: [
          "It does not matter where you live, or where this happened. Any station has to write it down.",
          "If you report this yourself, or a close relative does, that's enough for the police to act on it right away — not something they can put off.",
        ],
        quote: "irrespective of the area where the offence is committed",
        act: "BNSS",
        section: "173",
      },
      {
        number: 2,
        heading: "You get a copy of your complaint, free, right away.",
        body: ["Once the police write it down, ask for a copy. The law says you must get it"],
        quote: "free of cost",
        act: "BNSS",
        section: "173",
      },
      {
        number: 3,
        heading: "The police must update you within 90 days — even if you don't ask.",
        body: [
          "This is the one most people never hear about. It's often the reason a case goes quiet after the first visit.",
          "The law says the police must tell you how the investigation is going, within 90 days, on their own — you should not have to chase them for it.",
        ],
        quote: "inform the progress of the investigation … to the informant or the victim",
        act: "BNSS",
        section: "193",
        weighted: true,
      },
    ],
    practicalTips: [
      {
        afterEntitlement: 1,
        tip: {
          heading: "What to say",
          items: [
            "Say this: “This is a serious crime under section 85. I am entitled to have it registered here.”",
            "You can also say: “I would like a woman officer to record my statement, if one is available.” The law doesn't specifically require a woman officer for this complaint — that requirement applies to a different set of offences — but you're allowed to ask, and many stations will do this if you ask.",
            "Take someone with you if you can. A witness at the counter changes how a complaint like this gets received.",
          ],
        },
      },
    ],
    refusalHeading: "If you're turned away",
    refusalIntro: "Sometimes police say things like:",
    refusalBullets: ["“This is a family matter, sort it out at home.”", "“Come back with your husband.”", "“This isn't serious enough.”"],
    refusalOutro: "None of these are good reasons to refuse a serious crime. Here's what to do next.",
    refusalSteps: [
      {
        heading: "Step 1 — Write to the Superintendent of Police.",
        body: "Write down what happened, and send it by post to the Superintendent of Police — the senior police officer in charge of your district. The law says they must look into it themselves, or hand it to another officer to investigate.",
        act: "BNSS",
        section: "173",
      },
      {
        heading: "Step 2 — If that doesn't work, a magistrate can order an investigation.",
        body: "You can apply to a magistrate — a judge. You will need to sign a statement confirming what you're saying is true. The law lets the magistrate then order the police to investigate.",
        act: "BNSS",
        section: "175",
      },
    ],
    closingNote: [
      "If a death has occurred, that is a separate, far more serious matter with its own much heavier punishment — that is not something to handle through this page. Call 112 immediately.",
      "The law changed in 2024. If your situation started before then, that's fine — the police will apply whichever law fits. You don't need to work this out yourself.",
      "Every quote on this page is checked directly against the real law — nothing here is written from memory. Tap “Read the full section” to see the complete text.",
      "This page tells you what the law says. It cannot guarantee how any one police station will actually behave. NALSA: 15100. Women's Helpline: 181.",
    ],
  },

  {
    slug: "woman-reporting-harassment",
    navLabel: "Reporting harassment or stalking",
    navSummary:
      "Being followed, stalked, or harassed? What the law says the police and courts must do differently for you.",
    eyebrow: "Situation guide",
    title: "Reporting harassment or stalking",
    subtitle: "What counts. What you can expect from the police and the court. What to say if you're turned away.",
    openingLine:
      "This page is for when someone is following you, touching you, or harassing you in a way that keeps happening.",
    crossLink: {
      situationText: "If the person doing this lives with you or is family — a husband, or his relatives —",
      linkLabel: "see Facing cruelty at home instead",
      targetSlug: "domestic-cruelty",
    },
    recognition: {
      intro:
        "The law names specific things as criminal harassment of a woman — not just a general feeling that something is wrong. If any of these matches what's happening to you, you have a real complaint.",
      items: [
        {
          label:
            "Being followed or contacted repeatedly, or watched online, when you've made it clear you don't want that — the law calls this stalking.",
          quote:
            "follows a woman and contacts, or attempts to contact such woman to foster personal interaction repeatedly despite a clear indication of disinterest by such woman",
          act: "BNS",
          section: "78",
        },
        {
          label: "Someone touching you, or using force against you, meaning to disrespect you that way.",
          quote:
            "assaults or uses criminal force to any woman, intending to outrage or knowing it to be likely that he will thereby outrage her modesty",
          act: "BNS",
          section: "74",
        },
        {
          label: "Words, sounds, gestures, or being intruded on, meant to insult you.",
          quote: "utters any words, makes any sound or gesture, or exhibits any object … or intrudes upon the privacy of such woman",
          act: "BNS",
          section: "79",
        },
      ],
    },
    entitlementsHeading: "What you can expect from the police and the court",
    entitlementsIntro:
      "For these specific offences, the law adds protections that don't apply to every crime.",
    entitlements: [
      {
        number: 1,
        heading: "A woman police officer must record your complaint.",
        body: ["For these specific offences, the officer who writes down what happened must be a woman."],
        quote: "then such information shall be recorded, by a woman police officer or any woman officer",
        act: "BNSS",
        section: "173",
      },
      {
        number: 2,
        heading: "If it goes before a magistrate, a woman magistrate should record your statement wherever possible.",
        body: [
          "This should happen as soon as the police become aware of what happened, not months later.",
        ],
        quote:
          "the Magistrate shall record the statement of the person against whom such offence has been committed … as far as practicable, be recorded by a woman Magistrate",
        act: "BNSS",
        section: "183",
      },
    ],
    practicalTips: [
      {
        afterEntitlement: 1,
        tip: {
          heading: "If a woman officer isn't available",
          items: [
            "Say clearly: “The law requires a woman officer to record this, under section 173.”",
            "Take someone with you if you can — a family member, a friend, anyone.",
          ],
        },
      },
    ],
    refusalHeading: "If you're turned away",
    refusalIntro: "Sometimes police say things like:",
    refusalBullets: ["“This isn't serious enough.”", "“Sort it out privately.”", "“Come back later.”"],
    refusalOutro: "None of these are good reasons to refuse a serious crime. Here's what to do next.",
    refusalSteps: [
      {
        heading: "Step 1 — Write to the Superintendent of Police.",
        body: "Write down what happened, and send it by post to the Superintendent of Police — the senior police officer in charge of your district. The law says they must look into it themselves, or hand it to another officer to investigate.",
        act: "BNSS",
        section: "173",
      },
      {
        heading: "Step 2 — If that doesn't work, a magistrate can order an investigation.",
        body: "You can apply to a magistrate — a judge. You will need to sign a statement confirming what you're saying is true. The law lets the magistrate then order the police to investigate.",
        act: "BNSS",
        section: "175",
      },
    ],
    closingNote: [
      "CaseIQ has confirmed outraging modesty and insulting modesty as serious crimes the police can act on immediately. For stalking alone, that specific confirmation isn't in CaseIQ's data yet — if a station argues stalking by itself isn't serious enough, ask a free legal aid clinic to check.",
      "Every quote on this page is checked directly against the real law — nothing here is written from memory. Tap “Read the full section” to see the complete text.",
      "This page tells you what the law says. It cannot guarantee how any one police station will actually behave. NALSA: 15100. Women's Helpline: 181.",
    ],
  },

  {
    slug: "online-fraud",
    navLabel: "Online fraud",
    navSummary:
      "Lost money to a scam, phishing link, or fake call? What to do right now, and what the police must do.",
    eyebrow: "Situation guide",
    title: "You lost money to online fraud",
    subtitle:
      "What to do right now. What the law says you can expect. What to say if you're turned away.",
    openingLine:
      "This page is for exactly one thing: money was taken from you through a scam, a fake link, or a fraudulent call or message.",
    leadCallout: {
      heading: "Do this first, before you go to the police",
      note: "This part is practical advice from the government's own cyber crime website. It is not a quote from the law — that's why it looks different from the rest of this page.",
      paragraphs: [
        "Call 1930 right now. Or report at cybercrime.gov.in. Do this before you go to a police station.",
        "This is India's official cyber crime helpline.",
        "Speed matters a lot here. If you report fast, the bank may still be able to freeze the money before the fraudster moves it. If you wait — even one day — the money may already be gone.",
        "If you have these details, keep them ready: the transaction ID or UPI reference number, how much money, the date and time, and the account or UPI ID it went to. Don't wait to find these first. Call now. Give the details after.",
        "This does not replace an FIR. You should still go to the police and file one too. The rest of this page tells you what you can expect when you do.",
      ],
    },
    entitlementsHeading: "What you can expect from the police",
    entitlementsIntro:
      "Online fraud is normally treated as a serious crime. That means the police must act on it straight away. They cannot tell you to wait for a court's permission first. Because of this, the law gives you real things you can expect.",
    entitlements: [
      {
        number: 1,
        heading: "Any police station must take your complaint.",
        body: [
          "You do not need to find the \"right\" station. It does not matter where the fraud happened. It does not matter where you live. Any station has to write down what happened to you.",
          "People call this a \"Zero FIR.\" That is not a word the law itself uses — it's just what people call this rule. What the law actually says is that you can report a crime",
        ],
        quote: "irrespective of the area where the offence is committed",
        act: "BNSS",
        section: "173",
      },
      {
        number: 2,
        heading: "You get a copy of your complaint, free, right away.",
        body: ["Once the police write it down, ask for a copy. The law says you must get it"],
        quote: "free of cost",
        act: "BNSS",
        section: "173",
      },
      {
        number: 3,
        heading: "The police must update you within 90 days — even if you don't ask.",
        body: [
          "This is the one most people never hear about. It's often the reason a case goes quiet after the first visit.",
          "The law says the police must tell you how the investigation is going. They must do this within 90 days. They must do this on their own — you should not have to chase them for it. They can tell you by phone, by message, or any other way that reaches you.",
          "If 90 days have passed and no one has contacted you, the police have already missed something they were required to do. Asking about it isn't being impatient — it's pointing out a rule they broke.",
        ],
        quote: "inform the progress of the investigation … to the informant or the victim",
        act: "BNSS",
        section: "193",
        weighted: true,
      },
    ],
    practicalTips: [
      {
        afterEntitlement: 1,
        tip: {
          heading: "If a station hesitates or tries to send you elsewhere",
          items: [
            "Say this: “This is a serious crime. I am entitled to have it registered here, under section 173.” You don't need to say more than that. Saying it clearly and calmly is often enough.",
            "Take someone with you if you can — a family member, a friend, anyone. Reports get taken more seriously when someone isn't alone.",
          ],
        },
      },
    ],
    refusalHeading: "If a police station still refuses to write down your report",
    refusalIntro: "Sometimes police say things like:",
    refusalBullets: [
      "“This isn't our area.”",
      "“Go report it online instead.”",
      "“Come back later.”",
    ],
    refusalOutro:
      "None of these are good reasons to refuse a serious crime. You already know that from above. Here's what to do next.",
    refusalSteps: [
      {
        heading: "Step 1 — Write to the Superintendent of Police.",
        body: "Don't give up. Write down what happened, and send it by post to the Superintendent of Police — the senior police officer in charge of your district. The law says they must look into it themselves, or hand it to another officer to investigate.",
        act: "BNSS",
        section: "173",
      },
      {
        heading: "Step 2 — If that doesn't work, a magistrate can order an investigation.",
        body: "If the Superintendent of Police also does nothing, you can apply to a magistrate — a judge. You will need to sign a statement confirming what you're saying is true. The law lets the magistrate then order the police to investigate.",
        act: "BNSS",
        section: "175",
      },
    ],
    closingNote: [
      "Online fraud has been treated as a serious crime for years, and police generally register these cases. CaseIQ has confirmed this in the old law but not yet in the new one — if a station argues your case isn't serious enough, ask a free legal aid clinic (NALSA: 15100) to check.",
      "Every quote on this page is checked directly against the real law — nothing here is written from memory. Tap “Read the full section” to see the complete text.",
      "This page tells you what the law says. It cannot guarantee how any one police station will actually behave. If your situation is different from what's described here, talk to a lawyer or your nearest free legal aid clinic.",
    ],
  },

  {
    slug: "fir-refused",
    navLabel: "FIR refused",
    navSummary:
      "Police won't write down your complaint? What the law says they must do, and how to escalate.",
    eyebrow: "Situation guide",
    title: "The police won't register my complaint",
    subtitle: "What to say right now. What the law says they must do. What to do if they still refuse.",
    openingLine:
      "This page is for exactly one situation: you tried to report a crime, and the police at the station wouldn't write it down.",
    entitlementsHeading: "What the law says",
    entitlementsIntro:
      "The rules below apply when what happened to you is what the law calls a \"cognizable offence\" — a serious crime the police can act on right away, without asking a court first. Most crimes people report — theft, assault, robbery, serious fraud — are cognizable. If you're not sure whether yours counts, a free legal aid clinic can tell you. NALSA: 15100.",
    entitlements: [
      {
        number: 1,
        heading: "Any police station must take your complaint.",
        body: [
          "You do not need to find the \"right\" station. It does not matter where the crime happened. It does not matter where you live. Any station has to write down what happened to you.",
          "People call this a \"Zero FIR.\" That is not a word the law itself uses — it's just what people call this rule. What the law actually says is that you can report a crime",
        ],
        quote: "irrespective of the area where the offence is committed",
        act: "BNSS",
        section: "173",
      },
      {
        number: 2,
        heading: "You get a copy of your complaint, free, right away.",
        body: ["Once the police write it down, ask for a copy. The law says you must get it"],
        quote: "free of cost",
        act: "BNSS",
        section: "173",
      },
      {
        number: 3,
        heading: "The police must update you within 90 days — even if you don't ask.",
        body: [
          "This is the one most people never hear about. It's often the reason a case goes quiet after the first visit.",
          "The law says the police must tell you how the investigation is going. They must do this within 90 days, on their own — you should not have to chase them for it.",
          "If 90 days have passed and no one has contacted you, the police have already missed something they were required to do.",
        ],
        quote: "inform the progress of the investigation … to the informant or the victim",
        act: "BNSS",
        section: "193",
        weighted: true,
      },
    ],
    practicalTips: [
      {
        afterEntitlement: 1,
        tip: {
          heading: "What to say, right now",
          items: [
            "Say this: “This is a serious crime. I am entitled to have it registered here, under section 173.” You don't need to say more than that.",
            "Take someone with you if you can — a family member, a friend, anyone.",
            "Note the officer's name and badge number, and the time. If you need to complain later, this helps.",
          ],
        },
      },
    ],
    refusalHeading: "If they still refuse",
    refusalIntro: "Sometimes police say things like:",
    refusalBullets: ["“This isn't our area.”", "“This isn't serious enough.”", "“Come back later.”"],
    refusalOutro: "None of these are good reasons to refuse a serious crime. Here's what to do next.",
    refusalSteps: [
      {
        heading: "Step 1 — Write to the Superintendent of Police.",
        body: "Don't give up. Write down what happened, and send it by post to the Superintendent of Police — the senior police officer in charge of your district. The law says they must look into it themselves, or hand it to another officer to investigate.",
        act: "BNSS",
        section: "173",
      },
      {
        heading: "Step 2 — If that doesn't work, a magistrate can order an investigation.",
        body: "If the Superintendent of Police also does nothing, you can apply to a magistrate — a judge. You will need to sign a statement confirming what you're saying is true. The law lets the magistrate then order the police to investigate.",
        act: "BNSS",
        section: "175",
      },
    ],
    closingNote: [
      "This page describes what the law requires when a crime is \"cognizable.\" Whether your specific situation qualifies can depend on details a lawyer or legal aid clinic can check for you. NALSA: 15100.",
      "Every quote on this page is checked directly against the real law — nothing here is written from memory. Tap “Read the full section” to see the complete text.",
      "This page tells you what the law says. It cannot guarantee how any one police station will actually behave.",
    ],
  },

  {
    slug: "arrested-or-detained",
    navLabel: "Arrested or detained",
    navSummary: "What the police must do during an arrest, and what to say if a right isn't given to you.",
    eyebrow: "Situation guide",
    title: "You've been arrested or detained",
    subtitle: "What matters most right now. What to say if something isn't happening.",
    openingLine:
      "This page is for right after an arrest — yours, or someone you know's — while it's still happening or just happened.",
    leadCallout: {
      heading: "Right now",
      note: "This part is practical advice, not a quote from the law.",
      paragraphs: [
        "Stay calm. Do not resist, even if you believe the arrest is wrong. Resisting can lead to extra charges, and it can be used against you later.",
        "Save your objections for a lawyer, not for the moment of arrest. Cooperate physically, and use the rights below instead.",
      ],
    },
    entitlementsHeading: "What the police must do",
    entitlementsIntro:
      "The moment someone is arrested, the law gives real, specific things they can expect. These apply to everyone, regardless of what they're accused of.",
    entitlements: [
      {
        number: 1,
        heading: "You must be produced before a magistrate within 24 hours.",
        body: [
          "This is the single strongest check on how long the police can hold someone. Past 24 hours, only a magistrate can allow it to continue — the police alone cannot.",
          "The 24 hours does not count the time it takes to travel to court.",
        ],
        quote:
          "exceed more than twenty-four hours exclusive of the time necessary for the journey from the place of arrest",
        act: "BNSS",
        section: "58",
        weighted: true,
      },
      {
        number: 2,
        heading: "You must be told why you're being arrested.",
        body: [
          "This must happen straight away — not later at the station, and not only after questioning starts.",
        ],
        quote: "full particulars of the offence for which he is arrested",
        act: "BNSS",
        section: "47",
      },
      {
        number: 3,
        heading: "A relative or friend must be told where you are.",
        body: [
          "The police must contact someone you name — as soon as you're brought in, not hours later.",
        ],
        quote: "give the information regarding such arrest and place where the arrested person is",
        act: "BNSS",
        section: "48",
      },
      {
        number: 4,
        heading: "You can meet a lawyer during questioning.",
        body: [
          "Not throughout continuous questioning, but the right to meet a lawyer of your own choosing is real, not just implied.",
        ],
        quote: "to meet an advocate of his choice during interrogation, though not throughout interrogation",
        act: "BNSS",
        section: "38",
      },
      {
        number: 5,
        heading: "You have a right to a medical examination.",
        body: ["A medical officer must examine the arrested person soon after arrest, and note down any injuries."],
        quote: "he shall be examined by a medical officer",
        act: "BNSS",
        section: "53",
      },
    ],
    practicalTips: [
      {
        afterEntitlement: 1,
        tip: {
          heading: "This is the hardest right to assert — have the words ready",
          items: [
            "Say clearly: “I must be produced before a magistrate within 24 hours. That is my right under section 58.” This is worth repeating if you're held past that point.",
          ],
        },
      },
      {
        afterEntitlement: 2,
        tip: {
          heading: "If you aren't told",
          items: [
            "Ask clearly: “What is the offence? I am entitled to be told, under section 47.” You don't need to say more than that.",
          ],
        },
      },
      {
        afterEntitlement: 3,
        tip: {
          heading: "What to say",
          items: [
            "Give the police one clear name and phone number: “Please inform [name] at [number] where I am being held.” This is required of them, not a favour.",
          ],
        },
      },
    ],
    refusalHeading: "If any of this isn't happening",
    refusalIntro: "This can look like:",
    refusalBullets: [
      "Not told why you're being arrested",
      "No one contacted on your behalf",
      "Held well past 24 hours with no magistrate involved",
    ],
    refusalOutro:
      "If so, say so clearly the moment you're brought before a magistrate — that is exactly when this is meant to be checked.",
    refusalSteps: [
      {
        heading: "Tell the magistrate directly.",
        body: "When you're produced in court, say plainly what didn't happen. Ask for a lawyer immediately if you don't already have one. The magistrate has the power to act on this — that's the entire point of the 24-hour rule.",
        act: "BNSS",
        section: "58",
      },
    ],
    closingNote: [
      "This page describes what the law requires. It cannot guarantee how any one police station will behave in the moment.",
      "Every quote here is checked directly against the real law — nothing is written from memory. Tap “Read the full section” to see the complete text.",
      "If these rights aren't being honoured, tell a lawyer or a free legal aid clinic as soon as you can. NALSA: 15100.",
    ],
  },
];
