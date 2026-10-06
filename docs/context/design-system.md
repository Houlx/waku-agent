# Career interface

Career Agent owns its independent styles in `waku/ops/static/career/style.css`.
The shell loads system fonts and no images, font files or external stylesheets.
CSS variables prefixed `--career-` define light and dark themes. The resume uses
system CJK fallback fonts and explicit print isolation.

The classic scripts share the `CA` namespace. `ui.js` owns escaping and interface
helpers; `render.js` owns screens. [The frontend map](../../waku/ops/static/README.md)
explains ownership and browser verification.

Waku design copies, marks and bundled fonts are retired. Do not restore or copy
protected upstream styling. [LICENSE-BRAND](../../LICENSE-BRAND) preserves the
terms for retained Waku names and references.
