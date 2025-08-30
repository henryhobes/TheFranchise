# **ESPN Draft WebSocket Protocol Mapping**

## **Objectives**

* Intercept and understand ESPN fantasy football draft WebSocket communications in order to document the protocol. Specifically, identify the WebSocket connection endpoints and any handshake requirements, enumerate all relevant message types (e.g. `PICK_MADE`, `ON_THE_CLOCK`, `ROSTER_UPDATE`), and determine the structure/fields of each message type[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L16-L20). The goal is to validate that we can reliably read the draft stream and comprehend its format.

  ## **Scope**

* **In Scope:** Observational analysis of the ESPN draft WebSocket data. This includes joining a fantasy draft (likely a mock draft) and using tools (e.g., Chrome DevTools or an automated headless browser) to capture WebSocket traffic in real time. We will focus on documenting messages related to draft events (picks, clock updates, roster changes, etc.) and how the client connects and stays subscribed to the feed.

* **Out of Scope:** Any automation of draft actions (e.g. auto-picking players) or integration with the UI is not part of this task. Also, implementing alternative data-capture methods (REST polling or HTML scraping) is excluded at this stage[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L53-L57); those are only contingency plans if the WebSocket approach fails. This spec does not cover player ID decoding or connection recovery logic, which are addressed in separate specifications.

  ## **Deliverables**

* **WebSocket Protocol Document:** A detailed document describing each message type observed on ESPN’s draft WebSocket, including field-by-field breakdown and example message payloads[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L16-L20)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L41-L42). This document should clearly define events like pick announcements, on-the-clock notifications, roster updates, etc., and explain how to interpret them.

* **Proof-of-Concept Log Script:** A simple script or tool (e.g. a Python script using Playwright) that connects to an ESPN mock draft and logs incoming draft event messages in real time[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L40-L42). This validates that our understanding is correct by demonstrating we can capture every pick event as it happens.

  ## **Assumptions & Constraints**

* We have access to an ESPN fantasy draft (mock draft environment) for testing, and the WebSocket feed is accessible with standard tools.

* All interactions will be **read-only** to comply with ESPN’s Terms of Service (no automated actions taken)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L60-L63). We will run a single-session listener that does not disrupt the draft or send any data.

* The ESPN WebSocket protocol is undocumented and may change without notice, but we assume it remains stable during our analysis. We plan to version-control our protocol findings so they can be updated if ESPN alters the format[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L156-L160).

* We assume WebSocket interception is the fastest and most reliable method for real-time data (avoiding the latency of REST polling)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L15-L19). Therefore, the team will use browser automation or devtools to capture messages directly off the wire for near-instant updates.

* Time is limited (Sprint 0 is only 2 days), so this task will focus on capturing essential message types and patterns quickly, rather than an exhaustive analysis of every possible message.

  ## **Milestones**

1. **Setup Test Draft:** Join an ESPN mock draft lobby with network monitoring enabled (e.g. open Chrome DevTools or run a Playwright script to listen for WebSocket frames)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L16-L19).

2. **Identify Connection Details:** Capture the WebSocket endpoint URL and any connection handshake or authentication steps required to subscribe to the draft stream[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L16-L18).

3. **Capture Sample Messages:** During the draft, record examples of each type of message observed – including pick events, turn change notifications (teams going "on the clock"), roster updates after picks, and any timer or heartbeat messages[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L17-L20).

4. **Analyze Message Structure:** For each message type, parse the JSON (or relevant format) to understand the fields (e.g. player ID, team info, timestamp, pick number, etc.). Determine how player information is represented in the data (to be correlated with the player ID mapping effort) and document the meaning of each field.

5. **Document the Protocol:** Compile a clear specification listing all identified message types with their purposes and key fields. Include at least one example payload for each type to illustrate the format[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L19-L20)[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L41-L42).

6. **Validate via POC Script:** Implement a lightweight script that connects to the draft WebSocket and continuously logs incoming messages (especially pick announcements) to the console[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L40-L43). Run this against a mock draft to ensure that:

   * The connection can be established and maintained through the draft.

   * Every pick event is received in real time (no messages are missed).

   * The logged data matches the expected structure from our protocol documentation.
