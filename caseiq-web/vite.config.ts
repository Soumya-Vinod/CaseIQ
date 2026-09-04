import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Vite 8 defaults CSS minification to lightningcss with NO compatibility
    // target, which lets it rewrite every `min-width`/`max-width` media
    // query into the newer CSS Media Queries Level 4 range syntax
    // (`width<=859px`) as a size optimisation. That syntax needs Chrome/
    // Chrome-for-Android 104+, Safari 16.4+, Samsung Internet 20+ (~94.8%
    // global support per caniuse) -- fine for most projects, silently wrong
    // for this one. CaseIQ (docs/caseiq-industry-readiness.md G13) targets
    // Indian users on budget, non-flagship Android, and real usage data for
    // that audience (`npx browserslist "> 0.5%, last 2 versions, not dead"`,
    // 84.6% global coverage) still bottoms out no lower than Chrome 109 --
    // just above the cutoff -- because usage-share stats systematically
    // under-count exactly the old/budget-device tail this project cares
    // about (frozen WebView versions on Android 8/9 phones that stopped
    // receiving Chrome updates years ago don't show up as "current traffic"
    // the way a live crawl measures it). So the floor below is set by hand,
    // below both the range-syntax cutoff and what the usage query alone
    // would pick: Chrome/Edge 90 (Apr 2021 -- the version a lot of budget
    // Android 8/9 devices are frozen on; Samsung Internet, itself Chromium-
    // based, has no separate esbuild target key and is covered by the same
    // Chrome floor), Firefox 91, Safari/iOS 14. Verified directly against
    // the installed lightningcss binary that this floor produces the
    // legacy `max-width:` form, not the range syntax -- see
    // docs/evaluation.md's "Media query range syntax" finding for the full
    // trace, including why Playwright can never catch a regression here
    // (its bundled Chromium is always new enough to support either syntax).
    //
    // KaiOS (JioPhone, real share in India per the same browserslist query)
    // is deliberately NOT targeted here -- its Gecko-derived engine is
    // missing far more than range-syntax media queries, and meeting it
    // would mean not shipping a React SPA at all. Out of scope, stated
    // rather than silently ignored.
    cssTarget: ['chrome90', 'edge90', 'firefox91', 'safari14', 'ios14'],
  },
})
