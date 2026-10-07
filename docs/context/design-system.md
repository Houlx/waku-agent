# Career interface

Career Agent owns its independent styles in `waku/ops/static/career/style.css`.
The shell loads system fonts and no images, font files or external stylesheets.
CSS variables prefixed `--career-` define light and dark themes. The resume uses
system CJK fallback fonts and explicit print isolation.

The desktop shell uses a 260px left sidebar and document scrolling for main content.
Below 900px, navigation and Recent Jobs share an expandable section. Long titles and
translated labels wrap. Sidebar selections use stable job IDs for reports and resumes.

Contextual bars use `position: sticky` at the viewport top, opaque theme backgrounds
and wrapping controls. Profile save/confirm, analysis, resume generation and export
controls belong in these bars. Delete, record removal, evidence and back links stay
contextual. A native confirmation dialog explains permanent Job deletion. Print
media hides the sidebar, dialog and application controls for native and explicit printing.

Job reports separate scored required/preferred groups from Needs confirmation and
Not scoreable clauses. Excluded clauses show their source and eligibility reason
without MATCH/PARTIAL/GAP badges. Null Coverage reports insufficient scoreable
information and disables resume generation.

The interface supports English and Simplified Chinese. UI language controls never
change stored artifacts or the selected resume language. System fonts supply CJK glyphs.

The classic scripts share the `CA` namespace. `ui.js` owns escaping and interface
helpers; `render.js` owns screens. [The frontend map](../../waku/ops/static/README.md)
explains ownership and browser verification.

Waku design copies, marks and bundled fonts are retired. Do not restore or copy
protected upstream styling. [LICENSE-BRAND](../../LICENSE-BRAND) preserves the
terms for retained Waku names and references.
