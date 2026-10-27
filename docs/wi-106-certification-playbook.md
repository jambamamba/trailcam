# WI-106 — Certification Kickoff Playbook

**What this is:** the step-by-step checklist a human follows to **close WI-106** (Sprint 1's
procurement + certification kickoff for wapiti). Do the steps in order; tick the boxes as you go.

| Companion doc | What it's for |
|---|---|
| [certification-kickoff.md](certification-kickoff.md) | The full plan behind this playbook: module/eSIM selections, lab shortlists, **estimated cost + lead time for every §13 row (kickoff §4)**, itemized budget (§5), schedule, RFP packet text (§8.1) |
| [project-plan.md](project-plan.md) | §13 = *what* every certification is and *why*; the $200–400k / 6–9 month band; Sprint 1 line = where WI-106 gets marked done |
| [test-plan.md](test-plan.md) | Test IDs — WI-106 attaches **none** (no API/device surface); `PQT-01..14` + `COLD-05/06` (§22) is where lab *test evidence* lands later |

**In one sentence:** governments, carriers, and the Bluetooth organization each have to be
bought off before a camera with a radio in it can be sold — this playbook starts that 6–9
month, $200–400k clock now, with only **$30–65k** committed in this first phase.

> **Ground rule:** steps 1–5 involve money, contracts, and accounts. Nothing is sent, signed,
> or paid until **Step 0** is approved. The AI prepares quotes and paperwork; humans send them.

---

## Step 0 — Approve (5 minutes, closes the AC)

