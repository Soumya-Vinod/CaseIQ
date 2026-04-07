/**
 * extractFIRPrefill
 * 
 * Reads the last AI response from localStorage and extracts
 * structured data to pre-fill the FIR wizard.
 * 
 * Returns an object matching FIRWizard's formData shape,
 * or null if nothing useful found.
 */

const SECTION_PATTERNS = [
  /BNS\s+(?:Section\s+)?(\d+[A-Z]?)/gi,
  /BNSS\s+(?:Section\s+)?(\d+[A-Z]?)/gi,
  /IPC\s+(?:Section\s+)?(\d+[A-Z]?)/gi,
  /Section\s+(\d+[A-Z]?)\s+(?:of\s+)?(?:BNS|BNSS|IPC|BSA)/gi,
];

const DATE_PATTERN = /\b(\d{1,2}[\s/-]\w+[\s/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})\b/g;

const LOCATION_KEYWORDS = [
  'at', 'near', 'in', 'inside', 'outside', 'from', 'location:', 'place:'
];

export function extractFIRPrefill(messages = []) {
  if (!messages || messages.length === 0) return null;

  // Get all user messages to form the incident description
  const userTexts = messages
    .filter((m) => m.sender === 'user')
    .map((m) => m.text);

  if (userTexts.length === 0) return null;

  // Use the combined user messages as the incident description
  const combinedUserText = userTexts.join(' ');
  const description = combinedUserText.slice(0, 800);

  // Extract BNS/IPC sections from AI responses
  const aiTexts = messages
    .filter((m) => m.sender === 'ai')
    .map((m) => m.text)
    .join(' ');

  const sections = new Set();
  for (const pattern of SECTION_PATTERNS) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(aiTexts)) !== null) {
      // Get the act name from the pattern match context
      const fullMatch = match[0];
      sections.add(fullMatch.replace(/\s+/g, ' ').trim());
    }
  }

  // Extract incident date if mentioned
  let incidentDate = '';
  const dateMatches = combinedUserText.match(DATE_PATTERN);
  if (dateMatches && dateMatches.length > 0) {
    // Try to parse the first found date
    try {
      const parsed = new Date(dateMatches[0]);
      if (!isNaN(parsed.getTime())) {
        // Format as YYYY-MM-DD for the date input
        incidentDate = parsed.toISOString().split('T')[0];
      }
    } catch { /* skip */ }
  }

  // Try to extract a location hint from user messages
  let locationHint = '';
  const lowerText = combinedUserText.toLowerCase();
  for (const keyword of LOCATION_KEYWORDS) {
    const idx = lowerText.indexOf(` ${keyword} `);
    if (idx !== -1) {
      // Take the next ~30 chars after the keyword as a location hint
      const slice = combinedUserText.slice(idx + keyword.length + 2, idx + keyword.length + 40);
      const words = slice.split(/[,.!?]/)[0].trim();
      if (words.length > 3 && words.length < 60) {
        locationHint = words;
        break;
      }
    }
  }

  // Determine FIR type hint from AI response
  const firType = aiTexts.toLowerCase().includes('non-cognizable')
    ? 'Non-Cognizable'
    : 'Cognizable';

  // Build the applicable section string
  const applicableSection = Array.from(sections).slice(0, 3).join(', ');

  return {
    description,
    incidentDate,
    incidentLocation: locationHint,
    applicableSection,
    firType,
    _prefilled: true,
    _sourceMessageCount: userTexts.length,
  };
}

/**
 * saveFIRPrefill
 * Saves prefill data to localStorage for FIRWizard to read on mount.
 */
export function saveFIRPrefill(messages) {
  const prefill = extractFIRPrefill(messages);
  if (prefill) {
    localStorage.setItem('caseiq_prefill_fir', JSON.stringify({
      ...prefill,
      savedAt: Date.now(),
    }));
    return true;
  }
  return false;
}

/**
 * loadFIRPrefill
 * Reads and clears prefill data from localStorage.
 * Returns the prefill object or null.
 * Only valid for 10 minutes to avoid stale data.
 */
export function loadFIRPrefill() {
  try {
    const raw = localStorage.getItem('caseiq_prefill_fir');
    if (!raw) return null;

    const data = JSON.parse(raw);

    // Expire after 10 minutes
    const TEN_MINUTES = 10 * 60 * 1000;
    if (Date.now() - (data.savedAt || 0) > TEN_MINUTES) {
      localStorage.removeItem('caseiq_prefill_fir');
      return null;
    }

    return data;
  } catch {
    return null;
  }
}

/**
 * clearFIRPrefill
 * Call this after the wizard has consumed the prefill data.
 */
export function clearFIRPrefill() {
  localStorage.removeItem('caseiq_prefill_fir');
}