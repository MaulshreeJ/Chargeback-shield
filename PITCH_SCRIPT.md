# Chargeback Shield — 5-Minute Pitch Script

**Track:** Razorpay AI Buildathon 2026 — Track 02, AI Risk Manager
**Total runtime target:** 5:00 (the live-demo section's 1:45 already budgets real time for API round-trips, not just words — see the word/time note after each section)
**Live URL:** https://chargeback-shield-6egu.onrender.com/ — **warm it up 1-2 minutes before recording** (free tier sleeps after ~15 min idle and takes 30-60s to wake)
**Format:** Screen recording with voiceover. Cues in *[brackets]* are on-screen direction, not spoken. Almost the entire recording stays on one browser tab (the live dashboard) — the only two side trips are `/metrics` (one section) and the GitHub repo (one section).

---

## 0:00–0:25 — The problem (~65 words · 24s)

*[Screen: the live dashboard, already open, scrolled to the very top]*

"Imagine a completely normal payment. It succeeds. The merchant ships the product. Everything looks fine.

Then, two weeks later, the customer disputes it — and the merchant has a short window to prove the charge was legitimate, or lose the money.

That's a chargeback. Most fraud systems are built to stop the transaction before it happens. Almost none of them ask: what happens after?

That's what Chargeback Shield does."

## 0:25–1:00 — Predict, then Respond (~73 words · 27s)

*[Screen: same tab — point to the "STAGE 1 · PREDICT" and "STAGE 2 · RESPOND" cards already on the dashboard, right below the title]*

"Chargeback Shield works in two stages.

Predict: before a dispute is filed, we score every transaction for dispute risk — so a merchant can take a cheap action, like a confirmation email or a short hold, instead of guessing.

Respond: if a dispute does get filed, we identify what evidence that reason code requires, assemble it, and recommend fight, concede, or review.

That recommendation comes from a fixed, auditable policy — never from a model's best guess."

## 1:00–2:45 — Live demo (~205 words · ~75s speaking + ~30s of real clicks/API time = 1:45)

*[Screen: same tab throughout, scroll down section by section — this is the longest block, budgeted with real wait time, not just words]*

"Here's the system, live — not a mockup.

*[Point to the KPI tiles in §1]* These are held-out test metrics, regenerated fresh every run. At our threshold: 40% recall, 40% precision — a real number, not hand-picked, and I'll show you exactly what that traded against in a minute.

*[Scroll to §3, click 'Score transaction']* Let's score a transaction.

It comes back with a risk band and the top three factors that actually moved this prediction — in plain English, not a black box.

*[Scroll to §4. Select **TXN012908** from the dropdown — reason code and amount auto-fill. Click 'Generate packet'.]* Now say this one gets disputed.

Notice: only half the required evidence is available here — one document's missing. The system doesn't hide that. It recommends Review, not Fight, because the case isn't strong enough yet — and it tells you exactly which document would change that.

*[Point to the empty space where a narrative would go]* One more thing: there's no AI-written summary here right now. That's fine — the fight-or-review decision never depended on it. It's cosmetic phrasing on top, and if it's ever unavailable, the packet still works exactly like this.

*[Click 'Use in audit lookup', then 'Look up']* Every decision — score or packet — lands in an append-only audit log the moment it happens. One click pulls it back up by ID.

*[Scroll to §6, merchant rollup]* And this: which merchants run chronically high dispute rates — kept deliberately separate from what the model itself trains on, which only ever sees a merchant's history up to that point in time, never the future."

## 2:45–3:20 — Why trust the numbers (~79 words · 29s)

*[Screen: open a new tab to `/metrics` — the raw JSON, including the `"baseline"` field]*

"Everything here trains on 100% synthetic data — stated plainly from the README, because a few hours of buildathon time doesn't produce real cardholder patterns.

What we stand behind is the method: a held-out test set the tuning never touched, and a documented reason behind every signal we built in.

*[Point to the `baseline` field in the JSON]* And here's the honest comparison: the simplest rule you could write by hand gets 24% recall at 26% precision. Our model beats that — but we'd rather show you the real baseline than round up."

## 3:20–3:55 — Engineering rigor (~73 words · 27s)

*[Screen: github.com/MaulshreeJ/Chargeback-shield → Actions tab, green checks → test file list]*

"Under the hood: 23 tests across the evidence engine, audit log, model, and API, running in CI on every push.

The evidence engine never invents evidence — a missing document shows up as missing, exactly like you just saw.

The audit trail is append-only, so no past decision can be quietly edited.

And it's one FastAPI service with a dependency-free dashboard — no build step, so it runs the same live as it does on my machine."

## 3:55–4:20 — What's next (~38 words · 14s — deliberately short, say it slower)

*[Screen: README "Known limitations & what's next" section, same repo]*

"The honest gaps: synthetic data can't capture real adversarial adaptation, and evidence retrieval is still simulated — a real deployment calls Razorpay's own systems of record there, without touching the policy itself. That's an integration, not a research problem."

## 4:20–5:00 — Close (~81 words · 30s)

*[Screen: back to the live dashboard, top of page]*

"So Chargeback Shield isn't just another model saying 'this looks risky.'

It answers the bigger question: what should the merchant do about that risk, and can we prove why?

Predict the dispute before it happens. Respond honestly when it does. Assemble the evidence. Record every decision so it can be audited.

Because in financial risk, a model shouldn't just decide — it should decide in a way you can explain, verify, and trust.

This is Chargeback Shield, live at chargeback-shield-6egu.onrender.com. Thank you."

---

## Recording flow (screen order)

`Live dashboard (top)` → `Stage 1/2 cards (same page)` → `§1 metrics` → `§3 score` → `§4 packet (TXN012908)` → `narrative callout (same packet)` → `§5 audit (via button)` → `§6 merchant rollup` → `/metrics tab (baseline)` → `GitHub Actions tab` → `README limitations` → `back to dashboard top`

## Recording checklist

- [ ] Hit the live URL once, 1-2 minutes before recording, so it's already awake — a cold Render container takes 30-60s to respond and you do not want that on camera.
- [ ] Pre-check that **TXN012908** still shows 50% completeness / REVIEW before recording (it was verified live just before this script was written — if you've since retrained/redeployed, re-verify with the dropdown once).
- [ ] Use the **"Use in audit lookup ↓"** button for the audit demo — never type an ID by hand, it's easy to guess wrong and get "no record found" live (this happened once during testing).
- [ ] Have the `/metrics` URL and the GitHub repo's Actions tab each open in a background tab already, so you're not typing URLs live.
- [ ] Do one full silent dry run of the 1:00–2:45 block specifically — it's the longest and most click-dependent section.
- [ ] If any live click is ever slow, don't panic on camera — just keep talking about what you're pointing at; a 2-3 second pause reads fine on playback.

## Three things to make sure land, no matter what gets cut for time

1. **Predict → Respond** — this covers the whole lifecycle, not just a risk score.
2. **Policy ≠ LLM** — the LLM only phrases things; it never decides. The empty narrative field you saw live is proof of that, not a bug.
3. **Every decision is auditable** — score → evidence → recommendation → audit trail, and any of it can be pulled back up by ID.
