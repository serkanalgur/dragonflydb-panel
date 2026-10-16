## What

<!-- One or two sentences. What changes, for whom. -->

## Why

<!-- The problem being solved. Link the issue if there is one: Closes #123 -->

## How it was verified

- [ ] `./scripts/test.sh` passes
- [ ] Tested against a real aaPanel instance (only if the change affects runtime behaviour)
- [ ] `./scripts/package.sh` produces an installable zip (if the plugin payload changed)

## Release

- [ ] This changes plugin behaviour, so `versions` in `info.json` is bumped in this branch
- [ ] Documentation or CI only, no bump needed

## Risk

<!-- What could break, and how it would show up. "None, docs only" is a valid answer. -->

## Notes for the reviewer

<!-- Contracts are easy to violate silently. Call out anything touching
     dragonflydb_main.py or index.html, any gate you had to change (and why),
     and any decision you made that you would defend differently. -->
