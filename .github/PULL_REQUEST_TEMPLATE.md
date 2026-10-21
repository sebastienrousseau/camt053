<!--
Keep these sections and their order; fill every line from real evidence.
- Title: a Conventional Commit, e.g. "fix: keep the AC04 filter case-blind".
- Open with two lines, each its own paragraph: line 1 begins "This PR " and
  says what it does; line 2 says why it matters or the outcome.
- Write it plainly. No em dash characters anywhere in the body; use commas,
  colons, parentheses or a spaced hyphen. No tool-attribution footer.
- Every commit is signed (SSH or GPG) and signed off (`git commit -s`).
-->

This PR <what it does, in one plain line>.

<Why it matters or the outcome, in one plain line.>

## Highlights ⭐️

* **<Headline>**: <one or two plain sentences on what changed for the user>.
* **<Headline>**: <one or two plain sentences>.

## What's Changed

* `<commit subject>` by @<author>

<Optional: a few detail bullets naming files and the concrete change.
Name the issues this closes ("Closes #123") and anything deferred, with
the reason.>

## Validation

* `make check`: <result, with numbers: tests passed, coverage %>.
* `poetry run python scripts/check_complexity.py`: <result>.
* `poetry build && twine check dist/*`: <result>.

## Checksums

SHA-256 of the artifacts produced by `poetry build` on this branch:

```text
<sha256>  dist/camt053-<version>-py3-none-any.whl
<sha256>  dist/camt053-<version>.tar.gz
```

**Full Changelog**: https://github.com/sebastienrousseau/camt053/compare/<previous tag>...<this branch>
