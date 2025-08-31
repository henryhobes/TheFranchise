# **ESPN Draft WebSocket Connection Recovery & Continuity**

## **Objectives**

* Ensure **continuous monitoring of the draft** by implementing robust WebSocket connection recovery and maintenance strategies. In Sprint 0 we confirmed the connection is stable over short periods and identified heartbeat messages (PING/PONG)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L26-L34)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L182-L188); now we need to build on that to handle real-world network issues. The objective is to have the system automatically detect any disconnection or interruption in the WebSocket stream and **reconnect swiftly** without losing critical draft data[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L2-L5). We will implement the reconnection logic (exponential backoff retries, session restoration) outlined in the Sprint 1 plan[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L75-L83), ensuring that even if the network hiccups, DraftOps can resume monitoring the draft with minimal disruption. Ultimately, by end of Sprint 1, the monitor should recover from at least 1-2 connection drops during a draft with no missed picks[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L126-L130).

  ## **Scope**

* **In Scope:** Enhancing the `ESPNDraftMonitor` (connection manager) to handle connection lifecycle events. This includes detecting a dropped WebSocket (e.g. via error events, closure codes, or heartbeat timeouts) and performing reconnection attempts. The scope covers implementing methods such as `handle_disconnection()` and `reconnect_with_backoff()` as sketched in the plan[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L75-L83). Also in scope is re-initializing any necessary state after reconnect: re-subscribing to the draft WebSocket endpoint, and resuming state updates. We will also incorporate **heartbeat monitoring** – using ESPN’s PING/PONG or our own timer – to proactively catch a stalled connection. If a disconnect happens, the system should attempt to rejoin the same draft session (using stored league/session identifiers and authentication context) and synchronize the state (catch up on any picks that occurred while offline, if any).

* **Out of Scope:** Implementing a full fallback to the REST API or other data sources for pick data (we note this as a contingency if WebSocket fails entirely[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L52-L58), but it’s not planned for Sprint 1). Also, handling long downtime or complex re-sync (e.g., if the connection is lost for many minutes such that multiple picks pass) is limited – our focus is on short interruptions. Multi-session recovery (like pausing and resuming monitoring after a long break) is not covered; we assume the tool runs continuously during the draft. Additionally, dealing with ESPN’s OAuth reauthentication (if the session cookie expires mid-draft) is not in this sprint – we assume the login session remains valid through the draft. If a user manually closes the browser or ends the draft early, that is outside the control of our recovery logic.

  ## **Deliverables**

* **Connection Manager Enhancements:** Updated `ESPNDraftMonitor` class with implemented methods for robust connection handling:

  * `handle_disconnection(reason)` – a coroutine or callback that triggers when the WebSocket closes unexpectedly. This will log the event (with a reason code if available) and initiate the reconnection sequence.

  * `reconnect_with_backoff()` – logic to attempt reconnection to the draft WebSocket. This will try to reconnect immediately on first failure, and if it fails, retry with exponential backoff delays (e.g. 1s, 2s, 5s, up to a reasonable limit like 5 attempts). We will use non-blocking async waits for the backoff so as not to freeze the whole application.

  * `validate_connection_health()` – possibly a routine that checks if heartbeats (PONGs) are being received and triggers a reconnection if the connection is unresponsive even without a formal close event (this guards against silent drops).  
     These methods collectively ensure the monitor does not silently die on connection issues.

* **Seamless State Continuation:** The system will preserve and restore the draft state across a reconnection. The current `DraftState` in memory will be used to determine what has happened so far. After reconnecting, the monitor should quickly resync any missed information. For example, if one pick happened while we were disconnected, we have two strategies:

  * Use the `DraftState.current_pick` (or a pick counter) to know what pick number we were on, and when reconnected, cross-check with the first message or an API call to see if a new pick was made in the interim.

  * Optionally, immediately call the ESPN Fantasy API on reconnect to fetch the latest draft results as a sanity check (this API call can be done once on reconnect to fill any gaps, since a short disconnect might miss a pick).

* We will implement a lightweight mechanism (perhaps in `handle_disconnection` or `reconnect_with_backoff`) to ensure no picks are missed: e.g. after a successful reconnect, compare the number of picks we have in state vs. what pick number the draft is currently on (the protocol’s messages like `SELECTING X` might carry the pick index). If there’s a discrepancy, fetch the missing pick(s) via the API or via any backlog message ESPN might send on reconnect. Ensuring state continuity in this way is critical to meet the requirement of zero missed picks[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L184-L188)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L194-L198).

