# Chargeback Shield — 5-Minute Pitch Script

**Track:** Razorpay AI Buildathon 2026 — Track 02, AI Risk Manager
**Total runtime target:** 5:00
**Format:** Screen recording (dashboard walkthrough) with voiceover. Cues in *[brackets]* are on-screen direction, not spoken.
**Word count (spoken lines only): ~670 words → ~4:15-4:30 at a measured pace, before demo-click pauses (Score / Generate packet / audit lookup / scroll) which bring the real total close to 5:00.**

---

## 0:00–0:25 — Cold open: the problem

*[Screen: title card fades in over a card swipe, then a red "DISPUTED" stamp]*

"A merchant doesn't lose money to fraud at checkout. They lose it two weeks later — when a customer disputes a legitimate charge, and the merchant has ten days to prove it or eat the loss. That's a chargeback. Most merchants fight blind, or don't fight at all."

## 0:25–1:05 — Positioning

*[Screen: the two-stage Predict → Respond diagram]*

"Score-the-swipe, block-or-allow fraud detection is the obvious build for this track — and it's already a crowded lane. Chargeback Shield goes somewhere nobody else here is: the dispute itself. Before one's filed, we predict the risk, so a merchant can send a confirmation email or hold settlement, cheaply. After it's filed, we assemble exactly the evidence that reason code requires, and recommend fight, concede, or review — under a policy that's fixed and auditable, never a model's best guess."

## 1:05–2:35 — Live demo

*[Screen: dashboard at localhost, walk top to bottom]*

"Here's the live dashboard. [Point to KPI tiles] These are the model's held-out test metrics, regenerated fresh every run — not hand-picked. At our chosen threshold, the model catches about 40% of disputes at 40% precision. [Point to baseline row] The single most obvious rule you could write by hand only gets 24% recall at 26% precision — a real lift, not a black box we're asking you to trust on faith.

[Point to tradeoff table] Here's the full precision-recall curve, not one cherry-picked number — because 40% precision was a business call: the action on a flagged transaction is a cheap email, not a decline, so recall was worth more than precision here. A stricter threshold is one line away if that action ever gets costlier. The model card even shows what happens if you optimize purely for cost instead: it flags almost everyone — exactly why we didn't ship it.

[Score a transaction] Let's score one live. [Click Score] It comes back with a risk band and the top three factors that actually moved this prediction, in plain English — no black box.

[Generate packet] Now say it's disputed. [Click Generate packet] The evidence engine pulls exactly what the reason code needs and recommends fight, concede, or review. No LLM anywhere in that decision — only in one optional sentence of prose at the bottom, and if that call ever fails, the packet still works without it.

[Click an audit ID] Every decision — score or packet — lands in an append-only audit log the second it happens. Pull any of them back up by ID.

[Scroll to merchant rollup] One more section: which merchants are chronically high-risk, ranked by dispute rate — kept deliberately separate from the feature the model actually trains on, which only ever sees history up to that point in time."

## 2:35–3:15 — Why trust the numbers

*[Screen: model_card.md scrolling]*

"Everything here trains on 100% synthetic data — stated plainly, starting with the README, because a few hours of buildathon time doesn't produce real cardholder patterns. What we stand behind is the method: a held-out test set untouched by tuning, a documented reason behind every signal built into the data, and a model card that says plainly why recall improved — mostly a business threshold and a clearly-labeled new signal, not a smarter model in disguise. We'd rather hand you the real breakdown than round up."

## 3:15–3:55 — Engineering rigor

*[Screen: GitHub Actions tab, green checks, then the test file list]*

"Under the hood: 23 tests across the evidence engine, audit log, model, API, and narrative layer, running in CI on every push. The evidence engine never invents evidence — a missing document shows up as missing, and the completeness score reflects it. The audit trail is append-only, so no past decision can be quietly edited. And it's one FastAPI service with a dependency-free dashboard — no build step, so it runs the same live as it does in your terminal."

## 3:55–4:30 — What's next

*[Screen: README "known limitations" section]*

"The honest gaps: synthetic data can't capture real adversarial adaptation, and evidence retrieval is still simulated — a real deployment calls Razorpay's own systems of record there, without touching the policy itself. That's an integration, not a research problem."

## 4:30–5:00 — Close

*[Screen: title card again, GitHub URL on screen]*

"Chargeback Shield: predict the dispute before it happens, and respond to it honestly when it does — a policy you can audit, not a model you have to trust. Thanks."

---

**Recording checklist:**
- [ ] Start the local server (`uvicorn src.api:app --reload`) and pre-load one sample dispute before recording, so the packet demo doesn't stall on a slow synthetic lookup.
- [ ] Rerun `python -m scripts.train`, `python -m scripts.evaluate_packets`, and `python -m scripts.merchant_rollup` right before recording so every number on screen matches what you say.
- [ ] Zoom the browser to ~110% so dashboard text is legible in a screen recording.
- [ ] Practice the 1:05–2:35 demo block separately — it's the longest and most click-dependent segment.
- [ ] Have a fallback: if a live dispute-packet lookup is ever slow, cut to a pre-generated one rather than let dead air run.
- [ ] If you've deployed by recording time, swap the localhost URL for the live one and mention it once near the top.
