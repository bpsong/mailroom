# daisyUI Integration Summary

## Overview

Current frontend stack in this repository:

- Tailwind CSS `^3.4.0`
- daisyUI `^4.12.0`
- HTMX `1.9.10` (loaded from CDN in `templates/base.html`)

Source of truth:
- `package.json`
- `tailwind.config.js`
- `static/css/input.css`
- `templates/base.html`

## Current Configuration

### Tailwind + daisyUI

Configured using Tailwind v3 directives in `static/css/input.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

daisyUI plugin is enabled via Tailwind config (`tailwind.config.js`).

### Build Commands

From `package.json`:

- `npm run build:css`
- `npm run watch:css`

## Components in Use

Common daisyUI components used throughout templates:

- `btn`, `input`, `select`, `textarea`, `file-input`
- `card`, `badge`, `alert`, `modal`, `dropdown`
- `table`, `drawer`, `navbar`, `menu`, `toast`, `loading`

## Notes

- This project is **not** on Tailwind v4 / daisyUI v5 at this time.
- Any migration plan should be treated as a separate upgrade task with template and CSS validation.

## Verification Checklist

- [ ] `npm ls tailwindcss daisyui` matches expected major versions
- [ ] CSS builds without warnings
- [ ] Core pages render correctly (`/dashboard`, `/packages`, `/admin/users`)
- [ ] Mobile drawer, modals, and form styling remain functional
