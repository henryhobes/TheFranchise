# **ESPN Draft Event Message Flow Analysis**

## **Objectives**

* Document the chronological flow of events on the ESPN draft WebSocket during each pick, and measure the timing between these events[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L34-L38). This analysis will clarify what happens from the moment a team is put “on the clock” through to when a pick is made and the next team’s turn begins. Understanding this sequence (and any built-in delays) ensures that DraftOps can align its recommendation timing with ESPN’s update cadence.

## **Scope**

* **In Scope:** Observing and logging the sequence of WebSocket messages for each draft pick. We will focus on a representative portion of a mock draft to capture events such as:

  * The "on the clock" notification when a new team is up (ON\_THE\_CLOCK event).

  * Any intermediate tick or countdown messages (if ESPN sends periodic clock updates).

  * The pick event when a selection is made (PICK\_MADE message) and any immediate follow-up (for example, a roster update for the team that picked).

  * The transition to the next pick (the next ON\_THE\_CLOCK for the following team).

* We will also note how the draft state is synchronized – for instance, whether each pick event includes all info needed or if separate messages (like a roster update or a summary state message) accompany the pick.

* **Out of Scope:** Deep analysis of the content of each message (that's covered in Protocol Mapping) except as needed to describe flow. We are not measuring network latency beyond what is observable in timestamps. Additionally, we will not consider multi-draft interactions or any non-standard draft formats here; the focus is a normal snake draft flow.

## **Deliverables**

* **Event Sequence Documentation:** A clear narrative or diagram of the message sequence for a typical pick. For example, for one pick we might document:

  1. *Team A On The Clock* (timestamp T0) – ESPN sends an ON\_THE\_CLOCK message indicating Team A’s turn has started.

  2. *(Optional) Clock Tick Updates* – If applicable, messages updating remaining time (e.g. at 30 seconds, 10 seconds, etc.).

  3. *Pick Made by Team A* (timestamp T1) – A PICK\_MADE message when Team A selects a player, containing the player’s ID and relevant details.

  4. *Team A Roster Update* (timestamp T1 \+ δ) – A message confirming Team A’s roster now includes the drafted player (this could be part of the PICK\_MADE payload or a separate ROSTER\_UPDATE event).

  5. *Team B On The Clock* (timestamp T1 \+ δ') – ON\_THE\_CLOCK message for the next team (Team B) starting their turn, essentially beginning the next cycle.

* The documentation will include approximate time intervals (δ, δ') observed between these events. For instance, we expect the gap between a pick being made and the next on-clock event to be very short (on the order of tens of milliseconds in our test environment[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L15-L19)). Any notable delay or irregularity in this flow will be highlighted.

* **Flow Analysis Report:** A brief report interpreting the above sequence. This will cover whether the events always occur in the same order, if any messages are sometimes combined, and how the system ensures draft state consistency. For example, we will describe how the system knows a pick is finalized (via the PICK\_MADE event) and how it knows who is up next (via the subsequent ON\_THE\_CLOCK event). If the WebSocket provides a full state sync at certain points (such as upon reconnect or at the start of the draft), that will be mentioned as part of the state synchronization notes.

## **Assumptions & Constraints**

* We assume the order of events is consistent for every pick (ESPN’s system will always send an ON\_THE\_CLOCK, then a PICK\_MADE, etc., in that strict sequence for each turn). The analysis will verify this, but we proceed under the expectation of no out-of-order messages.

* Network latency during our test is minimal, so the timestamps we record closely reflect ESPN’s server timing. (Prior analysis indicates roughly 50–100ms latency for WebSocket updates[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-overview.md#L15-L19), which is negligible for sequence ordering.) We therefore treat events as effectively instantaneous for ordering purposes.

* The presence of countdown tick messages (if any) may depend on ESPN’s implementation. We suspect the client might handle the countdown locally and the server might not send frequent timer updates. If our test does not show distinct timer messages, we assume the client UI counts down based on an initial timer value and only critical events (like the pick being made or a final expiration notice) are sent. We will document whatever the case may be.

* We are focusing on the steady-state operation of the draft. Unusual situations (like a draft pause or an undo of a pick) are not covered. We assume a straightforward draft with each pick flowing to the next without manual delays.

* Our observations will likely come from a single mock draft session; we assume this is representative of general behavior for all standard ESPN drafts.

## **Milestones**

1. **Data Collection:** Instrument a mock draft to log all WebSocket messages with timestamps. Start from the beginning of the draft and ensure we capture at least a few rounds worth of data for pattern confirmation[GitHub](https://github.com/henryhobes/TheFranchise/blob/12686c72a8a4fc43b16321ca694c15dfa8b39b9f/draftOps/docs/draftops-implementation-plan.md#L34-L38).

2. **Single Pick Analysis:** Choose a specific pick (e.g. the transition from one team to the next in Round 1\) and analyze the messages around that pick in detail. Mark the times each relevant event arrived and classify them (ON\_THE\_CLOCK, PICK\_MADE, etc.). This will form the template for understanding the flow.

3. **Repeat & Confirm:** Examine several other picks (including one where the selection happens quickly and one where the clock runs down longer) to see if the sequence or timing of messages differs in any way. Confirm that each pick consistently triggers the same series of events in order.

4. **Identify State Sync Points:** If applicable, note any messages that provide a broader state update. For instance, on the very first pick of the draft, there might be an initial message establishing the draft state/order, or on a reconnection a bulk state summary might be sent. Determine when such synchronization messages occur (this may tie in with the Connection Stability tests if we simulate a reconnect during the draft).

5. **Document the Flow:** Create the event sequence documentation outlining the typical pick lifecycle on the WebSocket. Include the timeline and descriptions as described in the deliverables. Review this with the engineering/PM team to ensure it’s clear how the system transitions from one pick to the next. This documentation will guide the implementation of event handling in subsequent sprints by clarifying what triggers to listen for (e.g. using ON\_THE\_CLOCK as a signal to start recommendation logic when a team is up, and recognizing a PICK\_MADE to finalize that pick’s decision process).
