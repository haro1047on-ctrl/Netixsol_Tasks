"""Conversation Loader & Validation Schema for Evaluation Suite (Week 7 Day 6)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TurnExpectation(BaseModel):
    """Expectations for an individual turn in a test conversation."""
    turn_index: int
    user_input: str
    expected_intent: Optional[str] = None
    expected_entities: Dict[str, Any] = Field(default_factory=dict)
    expected_clarification: Optional[bool] = None
    expected_status: Optional[str] = None
    expected_keywords: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)
    is_security_test: bool = False
    is_silent: bool = False
    is_angry: bool = False


class ConversationTestCase(BaseModel):
    """Complete multi-turn test conversation model."""
    id: str
    category: str
    title: str
    description: str
    tags: List[str] = Field(default_factory=list)
    turns: List[TurnExpectation]
    expected_outcome: str


class EvaluationSuite(BaseModel):
    """Container for full 40+ conversation dataset."""
    version: str = "1.0.0"
    suite_name: str = "RealEstate Hub 40+ Production Evaluation Suite"
    categories: List[str]
    total_conversations: int
    conversations: List[ConversationTestCase]


def load_evaluation_conversations(file_path: Optional[Path | str] = None) -> EvaluationSuite:
    """Load and validate the evaluation conversations dataset from JSON."""
    if file_path is None:
        file_path = Path(__file__).resolve().parent / "test_conversations.json"
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation conversations file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    suite = EvaluationSuite(**data)
    return suite


def get_conversations_by_category(category: str, file_path: Optional[Path | str] = None) -> List[ConversationTestCase]:
    """Retrieve all conversations filtered by category."""
    suite = load_evaluation_conversations(file_path)
    cat_lower = category.lower().strip()
    return [c for c in suite.conversations if c.category.lower().strip() == cat_lower]
