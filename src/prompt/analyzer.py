"""
Prompt Analysis Engine - Epic 1

Analyzes user prompts to determine intent, entities, and context requirements.

Components:
- IntentClassifier: Classifies prompts into fix/explain/implement/debug/etc
- EntityExtractor: Extracts files, functions, errors using spaCy
- TokenBudgetEstimator: Estimates token budget (10k-400k)
- ContextTypeSelector: Selects which context types to gather
- PromptAnalyzer: Orchestrator class
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Set

# Note: spaCy will be loaded lazily to avoid import errors during installation
_nlp = None


def get_nlp():
    """Lazy load spaCy model"""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            # If spaCy not installed or model not downloaded, return None
            _nlp = None
    return _nlp


class IntentType(str, Enum):
    """Types of user intents"""
    FIX = "fix"
    EXPLAIN = "explain"
    IMPLEMENT = "implement"
    REFACTOR = "refactor"
    DEBUG = "debug"
    TEST = "test"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Types of entities that can be extracted"""
    FILE = "FILE"
    IDENTIFIER = "IDENTIFIER"  # function/class/variable name
    ERROR = "ERROR"
    CONCEPT = "CONCEPT"
    PERSON = "PERSON"
    ORG = "ORG"


@dataclass
class Intent:
    """Classified intent from prompt"""
    type: IntentType
    confidence: float  # 0.0 - 1.0
    method: str  # 'rule-based', 'ml', 'default'


@dataclass
class Entity:
    """Extracted entity from prompt"""
    text: str
    type: EntityType
    confidence: float  # 0.0 - 1.0
    source: str  # 'spacy', 'regex', 'codebase_match'
    metadata: dict = field(default_factory=dict)


