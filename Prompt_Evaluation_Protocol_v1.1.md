# Prompt Evaluation Protocol
**Iain Stark — Personal Learning & Development**

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v1.0 | June 2026 | Created following Manchester test failure post-deployment |
| v1.1 | June 2026 | Dublin test completed. Added closed venue failure type to classification table. Updated known failures log. |

---

## Purpose

This protocol defines the minimum evaluation required before deploying or sharing any AI tool built with chaining workflows. It exists because a single test on familiar ground is not sufficient to characterise how a tool behaves — the Ballater test proved the chain worked; the Manchester test exposed that the verification step was failing on unfamiliar ground.

**Standing rule: two known + one unknown test before any deployment.**

---

## When to Apply This Protocol

- Before deploying any chaining tool to a live URL
- Before sharing a tool with anyone else
- After any prompt change — re-run the minimum test suite
- After any model change

---

## The Minimum Test Suite

Every tool needs at least three test runs before deployment:

| Test | Type | Purpose |
|------|------|---------|
| Test 1 | **Known ground** | A case where you can verify the output from memory |
| Test 2 | **Known ground, different input** | A second case you know well — confirms Test 1 was not a lucky run |
| Test 3 | **Unknown ground** | A case where you cannot verify from memory — forces the tool to stand on its own |

The unknown ground test is the most important. If a tool only ever gets tested on inputs the builder knows well, errors that the tool should catch will be missed because the builder catches them instead.

---

## Per-Run Evaluation Checklist

After each test run, work through this checklist before calling it a pass.

### 1. Factual accuracy
- [ ] Are all named venues, businesses, and attractions real and currently trading?
- [ ] Are all dates correct and within the supplied travel window?
- [ ] Are all events confirmed for the correct year — not a past or future year?
- [ ] Are all web addresses correct and resolving?

### 2. Verification behaviour
- [ ] Did the verification step actually search for the items it was supposed to check?
- [ ] Are CHECK_FAIL items excluded from the output, or just flagged?
- [ ] Are any stale or unverifiable results being passed through rather than cut?
- [ ] Did the tool search for closed/relocated status on all named venues?

### 3. Output quality
- [ ] Is the output free of clutter from unverified or out-of-scope items?
- [ ] Does the Before You Go checklist contain only genuinely uncertain items?
- [ ] Is the pacing realistic for the group described in the brief?
- [ ] Are brief constraints (no car, mobility, budget) respected throughout?

### 4. Edge case handling
- [ ] What happens if no events are found? Does the tool degrade gracefully?
- [ ] What happens if a venue cannot be verified? Is it excluded or flagged correctly?
- [ ] What happens with an unusually short or long trip brief?

---

## Failure Classification

When a test run fails, classify the failure before fixing it.

| Failure type | Description | Fix location |
|---|---|---|
| **Prompt failure** | Claude followed the instructions but the instructions were wrong or incomplete | System prompt |
| **Verification failure** | The verification step did not search, or searched but did not act on what it found | VERIFY_SYSTEM + FORMAT_SYSTEM prompts |
| **Stale data failure** | Web search returned outdated pages and Claude did not reject them | DISCOVER_SYSTEM — add explicit year confirmation requirement |
| **Closed venue failure** | A permanently closed or relocated venue included without flagging | VERIFY_SYSTEM — add trading status check |
| **Architecture failure** | The chain structure itself is the problem | Code restructure |

---

## Documenting Test Runs

Record each test run in this format:

    Tool: [name]
    Date: [date]
    Test type: known / unknown
    Brief: [the input used]
    Pass/Fail:
    Failures found:
      - [description] | Type: [failure type]
    Fix applied:
      - [what was changed and where]
    Re-test result:

---

## Itinerary Planner — Known Failures Log

| Date | Test | Failure | Type | Status |
|------|------|---------|------|--------|
| June 2026 | Ballater, 10–14 Aug 2026 | Balmoral August closure missed in first run | Verification failure | Fixed — Verification Protocol 2 created |
| June 2026 | Manchester, 10–13 Jul 2026 | Bluedot Festival (last ran 2023), Parklife and Manchester Jazz outside travel dates included | Stale data + verification failure | Fixed — CRITICAL YEAR RULE, CRITICAL REMOVAL RULES, CRITICAL EXCLUSION RULE added to prompts. Re-test passed. |
| June 2026 | Manchester re-test, 10–13 Jul 2026 | Re-test after prompt fix | — | Pass — all three events absent. Output clean and actionable. |
| June 2026 | Dublin, 18–22 Sep 2026 | Dublin Writers Museum (closed 2022) included as visitable. Chapter One address listed at same building. | Closed venue failure | Fixed — trading status check added to VERIFY_SYSTEM. Re-test pending. |

---

## Relationship to Existing Protocols

- **Verification Protocol 1** (data/analysis) — source-check before any derivative content
- **Verification Protocol 2** (time-sensitive real-world claims) — verify venues and dates against actual travel dates
- **AI Build Framework** — operational reality check step at end of any build

The evaluation protocol is the pre-deployment gate. Verification Protocols 1 and 2 are runtime behaviour built into the tool itself.
