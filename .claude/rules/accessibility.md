---
description: Accessibility rules for the PWA (vanilla HTML + JS)
globs: "*.html,*.js,*.css"
---

# Accessibility

- Images: always set `alt`.
- Forms: every input has an associated `<label>` (or `aria-label` for
  pure icon controls).
- Interactive elements are keyboard-operable: Tab to reach, Enter /
  Space to activate, Escape to close overlays. The menu drawer and
  help/auth modals must trap focus visibly.
- Use semantic HTML: `<button>` (not `<div onclick>`), `<nav>`,
  `<main>`, `<aside>`. ARIA only when no native element fits.
- All i18n keys for aria-labels go through `data-i18n-aria` so the
  language switch updates them too. Never hardcode an `aria-label`
  that is also user-visible text in another language.
- Color contrast: WCAG AA (4.5:1 for text, 3:1 for large/UI elements).
  The dark and light themes both meet this; verify on new components.
- Focus ring visible during keyboard navigation. The global
  `:focus-visible` rule covers this — don't override it per component
  without an equivalent.
- Respect `prefers-reduced-motion` for any new animation longer than
  a brief micro-interaction.
