# **End-to-End Draft Monitoring & Logging**

## **Objectives**

* Combine the connection and state management components into a **Minimal Viable Draft Monitor** that runs through an entire draft, logging every pick in real time[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L120-L125). The objective is to deliver a console-based tool that a user can run, which will attach to an ESPN draft (likely a mock draft for testing) and output each draft event (especially picks) as they happen, along with relevant context (e.g. which team is on the clock, how many picks until the user’s turn, etc.). We aim to demonstrate that all pieces work together: the system consistently captures draft events, updates the internal state, and presents information to the user without lag. Performance is key – the monitor should process and print each pick recommendation within a fraction of a second so that it could feasibly be followed by a human drafter in real time[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L2-L5). By the end, we want to show that we can track a complete multi-round draft end-to-end, meeting the Sprint 1 goal of a working live draft monitor[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L2-L5).

  ## **Scope**

* **In Scope:** Building the **console application** (or script) that orchestrates the draft monitoring. This includes initializing the `ESPNDraftMonitor` (with Playwright) to connect to a draft room, starting the WebSocket listener, and integrating the event processing pipeline with our `DraftState` updates and logging. We will handle user configuration such as specifying which league or draft to join (for testing, this might be done via a URL or league ID input or by automatically joining the first available mock draft). The scope also covers real-time logging output: formatting each pick event into a human-readable line (e.g. “Round X, Pick Y: Team Z selected Player Name (Position, NFL Team)”). We will use the **PlayerResolver** implemented in Sprint 0 to translate ESPN player IDs to names for the log output[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L126-L130), thus fulfilling the requirement that player names are shown correctly (target 95%+ accuracy) in the console. Additionally, this integration will ensure that the **picks-until-my-turn** calculation is displayed or can be inferred, and that the monitor can indicate when our team is on the clock (for the user’s awareness). Basic end-to-end testing of different draft conditions (various league sizes, draft lengths) falls within scope to validate the monitor’s robustness.

* **Out of Scope:** Any graphical user interface beyond the console (no GUI app or web interface at this stage). Also, we are not implementing user input during the draft (the user won’t control the draft via our tool – they will still manually draft on the ESPN site; our tool is read-only assistance). The monitor will not **make recommendations** in Sprint 1 – it merely logs information. Strategy analysis or AI integration is deferred to Sprint 2+. Also out of scope is persistent logging to a file or database – we will print to console; persistent log can be added if needed but not required now. Finally, handling unexpected draft formats (auction drafts, or paused drafts) is not in this scope; we assume a standard snake draft as per the earlier assumptions.

  ## **Deliverables**

* **DraftOps Monitor Console Script:** A runnable Python script (e.g. `run_draft_monitor.py`) or entry-point that launches the monitoring process. This script will likely:

  1. Launch a Playwright browser and navigate to the ESPN fantasy draft page (possibly requiring the user to log in if not already).

  2. Instantiate `ESPNDraftMonitor` and call `connect_to_draft()` with the appropriate draft URL or league details.

  3. Set up the WebSocket frame handler such that each incoming message triggers our `process_websocket_frame` function.

  4. Continually listen and, for each relevant event, update the state and print a log line to the console.

  5. Also handle termination gracefully (e.g., when the draft ends or if the user aborts, close browser and exit).

* The deliverable includes this script and any necessary configuration or README notes on how to use it (e.g., “Launch this script while logged into ESPN in a browser, it will auto-join a mock draft and begin monitoring.”). It effectively ties together everything from Sprint 1 into a usable tool.

* **Real-Time Pick Logging:** The system will output each pick in a human-friendly format. For example:

  1. *“Pick 1.01: Team A selected **Justin Jefferson** (WR, MIN)”*

  2. *“Pick 1.02: Team B selected **Ja'Marr Chase** (WR, CIN)”*  
      This includes the pick number (round.pick format if possible), the team (if we can retrieve the team’s name or at least an identifier; initially we might use “Team X” where X is the team’s draft slot or ID), and the player's name and possibly position/NFL team for clarity. The PlayerResolver will supply the name (and we can have a pre-loaded mapping of player ID to (name, position, NFL team) from the projections or ESPN API). This deliverable ensures that the monitor’s output is easily understandable to the user, not just raw IDs. We will also include logging of key state info when appropriate, for example:

  3. Indicate when our team is on the clock: e.g., *“\>\>\> You are now on the clock\! \<\<\<”* (if our user’s team comes up).

  4. Optionally, a countdown or warning if time\_remaining is low (not critical for Sprint 1, but we could print something like “(10s left)” if we have that info).

* The primary deliverable is the log of picks; additional context like our team’s upcoming pick can be included to enhance usefulness.

* **Integrated State Updates:** As part of the console output, we might also display parts of the `DraftState` to verify it’s tracking correctly. For example, after each pick, we could log the total players drafted so far or the next pick number. Another possibility is logging `picks_until_next` for our team: e.g., after another team’s pick, print *“(Your pick in X picks)”* for situational awareness. These details, while not strictly required, will demonstrate that our state management is working and is being used in output. The deliverable is that the monitor uses the `DraftState` live – meaning if any bug in state occurred, it would likely show up in these outputs, so by having them, we also validate the state tracking indirectly.