* **Logging & Alerts:** The monitor will include logging for connection events. For deliverables, we will produce log output examples that show:

  * Detection of a disconnect (e.g., “**Warning: WebSocket disconnected, attempting to reconnect...**” with timestamps).

  * Attempts to reconnect (e.g., “**Reconnecting... attempt 1/5**”).

  * Successful reconnection (e.g., “**Reconnected after 3 seconds, resubscribed to draft feed**”).

  * If applicable, a log of any state correction (e.g., “**Caught up 1 missed pick during reconnection**”).

* These logs will help in debugging and will serve as evidence that our recovery mechanism works as intended. They can be reviewed during testing to confirm the timing (we expect to reconnect within a few seconds) and correctness of the process.

* **Test Results for Recovery:** As part of the Sprint 1 completion, we will have a documented test (in notes or a brief report) of a simulated drop scenario. For example, we might intentionally cut off the internet or close the WebSocket (via code) during a mock draft for a short time and then observe the system’s recovery. The deliverable includes confirming the system met the success criteria: e.g., it recovered from at least one disconnect and no pick events were ultimately missed by the end of the draft[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L126-L130). This could be demonstrated by comparing the draft log before and after the drop (no gap in picks), and ensuring our final list of drafted players matches the ESPN draft results.

  ## **Assumptions & Constraints**

* **Stable Reconnect Endpoint:** We assume that rejoining the WebSocket can be done by reusing the same draft URL and session parameters. The connection URL for the draft includes a session token and league/team IDs[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L28-L36)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L91-L99). We anticipate that if the connection drops but the browser context (and thus cookies/session) is still valid, we can simply call `connect_to_draft()` again (possibly needing to refresh the page or re-trigger the WebSocket connection via Playwright). We assume ESPN’s backend will allow reattachment to an ongoing draft without issue (this is typically true as long as the user is still logged in and the draft is active).

* **Short Interruptions:** The reconnection strategy is designed for short-term network blips (a few seconds to a minute). We constrain our solution to these scenarios. If the outage is very long (several minutes), the draft might progress significantly without us; our simple catch-up (fetching a pick or two) might not suffice. In such cases, manual intervention or a more complex state rebuild might be needed (not handled in Sprint 1). We assume for testing that any induced disconnect will be brief enough that at most a couple of picks could be missed.

