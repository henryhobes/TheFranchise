# **Pre-Draft Player Data Integration & Context Setup**

## **Objectives**

* **Load all player data into memory before the draft.** We will parse the provided CSV files in `draftOps/playerData` so that our AI has a complete, static knowledge base of every draftable player. No external API calls or real-time data fetching will occur during the draft.

* **Cover all draft positions (QB, RB, WR, TE, K, DEF).** The data includes separate files for offense and defense projections. We will combine these so the AI sees a unified player pool across all positions.

* **Include consensus rankings and projections.** We will extract each player’s ranking and ADP from the consensus ADP file (including *average ADP* and *standard deviation* for consensus) as well as projected fantasy points and stats from the projections files. League settings (PPR scoring, 6-pt passing TDs) are already reflected in the provided data.

* **Prepare data for AI usage.** The loaded data will be formatted into convenient structures (e.g. lists or dicts of Player objects) so that the AI agents can easily query top available players and positional rankings during the draft. By the end of this sub-sprint, every player’s key information will be in memory, enabling the AI to make informed recommendations.

## **Scope**

* **In Scope:**

  * **Loading provided CSVs:** We will parse the following data files:

    * **`ADP_Fantasy_Football_Rankings_2025.csv`** – Consensus ADP and rankings for all players (including defenses). Fields include overall ADP, a composite position code (e.g. `WR-01` means top wide receiver), team, and rankings from various sources. We will use the **average ADP** and **Std Dev** columns so the AI knows each player’s consensus ADP and reliability. (The “Position” field’s suffix (e.g. “01”) indicates the player’s rank within that position.)

    * **`Non_DEF_stats_ppr_6ptPaTD.csv`** – Projected fantasy points and detailed stats for offensive players (positions QB, RB, WR, TE, K). Columns include projected FF points, ADP, and per-category stats (passing yards, rushing yards, receptions, TDs, etc.). Each row also has a **PID** and player name.

    * **`DEF_stats_ppr_6ptPaTD.csv`** – Projected stats for team defenses (FF points, sacks, turnovers, etc.) along with ADP in 10- and 12-team leagues.

  * **Data merging and structuring:** We will merge these sources into unified player records. Offensive players will be matched by name (and PID if needed) between the ADP and stats files; defensive teams will be treated as “players” with position `DEF` (e.g. “Broncos Defense”). Each Player object will include fields such as name, team, position, position rank, overall ADP (Avg), ADP Std Dev, and projected fantasy points. For offensive players, we will also include their key projected stats.

  * **DraftState integration:** On draft start, we will initialize `DraftState.available_players` with the full list of loaded Player objects. As picks are made, the code will remove drafted players from this list (so the AI always sees who remains). We will support filtering by position when needed.

  * **League settings:** The provided data assumes a PPR league with 6-pt passing touchdowns (as noted in the file names). We will document that this is our default scoring. If the league had different settings (e.g. Standard scoring or 2-QB), adjustments are out of scope for this sprint.

* **Out of Scope:**

  * **Real-time data updates:** We will not fetch or update player data during the draft. All analysis uses the static preloaded data.

  * **Advanced algorithms:** We will not implement new projection models or AI pick logic beyond ensuring data availability. No deterministic pick engine or value calculations are in this task – the AI will use the raw data we load.

  * **Utility query functions:** (Removed per direction) For now, we focus solely on loading and structuring the data. We will *not* build extra helper functions like “get top 10 available” or implement ESPN ID cross-referencing in this sub-sprint. (These can be added later; currently we only need the basic data module.)

## **Deliverables**

* **Player Data Loader & Structures:** A new module (e.g. `draftops/data_loader.py`) that reads the CSV files and creates Python representations for each player. For each player (or defense unit), we will capture:

  * **Identity:** Player name (or team name for DEF) and team.

  * **Position & Rank:** Position (QB, RB, WR, TE, K, or DEF) and position-specific rank (parsed from strings like `WR-01`).

  * **Rankings/ADP:** Consensus ADP (average) and standard deviation (from the ADP CSV), plus any useful column like overall ADP.

  * **Projected Points/Stats:** Fantasy points projection and underlying stats from the projections CSVs (passing yards/TDs, rush yards/TDs, receptions, etc., for offensive players; sacks, turnovers allowed, etc., for defenses).  
     Each player entry will be keyed so that it can be removed when drafted. The loader will also perform basic validation (e.g. total player count, no duplicate names/IDs) and output a summary like “Loaded N players (X QBs, Y RBs, ...)” to confirm correctness.