* **Testing & Validation Reports:** We will document the results of running the end-to-end monitor in at least two scenarios:

  1. **Standard 10-team mock draft, 15 rounds** (or as many rounds as are typically in a mock). We expect \~150 picks. The deliverable is the console log (or an excerpt of it) demonstrating picks from 1.01 through the final pick, with no errors or crashes. We will note the performance (e.g., each pick logged within e.g. 50ms of it occurring). This scenario proves the monitor can handle a full-length draft.

  2. **Different league size (e.g., 12-team)** to ensure our calculation of rounds and picks still holds and that `picks_until_next` logic adapts (in a 12-team league, snake draft means picks\_until\_next will vary round to round if we are on the wheel, etc.). We’ll run a shorter test if needed just to confirm no assumptions break with different team counts.

* If possible, we’ll also test a scenario with an intentional disconnect to ensure the recovery (from the previous spec) works in the integrated system – e.g., in the middle of the full draft test, incorporate a drop and reconnect, and show that logging continued after a brief pause. The outcome of these tests will be summarized (e.g., “All 150 picks were logged correctly, with player names resolved; state remained accurate throughout. One reconnection occurred at pick 50 and system recovered within 3 seconds with no missed picks.”).

  ## **Assumptions & Constraints**

* **User Login and Access:** We assume the user of the tool will have the necessary credentials and access to the ESPN draft. For development and testing, we’ll often use ESPN’s mock drafts which are publicly joinable (no special credentials needed beyond an ESPN account login). The Playwright automation will either use an existing logged-in session (if the user has logged in via the launched browser) or we might prompt for credentials (not ideal for now; likely we rely on manual login in the opened browser). We assume this process is acceptable: i.e., the user may need to do a one-time login in the Playwright-controlled browser window for the monitor to access the draft room. This constraint means our tool isn’t fully headless unattended – a user action might be required to authenticate (at least in Sprint 1).

* **Console Environment:** We assume the monitor will be run in a console/terminal where real-time text output is acceptable. The performance of writing to console is generally fine for our needs (a few lines per second at most). We won’t implement any special optimization for logging (like buffering), as the volume is low (even 200 picks in a draft is manageable). We also assume the console encoding/font can handle any characters (should just be text, no unusual chars).

* **Player Data Availability:** The PlayerResolver will be used to get player names. It likely calls ESPN’s API or uses a cached mapping of IDs to names. We assume by the time of running the draft monitor, we have either loaded a roster of players (maybe from a projections file or an API call at start) so that most player IDs we encounter can be resolved quickly. If a new player ID appears that we haven’t seen, the resolver will fetch it via API on the fly (which could take some milliseconds). We assume this occasional API call will not significantly slow down our pick logging (the 95%+ name resolution success criterion[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L127-L131) suggests most names are resolved, and perhaps \<5% might need a quick fetch). This is acceptable, but we’ll keep an eye on it; name resolution might slightly delay printing a pick by, say, 100ms if it hits the API, which is still within our real-time bounds.

* **Draft Completion:** We assume the draft will run to completion once started, and our tool will simply end when the draft is over. ESPN likely closes the WebSocket or stops sending messages when the draft is done. Our monitor should detect “draft complete” either via a specific message or by the absence of further picks once the expected number of picks is reached. We won’t implement a complex end-of-draft detection in Sprint 1; a simple approach is to monitor pick count and if it equals total picks (teams \* rounds) based on league settings, we know it’s done and can exit gracefully. We might also just allow the user to Ctrl+C quit after they see it’s done. This is a minor detail; the main constraint is that the tool doesn’t erroneously quit early or hang indefinitely after the draft. We’ll likely rely on manual stop for now if needed.

* **Time Constraints:** We are aware that the entire sequence from receiving a WebSocket frame to logging the info should be well under the pick clock (usually 60-90s). Our target is to log within \<\<1s. Given our design (text parsing, dictionary lookups, maybe one API call rarely), this is easily achievable. We assume network latency for those rare API calls is the only unpredictable factor, but even then it should be quick if using ESPN’s endpoints. So we proceed under the assumption that performance is sufficient and will verify it in tests.

  ## **Milestones**

1. **Integration Setup:** Create the main script that ties everything together. Milestone steps:

   * Instantiate the Playwright browser and navigate to the draft lobby or a specific draft URL. (For a mock draft, we might navigate to the lobby and have the user select a mock room manually, or automate joining the first available mock draft via script if feasible).

   * Once in a draft, ensure the `ESPNDraftMonitor` is listening to the WebSocket. Confirm that our event handler (`process_websocket_frame`) is being called for incoming messages.

   * Initialize the `DraftState` at the start of the draft. This might involve pre-populating `available_players` with all draftable players. We can call ESPN’s API for all players in the league or use a static list if available. This ensures that when picks happen, we know how to remove players and we have baseline data.

   * Integrate the `PlayerResolver`: e.g., load a cache of player names (perhaps from the 39 IDs we already gathered[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L79-L87) plus an additional dataset). Possibly, call an API endpoint to get all players in the league once and store in a map for quick lookup. The milestone is reached when the monitor can start up and be “ready” in a draft, with state initialized and waiting for events.

