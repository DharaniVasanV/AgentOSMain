"""
Verification service for field validation and source metadata scoring.
Wraps Verifier for consistent service interface.
"""
from app.services.verifier import Verifier

class VerificationService(Verifier):
    """Alias/Wrapper for Verifier to match standard architecture naming."""
    pass
