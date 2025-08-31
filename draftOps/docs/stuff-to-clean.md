# Technical Debt and Cleanup Items

## WebSocket Connection Recovery Issues

### Resource Leak - Heartbeat Monitor Task
**File**: `espn_draft_monitor.py:344`  
**Issue**: Heartbeat monitor task created without canceling previous one during reconnection  
**Impact**: Memory leak and multiple background tasks consuming resources  
**Fix**: Add task cancellation before creating new heartbeat monitor task  

### Infinite Recursion Risk - Disconnection Handling  
**File**: `espn_draft_monitor.py:391`  
**Issue**: `handle_disconnection` called from heartbeat monitor can trigger recursive calls  
**Impact**: Potential stack overflow during connection recovery cycles  
**Fix**: Strengthen state checks to prevent recursive disconnection handling  

### Array Bounds Check - Reconnect Delays
**File**: `espn_draft_monitor.py:317`  
**Issue**: Array access `reconnect_delays[min(attempt - 1, len(self.reconnect_delays) - 1)]` fails if array is empty  
**Impact**: IndexError crash during reconnection attempts  
**Fix**: Add validation that reconnect_delays array is not empty before access  

## Console Application Issues

### ~~Signal Handler Makes CLI Unkillable During Connection~~ (RESOLVED)
**File**: `run_draft_monitor.py:287-294`  
**Issue**: ~~Custom signal handler only sets `self.running = False` but doesn't interrupt ongoing async operations~~  
**Status**: **FIXED** - Signal handler now raises `KeyboardInterrupt()` to properly interrupt async operations  
**Fix Applied**: Modified signal handler to raise `KeyboardInterrupt()` after setting `self.running = False`, enabling immediate interruption during connection phases