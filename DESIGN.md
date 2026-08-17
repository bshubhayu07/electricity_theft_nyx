# Smart Grid Electricity Theft Detection - Design System & Visual Specification

**Version:** 2.4.0-enterprise  
**Purpose:** Standardized design system, typography scale, color tokens, and visual accessibility rules for smart grid operational analytics interfaces.

---

## 1. Color Palette & Dark Slate Design Tokens

The visual interface adheres to an enterprise dark slate color system optimized for high legibility, low eye fatigue in control room environments, and crisp data contrast.

```css
:root {
  /* Surface & Background Tokens */
  --bg-dark: #0F172A;          /* Deep Slate Base */
  --card-bg: #1E293B;          /* Elevated Card Surface */
  --card-border: #334155;      /* Structural Card Outline */
  --card-hover: #0F172A;       /* Interactive Hover State */

  /* Typographic Tokens */
  --text-main: #F8FAFC;        /* Primary High-Contrast Text */
  --text-muted: #94A3B8;       /* Subtitle & Secondary Label Text */
  --text-subtle: #64748B;      /* De-emphasized Annotations */

  /* Accent & Risk Level Indicators */
  --accent-cyan: #06B6D4;      /* Primary Action & Active Tab Indicator */
  --accent-blue: #3B82F6;      /* Supervised ML Component Highlight */
  --accent-emerald: #10B981;   /* Unsupervised Anomaly Component Highlight */
  --accent-amber: #F59E0B;     /* Composite Risk & Warning Highlight */
  --accent-red: #EF4444;       /* Critical Risk & Discard Alert */
}
```

---

## 2. Component Layout & Glassmorphism Guidelines

### Elevated Data Cards
* **Background:** `rgba(30, 41, 59, 0.95)` with `backdrop-filter: blur(12px)`
* **Border:** `1px solid #334155`
* **Border Radius:** `8px`
* **Padding:** `16px 20px`

### Interactive Data Grids & Tables
* **Header Background:** `rgba(15, 23, 42, 0.8)` with uppercase 11px bold text.
* **Row Alternation:** Subtly alternating background tint (`rgba(15, 23, 42, 0.4)` vs `rgba(15, 23, 42, 0.1)`).
* **Hover State:** Highlight row on mouseover with border outline `#06B6D4`.

---

## 3. Visual Chart & Graph Standards

1. **Plotly Dark Theme Integration:** All charts utilize `template="plotly_dark"` with transparent background (`paper_bgcolor="rgba(0,0,0,0)"`).
2. **Scatter Quadrant Plots:** Always include reference threshold lines (`x=0.5`, `y=0.5`) in dashed `#64748B` to visually segment known theft from zero-day anomalies.
3. **No Decorative Emojis:** All UI text, chart labels, section headers, and audit reasons must remain free of decorative emojis.
