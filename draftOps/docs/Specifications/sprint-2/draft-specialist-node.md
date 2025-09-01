## **1\) Purpose**

Produce a **position→count allocation** and a **concise rationale** for the current pick context.  
 This **does not build the Scout or GM nodes**; it delivers the contract **they will consume in the next subsprints**.

---

## **2\) Scope (this sub-sprint)**

* Implement **Draft Strategist** logic and return payload.

* Make `SELECTION_BUDGET` **configurable** (default **15**).

* Expose read-only helpers to compute signals (need/tier/value/run).

* **Out of scope now:** Scout fetching, GM ranking/decision, UI.

---

## **3\) Inputs**

* **Draft state:** round, pick, snake direction, picks until our next turn; available/taken players.

* **Roster state (ours):** filled starters/bench per position; league settings (PPR, FLEX).

* **Player data (preloaded):** **ADP** (primary), optional projections/tiers/VOB/injury/bye.

* **Config:** `SELECTION_BUDGET` (int, default 15), weights, late-draft rule, optional min/max per position.

---

## **4\) Output Contract (to be consumed by future Scout/GM)**

Return a single JSON object:

`{`

  `"player_lookup": {`

    `"QB": 0,`

    `"RB": 0,`

    `"WR": 0,`

    `"TE": 0,`

    `"DST": 0,`

    `"K": 0`

  `},`

  `"pick_strategy": ""`

`}`

### **`player_lookup`**

* **Keys (fixed):** `QB`, `RB`, `WR`, `TE`, `DST`, `K`

* **Values:** integers ≥ 0

* **Invariant:** `sum(values) == SELECTION_BUDGET` (configurable; default 15\)

* **Meaning:** counts telling the **future Scout** how many candidates per position to pull.

### **`pick_strategy`**

* 1–3 sentences explaining the allocation (refer to roster need, tier urgency, ADP value, runs, late-draft rule).

Implementation note: This payload is **final API** for the next sub-sprint (Scout). Do not change field names without versioning.

---

## **5\) Decision Logic (how counts are set)**

Compute per-position signals in \[0,1\]:

* **RosterNeed**: deficit vs ideal starters \+ bench plan.

* **TierUrgency**: risk a tier cliff occurs before our next pick.

* **ValueGap**: best available ADP vs expected slot (fallers ↑).

* **RunPressure**: recent picks concentrated at a position.

* **Scarcity** (optional): structural scarcity (e.g., elite TE).

Default weights (configurable):

`score = 0.40*RosterNeed`

      `+ 0.25*TierUrgency`

      `+ 0.20*ValueGap`

      `+ 0.10*RunPressure`

      `+ 0.05*Scarcity`

Allocation:

1. Normalize scores → proportions.

2. `raw = proportion * SELECTION_BUDGET`

3. Floor; distribute remainders by largest fractions (stable tie-break).

4. Apply optional min/max clamps.

5. **Late-draft rule:** withhold `DST`/`K` until starters \+ priority depth are covered **or** final 2–3 rounds; once allowed, force ≥1 each before final pick.

6. Re-validate sum; rebalance deterministically if needed.

Determinism: identical inputs ⇒ identical outputs.

---

## **6\) Examples (assume `SELECTION_BUDGET=15`)**

**Early**

`{`

  `"player_lookup": { "QB": 0, "RB": 3, "WR": 10, "TE": 2, "DST": 0, "K": 0 },`

  `"pick_strategy": "WR tiers are deep and match roster gaps; keep small RB/TE slices for potential tier breaks or a falling RB."`

`}`

**Mid**

`{`

  `"player_lookup": { "QB": 1, "RB": 6, "WR": 7, "TE": 1, "DST": 0, "K": 0 },`

  `"pick_strategy": "RB tier thinning and you’re light there; maintain WR coverage; small QB/TE for opportunistic value."`

`}`

**Late**

`{`

  `"player_lookup": { "QB": 1, "RB": 4, "WR": 6, "TE": 2, "DST": 1, "K": 1 },`

  `"pick_strategy": "Starters set; balance RB/WR depth and begin shortlisting DST/K so you’re not scraping at the end."`

`}`

---

## **7\) Downstream Integration (next sub-sprint preview — not implemented now)**

* **Scout (next):** For each position `P` with count `c`, **filter available players at `P`, order by ADP asc, select top `c`** (ties via configured secondary sort, e.g., projection). Merge into a candidate set of size `SELECTION_BUDGET`.

* **GM (after Scout):** Score that shortlist and make the pick.

*(This section exists to justify the Strategist’s output shape; building Scout/GM happens in subsequent subsprints.)*

---

## **8\) Interfaces (read-only for this sub-sprint)**

* `get_available_players_by_position(pos) -> List[Player]`

* `get_current_roster() -> Roster`

* `get_draft_board() -> Board`

* `get_picks_until_next_turn() -> int`

* `get_adp(player_id) -> float`

* Optional tie-breakers: `get_projection(player_id)`, `get_tier(player_id)`

---

## **9\) Config (single source of truth)**

* `SELECTION_BUDGET: int = 15`

* `weights: {RosterNeed:0.40, TierUrgency:0.25, ValueGap:0.20, RunPressure:0.10, Scarcity:0.05}`

* `secondary_sort: "projection" | "vob" | "risk_adjusted_projection"`

* `late_draft_rounds: int = 2`

* `allow_dst_k_early: bool = false`

* Optional clamps: `min_per_pos`, `max_per_pos`

---

## **10\) Acceptance Criteria (this sub-sprint)**

* Returns valid JSON with **both** fields; includes all **six** position keys; integers ≥ 0\.

* `sum(player_lookup.values()) == SELECTION_BUDGET` (respects config changes).

* `pick_strategy` is 1–3 sentences and cites at least one driver (need/tier/value/run).

* Deterministic outputs for identical inputs.

* Edge handling:

  * If a position has fewer available players than requested, take all; rebalance remaining counts deterministically.

  * Major ADP faller at non-need position → `ValueGap` can increase that position’s share.

  * Detected positional run boosts `RunPressure` temporarily.

---

## **11\) Telemetry & Debug**

* Log inputs (round, picks-to-turn, roster gaps, tier snapshots).

* Log signals per position, final weights, raw counts, remainder distribution, clamps, and late-draft adjustments.

* Emit the finalized allocation and `pick_strategy`.

---

## **12\) Non-Goals (now)**

* Building Scout/GM, trade logic, keeper math, deep injury/bye optimization, UI.
