# Agent notes

## Commits

- Commit feature by feature: one commit per logical change.
- Keep commit messages minimal (a short summary line, little or no body).
- No attribution lines (no `Co-Authored-By`, no "Generated with" footers).

## Planned work

- Favorite folders in the folder tree next to the file changelist, stored
  in a cookie (a list of folder ids, cookie name includes the user id). Not in
  the database, to avoid a model, a migration and an API; not in localStorage,
  because the tree is rendered on the server, which needs the favorites. They
  are per browser, not across devices. Rendered above the tree with the full
  path as label (favorites may live outside the current root), toggled with a
  star, and usable as drop targets like the tree folders. Unknown or deleted
  folder ids are ignored.
