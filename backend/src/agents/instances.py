"""
Module-level singleton instances of AI agents.

Instantiated once at startup so that:
- EvaluatorAgent's in-memory idempotency cache persists across requests (§7.5).
- TutorAgent's CircuitBreaker and SCRTracker state are shared across requests.
- Anthropic SDK client objects are reused rather than recreated per request.
"""

from src.agents.evaluator.evaluator_agent import EvaluatorAgent
from src.agents.tutor.tutor_agent import TutorAgent

tutor_agent = TutorAgent()
evaluator_agent = EvaluatorAgent()
