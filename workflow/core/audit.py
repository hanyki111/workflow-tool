import os
import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class AuditLogger:
    def __init__(self, log_dir: str = ".workflow/audit"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "workflow.log")

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs a structured event to the audit file."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    @staticmethod
    def get_file_hash(path: str) -> str:
        """Calculates SHA-256 hash of a file for evidence."""
        if not os.path.isfile(path):
            return "not_found"
        
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return "error"

class WorkflowAuditManager:
    def __init__(self, audit_dir: str = ".workflow/audit"):
        self.logger = AuditLogger(log_dir=audit_dir)

    def record_transition(self, from_stage: str, to_stage: str, module: str, results: List[Dict], forced: bool = False, reason: str = ""):
        data = {
            "from": from_stage,
            "to": to_stage,
            "module": module,
            "rules_checked": results,
            "forced": forced
        }
        if forced:
            data["reason"] = reason
            
        self.logger.log_event("TRANSITION", data)