2. **Logging Message Formatting:** Design and implement the output format for console logs. For each pick event processed:

   * Determine the pick number (and round if desired). Round can be computed as `(pick_number - 1) // teams + 1` and pick within round as `(pick_number - 1) % teams + 1`. We can choose to display “Pick X” or “Round Y, Pick Z”.

   * Get the drafting team’s identifier. If we can extract a team name or owner name via ESPN API, that’d be ideal, but that may be complex for a mock draft. Instead, we might label teams by their draft position (Team 1, Team 2, etc., corresponding to draft slots). For now, use a simple “Team \#” or “Team \<slot\>” in the log.

   * Resolve the player’s name, position, team. Use `PlayerResolver.resolve_espn_id(id)` which should return a Player object or name. Format the string with the player’s name (and perhaps position/team for clarity).

   * Print to console. Ensure no undue delay; if the resolver needs to call API and that is slow, consider printing a placeholder “(resolving name...)” and update later, but likely not needed as the API is fast. We can also mitigate by pre-fetching as many players as possible.

   * Also decide if any additional info should be logged alongside the pick. E.g., after each pick, we could log something like “Your next pick in X picks” if the user’s team hasn’t picked yet in that round.  
      Milestone outcome: when a test pick event occurs, the console shows a nicely formatted line with correct information.

3. **Full Draft Dry-Run (Short Simulation):** Before doing a real full draft, simulate or conduct a partial run:

   * Possibly join a mock draft and only go through the first round or two as a test. Or use a saved message log from Sprint 0 and feed it through the system to see how the console output looks for the first 10-15 picks.

   * This will help tweak formatting or catch any issues (for example, if two messages come in very close together, ensure our logging doesn’t jumble them — using async should inherently serialize handling, but just to confirm).

   * Ensure the state updates reflect in logs if we choose to log extra state info (like upcoming pick count).

   * Check that names are resolving for all those picks (if any fail, see why – e.g., maybe a new rookie ID not in cache, and fix by allowing the resolver to fetch).  
      Milestone outcome: a short log sample of several picks that we verify for correctness (right names, no duplicates, proper sequence).

4. **End-to-End Test – Complete Mock Draft:** Execute the monitor through an entire mock draft session:

   * Join a mock draft (say 10-team, 15 rounds, fast pick if possible to expedite testing).

   * Let the monitor run from Pick 1 to final pick. Observe the console output. We should see every pick in order. The internal state should be updating – though we mostly observe that indirectly (we can optionally dump final state at the end to verify totals).

   * Verify that the monitor handled the “snake” aspect correctly (if implemented any logic for alternating pick order, etc.). Likely, the ESPN messages naturally handle the turn changes, so our state’s `on_the_clock` will just follow along.

   * Confirm performance: The printing should occur almost immediately after the pick happens on ESPN. Because we are intercepting WebSocket, we might even see it before the UI updates visually. A success criterion is that latency from ESPN event to our log is \<1 second, which our design should meet easily (likely \~100ms as per Sprint 0 observations[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L28-L31)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L50-L54)).

   * If a reconnect test is included, do it here (e.g., drop at round 5 for a short time, then ensure it resumes).

   * By draft end, check that no errors occurred, and all picks were logged. Also ensure the program can terminate gracefully (the draft end might be detected by no more messages; we can then print “Draft complete” and close).  
      Milestone outcome: a confirmed run where the tool captured an entire draft. This essentially validates that Sprint 1’s core goal – “track a complete mock draft end-to-end”[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L67-L71) – is achieved.

5. **Multi-Scenario Testing:** If time permits, repeat the test with variations:

   * Different team count (e.g., a 8-team or 12-team mock) to ensure no assumptions break (like indexing, or picks\_until\_next calculation).

   * Perhaps test with being a different draft slot (join as Team 5 vs Team 1\) to see that `picks_until_next` and on-the-clock detection for our team still works (if we implemented those features).

   * These tests ensure the monitor isn’t hard-coded to a specific configuration.  
      Milestone outcome: confidence that the monitor works generally for any standard league draft.

6. **User Documentation:** As a final step, prepare a brief usage guide (could be a README update) explaining how to run the monitor in Sprint 1\. For example: prerequisites (Playwright installed, etc.), how to log in to ESPN via the tool, and what output to expect. This isn’t a formal deliverable to the user story perhaps, but it’s a necessary aspect if others are to test or use the tool. It will include any known issues (e.g., “If the browser doesn’t open or you don’t see messages, ensure you joined a mock draft room” or “The tool does not pick for you, it only observes and logs.”).

By completing these milestones, we will have a clear demonstration of a functional draft monitoring system that lays the groundwork for the recommendation engine in the next sprint. The system will have proven its ability to reliably capture data, maintain state, recover from disconnects, and present information in a useful way to the user, fulfilling all the Sprint 1 requirements and incorporating the insights gained from Sprint 0\.
