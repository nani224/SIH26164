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
