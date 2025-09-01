# **Scout Node Specification**

The **Scout** node is an AI-driven pick recommendation agent that selects exactly one player from a provided shortlist of candidates, using the draft context and strategy to justify the choice. It runs GPT-5 (the same model instance used by the Supervisor) with the given inputs and outputs a single suggestion plus a concise 1–2 sentence reason[GitHub](https://github.com/henryhobes/TheFranchise/blob/bafceb001382849b4e740fa0a731a0ff7eca4f71/draftOps/docs/draftops-overview.md#L51-L55). We execute this agent 10 times (with high temperature and different random seeds) to generate 10 diverse pick recommendations for the GM node.

## **Inputs**

* **pick\_candidates** (list of length \= SELECTION\_BUDGET, default 15): A shortlist of player objects (pre-built by the Strategist). Each player entry must include at least: `player_id`, `name`, `position`, `adp`. It can optionally include rich context fields like `projection`, `tier`, `value_over_baseline`, `injury_status`, `risk_flag`, `bye_week`, `team`, `stack_keys`.

* **pick\_strategy** (string): A short strategy string from the Strategist describing the current draft approach.

* **draft\_state** (JSON): Current draft context summary, including fields such as `round`, `pick`, `picks_until_next_turn`, `our_roster_counts`, and `lineup_rules`. It may also contain `positional_runs` (how many picks since a position was taken) or `tier_snapshots` (status of tier breaks).

All inputs are provided to the Scout; it does **not** fetch additional data.

## **Output**

Each Scout run must return a JSON object with exactly one suggestion, for example:

`{`

  `"suggested_player_id": "<player_id>",`

  `"suggested_player_name": "<player_name>",`

  `"position": "<position>",`

  `"reason": "<concise justification (≤2 sentences)>",`

  `"score_hint": 0.0`

`}`

* **suggested\_player\_id/name/position**: Identifiers of the chosen player (must match one of the shortlist).

* **reason**: A maximum of two sentences explaining the pick. It should be concrete (e.g. “We need a WR2 and this player’s ADP has fallen”), citing at least one key factor.

* **score\_hint** (optional): A confidence or utility score (0–1), if produced.

Return *only* this JSON (no additional text or commentary).

## **Behavior & Constraints**

* **Single pick**: The agent must pick *one and only one* player from the provided `pick_candidates`.

* **Concise justification**: The `reason` field must be ≤2 sentences, specific and concrete. It should reference at least one driver such as roster **need**, tier **urgency**, ADP/value gap, position **run**, team **stack**, or player **risk** (citing that factor).

* **Tie-breaking**: If multiple candidates seem similar, prefer the one that better fits team needs, has a stronger tier edge, better ADP relative to current pick, higher projection, or lower risk (in that order).

* **No invented data**: Do **not** invent stats or use information not in the inputs. Do **not** expand the candidate list or hedge (avoid phrases like “maybe”, “should consider”).

* **Strict format**: Output must match the JSON schema above. No extra keys, lists, or commentary are allowed.

## **Prompt & Execution**

We use a fixed system prompt to define the Scout’s role and rules. The user prompt provides the inputs in a template form:

`PICK_STRATEGY: {pick_strategy}`

`DRAFT_STATE: {draft_state_json}`

`PICK_CANDIDATES (size={N}): {pick_candidates_json}`

The system prompt emphasizes: *“You are the SCOUT. Select exactly ONE player from the shortlist. Use the draft strategy and state to justify the pick in ≤2 sentences. Cite relevant factors (need, tier break, ADP/value drop, run, stack, risk). If players are close, break ties by need, tier, ADP, projection, or lower risk. Return only the JSON schema.”*

* **Model**: We call GPT-5 (same family of model used by the Supervisor agent[GitHub](https://github.com/henryhobes/TheFranchise/blob/bafceb001382849b4e740fa0a731a0ff7eca4f71/draftOps/docs/draftops-overview.md#L51-L55)).

* **Inference settings**: Use a temperature around 1.0 (e.g. 0.9–1.1) and `top_p=0.95`, `max_tokens=120`.

* **Parallel runs**: Execute 10 concurrent GPT calls with identical prompts but different random seeds (e.g. seeds 101–110) to encourage diverse outputs.

* **Result collection**: Gather the 10 JSON responses. (No de-duplication at this stage; overlap is handled downstream.)

## **Acceptance Criteria**

* **Valid JSON**: Each output must be valid JSON matching the schema above, containing exactly one suggested player from the input list.

* **Constrained output**: The reason must be ≤2 sentences, focused, and cite at least one specified driver (need/tier/ADP/value/run/stack/risk).

* **Consistency and diversity**: With the same inputs and seed, the output should be stable. Changing the seed should produce a different plausible suggestion.

* **No rule violations**: The agent must not make network calls, fetch additional data, or modify the draft state. It must not add or remove candidates, nor introduce extra output fields.

* **Performance**: Running 10 GPT-5 calls in parallel should complete within a reasonable time (target a few seconds overall for typical draft use).

## **Non-Goals**

* The Scout node does *not* make the final draft decision (that is the GM node’s responsibility).

* It does *not* manage roster counts or perform any reallocation of resources.

* It does *not* fetch or compute new player data; it only uses the provided candidate list.

* It does *not* handle any UI, timers, or ESPN draft integration – only the pick evaluation logic.

The above specification aligns with the overall DraftOps architecture of pure AI-driven decision-making using GPT-5[GitHub](https://github.com/henryhobes/TheFranchise/blob/bafceb001382849b4e740fa0a731a0ff7eca4f71/draftOps/docs/draftops-overview.md#L51-L55), ensuring the Scout node reliably produces one concrete, justified pick recommendation per invocation.

**Sources:** Derived from the DraftOps design and sprint planning documents[GitHub](https://github.com/henryhobes/TheFranchise/blob/bafceb001382849b4e740fa0a731a0ff7eca4f71/draftOps/docs/draftops-overview.md#L51-L55).
