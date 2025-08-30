# **ESPN Draft WebSocket Connection Stability Testing**

## **Objectives**

* Assess the reliability of the ESPN fantasy draft WebSocket connection over the course of a full draft and identify how it behaves under network stress. The aim is to document any disconnections, reconnection behavior, and potential session timeouts[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L28-L32). By understanding these factors, we can ensure that the DraftOps system remains robust (i.e. no draft picks are missed due to connection drops).

  ## **Scope**

* **In Scope:** Full-session monitoring of the WebSocket connection during a mock draft, including intentional network interruption tests. We will observe normal operation (from pick 1 to final pick) to see if the connection stays live throughout, and deliberately introduce network disruptions (e.g. turning off internet or dropping the WebSocket) to see how the system reacts[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L28-L32). This includes noting any reconnection messages from ESPN, how the draft client recovers once connectivity is restored, and what must be done to resubscribe to the stream if needed.

* **Out of Scope:** Implementing automatic reconnection logic or failover mechanisms is not part of this sprint (those will be developed in the next phase using the insights gathered). Also, testing extreme scenarios (like server outages on ESPN’s side or multiple simultaneous draft connections) is beyond the scope; we focus on a single draft instance and typical home network conditions. Analysis of the content of messages is covered in other specs – here we concentrate on connection status events.

  ## **Deliverables**

* **Stability Test Report:** A concise report detailing the findings on connection stability. This should cover:

  * Whether a standard mock draft can run from start to finish without any unsolicited disconnects.

  * What happens during a forced network break (e.g. does the WebSocket automatically reconnect, or is manual intervention needed).

  * How the system should detect a dropped connection (e.g. via error events or absence of expected messages).

  * The observed behavior on rejoining a draft after a disconnect (for instance, do we receive missed picks in a backlog or only new events).

* **Recommendations for Reconnection Strategy:** Based on the above results, outline any requirements for the DraftOps system’s reconnection logic. For example, if the connection does not auto-recover, we will suggest implementing an exponential backoff reconnection mechanism[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L156-L160) and resynchronization of draft state upon rejoin.

  ## **Assumptions & Constraints**

* The testing assumes that we can simulate network issues in a controlled manner (e.g. disabling the network adapter or using tooling to cut the WebSocket) without causing the draft room to entirely reset. We assume ESPN’s draft room allows re-entry after a temporary loss of connection (similar to how a user can refresh their browser during a draft).

* ESPN likely uses heartbeats or pings to keep the WebSocket alive. If such keep-alive messages exist, we assume we’ll observe them; if none are observed, we’ll assume the connection relies on active traffic to stay open.

* We expect that short network interruptions (a few seconds) can be tolerated, but longer interruptions might cause a session timeout. A constraint is that we might not know the exact timeout threshold in this limited test, but we will try to estimate it (e.g. if a 30-second drop causes a disconnect).

* No actual draft picks should be impacted by our testing – this will be done in mock drafts where our connectivity changes do not affect real leagues. We will ensure the testing is done in a safe environment and complies with read-only monitoring (not attempting to send any data that could violate ToS).

  ## **Milestones**

1. **Baseline Run:** Connect to an ESPN mock draft and let it run to completion under normal conditions. Observe if the WebSocket connection remains stable for the entire draft duration (e.g. 15 rounds) without manual interference. Log any instances of disconnect or errors (if none, note that baseline stability is good).

2. **Interrupt Test (Short):** During an active draft, briefly disconnect the network (for example, disable Wi-Fi or block the connection for \~5–10 seconds)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L30-L32). Then restore connectivity and check:

   * Did the WebSocket automatically reconnect on its own, or did it close?

   * If closed, establish a reconnection (refresh or restart the listener) as quickly as possible. Confirm that once reconnected, new pick messages are received. Document whether any picks that occurred during the downtime were missed or if the server sent them upon reconnection.

3. **Interrupt Test (Extended):** If feasible, attempt a longer network interruption (e.g. \~30 seconds) to see if there’s a point at which the ESPN server or client gives up (session timeout)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L31-L32). Note if a manual reconnection still works after this longer gap or if additional steps (like re-authentication) are required to rejoin the draft stream.

4. **Observe Reconnection Patterns:** For any of the above drops, record any reconnection messages or behaviors. For instance, there might be a specific WebSocket event or error code when the connection is lost. Also, check if ESPN’s system sends a full state update upon reconnection (to catch up on missed events) or if it only continues with new events.

5. **Document Findings and Guidance:** Consolidate the results into the stability test report. Highlight key observations such as “connection remained stable for X minutes with no issues,” or “after a disconnect, manual reconnection was necessary and took Y seconds.” Provide guidance for the engineering team on what kind of reconnection logic to implement (e.g. automatic retry with exponential backoff if no messages are received for Z seconds[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L156-L160), and logic to refresh or synchronize state if we’ve missed picks during a drop). Ensure these recommendations align with the success criteria of zero missed picks and quick recovery.
