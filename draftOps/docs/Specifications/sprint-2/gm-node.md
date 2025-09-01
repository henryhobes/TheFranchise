# **GM Node Specification**

The **GM (General Manager)** node is the final decision-making agent in the DraftOps AI pipeline. It takes the curated recommendations from the Scout node (ten candidate picks with reasoning) plus the current draft context, and selects exactly one final player to draft, with a concise justification. Like other nodes, it runs on the GPT-5 model. The GM node’s job is to **aggregate multiple Scout suggestions** and synthesize them into a single pick[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L541-L546)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L550-L554).

## **Inputs**

* **scout\_recommendations** (list of 10 objects): The ten JSON suggestions produced by the Scout node (parallel runs). Each object contains the keys `suggested_player_id`, `suggested_player_name`, `position`, `reason`, and an optional `score_hint` (confidence score)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L500-L504)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L550-L554).

* **pick\_strategy** (string): The strategy rationale string from the Draft Strategist, describing the current draft approach (same as provided to the Scouts).

* **draft\_state** (JSON): Current draft context (same format used by other nodes). This includes fields like round, pick number, our roster counts, picks-until-next, lineup rules, etc., so the model knows team needs and draft position.

*Note: All inputs are provided in the prompt; the GM node does not fetch external data.*

## **Output**

The GM node must return a single JSON object with exactly one final recommendation. For example:

`{`

  `"selected_player_id": "<player_id>",`

  `"selected_player_name": "<player_name>",`

  `"position": "<position>",`

  `"reason": "<concise justification (≤2 sentences)>",`

  `"score_hint": 0.0`

`}`

* **selected\_player\_id/name/position**: The identifiers of the chosen player (must match one of the Scout candidates).

* **reason**: A brief explanation (up to 2 sentences) justifying the selection. It should be specific and reference at least one relevant factor (need/tier/ADP/run/stack/risk/etc.), summarizing why this pick is best.

* **score\_hint** (optional): A confidence or utility score (0–1) for the chosen pick, if the model outputs one (this can help downstream weighting).

Return *only* this JSON (no extra text or commentary).

## **Behavior & Constraints**

* **Single pick**: Must select *exactly one* player from the Scout recommendations.

* **Reasoning focus**: Provide a concise justification (≤2 sentences) tied to concrete factors (e.g. roster need, tier urgency, ADP value, position run, etc.). Do **not** add unrelated rationale or introduce new criteria not implied by the inputs.

* **Tie-breaking**: If multiple candidates seem viable, prefer the one with higher `score_hint` or clearer need. In practice, the GM should favor the suggestion with the strongest confidence and strategic fit[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L543-L546)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L550-L554). (If the model fails or ties occur, fallback to the highest-confidence Scout pick as a safety measure[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L544-L548).)

* **No extraneous data**: Do **not** invent any facts or stats. Only use information present in the inputs. Do **not** alter the set of candidates or their details. No lists or additional keys are allowed.

* **Strict format**: Output must match the JSON schema above exactly. No additional fields or prose.

## **Prompt & Execution**

A fixed system prompt defines the GM’s role and rules, similar to the Scout. The user prompt will present the inputs, for example:

`SCOUT_RECOMMENDATIONS: {scout_recommendations_json}`

`PICK_STRATEGY: {pick_strategy}`

`DRAFT_STATE: {draft_state_json}`

A suitable system prompt might be: *“You are the GENERAL MANAGER (GM). From the 10 candidate recommendations and the given strategy and state, choose **exactly ONE player** to draft. Use context (roster needs, strategy, tier runs, ADP, etc.) to justify the pick in ≤2 sentences. Return only a JSON object with `selected_player_id`, `selected_player_name`, `position`, `reason`, and optional `score_hint`.”*

* **Model**: GPT-5 (same model family as the Supervisor and Scout)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L541-L546).

* **Inference settings**: Typical settings (e.g. temperature \~0.8–1.0, top\_p \~0.9) to allow reasoning, with a token limit sufficient for the output (≤120 tokens).

* **Execution**: Single GPT call (no parallel runs needed, since GM is the final aggregator).

* **Result**: Parse the JSON output as the final pick decision.

## **Acceptance Criteria**

* **Valid JSON**: The output must be well-formed JSON matching the schema above, with exactly one selected player.

* **Concise, relevant justification**: The `reason` is ≤2 sentences and cites at least one driver (e.g. team need, best value, position scarcity).

* **Determinism and consistency**: For identical inputs and seed, output should be stable. Varying the seed (if used) may produce a different but still plausible selection.

* **No violations**: The GM must not fetch extra data, call APIs, or perform any draft state changes. It should not reference the Scout process explicitly or output anything beyond the JSON object.

* **Performance**: The GPT call should complete quickly (a few seconds at most) to suit live draft timing.

## **Non-Goals**

* The GM node does *not* fetch or update draft data (state is read-only).

* It does *not* interact with ESPN or UI – it only computes the pick selection logic.

* It does *not* manage roster assignments or suggest bench swaps; it only picks the next player.

**Sources:** Requirements and design derived from the DraftOps Sprint 2 plan and summaries[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L541-L546)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L550-L554)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L501-L504), which outline the GM’s role of aggregating Scout recommendations and performing final selection (with confidence weighting and fallback)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L543-L546)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L548-L554). The format and constraints follow the existing spec style used for the Scout node[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/Specifications/sprint-2/scout-node.md#L15-L23)[GitHub](https://github.com/henryhobes/TheFranchise/blob/48bba1aa1d2c3771832b396d1945c99cc941c097/draftOps/docs/sprint-results/sprint-2-summary.md#L541-L546).