@dataclass
class PromptIntent:
    """Complete analysis result of a prompt"""
    original_prompt: str
    intent: Intent
    entities: List[Entity]
    token_budget: int
    context_types: Set[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


class IntentClassifier:
    """
    Classify user intent from prompt using rule-based patterns

    Approach: Fast rule-based matching with optional ML fallback
    """

    # Rule-based patterns for each intent type
    INTENT_PATTERNS = {
        IntentType.FIX: [
            r'\bfix\b', r'\bbug\b', r'\berror\b', r'\bissue\b',
            r'\bproblem\b', r'\bbroken\b', r'\bfailing\b', r'\bcrash'
        ],
        IntentType.EXPLAIN: [
            r'\bhow does\b', r'\bwhat is\b', r'\bexplain\b',
            r'\bunderstand\b', r'\bwhy\b', r'\bdescribe\b', r'\bwhat does\b'
        ],
        IntentType.IMPLEMENT: [
            r'\badd\b', r'\bcreate\b', r'\bimplement\b', r'\bbuild\b',
            r'\bmake\b', r'\bdevelop\b', r'\bwrite\b'
        ],
        IntentType.REFACTOR: [
            r'\brefactor\b', r'\bimprove\b', r'\boptimize\b',
            r'\bclean\b', r'\breorganize\b', r'\brestructure\b'
        ],
        IntentType.DEBUG: [
            r'\bdebug\b', r'\binvestigate\b', r'\btrace\b',
            r'\bfind out\b', r'\bdiagnose\b'
        ],
        IntentType.TEST: [
            r'\btest\b', r'\bunit test\b', r'\bintegration test\b',
            r'\btest case\b', r'\btest coverage\b'
        ],
        IntentType.DOCUMENT: [
            r'\bdocument\b', r'\bdocs\b', r'\bcomment\b',
            r'\bdocstring\b', r'\breadme\b'
        ],
    }

    def __init__(self, ml_model=None):
        """
        Initialize intent classifier

        Args:
            ml_model: Optional ML model for fallback classification
        """
        self.ml_model = ml_model

    async def classify(self, prompt: str) -> Intent:
        """
        Classify intent from prompt

        Args:
            prompt: User's prompt text

        Returns:
            Intent with type, confidence, and classification method
        """
        prompt_lower = prompt.lower()

        # Try rule-based first (fast path)
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    return Intent(
                        type=intent_type,
                        confidence=0.9,
                        method='rule-based'
                    )

        # Fallback to ML if available
        if self.ml_model:
            return await self._ml_classify(prompt)

        # Default to EXPLAIN if uncertain
        return Intent(
            type=IntentType.EXPLAIN,
            confidence=0.5,
            method='default'
        )

    async def _ml_classify(self, prompt: str) -> Intent:
        """ML-based classification (placeholder for future implementation)"""
        # TODO: Implement ML classification if needed
        # For now, return default
        return Intent(
            type=IntentType.EXPLAIN,
            confidence=0.6,
            method='ml'
        )


class EntityExtractor:
    """
    Extract entities from prompt using spaCy NLP and regex patterns

    Extracts:
    - File paths
    - Function/class names
    - Error messages
    - Concepts/keywords
    """

    # Regex patterns for specific entity types
    FILE_PATTERN = re.compile(
        r'[\w/.-]+\.[\w]+'  # file.ext or path/to/file.ext
    )

    ERROR_PATTERN = re.compile(
        r'(TypeError|ValueError|AttributeError|KeyError|IndexError|'
        r'NameError|SyntaxError|RuntimeError|ImportError|FileNotFoundError|'
        r'Exception|Error):\s*[^\n]+'
    )

    IDENTIFIER_PATTERN = re.compile(
        r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    )

    def __init__(self):
        """Initialize entity extractor"""
        # spaCy model loaded lazily
        pass

    async def extract(self, prompt: str, user_context) -> List[Entity]:
        """
        Extract entities from prompt

        Args:
            prompt: User's prompt text
            user_context: Current user context (for validation)

        Returns:
            List of extracted entities
        """
        entities = []

        # Extract using spaCy NLP
        entities.extend(await self._extract_with_spacy(prompt))

        # Extract file paths
        entities.extend(self._extract_file_paths(prompt, user_context))

        # Extract error messages
        entities.extend(self._extract_errors(prompt))

        # Extract code identifiers
        entities.extend(self._extract_code_identifiers(prompt, user_context))

        # Deduplicate entities
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.text, entity.type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    async def _extract_with_spacy(self, prompt: str) -> List[Entity]:
        """Extract entities using spaCy NLP"""
        nlp = get_nlp()
        if nlp is None:
            return []

        entities = []
        doc = nlp(prompt)

        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'GPE']:
                entities.append(Entity(
                    text=ent.text,
                    type=EntityType.PERSON if ent.label_ == 'PERSON' else EntityType.ORG,
                    confidence=0.8,
                    source='spacy',
                    metadata={'label': ent.label_}
                ))

        return entities

    def _extract_file_paths(self, prompt: str, user_context) -> List[Entity]:
        """Extract file paths from prompt"""
        entities = []

        for match in self.FILE_PATTERN.finditer(prompt):
            file_path = match.group(0)

            # Validate file exists (if user_context has workspace path)
            confidence = 0.7
            if hasattr(user_context, 'workspace_path'):
                import os
                full_path = os.path.join(user_context.workspace_path, file_path)
                if os.path.exists(full_path):
                    confidence = 0.95

            entities.append(Entity(
                text=file_path,
                type=EntityType.FILE,
                confidence=confidence,
                source='regex'
            ))

        return entities

    def _extract_errors(self, prompt: str) -> List[Entity]:
        """Extract error messages from prompt"""
        entities = []

        for match in self.ERROR_PATTERN.finditer(prompt):
            error_msg = match.group(0)
            entities.append(Entity(
                text=error_msg,
                type=EntityType.ERROR,
                confidence=0.9,
                source='regex'
            ))

        return entities

    def _extract_code_identifiers(self, prompt: str, user_context) -> List[Entity]:
        """Extract potential function/class names"""
        entities = []

        # Get potential identifiers
        potential_identifiers = set(self.IDENTIFIER_PATTERN.findall(prompt))

        # Filter out common English words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'fix', 'bug', 'error', 'how', 'what', 'why', 'when', 'where', 'which'
        }

        for identifier in potential_identifiers:
            if identifier.lower() in common_words:
                continue

            # Only include if it looks like a code identifier
            # (camelCase, snake_case, or has uppercase letters)
            if '_' in identifier or any(c.isupper() for c in identifier[1:]):
                entities.append(Entity(
                    text=identifier,
                    type=EntityType.IDENTIFIER,
                    confidence=0.6,
                    source='regex'
                ))

        return entities


