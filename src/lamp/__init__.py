"""LAMP executable audit framework."""

from .audit import LAMP_Audit, run_audit
from .bio import diagnose_biological_claim, load_bio_contract
from .config import AuditConfig, load_audit_config
from .discovery import run_discovery

__all__ = [
    "AuditConfig",
    "LAMP_Audit",
    "diagnose_biological_claim",
    "load_audit_config",
    "load_bio_contract",
    "run_audit",
    "run_discovery",
]
__version__ = "0.1.0"