- [ ] **Budget:** approve the S1–S2 kickoff band **$30–65k** (detail: [kickoff §5](certification-kickoff.md#5-budget--s1s2-kickoff-tranche-phase-1); phase 1 of §13's $200–400k / 6–9 month program).
- [ ] **Module (⚠ reopened 2026-10-26):** the verification run says **do not order EG915U** — no NA variant, no B12/B13/B71, no PTCRB/GCF/US-carrier approvals, no GNSS ([kickoff §1](certification-kickoff.md#1-selection-cellular-module)). Approve the **requalification shortlist with its ranking** (1 EG916Q-GL → 2 SIM7672G → 3 SIM7672NA → 4 EG91-NA — full comparison in [kickoff §1](certification-kickoff.md#1-selection-cellular-module), checked against the vendors' own spec sheets 2026-10-27) plus the **PO gate (a)–(f)** (bands incl. B12+B13, PTCRB cert ID, three carrier approvals, GNSS answer, 701 question, written answer for every `*`/`#` spec row). Recorded as project-plan §19 risk 14; blocking for the S2 hardware freeze like WI-107.
- [ ] **Send the vendor question sheet:** forward [kickoff §8.3](certification-kickoff.md#83-vendor-question-sheet-send-verbatim-to-every-shortlisted-module-vendor--quectel--simcom-faes--before-any-poevk-spend) verbatim to every shortlisted module vendor + the eSIM candidates; no written answers in 2 weeks → drop that candidate down the ranking.
- [ ] **eSIM:** approve **1GLOBAL** (alternates: Truphone, Kigen — [kickoff §2](certification-kickoff.md#2-selection-esim--connectivity)).
- [ ] **Labs:** approve the shortlists — PTCRB ATL ×5, FCC TCB, ISED CAB, RED notified body ×4, UN 38.3 lab ×5, cold chamber ([kickoff §3](certification-kickoff.md#3-lab--body-engagement-engage--open--book)).
- [ ] **Out of scope:** confirm Skylo NB-NTN, GCF, SOC 2 and a GNSS accuracy claim stay deferred past v1 ([kickoff §0](certification-kickoff.md#0-what-transfers-from-lugtrax-and-what-does-not)).
- [ ] **Record approval:** flip **WI-106** to `[x]` in project-plan with the approved band, and the *Certification program (§13)* status row to `[~] Kickoff underway`.

**AC check:** "procurement plan + budget approved" = these boxes ticked + recorded.

---

## Step 1 — Open the accounts (week 1–3, mostly free)

- [ ] **Bluetooth SIG:** sign up the company at [bluetooth.com](https://www.bluetooth.com/develop-with-bluetooth/qualification-listing/) →
      Adopter membership (no annual fee) → confirm the **ESP32-C6's existing QDID**
      (Espressif's qualified stack) → file the **End Product** listing → pay the Declaration
      fee (**$4.0–9.6k**, tier-dependent; [kickoff §3.5](certification-kickoff.md#35-bluetooth-sig--open-the-declaration-early-declare-early--cheap)).
- [ ] **Save:** Declaration/Listing ID → record in the kickoff doc; it feeds the future **UK PSTI** statement (§13 cyber row).
- [ ] **Module requalification (PO gate):** send [kickoff §8.3](certification-kickoff.md#83-vendor-question-sheet-send-verbatim-to-every-shortlisted-module-vendor--quectel--simcom-faes--before-any-poevk-spend) (questions 1–10) and get the **six PO-gate answers in writing** from the vendor of the module chosen at Step 0 — NA band map with B12+B13 (B71/B14 stated), PTCRB certificate ID, AT&T/Verizon/T-Mobile approval references, GNSS on-module or companion part, the `701` question (§8.7 lineage), and a dated answer for every `*`/`#` spec-sheet row. Also ask Quectel to confirm in writing that **no PTCRB listing exists for EG915U** (their spec's certification row shows FCC + Anatel only).
- [ ] **Order EVKs:** SSC377Q + IMX415 kit, **cellular module EVB for the Step-0 choice** (not the EG915U by default), ESP32-C6 devkit ([§4.3](project-plan.md#43-benchdev-hardware)) — these unblock WI-201/204 anyway.
- [ ] **eSIM trial:** open the vendor IoT account → ~10 trial profiles → attach test on the **Step-0 module's** EVB across NA networks (questions 11–13; [kickoff §8.2](certification-kickoff.md#82-other-openings)).
- [ ] **Cell evidence gate:** before any cell/pack PO — datasheet carries **IEC 60086-4 + cell-level UN 38.3** for the Li-FeS₂ AAs and the reserve cell; packs need IEC 62133-2 on their own track ($0 if present — [kickoff §3.6](certification-kickoff.md#36-battery--transport--un-383-and-cell-evidence)).

## Step 2 — Send the RFP packet (week 1–3)

- [ ] Copy the **RFP packet** text from [kickoff §8.1](certification-kickoff.md#81-lab-rfp-packet-one-packet-sent-to-every-lab-in-3134).
- [ ] Send it to **all five PTCRB ATLs** (Element, UL Solutions, Bureau Veritas, SGS, TÜV SÜD).
- [ ] Send it to the **RED notified bodies** (CETECOM, Applus+, TÜV SÜD, Nemko) — one ask added: *does Art. 3.3 need a full notified-body opinion or harmonized-standard self-assessment?*
- [ ] Send it to an **ISED Certification Body** and a **TCB** for FCC (labs often bundle all three).
- [ ] Optional add-on in the same packet: **PQT/environmental bundle** (IEC 60529 IP67, IEC 60068 drop/thermal/vibration, salt-fog) + chamber time — quote now even though it runs in S5.
- [ ] Log replies in this table (one row per quote):

| Lab | Scope quoted | Price | Earliest slot | Grant reuse recognized? |
|---|---|---|---|---|
| | | | | |

**Decision criteria:** grant-reuse recognition first, then slot date, then price
([kickoff §3.1](certification-kickoff.md#31-ptcrb--via-a-ptcrb-authorized-test-lab-atl)).

## Step 3 — Book the battery + chamber (week 3–4)

- [ ] Get a **UN 38.3** quote + hold a slot (≈$2.5–10k, 4–8 weeks lab; UL / TÜV SÜD / Intertek / SGS / Bureau Veritas).
- [ ] **Important:** device-level testing needs *real boards with a cell installed* — you are booking a **date**; testing happens when EVT hardware exists (WI-201 overlap).
- [ ] Quote the **rechargeable pack track** separately (UN 38.3 + IEC 62133-2, ± UL 2054) — the NMC/LTO packs are SKUs with their own certification (§19 risk 4); phase 3 budget.
- [ ] **Cold-chamber slot + mitten rig** held for `COLD-05` (gloved swap < 20 s @ −40 °C) and `COLD-06` (500-cycle latch) — booked now, executed in S5/WI-501.

## Step 4 — Compare & sign (week 4–5)

- [ ] Pick the PTCRB lab from the Step 2 table → **sign the lab contract**.
- [ ] Agree the **slot calendar**: PTCRB / FCC / ISED / RED dates pinned against EVT→PVT board dates.
- [ ] Every signature stays inside the approved band — if a quote breaks it, stop and revisit Step 0.

## Step 5 — Carrier pre-check (week 5–6)

- [ ] Open the **Verizon Open Development / AT&T IoT / T-Mobile device-certification** forms and confirm the module's existing carrier approvals carry over for our variant.
- [ ] Confirm the eSIM vendor's profiles attach on all three (trial accounts from Step 1) — carrier acceptance, not eSIM, is the gate before a SIM activates.

## Step 6 — Close WI-106 (week 6+)

- [ ] Fill the **named owners** column in [kickoff §7](certification-kickoff.md#7-owner-assignment-13-mandate-named-owner-per-row-before-s2-exits) (§13 mandate: every row has a named owner before S2 exits).
- [ ] Update project-plan: append **contracts signed + booking references** to the WI-106 line, and flip the status row *Certification program (§13)* from `[~] Kickoff underway` to `[x] Kickoff done — phase 2/3 tracked in WI-502`.
- [ ] File evidence (see below) under `docs/` + the lab folder.
- [ ] **test-plan.md / tests/test.py: no changes** — WI-106 introduces no test IDs (verify once: catalog total still 307; lab evidence later lands in `PQT-01..14` / `COLD-*`).

---

## Budget at a glance (phase 1 only — detail: [kickoff §5](certification-kickoff.md#5-budget--s1s2-kickoff-tranche-phase-1))

| Line | Cost | Time to first result |
|---|---:|---|
| Bluetooth SIG declaration | $4.0–9.6k | 1–2 weeks |
| UN 38.3 booking (device-level) | $2.5–10k | 4–8 weeks lab, at EVT |
| PTCRB lab contract (deposit + testing) | $12–18k | 4–8 weeks to certificate |
| FCC TCB + ISED CAB fees | $3–6k | 2–6 weeks after testing |
| RED notified-body retainer | $3–6k | 4–8 weeks (phase 2 test) |
| EVKs / samples / trial eSIM profiles | $2–4k | days–2 weeks |
| Cold-chamber slot + mitten rig | $2–6k | slot now, run S5 |
| Legal/admin + PTCRB program admin | $1.5–3k | — |
| **Phase 1 total** | **$30.0–62.6k** (band **$30–65k**) | weeks 1–6 to sign/hold |

Later phases (**do not start from this playbook**): radio-cert wave **≈$25–94k** (months 3–7),
safety/EMC/environmental/claims **≈$29–94k** (months 5–9).

## Estimated cost + time per certification (every §13 row)

Condensed from [kickoff §4](certification-kickoff.md#4-estimated-cost--time--every-13-row) —
that table is the source of truth; **the Step 2 quotes outrank both**.

| Certification (§13) | Est. cost | Est. time | Phase / when |
|---|---:|---|---|
| Bluetooth SIG qualification + listing | **$4.0–9.6k** | 1–2 weeks | 1 — Step 1 |
| UN 38.3 device-level T1–T8 | **$2.5–10k** | 4–8 weeks (at EVT) | 1 — Step 3 |
| Cell-level evidence (Li-FeS₂ AA + reserve cell) | **$0** | days–2 weeks | 1 — Step 1 gate |
| PTCRB end-device cert (module reuse) | **$10–20k** | 4–8 weeks | 1–2 — Step 2/4 |
| FCC (TCB Certification + SDoc) | **$3–10k** | 2–6 weeks after testing | 1–2 — Step 2 |
| ISED Canada via CAB | **$2–6k** | 2–4 weeks | 1–2 — Step 2 |
| CE — RED notified body + radio/EMC | **$10–25k** | 4–8 weeks from test | 1–2 — Step 2 |
| UKCA | **$0–3k** | 1–2 weeks | 2 |
| Carrier acceptance (AT&T / Verizon / T-Mobile) | **$0–10k per carrier** | 2–6 weeks each | 2 — Step 5 |
| GCF | **$0** — skipped v1 | — | optional |
| Safety IEC/EN 62368-1 + CISPR 32/35 | **$8–20k** | 3–6 weeks | 3 |
| UL 62368-1 NRTL (US retail only) | **$5–15k** | 4–8 weeks | 3 (S4 gate) |
| RoHS + REACH SVHC | **$1–4k** | 2–4 weeks | 3 |
| EU Battery Reg / WEEE / Prop 65 | **$1–4k** | 2–6 weeks | 3 |
| UK PSTI / ETSI EN 303 645 / EU CRA / GDPR DPIA | **$0.5–4k** | 2–6 weeks | 3 (WI-505) |
| IATA/ICAO DGR + 49 CFR shipping | **$0–2k** | 1–2 weeks | 3, before first shipment |
| PQT durability suite + COLD evidence (IP67, drop, 500-cycle latch) | **$8–25k** | 4–8 weeks | 3 (S5, WI-501) |
| Rechargeable pack track (UN 38.3 + 62133-2 ± UL 2054) | **$5–20k** | 8–14 weeks | 3 |
| SPDX / OSS license compliance | **$0** | per build | ongoing (YOCTO-06) |
| Skylo NB-NTN · GNSS accuracy claim · SOC 2 | deferred | — | not v1 |
| | | | |
| **Program total** | **≈$84–251k itemized, inside §13's $200–400k** | **6–9 months** | parallel from S1 |

Sanity check: phase 1 **$30–65k** + phase 2 **≈$25–94k** + phase 3 **≈$29–94k**; phase-1
PTCRB/FCC/RED lines are deposits drawn against phase 2, not additive. The gap to §13's
$200–400k ceiling is rush fees, retests, and consultant support — the band is the ceiling,
the itemized numbers are the plan.

## What's deliberately NOT in this program

| Item | Why not |
|---|---|
| Skylo NB-NTN certification | no satellite path in §13; media is LTE-only |
| GCF listing | operator-agnostic, optional; revisit only if an operator asks |
| SOC 2 | not a ticket-to-sell for hardware; revisit with an enterprise/outfitter cloud SKU |
| L1+L5 GNSS accuracy claim | no published accuracy claim in v1; the positioning path itself follows the §1 module decision (EG915U has no GNSS) |
| FTO search on reserve-battery GPS | **not a certification** — it's WI-107, its own budget, blocking for the S2 hardware freeze (§13.1) |

## Evidence to keep (audit trail)

- [ ] Bluetooth Declaration/Listing ID (QDID reused from the C6)
- [ ] Every lab quote (email/PDF) — filed against the Step 2 table
- [ ] Signed lab contracts + slot calendar
- [ ] UN 38.3 booking reference (report arrives later, with EVT boards)
- [ ] Cell datasheet evidence: IEC 60086-4 + cell UN 38.3 (Li-FeS₂ AA, reserve cell)
- [ ] eSIM trial account + validated attach on NA networks (feeds the "N countries" box/site claim)
- [ ] **Quectel answers:** variant/bands, grant list, carrier approvals, 701 question (→ §8.7 / R-12) — plus the §1 PO-gate record (a)–(f) for the chosen module (bands, PTCRB ID, three carriers, GNSS, 701, dated answers for every `*`/`#` spec row)
- [ ] **Vendor question sheet:** completed answers to [kickoff §8.3](certification-kickoff.md#83-vendor-question-sheet-send-verbatim-to-every-shortlisted-module-vendor--quectel--simcom-faes--before-any-poevk-spend) (Q1–10 module, Q11–13 eSIM, Q14–16 lab) — one file, per vendor, dated
- [ ] Cold-chamber slot confirmation (→ `COLD-05/06` evidence in `tests/reports/pqt/`)

---

## Do competitors go through this too?

**Yes — the same statutes hit them, and the FCC record proves it.** Checked against FCC
filings (fccid.io mirror via trailcamspecs.com) and carrier records on **2026-10-27:**

| Brand | What their filings show | What it means |
|---|---|---|
| **Tactacam (REVEAL)** | Own grants, e.g. **`2BBNQ-RVX4CD`** (Reveal X 4.0 / Pro 4.0, filed 2026-08) — **TCB: NMi TESTLAB GmbH**, test lab Eurofins TA (Shanghai); bands **B2/25, B4, B5, B12, B13, B14, B66** + 2.4 GHz Wi-Fi/BT (Part 15C); grantee Deer Management Systems LLC, Decorah IA | Full FCC Certification route with a TCB, same as our §3.2 — including the low-band (B12/B13) and FirstNet B14 our §1 gate demands |
| **Moultrie** | Own filings under grantee code **2AJQ6** — e.g. Edge 4 `2AJQ6MCAM4`, Edge 4 Pro `2AJQ6MCAM4P` (filed 2026, LTE Cat 1bis); Browning files under **2ALGT** | Same: per-model FCC filings, not module-only |
| **SPYPOINT** | **No FCC ID of its own** — the Flex-M manual states *“Contains FCC ID: XMR201807EG91NA”*, i.e. **Quectel's EG91-NA module grant** (2018, B2/4/5/12/13) | They use exactly the module-grant-reuse strategy §13 prescribes — on the very EG91-NA we shortlist as our proven fallback |

- **PTCRB + carrier acceptance** are not visible in marketing, but they are implied: those
  cameras activate on AT&T/Verizon/T-Mobile, and no carrier accepts a device that hasn't
  cleared its process. (Direct PTCRB spot-check still open — their device search is
  JS-rendered; add it to the Step 2 verification list before we claim it for a rival.)
- **So there is no certification shortcut available to us — or to anyone.** The scope in
  §13 is the cost of selling a radio at all; competitors amortize it over far more units.
- **The delta is on the claims side, not the cert side:** nobody in the category publishes
  a *tested* cold minimum (Tactacam's Reveal X 4.0 rating is −13…130 °F ≈ −25…+54 °C, IP66),
  and no rival publishes PQT/COLD-style lab evidence. Our −40 °C, IP67, 500-cycle and
  14-month claims (PQT-01..14, COLD-05/06) are the part competitors *don't* do — which is
  why §22 evidence and the §13 certification rows are two separate budgets.
