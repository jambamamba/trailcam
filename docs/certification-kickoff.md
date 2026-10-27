# wapiti WI-106 Certification Kickoff — Procurement Plan & Budget

**Status:** 🟡 **DRAFT — awaiting the §9 approval gate** · **Date:** 2026-10-26 · **Scope:** Sprint 1–S2 kickoff actions of [project-plan §13](project-plan.md#13-certifications--compliance)
**AC:** procurement plan + budget approved.
**Human follow-along:** [`wi-106-certification-playbook.md`](wi-106-certification-playbook.md) — the ordered checklist that closes this WI.

This document is the WI-106 deliverable: it turns §13's certification matrix into **buyable,
bookable, outreach-ready decisions** — module/eSIM selections with rationale, lab & body
shortlists, an itemized budget, and **an estimated cost and lead time for every §13 row**.
It does **not** place orders, sign contracts, or pay fees — that is the human approval gate
in §9.

Modeled on the lugtrax kickoff (`/repos/www/lugtrax/docs/certification-kickoff.md`), but
**re-derived for wapiti's hardware**: the plan structure and fee research transfer, the
module, cells, and satellite rows do not (see §0).

**Strategy recap (§13):** buy pre-certified silicon (EG915U module grants; multi-IMSI eSIM)
and certify the final product only for the remaining scope. Program budget **$200–400k**,
lead time **6–9 months**, running parallel to sprints; this kickoff commits the **$30–65k**
phase-1 tranche (§5).

---

## 0. What transfers from lugtrax, and what does not

| | lugtrax LT-1 | wapiti (this plan) |
|---|---|---|
| Cellular module | Quectel **BG95-M5** (LTE-M / NB-IoT) | Quectel **EG915U** LTE **Cat-1bis** (alt SimCom A7672SA) — §4.2 … ⚠ **verified failing the NA gate 2026-10-26: no NA variant, no GNSS, no PTCRB/carrier (§1)** |
| Co-processor / BLE | (nRF91-class) | **ESP32-C6** (BLE 5 + Wi-Fi 6) → Bluetooth SIG QDL reuses **Espressif's** QDID |
| Cells | CR123A Li-SOCl₂ primary | **12×AA Li-FeS₂ primary** + small Li reserve cell + **rechargeable smart packs** (NMC / LTO) — §5.1 |
| Satellite | **Skylo NB-NTN** cert ($4–7.5k + lab) | **Not applicable** — no NTN path in §13; media is LTE-only |
| GNSS claim | dual-band L1+L5 accuracy claim | **Not applicable** — no published accuracy claim in v1; and note our intended “on-module GNSS” does not exist on EG915U (§1), so positioning rides whatever module/part Step 0 picks |
| SOC 2 | in lugtrax §12.5 | **Deferred** — not a ticket-to-sell for hardware; revisit only with an enterprise/outfitter cloud SKU |
| GCF | optional, skip v1 | optional, skip v1 (revisit only if an operator asks) |
| Everything else | FCC · ISED · PTCRB + carrier · CE RED · UKCA · SIG · UN 38.3 · IEC 62368-1 + CISPR · UL NRTL · RoHS/REACH/Battery Reg/WEEE/Prop 65 · PSTI/ETSI/CRA/GDPR · IATA DGR · PQT | **identical scope** — already the §13 table |

Two rows need *different evidence* rather than different scope: primary Li-FeS₂ AA is
qualified by **IEC 60086-4 + cell-level UN 38.3** (usually already on the cell datasheet —
a buying gate, like lugtrax's IEC 62133-2 check), while the **rechargeable packs** are the
ones that need **IEC 62133-2 + their own UN 38.3 + UL 2054** (project-plan §19 risk 4:
*pack as separate SKU with its own track*).

---

## 1. Selection: cellular module

> ### ⚠ Verification result (2026-10-26): the §4.2 BOM part **fails the US gate**
> Checked against Quectel's own sheets — *EG915U Series Specification V1.3* (Nov 2024) and
> *Introduction V1.0* — plus the FCC grant record and carrier requirement docs. **Decision
> status: REOPENED** (tracked as project-plan §19 risk 14); no EVK/PO money moves until
> Step 0 approves the requalification shortlist below.

**Original selection: Quectel EG915U class (the §4.2 BOM part), SimCom A7672SA as named alternate — both now gated.**

| Criteria | Verified status (2026-10-26) | Why it matters for wapiti |
|---|---|---|
| Variants | **CN / EU / LA only — there is no North America variant** (Quectel spec V1.3 variant table) | The NA market is the entire §13 program; a LatAm/EMEA variant is not a formality, it is band + carrier scope |
| Bands | LA: **B2/3/4/5/7/8/28/66** · EU: B1/3/5/7/8/20/28 · CN: B1/3/5/8. FCC grant `XMR202210EG915ULA` authorizes US operation on **B2, B4, B5, B66, B7** (grant notes; TCB Certification 2022-10-20, Class II permissive 2025-09-28) | **No low-band 600/700 MHz on any variant** — no B12 (AT&T/T-Mobile), no B13 (Verizon), no B71 (T-Mobile). project-plan §1's “buyer is rural” premise breaks without low-band |
| PTCRB | **No** — Quectel's certification row for the LA variant reads *Regulatory: FCC, Anatel*; GCF/CE appear on the EU row only (and are marked “under development” in the intro deck). No public PTCRB listing found; PTCRB's own device search is JS-rendered, so get it **in writing** | §13 strategy is module-grant reuse; without PTCRB/GCF on the module the device-level scope (and §4 row 4/row 9 cost) grows |
| Carrier approvals | **None** — Quectel's *Carrier* row: LA “-”, EU “Deutsche Telekom” | AT&T/Verizon/T-Mobile acceptance would run from zero at device level |
| Verizon | **Not achievable on this module** — Verizon's Open Development process requires GCF certification for LTE **Band 13** before conformance testing; EG915U-LA has neither B13 nor GCF | Verizon is a §13 radio-row target; plan either drops it or the module changes |
| GNSS | **Not supported** — GNSS row is “-” on all three variants; only QuecLocator® (cellular LBS) is offered | §4.2's “EG915U … **+ GNSS combo**, GNSS on-module saves BOM” is wrong as written; the anti-theft GPS (§8.4, WI-307) needs on-module GNSS or a companion GNSS part |
| Category | LTE **Cat-1bis**, ~5 Mbps uplink — confirmed | Photo-class media path (the BG950A-GL LTE-M rejection in §8.7 stands) |
| Temperature | operating −35…+75 °C; **extended −40…+85 °C** | Our −40 °C claim rests on the *extended* rating — confirm on the datasheet at PO |
| Integration | Quectel AT family: `AT+QHTTP*` on-modem TLS/HTTP, `AT+QFUPL` cert upload — §8.7's six bench-measured rules | Keeping a Quectel part preserves the §8.7 driver lineage for WI-204; switching to SIMCom means SIM800-style AT and a port of those rules |

**Requalification comparison — re-derived from the vendors' own spec sheets (checked 2026-10-27):**

> **Reading the sheets:** SIMCom's legend says `*` = "under developing/on-going/planning"
> and `#` = "optional"; Quectel's says `*` = "under development / in progress". An
> **unstarred** FCC/PTCRB/carrier row is a claim that the certificate exists; a **starred**
> one is a promise. Promises go straight onto the §8.3 question sheet, not into the BOM.

| Candidate | US band map (own spec sheet, 2026-10-27) | Cert row as printed | GNSS | Temp (extended) | AT lineage (§8.7) | Read |
|---|---|---|---|---|---|---|
| **Quectel EG916Q-GL** | B1/2/3/4/5/7/8/**12**/**13**/18/19/20/25/26/28/66 — **B12+B13 firm; no B71, no B14** | **PTCRB · FCC · IC · GCF · CE unstarred**; carrier row `Verizon/AT&T/T-Mobile*` and `UKCA*` = under development; GNSS **optional** | optional GPS/GLONASS/BDS/Galileo/QZSS (order the GNSS SKU) | −40…+85 °C (normal −35…+75) | ✓ **same Quectel family** — `AT+QHTTP*`/`AT+QFUPL` rules carry over | **Leads on certificates + driver lineage**, lags on B71/B14 and on carrier approvals (and Quectel's own 2023 PR says "Verizon" while the spec stars it — reconcile in writing) |
| **SIMCom SIM7672G** | B1/2/3/4/5/7/8/**12**/**13**/18/19/20/25/26/28/66 + `B71#` | FCC / CE-RED / TELEC / JATE printed unstarred; `GCF*`, `PTCRB*`, `IC*`, `AT&T*`, `TMOBILE*`, `VERIZON*` = planned per SIMCom legend | `GNSS#` optional (Multi-GNSS) | −40…+85 °C (normal −30…+75) | ✗ SIM800-compatible AT → port the §8.7 rules | **Only candidate with independent carrier evidence** — Verizon approved-module list #32869 (B2/4/5/13/66), AT&T cert dated 2024 — but its own sheet still stars PTCRB/carriers, so confirm IDs |
| **SIMCom SIM7672NA** | B2/B4/B5/**12**/**13**/B66, plus `B14#` and `B71#` (optional) | FCC unstarred; `IC*`, `GCF*`, `PTCRB*`, `AT&T*`, `T-MOBILE*`, `VERIZON*` = planned | `GNSS#` optional | −40…+85 °C (normal −30…+75) | ✗ SIM800-compatible AT | Tightest NA fit (FirstNet B14 + T-Mobile B71 *if* the SKU opts them in); PTCRB/carrier rows are promises, not certificates |
| **Quectel EG91-NA (EG91-NAXDL)** | B2/4/5/**12**/**13** only (grant `XMR201807EG91NA`, 2018) | FCC grant + **Verizon approved module** (#18258) | advertised on the Verizon listing — confirm | confirm | ✓ Quectel family | **Proven, not competitive** — ships today in SPYPOINT Flex-M, but Cat-1 (not bis), no B66/B71/B14, 2018 vintage; the fallback, not the pick |
| ~~SimCom A7672SA~~ (§4.2 named alternate) | B1/2/3/4/5/7/8/28/66 — **same B12/B13/B71 gap** | Anatel-centric on public record; no PTCRB/US-carrier evidence found | has GNSS | confirm | ✗ SIM800 family | fails the same gate — re-qualify, don't assume |

**Ranking for Step 0 (recommendation only — the gate is the human's):**
1. **EG916Q-GL** — only candidate whose cert row already shows PTCRB + FCC + GCF unstarred *and* keeps the §8.7 AT driver; conditional on firming the carrier row in writing and accepting no B71/B14.
2. **SIM7672G** — the coverage pick (B12/B13 firm, B71/B14 optional, independent Verizon + AT&T evidence); costs the §8.7 AT port.
3. **SIM7672NA** — same port cost with a narrower band map and no independent carrier record; the low-cost NA option if quotes differ materially.
4. **EG91-NA** — drop-in proven fallback (SPYPOINT ships it) if 1–3 stall at the written-confirmation step.

**PO gate — all five must come back in writing from the vendor before any order:**
(a) NA band map including **B12 + B13** (B71/B14 stated present or absent for the exact SKU),
(b) **PTCRB certificate ID**, (c) **AT&T / Verizon / T-Mobile** approval references for that
exact variant, (d) **GNSS on module** or the named companion GNSS part + its cert scope,
(e) does the ~3% `701` HTTP failure mode from the bench sibling apply to this part.
**(f)** a dated answer for **every spec-sheet row marked `*` or `#`** — the §8.3 question
sheet is the instrument for (a)–(f).

## 2. Selection: eSIM / connectivity

**Decision: multi-IMSI eSIM — 1GLOBAL primary, Truphone "for Things" and Kigen as alternates (vendor not yet contracted; confirm at Step 1 of the playbook).**

| Criteria | Why it matters |
|---|---|
| Multi-IMSI + eUICC/RSP | profile swap OTA → **no recertification** when the operator profile changes (radio grants ride the module) |
| Coverage claim | publish our own country count on box + site (WI-405 pattern — same honesty rule as the battery claims) |
| IoT B2B account model | per-device data plans; bundled into the subscription pricing (§7.1) |

**Certification impact:** the eSIM choice does not change radio grants, but **carrier
acceptance** (§13 radio row — Verizon Open Dev / AT&T IoT / T-Mobile) must complete before a
SIM activates on those networks. S3–S4 item, pre-checked in Step 5 of the playbook.

## 3. Lab & body engagement (engage / open / book)

### 3.1 PTCRB — via a PTCRB Authorized Test Lab (ATL)
- **Shortlist (request quotes from all five):** Element, UL Solutions, Bureau Veritas, SGS, TÜV SÜD — all Primary Labs on the PTCRB site.
- **Fee research (checked 2026-10-26):** PTCRB certification fees are set by the Program Management Document and range **$1,500–$15,000**; lab testing fees are set independently by each lab — indicative all-in **$10–20k when module-grant reuse applies**, **4–8 weeks** to certificate (2–3 week test cycle).
- **Action:** send the RFP packet (§8.1) to all five; select on grant-reuse recognition + slot availability; sign in wk 4–5.

### 3.2 FCC (USA) — file through a TCB, leaning on the module grant
- Intentional radiator (LTE) → **Certification via TCB** with module-grant reuse; unintentional radiator (C6 Wi-Fi, digital device) → **SDoC**. TCBs set their own fees and review times (typical total **$3–10k**, **2–6 weeks** after testing) and overlap the labs above (UL, Eurofins, TÜV, Element).
- **Action:** include FCC scope in the same RFP packet; book the SDoC/EMC space with the CISPR bundle (safety/EMC row, phase 3).

### 3.3 ISED Canada — via a Certification Body (CAB)
- Route: RSS-247 (intentional) + RSS-Gen/ICES-001 EMC through a listed CAB; **$2–6k**, **2–4 weeks**, usually bundled with FCC/PTCRB at one lab.
- **Action:** request quotes alongside PTCRB (same packet).

### 3.4 CE / RED notified body (EU)
- **Shortlist:** CETECOM, Applus+ Laboratories, TÜV SÜD, Nemko.
- Scope: RED 2014/53/EU Art. 3.2(b) + 3.3 delegated acts (privacy/fraud — evidence leans on ETSI EN 303 645 / cyber row) + EMC harmonized standards. Public fee research (2026): lab testing **€2–12k**, notified-body fee **€1.5k+**, **4–8 weeks** from test completion to declaration.
- **Action:** RFQ to all four in wk 1–3; ask whether Art. 3.3 needs a full NB opinion or harmonized-standard self-assessment — their answer sizes the cyber workstream.

### 3.5 Bluetooth SIG — open the declaration early ("declare early — cheap")
1. Sign up the company at bluetooth.com → **Adopter membership (no annual fee)**.
2. Reuse the **ESP32-C6's existing QDID** (Espressif's qualified stack/design) → list an End Product citing that QDID; a new design qualification is needed only if we change the BT stack.
3. Pay the **Declaration / Product Qualification Fee** at first submission — tier-dependent; public schedules and third-party fee pages put it at **≈ $4,000 (Associate) to ≈ $9,600**; confirm the exact tier fee at signup.
4. Deliverables: QDID + Declaration/Listing ID → feeds the **UK PSTI statement of compliance** (cyber row).

### 3.6 Battery / transport — UN 38.3 and cell evidence
- **UN 38.3 (device-level, T1–T8):** accredited-lab fee **$2,500–$10,000**, **4–8 weeks** lab time; book the slot now, ship samples when EVT boards exist (WI-201 overlap). Cell installed in the camera — cell-vendor reports do not cover us.
- **Primary cells (12×AA Li-FeS₂ + reserve Li cell):** verify **IEC 60086-4** + cell-level UN 38.3 on the vendor datasheet **before any cell PO** — $0 if present, a sourcing gate otherwise.
- **Rechargeable smart packs (NMC / LTO, sold as SKUs):** own track — **IEC 62133-2 ($2–6k) + UN 38.3 ($2.5–10k) + UL 2054 ($3–8k)** if we want the US retail mark; **8–14 weeks**, needs pack samples. Budgeted phase 3 (§5).
- **Shipping program:** IATA/ICAO DGR + 49 CFR (PI 967, cells in equipment) before first shipment — **$0–2k**, **1–2 weeks** of paperwork/training.

### 3.7 Cold chamber + PQT lab (our claim evidence, not a statutory cert)
- IP67 (IEC 60529), drop (IEC 60068-2-31), thermal, vibration, salt-fog, latch/swap cycles — `PQT-01..14` + `COLD-05/06` in test-plan §22 run at an accredited environmental lab.
- **Estimate:** chamber rental/contract **$8–25k**, **4–8 weeks** of lab time in S5 (WI-501). **Kickoff action:** hold a chamber slot + mitten rig now (WI-106 lists it), because the −40 °C and 500-cycle latch claims are marketing claims that must have reports behind them.

### 3.8 Explicitly not in scope for v1
Skylo NB-NTN, GCF, SOC 2, dual-band GNSS accuracy claim (§0 table). Revisit only if a
market or an operator forces it.

## 4. Estimated cost & time — every §13 row

Costs are planning-grade estimates from public sources **checked 2026-10-26**; lead times
assume grant reuse and no failed first pass. **The Step 2 quotes are the source of truth.**
Phases: **1** = this kickoff (S1–S2) · **2** = radio-cert wave (S2–S4) · **3** =
safety/EMC/environmental/claims (S3–S5, closure in WI-502).

| # | Certification / workstream (§13 row) | What the money buys | Est. cost | Est. time | Phase |
|---|---|---|---:|---|---|
| 1 | **Bluetooth SIG qualification + listing** (radio) | Declaration fee at first submission; free thereafter for products reusing the design | **$4.0–9.6k** | 1–2 weeks (after signup; QDID reuse) | 1 |
| 2 | **UN 38.3 device-level T1–T8** (battery/transport) | Accredited lab, cell installed in the camera; booked now, tested at EVT | **$2.5–10k** | 4–8 weeks lab (booking lead 2–4 wks) | 1 |
| 3 | **Cell-level evidence — Li-FeS₂ AA + reserve cell** (battery/transport) | Datasheet verification: IEC 60086-4 + vendor UN 38.3 | **$0** (buying gate) | days–2 weeks | 1 |
| 4 | **PTCRB end-device certification** (radio) | Program fee ($1.5–15k band) + lab testing → **all-in $10–20k with module-grant reuse** | **$10–20k** | 4–8 weeks to certificate | 1–2 (contract in 1, test in 2) |
| 5 | **FCC — TCB Certification + SDoc** (radio) | TCB filing + test space, leaning on the module grant | **$3–10k** | 2–6 weeks after testing | 1–2 |
| 6 | **ISED Canada via CAB** (radio) | CAB fee, bundled with FCC/PTCRB at one lab | **$2–6k** | 2–4 weeks | 1–2 |
| 7 | **CE / RED notified body + radio/EMC** (radio + safety/EMC) | Type examination + lab time (harmonized standards) | **$10–25k** | 4–8 weeks from test completion | 1 (engagement) → 2 |
| 8 | **UKCA** (radio) | Reuses EU test reports; approved-body fee only if an opinion is needed | **$0–3k** | 1–2 weeks | 2 |
| 9 | **Carrier acceptance — AT&T / Verizon / T-Mobile** (radio) | Program forms/fees; module + PTCRB reuse covers most tests | **$0–10k per carrier** (≤ $30k) | 2–6 weeks each, parallel | 2 |
| 10 | GCF (radio) | Operator-agnostic listing | **$0** — skip v1 | — | — |
| 11 | **Safety IEC/EN 62368-1 + EMC CISPR 32/35** (safety/EMC) | CB-scheme lab; EMC often already in the RED quote | **$8–20k** | 3–6 weeks | 3 |
| 12 | **UL 62368-1 NRTL listing** (safety/EMC) | US retail-channel listing only (not legally required to sell direct) | **$5–15k** | 4–8 weeks | 3 (S4 gate) |
| 13 | **RoHS + REACH SVHC reports** (environmental) | Accredited lab reports + self-declaration | **$1–4k** | 2–4 weeks | 3 |
| 14 | **EU Battery Reg. / WEEE / Prop 65** (environmental) | Registrations + declarations (battery removability already designed in) | **$1–4k** | 2–6 weeks | 3 |
| 15 | **UK PSTI / ETSI EN 303 645 / EU CRA readiness / GDPR DPIA** (cyber/data) | Statement of compliance + privacy work (WI-505) | **$0.5–4k** | 2–6 weeks (mostly documentation) | 3 |
| 16 | **IATA/ICAO DGR + 49 CFR shipping program** (battery/transport) | Training + docs for cells-in-equipment (PI 967) | **$0–2k** | 1–2 weeks, before first shipment | 3 |
| 17 | **PQT durability suite PQT-01..14 + COLD evidence** (ingress/mech) | IP67, drop, thermal, vibration, salt-fog, 500-cycle latch, gloved swap | **$8–25k** | 4–8 weeks lab | 3 (S5, WI-501) |
| 18 | **Rechargeable pack track** — UN 38.3 + IEC 62133-2 (+ UL 2054) | Pack SKUs (NMC / LTO) as separate certified items | **$5–20k** | 8–14 weeks | 3 |
| 19 | **SPDX / OSS license compliance** (open-source/IP) | License texts + corresponding-source offer shipped with OTA (`YOCTO-06`) | **$0** | per build | ongoing |
| 20 | FTO search on reserve-battery GPS (**not a certification**) | WI-107, separate budget, blocking for the S2 hardware freeze | see WI-107 | S1 | — |

**Roll-up:** phase-1 rows 1–7 + EVK/chamber/admin = the §5 tranche · phase-2 rows ≈ **$25–94k** · phase-3 rows
≈ **$29–94k**. Phase-1 §5 lines 3–5 are *deposits/retainers drawn against* the phase-2 scope,
not additive. Itemized program total ≈ **$84–251k**, held inside §13's **$200–400k** approved
envelope — the delta is rush fees, retests, and consultant support. Elapsed **6–9 months**
from kickoff to final certificate (matches §13).

## 5. Budget — S1–S2 kickoff tranche (phase 1)

| # | Line item | Basis | Low | High |
|---|---|---|---:|---:|
| 1 | Bluetooth SIG declaration (End Product listing) | tier fee at signup (§3.5) | $4,000 | $9,600 |
| 2 | UN 38.3 device-level booking | lab fee T1–T8, held against EVT date (§3.6) | $2,500 | $10,000 |
| 3 | PTCRB lab contract (deposit + testing, module reuse) | ATL quotes (§3.1) | $12,000 | $18,000 |
| 4 | FCC TCB + ISED CAB fees (same RFP packet) | TCB/CAB published schedules | $3,000 | $6,000 |
| 5 | RED notified-body RFQ retainer (EU) | CETECOM/Applus/TÜV/Nemko quote | $3,000 | $6,000 |
| 6 | EVKs + samples: SSC377Q+IMX415 kit, cellular module EVB (post Step-0 module decision), C6 devkit, trial eSIM profiles | §4.3 bench list | $2,000 | $4,000 |
| 7 | Cold-chamber slot hold + mitten rig (WI-106 line) | chamber rental/contract quote | $2,000 | $6,000 |
| 8 | Lab-contract legal/admin + PTCRB program admin | nominal | $1,500 | $3,000 |
| | **S1–S2 kickoff subtotal** | proposed band **$30–65k** | **$30,000** | **$62,600** |

> Lines 2 and 3 are **bookings made at kickoff, invoiced when hardware exists** — cash out
> follows EVT/PVT board availability, so months 1–3 spend tracks the low end.

**Program totals:** phase 1 (this doc) **$30–65k** months 1–3 · phase 2 radio wave
**≈$25–94k** months 3–7 · phase 3 safety/EMC/environmental/claims **≈$29–94k** months 5–9 →
itemized **≈$84–251k**, inside §13's **$200–400k / 6–9 months**. Approval requested for the
**bands, not point estimates** (retests and rush slots are where cert budgets break).

## 6. Schedule (months 1–3, aligned to S1–S2)

| Week | Action | Owner role |
|---|---|---|
| 1 | Approve this plan + budget (§9); open SIG account; start EG915U variant/grant verification at Quectel + eval order | Regulatory Lead |
| 1–3 | Send RFP packet (§8.1) to 5 PTCRB ATLs + 4 notified bodies + ISED CAB/TCB | Regulatory Lead |
| 1–2 | eSIM vendor trial (1GLOBAL + one alternate): profiles, attach test on the chosen module's EVB (§1 decision) | Connectivity Lead |
| 2–3 | Bluetooth SIG: Adopter signup → Espressif QDID reuse check → End Product listing filed | Regulatory Lead |
| 3–4 | UN 38.3 slot booked (held against EVT-board date); cell datasheet evidence verified (IEC 60086-4 / UN 38.3) before any cell PO; cold-chamber slot + mitten rig held | Battery Lead / PQT Lead |
| 4–5 | Lab contracts signed (PTCRB ATL + TCB/CAB + notified body); slot calendar agreed against EVT→PVT dates | Regulatory Lead |
| 5–6 | Carrier acceptance pre-check: Verizon Open Dev / AT&T IoT / T-Mobile forms against the module's approvals | Connectivity Lead |
| 6–12 | Stay-on-track reviews; §7 owner table filled (§13 mandate: named owner per row before S2 exits) | Regulatory Lead |

## 7. Owner assignment (§13 mandate: named owner per row before S2 exits)

| Domain (§13 rows) | Owner role | Filled? |
|---|---|---|
| Radio/telecom (FCC, PTCRB, ISED, carrier, CE RED, UKCA, GCF, SIG QDL) | **Regulatory Lead** | at approval |
| Safety/EMC (62368-1, CISPR, UL NRTL) | **Regulatory Lead** via CB-scheme lab | at approval |
| Battery/transport (UN 38.3, 62133-2 cells/packs, IATA, UL 2054) | **Battery Lead** | at approval |
| Environmental (RoHS, REACH, EU Battery Reg, WEEE, Prop 65) | **Operations Lead** | at approval |
| Cyber/data (ETSI EN 303 645, UK PSTI, EU CRA, GDPR) | **Security & Privacy Lead** | at approval |
| Open-source/IP (SPDX per build, FTO gate §13.1) | **Firmware Lead** (SPDX) / **WI-107 counsel** (FTO) | at approval |
| Ingress/mech claims (IP67, −40 °C, PQT/COLD) | **PQT Lead** (WI-501) | at approval |

Roles are role-named until approval; the named-person column is filled at the §9 gate.

## 8. Outreach-ready packets

### 8.1 Lab RFP packet (one packet, sent to every lab in §3.1–§3.4)

1. **Product:** wapiti cellular trail camera — IP67 ABS-PC enclosure, −40 °C rated,
   4K stills / 1080p video, motion-triggered, LTE-only media path.
2. **Radios:** the module selected at Step 0 — attach **its** grant certificates (for EG915U-LA that is FCC `XMR202210EG915ULA` only; PTCRB/CE/RED/carrier certificates do not exist for it, see §1) — plus **ESP32-C6** (BLE 5 + Wi-Fi 6). Quote with **grant reuse** applied; state exactly which tests remain at device level. **Scope note:** the C6's Wi-Fi/BLE are *intentional* radiators riding Espressif's module grant — not an SDoC-only line (§14.4's correction to §3.2) — so ask (i) below firms that reuse before you price it.
3. **Power:** 12×AA Li-FeS₂ primary (user-replaceable) + small Li reserve cell + rechargeable
   smart packs (5 Ah NMC / LTO).
4. **Asks:** (a) itemized test plan + price, (b) earliest slot dates, (c) reuse recognition
   confirmation, (d) EMC bundle (CISPR 32 / EN 55032), (e) UN 38.3 device-level T1–T8 price
   + sample quantity, (f) ISED RSS bundle price, (g) optional PQT/environmental bundle
   (IEC 60529 IP67, IEC 60068 drop/thermal/vibration, salt-fog) and chamber time,
   (h) **whether a device-level UN 38.3 run is required at all** when the primary AA cells are
   user-installed — price both ways (cell-level UN 38.3 + IEC 60086-4 evidence vs a full T1–T8
   run on the camera; §14.5 open question), and (i) written confirmation that **Espressif's
   ESP32-C6 module grant** covers our antenna/enclosure with no permissive change, so the C6
   is scoped as modular-grant reuse rather than a new intentional-radiator test (§14.4).
5. **Timeline:** test window tied to EVT/PVT board dates (TBD at WI-201/WI-204 kickoff).

### 8.2 Other openings

- **Bluetooth SIG:** company profile → Adopter → confirm the C6's QDID → End Product listing (§3.5 steps 1–4).
- **UN 38.3:** booking form items — UN Manual of Tests and Criteria T1–T8, chemistry (primary Li-FeS₂ + reserve Li primary; pack track quoted separately), device-level with cell installed, samples per lab quote, target slot ≤ EVT + 4 weeks.
- **Cold chamber:** slot + mitten rig for `COLD-05` (gloved swap < 20 s @ −40 °C) and `COLD-06` (500-cycle latch) — book in week 3–4, run in S5.
- **eSIM trial:** vendor IoT account → ~10 trial profiles → attach test on the Step-0 module's eval board across NA networks before the commercial MOU.

### 8.3 Vendor question sheet (send verbatim to every shortlisted module vendor — Quectel + SIMCom FAEs — before any PO/EVK spend)

> Purpose: convert every starred/`#` row of §1's comparison into a dated, written answer.
> No answer in writing = the candidate drops down the §1 ranking. Quote the question number
> in the reply so the answers can be filed against the PO-gate record (§1, (a)–(f)).
>
> **Module vendor — radio & certificates**
> 1. **Band map:** the exact LTE-FDD/TDD band list of the **shipping SKU** for our order — confirm **B12 and B13 enabled**, and state explicitly whether **B71 and B14** are present, absent, or a separate SKU option (`#` on your sheet).
> 2. **PTCRB:** certificate ID + issue date for that exact model/variant. Your sheet prints `PTCRB*` (under development) — is it issued today, and if not, the dated plan.
> 3. **FCC/ISED/CE:** grant ID(s) covering this variant (not a sibling's), ISED IC cert ID, CE-RED notified-body number, and the module's GCF listing status.
> 4. **Carrier approvals:** AT&T device ID, Verizon Open Development / approved-module-list entry, and T-Mobile acceptance reference **for this exact variant**, each with its date. Quectel's 2023 PR says "Verizon" for EG916Q-GL while the spec stars the carrier row — which is it?
> 5. **GNSS:** is GNSS on the SKU we would order, or a separate part number (`GNSS#` / "optional")? Which antenna feed and does it change the cert scope?
> 6. **Temperature:** is **−40…+85 °C** the *extended* rating (as printed) and is it warranted for **continuous** operation, not intermittent bursts? Datasheet line, please — our −40 °C published claim rides on it.
> 7. **Power:** burst current at 5 Mbps UL, idle/sleep figures, PSM and eDRX values — feeds the §6 power budget and the −40 °C derate.
> 8. **Known errata:** does the ~3% `701` HTTP failure mode we saw on the bench sibling (§8.7 / project-plan R-12) apply to this part? Errata list + DFOTA policy for baseband fixes.
> 9. **Supply:** unit price at 1k / 10k / 100k, MOQ, lead time, longevity/EOL notice period, form-factor compatibility statement (we design to LCC+LGA once).
> 10. **Samples:** quote the eval board + 10 production samples with the PO, and the full AT manual + certification schedule sheet (NDA'd carrier certificates included).
>
> **eSIM vendor — connectivity (1GLOBAL + each alternate)**
> 11. Multi-IMSI profile count and which NA networks each profile attaches to; eUICC/RSP platform and whether profiles are transferable off your platform (no lock-in).
> 12. Per-device pricing at our tier, trial terms (~10 profiles), and a written statement that no operator-profile change forces device recertification.
> 13. Activation evidence: an attach log on the Step-0 module's EVB across AT&T / Verizon / T-Mobile before the MOU is signed (feeds the §12 "N countries" box/site claim).
>
> **Lab / TCB / notified body — three answers the RFP (§8.1) must force**
> 14. Exactly **which grants you will reuse** at device level for the chosen module (name the grant IDs) and which tests remain — that sentence sizes §4 rows 4 and 9.
> 15. Earliest slot vs our EVT/PVT dates, with sample quantities per test.
> 16. Itemized price mapping every line to a standard (PTCRB program fee passed through at cost?).

## 9. Approval gate (the AC)

| Ask | Value |
|---|---|
| Approve kickoff budget band (§5) | **$30–65k for months 1–3** (part of §13's $200–400k program) |
| Approve selections | ⚠ **Module line reopened (§1):** EG915U fails the NA gate — approve the **requalification shortlist + its ranking** (1 EG916Q-GL → 2 SIM7672G → 3 SIM7672NA → 4 EG91-NA), the **PO gate (a)–(f)**, and sending the [§8.3 question sheet](#83-vendor-question-sheet-send-verbatim-to-every-shortlisted-module-vendor--quectel--simcom-faes--before-any-poevk-spend) to both vendors · eSIM: **1GLOBAL** (+ Truphone/Kigen alternates) |
| Approve lab shortlists | PTCRB ATL ×5, FCC TCB, ISED CAB, RED notified body ×4, UN 38.3 lab ×5, cold chamber |
| Authorize | RFP sends, SIG account, UN 38.3 + chamber slot holds, EVK orders (human actions) |
| Confirm out-of-scope | Skylo NB-NTN · GCF · SOC 2 · GNSS accuracy claim — deferred past v1 |

**Sign-off:** _pending_ — tick the boxes in [the playbook, Step 0](wi-106-certification-playbook.md#step-0--approve-5-minutes-closes-the-ac).

---

## 10. Verification (WI-106 self-check)

- [x] Every §13 row has a cost, a lead time, a phase, and an owner slot (§4, §7) — nothing in §13's matrix is uncosted.
- [x] Phase-1 subtotal $30.0–62.6k → proposed band **$30–65k**; itemized program ≈ $84–251k sits inside §13's **$200–400k / 6–9 months** (delta = retest/rush/consultant contingency, stated in §4).
- [x] Fee & lead-time claims sourced from public references checked **2026-10-26**: PTCRB program fees ($1.5–15k, ptcrb.com) · UN 38.3 (~$2.5k / 6–8 weeks lab, UltraLife Sep 2026) · Bluetooth SIG declaration ($4k Associate / free Adopter membership, TÜV SÜD + SIG FAQ) · CE RED (lab €2–12k + NB fee €1.5k+, 4–8 weeks) · FCC TCB sets its own fees/review time.
- [x] Module reconciled with §4.2 BOM and §8.7 AT-driver lineage, then **verified against primary sources on 2026-10-26**: Quectel *EG915U Series Specification V1.3* + *Introduction V1.0* (variant/band/certification/GNSS rows), FCC grant `XMR202210EG915ULA` (fccid.io grant notes), Verizon Open Development *Requirement Plan* (GCF Band 13) + approved-modules listings (SIM7672G #32869, EG91-NAXDL #18258), SIMCom SIM7672NA product page. **Result: fails the NA gate — §1 reopened, §19 risk 14.**
- [x] Program-cost risk from §1 stated where it lands: no module PTCRB/GCF reuse → §4 rows 4 and 9 grow; the Step 2 quotes re-price both.
- [x] Requalification shortlist **compared, not just listed** — checked against the vendors' own spec sheets on **2026-10-27**: SIMCom *SIM7672 Series* spec (2023-12-05) for the NA/G band maps, `*` (planning) and `#` (optional) legend, −40…+85 °C extended rating and SIM800-compatible AT; Quectel *EG916Q-GL* spec V1.1 for its band map, `*` (under development) carrier row, unstarred PTCRB/FCC/IC/GCF rows and optional GNSS; Verizon approved-modules #32869 (SIM7672G) and #18258 (EG91-NAXDL); SPYPOINT Flex-M manual (module-grant reuse of `XMR201807EG91NA`). Ranking recorded in §1; §8.3 question sheet is the instrument that firms every starred row.
- [x] Battery rows split correctly: primary Li-FeS₂ AA → IEC 60086-4 + cell UN 38.3 (buying gate); rechargeable packs → own 62133-2/UN 38.3/UL 2054 track (§19 risk 4).
- [x] Out-of-scope rows named explicitly (§0, §3.8, §9) so nothing is silently dropped.
- [ ] **Not fetch-verified — open in a browser before sending the RFP packet:** PTCRB test-lab list, ISED CAB list, Bluetooth fee schedule page, and a **written PTCRB non-existence confirmation for EG915U** (their device search is JS-rendered; absence is inferred from Quectel's own certification row).
- [x] No test IDs attach to WI-106 (no §13 API/device surface) — test-plan totals unchanged; lab evidence later lands in `PQT-01..14` / `COLD-*` (test-plan §22) filed under `tests/reports/pqt/`.
- [ ] **§14 options pass added 2026-10-27** — four cheaper paths priced against §4's rows; **no decision taken** — the §9 gate still governs, and a "cheaper path" pick is itself a Step-0 approval item.

---

## 14. Options analysis — cheaper paths

**Status:** 🟡 **PROPOSED — options pass, not a decision** · **Date:** 2026-10-27 · **Scope:**
addendum to this WI-106 deliverable, re-reading §4's cost table as *scope choices* rather than
fixed law.
**Trigger:** §1 reopened the module line, and $200–400k of envelope is mostly radio scope —
price the alternatives before Step 0 commits.

### 14.0 The precedent: a radio that was already certified

Field note from the AgLeader display program: the display shipped with a **USB WiFi/cellular
dongle**, and the display itself went through **no radio certification**. That is not a
loophole — it is the certification boundary working as designed:

- the dongle was a **separately authorized product**: its own FCC ID, its own PTCRB, its own
  carrier approvals, all held by the dongle's vendor and already paid for;
- the display had **no intentional radiator of its own**, so its US obligation was Part 15B
  **SDoC** — an EMC emissions test, self-declared: no TCB filing, no radio lab slot, no
  program fee;
- carrier acceptance rode the dongle, because the network approves the certified radio
  product, not your enclosure.

**The lesson for wapiti:** rows 4–9 of §4 (PTCRB, FCC/TCB, ISED, RED radio, carrier —
**$25–100k** of the itemized program) exist only because the radio is *inside the thing we
sell*. Move that boundary, or delete the radio, and those rows disappear; everything else in
§4 stays.

### 14.1 Fixed floor vs. variable scope

| Fixed (owed by any unit we sell, radio or not) | Variable (scope decisions this section prices) |
|---|---|
| FCC **SDoC** for the digital device (Part 15B EMC) — always | FCC **Certification** scope: which radios, which markets (rows 5, 6) |
| FCC authorization for **whatever radio we ship** — you cannot lawfully market a US radio without it | **PTCRB + carrier acceptance** (rows 4, 9) — cellular-only, and the largest/most fragile line |
| Cell transport evidence (row 2/3): cell- or pack-level UN 38.3 | CE/RED + UKCA (rows 7, 8) — market choice, not law, for a US-first v1 |
| Every published claim needs a report: IP67, −40 °C, 500-cycle latch (row 17) | BLE → Bluetooth SIG declaration (row 1) — drop BLE, drop the fee |
| PSTI/ETSI for a network-connectable product (row 15) — documentation work | UL NRTL (row 12) and the rechargeable-pack track (row 18) — channel / SKU choices |

### 14.2 Option A — radio outside the enclosure (the AgLeader model, literally)

Ship the product **without a wide-area radio** and put cellular in a separately certified,
resold peripheral/gateway.

- **For wapiti this works only as a two-SKU split:** the camera is WiFi/BLE + local storage
  (SD card), and cellular lives in a separate certified outdoor bridge (an off-the-shelf or
  ODM-certified box) sold as an accessory. The camera's program then has **no cellular rows at
  all**: row 4 → $0, row 9 → $0, row 5 → SDoC-only for the camera, row 6 → $0, row 7 → RED
  self-assessment.
- **Cost of the split:** two SKUs, two enclosures, a cable/ingress (IP67) problem between them,
  cloud ingestion for two device classes, and a support story ("why doesn't my camera
  upload?"). A bridge also needs mains or solar power — many trail sites have neither.

**Costing — planning-grade, built from §4.2's BOM; assumptions stated, not quotes:**

| Line | Integrated (plan of record) | A-1: bridge **bought** (resold, already certified) | A-2: bridge **built** |
|---|---|---|---|
| Camera BOM @10k | **$62–65** (§4.2) | **$49–52** — minus cellular $11 + eSIM $2; the C6 stays for setup/live-aim | **$49–52** |
| Bridge cost per site | — | ~**$60–90** landed (outdoor LTE gateway; the vendor holds the grants) | ~**$30–38** BOM (Cat-1bis module $11 + SoC/PSU/PCB/IP enclosure) |
| Radio certification (§4 rows 4, 5, 6, 9) | ≈ **$15–60k** on one unit | **≈ $0 new** — reselling a certified device; camera drops to SDoC + SIG | ≈ **$15–60k again**, but on a mains, indoor-rated box: no −40 °C, no IP67 chamber, simpler EMC |
| UN 38.3 device-level | required — cells ship installed in the camera | still required for the camera (ask (h) above) | camera only; the bridge is mains, no cell |
| Certification envelope | **$84–251k** itemized (§4) | **≈ $10–25k** (SDoC/EMC + SIG + cell evidence + whatever claims we keep) | ≈ §4 unchanged, less only what the mains box drops |
| Elapsed | 6–9 months | **~2–4 months** to a sellable camera | 6–9 months |
| Physical constraint | none | camera must sit within **WiFi range of the bridge** (tens of metres outdoors, best with line of sight); bridge needs **mains or solar** | same |

**Read:** only **A-1 changes the envelope** — it turns a $200–400k program into a ~$10–25k one
— but it sells a camera that uploads *only near a bridge*, so it is a cabin/yard SKU, not a
replacement for the remote camera. A-2 spends the same certification money on a second unit
plus a second support surface: **do not build the bridge unless the off-the-shelf options fail
the §1 PO-gate discipline.**

- **Verdict:** the right shape if a **cabin/yard WiFi variant** is a real product line; wrong
  as a replacement for the all-in-one remote camera, which is the product §0 describes.

### 14.3 Option B — sell a product that is already certified (highest leverage while §1 stands)

Private-label an ODM product that **already holds** FCC + PTCRB + carrier grants, exactly the
pattern §1 already cites (SPYPOINT Flex-M shipping `EG91-NA`).

- **What it removes:** the whole §1 requalification gate stops being our problem; rows 4, 5, 6,
  9 collapse to a **permissive-change** evaluation (Class I for enclosure-only changes — no new
  grant) or to zero if the RF chain, antenna and enclosure apertures are untouched.
- **What it keeps:** rows 11 (safety/EMC), 13, 14 (environmental), 15 (cyber), 19 (SPDX), and
  row 17 if we keep publishing IP67 / −40 °C claims — our differentiators don't come free.
- **What it costs:** margin (ODM + margin vs. in-house BOM), MOQ, roadmap locked to the ODM,
  and the **grantee question** — rebranding a certified device needs either the vendor to file a
  change of grantee ID (cheap, via a TCB) or the original markings to stay.
- **Verify before believing it:** the grant must cover the **exact SKU + variant we sell**, and
  the carrier approvals must be for **that model**, not a sibling — the PO-gate questions (a)–(f)
  in §1 get *shorter*, not deleted.
- **Est. effect:** −**$13–60k** on §4 rows 4–9 plus the removal of the §1 schedule risk; the
  remaining itemized program is roughly **$70–140k**, still inside §13's envelope.

### 14.4 Option C — WiFi/BLE only: what "just WiFi" or "just BLE" actually requires

**Answering the direct question — yes, a WiFi-only or BLE-only product still needs
authorization, but a completely different (and much cheaper) kind:**

| Obligation | WiFi only | BLE only | Both (our ESP32-C6) |
|---|---|---|---|
| FCC (US) | **Certification** (Part 15 Subpart C, §15.247 / §15.407) → FCC ID via TCB — *unless* ridden on a pre-certified module's grant | **Certification** (§15.247) → FCC ID — same module caveat | same, once, on the module grant |
| FCC (US), digital circuits | Part 15B **SDoC** — always, even when the radio rides a module grant | same | same |
| Bluetooth SIG | none | **Declaration + listing** (QDID reuse ≈ $4–9.6k) — contractual, not statutory, but enforced | SIG applies (row 1) |
| EU (RED) | EN 300 328 (2.4G) / EN 301 893 (5G DFS) + EN 301 489 → **self-assessed DoC** when harmonized standards are fully applied | EN 300 328 + EN 301 489 → self-assessed | DoC incl. EN 303 645 / EN 18031 (RED 3.3, in force since 2025-08-01) |
| Canada (ISED) | reuse the module's IC grant, else Certification (RSS-247 family) + ICES-003 | reuse, else RSS-247 | reuse, else RSS-247 |
| **PTCRB / carrier acceptance** | **none — cellular-only** | **none** | **none** |

- **Correction to §3.2:** the line "unintentional radiator (C6 Wi-Fi, digital device) → SDoC"
is right only because the **C6 rides Espressif's module grant**. WiFi/BLE are *intentional*
radiators; what makes them cheap is the modular grant, not the SDoC classification. Worth one
line of RFP wording so the lab scopes us correctly.
- **What a WiFi/BLE-only wapiti would cut:** rows 4 ($10–20k), 6 ($2–6k), 9 (≤$30k) → $0; row
  5 → SDoC-only; row 7 (RED) → self-assessment, no notified-body retainer; §1's entire module
crisis becomes irrelevant (there is no cellular module to qualify). **Rough cut: $40–100k off
the itemized program and the longest schedule risk removed.**
- **What it costs in product terms:** no uploads away from home WiFi, so "buyer is rural"
(§1) stops being true; cellular becomes a later, properly-funded wave. This is the honest
trade: it is a **different product**, not a cheaper one.

**Pre-certified hosts — the CM4/CM5 question (applies to any Pi-based variant of this
product):**

- **Raspberry Pi has already done the radio work.** The CM4 launch material tells integrators
  to "take advantage of our **modular certification** to reduce the conformance testing costs
  for your finished product", and the CM5 launch states that use of the Pi Antenna Kit "is
  covered by our FCC modular compliance". Pi's Product Information Portal publishes the FCC,
  CE/DoC and world-wide approvals per module (CM4 approvals, CM5 approvals incl. a *Radio
  Module* section).
- **So: no WiFi/BLE Certification of our own** when we build on the wireless CM4/CM5 variant,
  **provided we stay inside the modular conditions**: approved antenna options only (on-board
  PCB antenna *with* the specified ground-plane cut-out, or the Pi Antenna Kit for metal
  enclosures), no RF-layout deviations, the FCC ID / "Contains FCC ID…" statement on our
  label and in our manual, and no change that would be a permissive change.
- **What we still owe with a CM4/CM5 host:** (1) our own **Part 15B SDoC** for the carrier
  board (its digital emissions are ours), (2) the **SIG declaration** for our end product —
cite the existing controller/stack QDID rather than qualifying a new design, (3) an **EU DoC**
  that references Pi's RED reports plus our own EMC, (4) the same for ISED.
- **One trap:** the *whole-board* Pi 4B / Pi 5 (FCC IDs `2ABCB-RPI4B`, `2ABCB-RPI5`) is
  certified as a **single board computer** — a host certification, not a modular transmitter
  grant. Embedding a full SBC inside our product is a case-by-case call labs handle
  differently from a CM. **Take the CM route for anything we ship; get the SBC route in
  writing from a lab first.**
- **Nothing is owed until we market it:** prototypes, EVK rigs and in-house bench units carry
  **no** FCC equipment authorization — the obligation attaches on *marketing* (sale or
  distribution) in the US, so bring-up costs zero radio paperwork.
- **Sources (checked 2026-10-27):** CM4 launch post, modular-certification quote —
  raspberrypi.com/news/raspberry-pi-compute-module-4/ · CM5 launch post, Antenna Kit "covered
  by our FCC modular compliance" — raspberrypi.com/news/compute-module-5-on-sale-now/ ·
  approval sets — pip.raspberrypi.com/categories/636-approvals (CM4) and
  /categories/1102-approvals (CM5, *Radio Module* section incl. an FCC SDoC) · full-board IDs
  `2ABCB-RPI4B` / `2ABCB-RPI5` (fccid.io).
- **Fit for wapiti:** a CM4/CM5 is far too much power and cost for the camera's always-on
  −40 °C duty cycle; it is relevant only to a mains-powered hub/base variant (Option A's
  bridge) or to bench tooling.

### 14.5 Option D — scope surgery inside the current plan (no radio change)

Keeps the §1 module decision intact; cuts market/claim/channel scope instead.

| Cut | Rows affected | Saves (our own §4 estimates) | What it costs us |
|---|---|---:|---|
| US-first: defer CE/RED + UKCA + ISED | 6, 7, 8 | **$14–34k** + a notified-body queue | no EU/UK/CA sale until a later wave |
| Sell direct (no big-box): drop UL NRTL | 12 | **$5–15k** | retail-channel listing if we ever want it |
| Drop the NMC/LTO pack SKUs, primary cells only | 18 | **$5–20k** + 8–14 weeks | no rechargeable pack revenue; §5.1 smart-pack story |
| Drop published PQT/COLD claims | 17 | **$8–25k** | IP67 / −40 °C / latch claims we can no longer print |
| Drop BLE (WiFi + button/app setup instead) | 1 | **$4–9.6k** | setup UX; PSTI still applies to a network-connectable product |
| Module already carries carrier approvals (§1 gate (c)) | 9 | **$0–10k per carrier** | only achievable on EG916Q/SIM7672G-class parts — see §1 |
| | **Total removable** | **≈ $36–134k** of the $84–251k itemized program | |

### 14.6 What none of the options let us skip

1. **FCC authorization for any radio we ship** (Certification via TCB) and **SDoC for the
   digital device** — legal to market in the US, not a budget preference.
2. **PTCRB + carrier acceptance** if we keep cellular and want AT&T/T-Mobile/Verizon — their
   own program docs require end-device PTCRB; module grants alone do not get a device on
   network (§1 is right, and this is why Option C exists as a product fork).
3. **UN 38.3 at cell or pack level** for the lithium chemistry we ship.
4. **SIG declaration if BLE ships** — with QDID reuse it is the cheapest radio-adjacent row we
   have; cutting BLE to save it is usually a bad trade against the setup UX.

### 14.7 Read + recommended order

1. **Do Option D now** — it is free, reversible, and independent of §1. Take the
   "US-first + primary cells only" pair at Step 0; treat UL NRTL and PQT claims as a *channel*
decision recorded in §13's row notes.
2. **Run Option B in parallel with §1's PO gate** — if the §8.3 question sheet does not come
   back in writing from Quectel/SIMCom inside the Step-0 window, the rebadge path is the
   fallback that keeps the schedule, and it is already half-researched (§1's `EG91-NA` row).
3. **Treat Option A/C as a product fork, not a cost cut** — put "WiFi-first v1 + certified
cellular bridge" to the same human gate as the module ranking; it is the only path that
   genuinely removes the $200–400k radio program rather than shrinking it.

**Three questions this section could not answer from documents alone:** (a) does the lab agree
that a user-installed primary AA (row 2/3) needs only cell-level UN 38.3, not a device-level
T1–T8 run? (b) does Espressif's C6 module grant cover *our* antenna/enclosure without a
permissive change? (c) is a "camera + certified bridge" two-SKU BOM cheaper than one
integrated unit over 3 years? Route (a)–(b) to the RFP packet (§8.1) and (c) to product.
