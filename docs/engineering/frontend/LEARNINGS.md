# Technical Learnings & Gotchas

### 1. Air-Gapped Fonts & Runtime
- No external Google Font CDN fetches allowed at runtime. Fonts must be loaded locally using `next/font/local` or bundled variable fonts.
- All dependencies must be statically bundled or work without external outbound requests.

### 2. OKLCH Perceptual Uniformity
- Unlike standard sRGB/HSL where perceived lightness fluctuates drastically across hues (yellow appears far brighter than blue), OKLCH maintains consistent perceived lightness ($L$).
- For semantic alert states, fixing lightness at $L \approx 0.62$ for dark mode ensures WCAG AA contrast against dark surfaces ($\ge 4.5:1$) while preventing eye fatigue.

### 3. Classically Broken UI Accessibility
- Color alone cannot signify classically broken algorithms (Section 7 rule).
- We pair magenta-violet with a continuous 45-degree diagonal hatch pattern (`repeating-linear-gradient`) and an explicit `[BROKEN]` textual tag, ensuring immediate recognition under protanopia, deuteranopia, and tritanopia color blindness.

### 4. Mosca Re-Scoring Invariants
- Classically broken algorithms (DES, MD5, SHA-1, RC4, ECB) have $U = 1$ by definition. Changing CRQC horizon $Z$ MUST NOT change their risk score or band.
- Moving $Z$ only shifts quantum-vulnerable public key algorithms (RSA, ECC, DH).

### 5. Playwright Service Worker Isolation
- When executing Playwright tests where some suites need offline MSW service worker mocks while others (`finale-integration.spec.ts`) need live backend integration, Playwright workers retain registered service workers across page navigations.
- Using `test.use({ serviceWorkers: 'block' })` at the suite level cleanly prevents service worker registration and intercept for live backend test runs without affecting mock-driven suites.

### 6. MSW Initialization Lifecycle in App Router
- Setting `ready` state initially to `shouldBypass` in `MswProvider` ensures that when MSW is deliberately disabled or bypassed for backend integration, the UI renders immediately without flashing the initialization spinner.

### 7. Skeleton Loader Token Conformance for Automated Gates
- Automated architecture gates checking for zero-mock-leak fallback behavior look for `.animate-pulse` classes on skeleton loaders during network delays. All loading fallback containers must include `animate-pulse` to be recognized by automated architecture assertions.

