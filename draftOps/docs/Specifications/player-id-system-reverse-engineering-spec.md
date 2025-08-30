# **ESPN Player ID System Reverse Engineering**

## **Objectives**

* Determine the method ESPN uses to identify players in draft data and establish a mapping between ESPN’s internal player IDs and the actual player names. We need to confirm whether the draft messages use numeric player IDs (likely) or names, verify that these IDs remain consistent across different drafts, and produce a preliminary lookup for ID → player name[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L22-L26). This will allow the DraftOps system to translate raw draft data into human-readable form.

## **Scope**

* **In Scope:** Analyzing draft message payloads and any available ESPN data sources to decode player identities. This includes extracting player identifiers from the WebSocket messages and cross-referencing them with known data (for example, using ESPN’s public API or existing player lists) to find the corresponding player names. We will perform tests in multiple mock drafts to ensure that the same player yields the same ID every time (consistency check across leagues)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L23-L25). Edge cases like new rookies, defensive team entries (DST), or players not in the standard dataset will be noted and investigated.

* **Out of Scope:** Comprehensive database development for all ESPN players is not required – we only need a functional mapping for the draft context. We are not implementing the full player resolution code here (the actual `PlayerResolver` class will be built in a later sprint); this task is limited to research and compiling reference data. Additionally, handling dynamic updates (e.g. new players added mid-season) is beyond the current scope.

## **Deliverables**

* **ID Mapping Reference:** A preliminary dataset or document mapping ESPN player IDs to player names. This could be a simple table (ID → Name) covering all players likely to be encountered in a draft. It will highlight any special cases (e.g., team defenses might have IDs that represent an entire NFL team).

* **Analysis Report:** Brief documentation of how the mapping was obtained and validated. This should describe the source of the data (e.g., extracted from draft messages or via an ESPN API) and note any anomalies or edge cases discovered (such as duplicate names or ID inconsistencies). For example, if we find that rookie players or free agents have unique handling in the ID system, it will be recorded here for future development consideration.

## **Assumptions & Constraints**

* ESPN’s draft events provide a consistent player identifier (expected to be a numeric ID) for each pick. We assume these IDs are globally unique and persistent at least within the 2025 season.

* We anticipate that the WebSocket messages might include only an ID (and not the full name), so external data will be needed to translate that ID. We are assuming access to an ESPN endpoint or dataset that can be leveraged for this mapping (for instance, ESPN’s fantasy API endpoints or a downloaded player list).

* The mapping is done for current season players; any future changes in ESPN’s ID scheme (or yearly new IDs for players) are outside the scope of this sprint. We will note the need to update the mapping each season as a future consideration.

* Our solution will rely on **ESPN player IDs as the primary key for players**, using names purely for display[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L156-L160). This approach avoids any ambiguity from duplicate names and aligns with best practices (the DraftOps design notes that using stable IDs prevents name mismatch issues[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L156-L160)).

* Time is a factor; we will gather enough samples to be confident in the mapping but may not exhaustively verify every single player. We assume common players and a handful of edge cases will provide sufficient coverage to proceed.

## **Milestones**

1. **Extract Sample IDs:** Capture the raw data for a few draft picks in a mock draft and identify where the player identifier is present in the message (e.g., a field like `playerId` or similar)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L22-L25). Note the format (numeric string, integer, etc.) and whether any player name or metadata accompanies it.

2. **Cross-Reference Player Data:** Using the identified IDs, query available resources to find the corresponding player names. This may involve:

   * Checking if the ESPN WebSocket or related API provides a lookup (for example, an initial draft sync message or a known ESPN API endpoint that returns player info by ID).

   * If no direct API is accessible, using an external data source (like a pre-existing list of ESPN player IDs from FantasyPros or an ESPN players dataset) to match IDs to names.

3. **Consistency Verification:** Repeat the identification process in at least one additional draft (or using multiple known player examples) to ensure that the same player always has the same ESPN ID[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L23-L25). For instance, confirm that a specific star player’s ID in one draft is identical in another draft session.

4. **Handle Edge Cases:** Investigate any special cases:

   * **Rookies:** Ensure newly added players (rookies for the season) have IDs and appear in our mapping.

   * **Team Defenses (DST):** Verify how team defense/special teams are represented (they might have their own ID entries distinct from individual players).

   * **Name Collisions:** Consider if two players share a name; our approach of using IDs should avoid confusion, but note if any context is needed (likely not, since IDs are unique).

   * **Inactive/Free Agents:** If the draft pool includes players who are not currently on an NFL team (free agents), confirm they have IDs and are mapped correctly.

5. **Compile Mapping and Documentation:** Assemble the list of ID-to-name mappings into a reference document or file. Include notes on how it was generated and any uncertainties that remain (e.g., if some IDs couldn’t be resolved with confidence). This deliverable will serve as the basis for implementing the player resolution logic in the next sprint.
