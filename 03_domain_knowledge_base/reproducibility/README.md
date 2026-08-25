# Archived Domain Knowledge Base

`dkb_japan_bda2026_experimental.json` is the exact Domain Knowledge Base file used
for the BDA 2026 generations reported in the paper. It is kept unchanged so the
reported runs remain reproducible.

The active file, `../dkb_japan.json`, corrects the documentation of the PM2.5
category bands stored in JPM2KG under `ObservedPM25.pm25_level`. The canonical
graph values and the query behaviour exercised in the reported experiment are
unchanged: the category strings, the enumerations, the traversal policies and
the query patterns are identical in both files.
