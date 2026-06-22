---
orphan: true
---

<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Hacker News submission template

When you're ready to post
[`2026-06-22-shipping-camt053-v006-for-the-november-2026-cliff.md`](2026-06-22-shipping-camt053-v006-for-the-november-2026-cliff.md)
to Hacker News.

## Title (≤ 80 chars; HN truncates harder than that)

```
Show HN: camt053 v0.0.6 — ISO 20022 bank-statement suite for the Nov 2026 cliff
```

Alternates if the above feels too long once published:

- `camt053 v0.0.6: ISO 20022 bank-statement suite (Python, MCP, LSP)`
- `Show HN: A 5-package ISO 20022 camt.053 suite for the Nov 2026 cliff`
- `Shipping for the 14-16 Nov 2026 ISO 20022 cross-border cutover`

The first form is preferable: "Show HN" is the HN tag for projects
you built and are sharing; "Nov 2026 cliff" is the news hook (most
finance-adjacent readers know roughly what the cliff is and care).

## URL

Point to the blog post on whatever you publish to:

- If on your own domain (preferred): `https://sebastienrousseau.com/posts/camt053-v006-nov-2026-cliff`
- If on GitHub Pages: `https://sebastienrousseau.github.io/camt053/posts/2026-06-22-shipping-camt053-v006-for-the-november-2026-cliff.html`
- If on Substack / Dev.to / Medium: the canonical post URL

**Pick one URL and stick with it.** HN dedupes by URL; if a similar
URL has been submitted before, the new submission gets silently
marked "duplicate" and never reaches the front page.

## Submission body (first comment)

HN's first comment from the author traditionally summarises the
post and invites the conversation. The whole audience reads it
even when they don't read the article. Keep it ≤ 200 words.

> I just shipped v0.0.6 of camt053 (https://github.com/sebastienrousseau/camt053),
> a Python library for ISO 20022 `camt.05x` bank statements — parse,
> validate, reverse — timed against the 14-16 November 2026
> coordinated CBPR+ / Fedwire / CHAPS / T2 cutover. After that
> weekend, payments carrying unstructured-only postal addresses get
> rejected at FINplus, MT 19x exception flows are retired, and T2/T2S
> RTGS upgrades to MR2026.
>
> Five months out, the producer/consumer schema gap is real: banks
> ship `.001.08`, ERPs still consume `.001.02`. The library handles
> the version negotiation explicitly and ships a `check_cbpr_readiness`
> pre-flight you can run before forwarding a payload on.
>
> v0.0.6 lands across a vertical slice — core + CLI + REST API +
> MCP server + LSP server — with two companion packages
> (Excel writer, MT940 loader). Every package is 100% line + branch
> coverage in CI, ships SLSA L3 + PEP 740 attestations, and maps every
> control to NIST SP 800-218 SSDF practice IDs in SECURITY.md.
>
> Happy to take questions on the cliff, the schema gap, or what 100%
> coverage actually buys for an artefact that moves real money.

## Likely first-comment questions (pre-baked answers)

**"Why Python and not Java/Prowide?"**
> Prowide is excellent, but it's JVM-only, enterprise-licensed, and
> not pip-installable. Most fintech Python shops can't run JVM
> services next to their existing data pipelines. The camt053 suite
> targets the gap: pure Python, MIT/Apache 2.0 dual-licensed,
> pip-installable.

**"How is this different from `iso20022-mcp`?"**
> [`deniskarlinsky/iso20022-mcp`](https://github.com/deniskarlinsky/iso20022-mcp)
> ships 9 generic tools, 2 stars, no Prompts/Resources/Sampling, no
> auth. camt053-mcp ships 13 tools + 2 resources + a structured
> `reversal_preview` prompt + curated rulebook citations
> (`cite_rulebook`), all backed by the same `camt053.services` layer
> the CLI/REST API/LSP server use, so the agent's tools behave
> identically to the CLI.

**"100% coverage is a vanity metric."**
> Maybe in CRUD apps. For an artefact that moves real money and
> produces files clearing systems will reject if a single tag is
> wrong, 100% line + branch coverage is the minimum cost of "we
> tested the unhappy paths." The pain001 sister project
> (https://github.com/sebastienrousseau/pain001) shipped 1,265 tests
> at 100% coverage in v0.0.53; the camt053 suite follows the same
> floor.

**"What about validating XML in 2026? Surely XSD is dead."**
> Tell that to SWIFT, the Eurosystem, the Fed, and the BoE. ISO
> 20022 is XML, served as XML, validated against XSD. Until that
> stops being true (no signs of it in this decade) the library
> shape is the right one.

## What time to post

HN front-page traffic peaks **08:00-11:00 UTC** on weekdays
(early morning US East coast / end of EU morning). Tuesday and
Wednesday tend to outperform Monday. Avoid Friday afternoon and
weekend posts — they get buried by Show HN regulars submitting
from Asia / Pacific time zones.

If the post catches, expect:

- 200-400 comments in the first 4 hours
- A burst of GitHub stars (50-300 typically)
- A few dozen `pip install camt053` events visible in PyPI's
  daily download stats next day

If it doesn't catch (front page is hard; the front page algorithm
weighs many factors), repost it ONCE 24 hours later with a slightly
different angle / title. Twice is OK; three submissions of the same
URL gets the URL banned.

## After the front page

- Have the [v0.0.6 release notes](https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.6)
  ready to share verbatim — HN commenters will quote them.
- Be in `#payments` channels on the obvious Slacks (rfintech etc.).
  A few people will DM "I tried it; here's what broke" — those are
  the most valuable bug reports of the launch week.
- Pin a tweet / Bluesky / LinkedIn post linking the HN thread + the
  release notes.
- Don't argue with low-quality criticism on HN. The signal-to-noise
  ratio is what it is. Reply only when the question is a real one
  and your answer is useful to the silent 95%.

## Cross-post afterwards

- `/r/Python` (Python community) — same title is fine.
- `/r/fintech` (audience that actually uses ISO 20022) — tweak the
  title to lead with the Nov 2026 cliff.
- LinkedIn — paste the TL;DR + a screenshot of the version-matrix
  page.
- Lobste.rs — same URL, tag `python` + `release`.

Avoid `/r/programming` (covered by HN demographically; you'll get
the same crowd) unless the article also lands a generic-software
narrative.