class TokenBudgetEstimator:
    """
    Estimate optimal token budget for enhanced prompt

    Budget ranges:
    - Simple query (1-2 entities): 10k-50k tokens
    - Medium query (3-5 entities): 50k-150k tokens
    - Complex query (6+ entities): 150k-400k tokens
    """

    BASE_BUDGETS = {
        IntentType.EXPLAIN: 50000,      # Explanation needs moderate context
        IntentType.FIX: 100000,         # Bug fixes need more context
        IntentType.IMPLEMENT: 150000,   # Implementation needs extensive context
        IntentType.REFACTOR: 120000,    # Refactoring needs architecture context
        IntentType.DEBUG: 120000,       # Debugging needs error traces, logs
        IntentType.TEST: 80000,         # Testing needs code + examples
        IntentType.DOCUMENT: 60000,     # Documentation needs code + existing docs
        IntentType.UNKNOWN: 100000,     # Default to medium budget
    }

    MAX_BUDGET = 400000
    MIN_BUDGET = 10000

    def estimate(self, intent: Intent, entities: List[Entity]) -> int:
        """
        Estimate token budget based on intent and entities

        Args:
            intent: Classified intent
            entities: Extracted entities

        Returns:
            Estimated token budget (10k-400k)
        """
        # Start with base budget for intent type
        base = self.BASE_BUDGETS.get(intent.type, 100000)

        # Adjust based on entity count
        entity_multiplier = 1.0 + (len(entities) * 0.1)  # +10% per entity

        # Calculate budget
        budget = int(base * entity_multiplier)

        # Clamp to min/max range
        budget = max(self.MIN_BUDGET, min(budget, self.MAX_BUDGET))

        return budget


class ContextTypeSelector:
    """
    Select which context types to gather based on intent

    Context types:
    - current: Current file, selection, open files
    - code: Related code, dependencies, tests
    - architecture: Schemas, configs, dependency graph
    - history: Git log, blame, recent commits
    - team: CODEOWNERS, experts, patterns
    - external: GitHub issues, Jira tickets (optional)
    """

    # Default context types for each intent
    DEFAULT_CONTEXT_TYPES = {
        IntentType.FIX: {'current', 'code', 'history', 'team'},
        IntentType.EXPLAIN: {'current', 'code', 'architecture'},
        IntentType.IMPLEMENT: {'code', 'architecture', 'team'},
        IntentType.REFACTOR: {'current', 'code', 'architecture', 'team'},
        IntentType.DEBUG: {'current', 'code', 'history', 'team'},
        IntentType.TEST: {'current', 'code', 'team'},
        IntentType.DOCUMENT: {'current', 'code', 'architecture'},
        IntentType.UNKNOWN: {'current', 'code'},
    }

    def select(self, intent: Intent, entities: List[Entity]) -> Set[str]:
        """
        Select which context types to gather

        Args:
            intent: Classified intent
            entities: Extracted entities

        Returns:
            Set of context type names
        """
        # Get default context types for this intent
        context_types = self.DEFAULT_CONTEXT_TYPES.get(
            intent.type,
            {'current', 'code'}
        ).copy()

        # Add history if we have file entities (to get git blame)
        has_files = any(e.type == EntityType.FILE for e in entities)
        if has_files and intent.type not in [IntentType.FIX, IntentType.DEBUG]:
            context_types.add('history')

        # Add external if we have error entities (to search for similar issues)
        has_errors = any(e.type == EntityType.ERROR for e in entities)
        if has_errors:
            context_types.add('external')

        return context_types


class PromptAnalyzer:
    """
    Main orchestrator for prompt analysis

    Coordinates:
    - Intent classification
    - Entity extraction
    - Token budget estimation
    - Context type selection
    """

    def __init__(self):
        """Initialize prompt analyzer with all sub-components"""
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.token_estimator = TokenBudgetEstimator()
        self.context_selector = ContextTypeSelector()

    async def analyze(self, prompt: str, user_context) -> PromptIntent:
        """
        Main analysis pipeline

        Args:
            prompt: User's prompt text
            user_context: Current user context

        Returns:
            PromptIntent with complete analysis results
        """
        # Step 1: Classify intent and extract entities in parallel
        intent, entities = await asyncio.gather(
            self.intent_classifier.classify(prompt),
            self.entity_extractor.extract(prompt, user_context)
        )

        # Step 2: Estimate token budget
        token_budget = self.token_estimator.estimate(intent, entities)

        # Step 3: Select context types
        context_types = self.context_selector.select(intent, entities)

        # Calculate overall confidence
        confidence = self._calculate_confidence(intent, entities)

        return PromptIntent(
            original_prompt=prompt,
            intent=intent,
            entities=entities,
            token_budget=token_budget,
            context_types=context_types,
            confidence=confidence
        )

    def _calculate_confidence(self, intent: Intent, entities: List[Entity]) -> float:
        """
        Calculate overall confidence in the analysis

        Args:
            intent: Classified intent
            entities: Extracted entities

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Weight intent confidence heavily
        confidence = intent.confidence * 0.7

        # Add entity confidence
        if entities:
            avg_entity_confidence = sum(e.confidence for e in entities) / len(entities)
            confidence += avg_entity_confidence * 0.3
        else:
            # No entities reduces confidence slightly
            confidence *= 0.9

        return min(1.0, confidence)