* **Heartbeats as Health Indicator:** ESPN’s protocol sends PING/PONG messages roughly every 15 seconds[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L26-L34)[GitHub](https://github.com/henryhobes/TheFranchise/blob/04eca3f828c65c10c55e0c5ed99f03bf7d47ca10/draftOps/docs/sprint-results/sprint-0-completion-summary.md#L300-L304). We assume these heartbeats continue reliably. Our plan is to use them: if we do not receive either a PING or PONG in a certain interval (say 20-30 seconds), we infer the connection is dead even if not formally closed, and trigger a reconnect. This implies the environment running DraftOps can miss heartbeats if the network is down or the socket is stuck. We will implement this check with care to avoid false positives (e.g., don’t prematurely reconnect if the heartbeat is slightly delayed).

* **No Concurrent Reconnect Attempts:** We constrain the design such that if one reconnect attempt is ongoing, we won’t start another in parallel. The system will either succeed or exhaust retries before a new cycle. This avoids thrashing or spamming ESPN’s servers with reconnects. We also assume ESPN won’t blacklist or throttle us for reconnect attempts in these low numbers (the attempts are few and only triggered on genuine disconnect).

* **Testing Environment:** For safe testing, we assume we can simulate disconnects without harming the draft. In a mock draft, dropping the connection only affects our monitoring (the draft itself continues). We will likely run tests in mock drafts to avoid any risk in real leagues. This should be acceptable within ESPN’s policies as we are not automating actions, just reading data.

  ## **Milestones**

1. **Implement Disconnection Detection:** Augment the `ESPNDraftMonitor` to listen for WebSocket close events or errors. Using Playwright’s API, we can subscribe to the WebSocket `close` event. Also implement a watchdog for heartbeats: start a timer on the last received message or PONG, and if it exceeds a threshold with no traffic, treat it as a lost connection. Milestone outcome: the monitor can reliably detect when the connection is no longer alive, whether via an explicit event or inferred by timeout.

2. **Develop Reconnect Logic:** Write the `reconnect_with_backoff()` method. Milestone steps:

   * Attempt an immediate reconnect by re-running the connection sequence (likely re-opening the draft page or reinitializing the WebSocket listener). Since the Playwright browser may still be open, this could mean navigating to the draft page again or refreshing it. Ensure the `ESPNDraftMonitor.connect_to_draft()` method can be called again safely.

   * If the first attempt fails (no messages or an error), wait a short delay then try again. Implement exponential backoff delays (e.g., 1s, 2s, 4s, etc.) up to a maximum (say 5 attempts or \~15-30 seconds total).

   * After each attempt, check if the WebSocket successfully reconnected (e.g., we start receiving messages or a successful subscription message).

   * If reconnect succeeds, break out and resume normal operation. If all retries fail, for now, log an error and give up (for Sprint 1, we won’t implement infinite retries to avoid endless loops; failing after several attempts will be an edge-case we note).  
      Milestone outcome: tested reconnect method in isolation (e.g., call it while not in a draft to see it tries, or simulate a disconnect event to trigger it and watch the attempts via logs).

3. **State Re-synchronization on Reconnect:** On a successful reconnect, ensure the system handles any missed data:

   * Approach: The first meaningful message after reconnect might be an `ON_THE_CLOCK/SELECTING` event for the current pick. Compare that pick number to our last known `current_pick`. If the new pick number is greater, it means we missed some picks. Implement a small routine to fetch those missing picks via ESPN’s API (if available) or handle them if ESPN re-sends them. (Sometimes, upon connecting, systems send a summary of current state. We will check if ESPN sends any recap. If not, we use the API.)

   * Update the DraftState for any missed picks (as if they were just received normally) before proceeding. This ensures continuity.

   * Also handle edge case: if the disconnect was so short that we reconnected before the next pick happened, then `current_pick` will match and no action is needed beyond resuming listening.  
      Milestone outcome: tested by simulating a scenario where one pick occurs during disconnect. This can be done by pausing our script’s processing right after a pick and resuming after another pick (or manually causing a drop between two picks in a fast mock draft). After reconnection, verify our state now includes the missed pick. If using the API, verify we fetched and logged that pick.

4. **Testing in Mock Draft (Induced Drop):** Perform an end-to-end test in a controlled environment:

   * Start monitoring a mock draft normally. Partway through, intentionally disconnect the network or kill the WebSocket (perhaps by closing the page via script, or using Playwright to simulate network offline mode briefly).

   * Observe that our monitor logs the disconnect detection and triggers reconnection.

   * Restore the connection (if we disabled network, re-enable it). Check that the monitor successfully reconnects and continues logging subsequent picks.

   * Compare the draft log: all picks from the beginning to end should be present. Particularly, focus on the period of the drop: ensure that either the monitor caught up the missed pick(s) or the draft didn’t have any in that interval. We expect, after testing, to see that no pick was permanently missing from our logs and `drafted_players` set matches the number of picks made.

   * Also measure the downtime: ideally reconnection happens within a few seconds. This test confirms we meet the continuity requirement.  
      Milestone outcome: a verified scenario in which the system endured a connection loss and recovered without losing data, demonstrating we hit the success criteria (“Recovers from 1-2 drops per draft”)[GitHub](https://github.com/henryhobes/TheFranchise/blob/61826e965192e96acf8b293554a7d5d5a31ddeb4/draftOps/docs/draftops-implementation-plan.md#L126-L130).

5. **Review and Refinement:** Analyze if any edge cases remain unhandled (e.g., multiple quick disconnects in succession, or a scenario where the WebSocket reconnects but doesn’t properly receive new messages). Add safeguards as needed (for example, if reconnect succeeds but no draft messages come through in, say, 5 seconds, maybe attempt one more reconnect or abort with an error). Document the reconnect behavior and any known limitations for future reference. At this point, the connection manager should be production-quality for typical use, and we can proceed to integrate it fully with the draft monitor for Sprint 1’s final deliverable.
