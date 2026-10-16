# Agent notes

## Commits

- Commit feature by feature: one commit per logical change.
- Keep commit messages minimal (a short summary line, little or no body).
- No attribution lines (no `Co-Authored-By`, no "Generated with" footers).

## Planned work

- Prototype a collapsible folder tree next to the file changelist. Files
  should be movable by dragging them onto any folder in the tree; today only
  the visible subfolders and `../` could be drop targets, which isn't useful
  enough. The tree could also hold favorite folders (client side in
  `localStorage`, or server side if they should be shared across devices or
  the team).
