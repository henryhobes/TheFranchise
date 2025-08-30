import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Set
from urllib.parse import urlparse

class WebSocketDiscovery:
    """
    Utility for analyzing and categorizing discovered WebSocket connections
    during ESPN draft room monitoring.
    """
    
    def __init__(self):
        self.discovered_endpoints: Set[str] = set()
        self.message_patterns: Dict[str, List[Dict]] = {}
        self.connection_metadata: List[Dict[str, Any]] = []
        
    def analyze_websocket_url(self, url: str) -> Dict[str, str]:
        """
        Analyze WebSocket URL to extract connection details.
        
        Args:
            url: WebSocket URL
            
        Returns:
            Dict containing parsed URL components
        """
        parsed = urlparse(url)
        
        analysis = {
            "full_url": url,
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": str(parsed.port) if parsed.port else "default",
            "path": parsed.path,
            "query": parsed.query,
            "fragment": parsed.fragment
        }
        
        # Extract ESPN-specific patterns
        if "espn" in url.lower():
            analysis["service"] = "ESPN"
            
            # Look for draft-related paths
            if "draft" in url.lower():
                analysis["purpose"] = "draft"
            elif "fantasy" in url.lower():
                analysis["purpose"] = "fantasy"
                
        return analysis
        
    def record_connection(self, url: str, timestamp: str = None):
        """Record a new WebSocket connection."""
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        self.discovered_endpoints.add(url)
        
        analysis = self.analyze_websocket_url(url)
        analysis["discovered_at"] = timestamp
        
        self.connection_metadata.append(analysis)
        
    def categorize_message(self, payload: str) -> Dict[str, Any]:
        """
        Attempt to categorize and analyze a WebSocket message.
        
        Args:
            payload: Raw message payload
            
        Returns:
            Dict containing message analysis
        """
        analysis = {
            "raw_payload": payload,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": len(payload),
            "is_json": False,
            "message_type": "unknown",
            "contains_draft_keywords": False
        }
        
        # Try to parse as JSON
        try:
            parsed = json.loads(payload)
            analysis["is_json"] = True
            analysis["parsed_json"] = parsed
            
            # Look for message type indicators
            if isinstance(parsed, dict):
                # Common message type fields
                for type_field in ["type", "messageType", "event", "action", "command"]:
                    if type_field in parsed:
                        analysis["message_type"] = parsed[type_field]
                        break
                        
                # Look for draft-related content
                draft_keywords = ["pick", "draft", "player", "team", "clock", "roster", "turn"]
                message_str = json.dumps(parsed).lower()
                
                for keyword in draft_keywords:
                    if keyword in message_str:
                        analysis["contains_draft_keywords"] = True
                        analysis["draft_keywords_found"] = [k for k in draft_keywords if k in message_str]
                        break
                        
        except json.JSONDecodeError:
            # Try to find patterns in non-JSON messages
            analysis["is_json"] = False
            
            # Look for common patterns
            if payload.startswith("42"):  # Socket.IO pattern
                analysis["likely_protocol"] = "socket.io"
            elif payload.startswith("{") or payload.startswith("["):
                analysis["likely_protocol"] = "json"
            elif payload.startswith("ping") or payload.startswith("pong"):
                analysis["likely_protocol"] = "websocket_ping_pong"
                
        return analysis
        
    def record_message_pattern(self, websocket_url: str, payload: str):
        """Record and categorize a message for pattern analysis."""
        if websocket_url not in self.message_patterns:
            self.message_patterns[websocket_url] = []
            
        analysis = self.categorize_message(payload)
        self.message_patterns[websocket_url].append(analysis)
        
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get a summary of all discovered WebSocket activity."""
        summary = {
            "total_endpoints": len(self.discovered_endpoints),
            "endpoints": list(self.discovered_endpoints),
            "connection_metadata": self.connection_metadata,
            "message_summary": {}
        }
        
        # Summarize message patterns by endpoint
        for url, messages in self.message_patterns.items():
            url_summary = {
                "total_messages": len(messages),
                "json_messages": len([m for m in messages if m["is_json"]]),
                "draft_related_messages": len([m for m in messages if m["contains_draft_keywords"]]),
                "unique_message_types": list(set([m["message_type"] for m in messages if m["message_type"] != "unknown"])),
                "protocols_detected": list(set([m.get("likely_protocol", "") for m in messages if m.get("likely_protocol")]))
            }
            summary["message_summary"][url] = url_summary
            
        return summary
        
    def identify_draft_websockets(self) -> List[str]:
        """
        Identify WebSocket URLs that are likely related to draft functionality.
        
        Returns:
            List of URLs that appear to be draft-related
        """
        draft_urls = []
        
        for url in self.discovered_endpoints:
            # Check URL patterns
            if any(keyword in url.lower() for keyword in ["draft", "live", "room", "socket"]):
                draft_urls.append(url)
                continue
                
            # Check message content
            if url in self.message_patterns:
                messages = self.message_patterns[url]
                draft_message_ratio = len([m for m in messages if m["contains_draft_keywords"]]) / len(messages)
                
                if draft_message_ratio > 0.1:  # More than 10% of messages are draft-related
                    draft_urls.append(url)
                    
        return draft_urls
        
    def extract_message_schemas(self) -> Dict[str, Dict]:
        """
        Extract common message schemas from JSON messages.
        
        Returns:
            Dict mapping message types to their common schema patterns
        """
        schemas = {}
        
        for url, messages in self.message_patterns.items():
            json_messages = [m for m in messages if m["is_json"]]
            
            for message in json_messages:
                msg_type = message["message_type"]
                if msg_type == "unknown":
                    continue
                    
                if msg_type not in schemas:
                    schemas[msg_type] = {
                        "sample_count": 0,
                        "common_fields": set(),
                        "examples": []
                    }
                    
                schemas[msg_type]["sample_count"] += 1
                
                if "parsed_json" in message and isinstance(message["parsed_json"], dict):
                    schemas[msg_type]["common_fields"].update(message["parsed_json"].keys())
                    
                    if len(schemas[msg_type]["examples"]) < 3:  # Keep up to 3 examples
                        schemas[msg_type]["examples"].append(message["parsed_json"])
                        
        # Convert sets to lists for JSON serialization
        for schema in schemas.values():
            schema["common_fields"] = list(schema["common_fields"])
            
        return schemas
        
    def save_discovery_report(self, filename: str):
        """Save a comprehensive discovery report to file."""
        report = {
            "discovery_timestamp": datetime.now().isoformat(),
            "summary": self.get_discovery_summary(),
            "draft_websockets": self.identify_draft_websockets(),
            "message_schemas": self.extract_message_schemas(),
            "raw_message_patterns": self.message_patterns
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Discovery report saved to {filename}")
        except Exception as e:
            print(f"Failed to save discovery report: {e}")