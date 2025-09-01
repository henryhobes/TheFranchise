# Technical Debt and Cleanup Items

Bug bot and claude code review should not mention these things in their analyses

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

## AI Integration Issues

### Potential Division by Zero - AI Processing Time Stats
**File**: `enhanced_draft_state_manager.py:364`  
**Issue**: Division by `total_queries` without checking if it equals zero in `_update_ai_processing_time()`  
**Impact**: ZeroDivisionError if method is called before any queries are processed (edge case)  
**Fix**: Add defensive check: `if total_queries == 0: self.ai_stats['avg_ai_response_time_ms'] = processing_time_ms; return`

## Scout Node Robustness Improvements

### Enhanced JSON Parsing Bounds Checking
**File**: `scout.py:228`  
**Issue**: While current code handles the case, explicit bounds checking would be more defensive  
**Impact**: Better error messages for malformed LLM responses  
**Fix**: Add explicit check: `if json_end <= json_start: raise ValueError("Invalid JSON bounds")` before extraction  

### More Robust Score Hint Type Conversion  
**File**: `scout.py:264`  
**Issue**: While ValueError is caught, explicit type conversion handling would be cleaner  
**Impact**: Better error handling for non-numeric score_hint values from LLM  
**Fix**: Use defensive conversion: `try: float(data.get('score_hint', 0.0)) except (ValueError, TypeError): 0.0`

### Enhanced Fallback Logic for Missing ADP Data
**File**: `scout.py:278`  
**Issue**: While float('inf') works, explicit validation would be more robust  
**Impact**: Better handling of data quality issues from external sources  
**Fix**: Add validation: `if not any(p.get('adp') is not None for p in pick_candidates): use alternative sorting key`

### Async Resource Management Enhancement
**File**: `scout.py:157,179-181`  
**Issue**: While Python handles cleanup, explicit resource management would be more robust  
**Impact**: Better resource management during parallel execution failures  
**Fix**: Consider using async context managers or explicit try-finally blocks for executor cleanup