* **Integration with DraftState:** Code changes so that when a draft begins, we call the loader and set `DraftState.available_players` to the full list of loaded players. We will test that when a pick occurs (we simulate this in a unit test or small script), the chosen player is removed from `available_players` and added to `drafted_players`. This ensures that the DraftState stays in sync with our data pool.

* **Context Readiness (brief):** While detailed AI prompt construction is not in scope, we will ensure the data format allows easy extraction of useful subsets. For example, after loading we can quickly obtain “top 5 available players overall” or “best available RB” by sorting the `available_players` list by ADP or projected points. (We will verify this in testing.)

* **Verification & Testing Outputs:** We will produce sample outputs to demonstrate that the data has been loaded correctly. This might include a printed list of the top 10 players by ADP and by each position, and a demonstration of removing a player when he is drafted. These tests will show that the system has the correct players and that the data fields (like ADP and Std Dev) match expectations from the source files.

## **Assumptions & Constraints**

* **Static, up-to-date data:** We assume the provided CSV files are comprehensive and current (e.g. updated shortly before draft day). Keeping them updated is a manual step outside this sprint.

* **Positions covered:** All standard roster slots are included: QB, RB, WR, TE, K, and DEF (team defenses). The Non\_DEF stats file covers QB/RB/WR/TE/K, while the DEF stats file covers defenses. Every draftable player should appear in at least one file.

* **Position rank format:** The ADP CSV’s “Position” field uses a format like `WR-01` or `RB-03`; the number is the player’s rank within that position. We will parse this so the AI can distinguish, for example, “WR-01” (the top WR) from other WRs.

* **Name matching:** We assume player names in the ADP file and the Non\_DEF stats file will match closely. If discrepancies arise (like middle initials or suffixes), we will handle them via a simple resolver or manual mapping as needed. (This sprint does not rely on ESPN’s ID system; we’ll match on name/position and log any misses for review.)

* **League settings:** The loaded data already reflects PPR scoring and 6-point passing TDs (as indicated by file names). We will proceed with those settings. If the league had different scoring, that would require separate data or adjustments, which is beyond the current scope.

* **Memory/Performance:** The total player pool is on the order of a few hundred players, which is easily handled in memory. We will not worry about database persistence; all data will reside in RAM for the duration of the draft session. The main limitation to note is the AI context window – we won’t try to feed the entire list of 300+ players to GPT at once, but will extract top subsets as needed.

## **Milestones**

1. **Data Schema & File Preparation:** Define the data model for our players. Decide which fields from the CSVs we need (e.g. name, position, team, ADP, Std Dev, projected points, etc.). Place the provided CSVs (ADP and stats) into our project (e.g. under `draftOps/playerData`). Verify the file formats by inspecting a few rows (confirm columns like “ADP”, “Avg”, “Std Dev” exist, and note positions included). By the end of this step, we have a clear list of fields and sample data to work with.

2. **Implement Data Loader:** Write the code to parse `ADP_Fantasy_Football_Rankings_2025.csv` and the two stats files. Merge records by player name (and PID if helpful). Create a `Player` class or dict for each entry with all the desired fields. After implementation, run a quick script that prints: total number of players loaded, and the top 5 players overall and top 5 by each position (sorted by ADP). Check that these match the expected names from the source files.

3. **Integrate with DraftState:** Modify the draft initialization so that it calls the loader and fills `DraftState.available_players` with the full player list. Write a small test (or use an existing mock draft script) that simulates a few picks: remove a player from the list and verify the next top players update correctly. For example, if player X (with lowest ADP) is drafted, ensure that a later ADP player now appears as the top available. This verifies that removal logic works.

4. **Basic Context Verification (optional):** As a sanity check, we may create a simple function that takes `DraftState` and returns a formatted string of “Top available players: …” or “Our roster needs: …” based on the loaded data. We will use this to ensure that retrieving subsets (e.g. top RBs) works as intended. This step is not about final AI prompts, but about demonstrating data is easily queryable.

5. **Documentation & Final Testing:** Document the data loader usage (e.g. in code comments or a brief MD file). Include notes on where the files come from and what each field means (especially noting that “Avg” and “Std Dev” are in the ADP CSV). Perform a final dry-run: e.g. load data, simulate 10 picks in sequence (removing players each time), and ensure no errors occur. Print out a final roster or remaining player count to confirm consistency. This completes the sprint’s goal of having a reliable, integrated pre-draft data module for the AI to use.
