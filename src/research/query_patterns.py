"""
Tree-sitter Query Pattern Prototypes

Demonstrates advanced Tree-sitter queries for common code structures
across multiple programming languages.
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
from dataclasses import dataclass

from src.parsing.parser import get_parser
from src.parsing.ts_loader import load_language

logger = logging.getLogger(__name__)


@dataclass
class QueryMatch:
    """Represents a match from a Tree-sitter query."""

    pattern_name: str
    language: str
    file_path: str
    start_line: int
    end_line: int
    matched_text: str
    captures: Dict[str, str]  # capture_name -> captured_text
    confidence: float = 1.0


@dataclass
class QueryPattern:
    """Represents a Tree-sitter query pattern."""

    name: str
    description: str
    language: str
    query_string: str
    expected_captures: List[str]


class TreeSitterQueryEngine:
    """
    Advanced Tree-sitter query engine for pattern matching.

    Demonstrates sophisticated queries for:
    - Async functions and patterns
    - Factory method patterns
    - Repository CRUD operations
    - Error handling patterns
    - Design pattern detection

    Production features:
    - Precompiled query cache per language/pattern
    - Result cache keyed by (language, pattern, code hash)
    - Graceful degradation if a query fails on a grammar
    """

    def __init__(self, max_result_cache: int = 256):
        """Initialize the query engine."""
        from collections import OrderedDict
        import hashlib

        self._hashlib = hashlib
        self._OrderedDict = OrderedDict

        self.parser = get_parser()
        self.query_patterns = self._initialize_patterns()
        self._compiled_queries: dict[tuple[str, str], Any] = {}
        self._result_cache: OrderedDict = OrderedDict()
        self._max_result_cache = max_result_cache

        logger.info("TreeSitterQueryEngine initialized with caching")

    def _initialize_patterns(self) -> Dict[str, List[QueryPattern]]:
        """Initialize query patterns for all languages."""
        patterns = {
            "python": self._get_python_patterns(),
            "javascript": self._get_javascript_patterns(),
            "typescript": self._get_typescript_patterns(),
            "java": self._get_java_patterns(),
            "cpp": self._get_cpp_patterns(),
            "go": self._get_go_patterns(),
            "rust": self._get_rust_patterns(),
        }

        total_patterns = sum(len(lang_patterns) for lang_patterns in patterns.values())
        logger.info(
            f"Initialized {total_patterns} query patterns across {len(patterns)} languages"
        )

        return patterns

    def _get_python_patterns(self) -> List[QueryPattern]:
        """Get Python-specific query patterns."""
        return [
            QueryPattern(
                name="async_functions",
                description="Find functions with await and error handling (proxy for async)",
                language="python",
                query_string="""
                (function_definition
                  name: (identifier) @function_name
                  body: (block
                    (try_statement
                      body: (block
                        (_)
                      )
                    ) @try_block
                  )
                ) @async_like_function
                """,
                expected_captures=["function_name", "try_block", "async_like_function"],
            ),
            QueryPattern(
                name="factory_methods",
                description="Find factory method patterns",
                language="python",
                query_string="""
                (class_definition
                  name: (identifier) @class_name
                  body: (block
                    (function_definition
                      name: (identifier) @method_name
                      body: (block
                        (return_statement
                          (call
                            function: (identifier) @constructor_call
                          )
                        ) @return_stmt
                      )
                    ) @factory_method
                  )
                ) @factory_class
                """,
                expected_captures=[
                    "class_name",
                    "method_name",
                    "constructor_call",
                    "factory_method",
                ],
            ),
            QueryPattern(
                name="repository_crud",
                description="Find repository CRUD operations",
                language="python",
                query_string="""
                (class_definition
                  name: (identifier) @class_name
                  body: (block
                    (function_definition
                      name: (identifier) @method_name
                      body: (block
                        (expression_statement
                          (call
                            function: (attribute
                              object: (_)
                              attribute: (identifier) @db_operation
                            )
                          )
                        ) @db_call
                      )
                    ) @crud_method
                  )
                ) @repository_class
                """,
                expected_captures=[
                    "class_name",
                    "method_name",
                    "db_object",
                    "db_operation",
                ],
            ),
            QueryPattern(
                name="decorator_patterns",
                description="Find decorator usage patterns",
                language="python",
                query_string="""
                (decorated_definition
                  (decorator
                    (identifier) @decorator_name
                  ) @decorator
                  definition: (function_definition
                    name: (identifier) @function_name
                  ) @decorated_function
                ) @decorated_def
                """,
                expected_captures=[
                    "decorator_name",
                    "function_name",
                    "decorated_function",
                ],
            ),
        ]

    def _get_javascript_patterns(self) -> List[QueryPattern]:
        """Get JavaScript-specific query patterns."""
        return [
            QueryPattern(
                name="async_functions",
                description="Find functions using await with try/catch",
                language="javascript",
                query_string="""
                (function_declaration
                  name: (identifier) @function_name
                  body: (statement_block
                    (try_statement
                      body: (statement_block
                        (expression_statement (await_expression) @await)
                      )
                    ) @try_block
                  )
                ) @async_like_function
                """,
                expected_captures=["function_name", "try_block", "await"],
            ),
            QueryPattern(
                name="factory_classes",
                description="Find class methods that return a new instance (factory)",
                language="javascript",
                query_string="""
                (class_declaration
                  name: (identifier) @class_name
                  body: (class_body
                    (method_definition
                      name: (property_identifier) @method_name
                      body: (statement_block
                        (return_statement
                          (new_expression
                            constructor: (identifier) @constructor_name
                          )
                        ) @return_stmt
                      )
                    ) @factory_method
                  )
                ) @factory_class
                """,
                expected_captures=["class_name", "method_name", "constructor_name"],
            ),
            QueryPattern(
                name="promise_chains",
                description="Find promise chain patterns",
                language="javascript",
                query_string="""
                (call_expression
                  function: (member_expression
                    object: (call_expression) @promise_call
                    property: (property_identifier) @chain_method
                  )
                  arguments: (arguments
                    (arrow_function) @callback
                  )
                ) @promise_chain
                """,
                expected_captures=["promise_call", "chain_method", "callback"],
            ),
        ]

    def _get_typescript_patterns(self) -> List[QueryPattern]:
        """Get TypeScript-specific query patterns."""
        return [
            QueryPattern(
                name="interface_implementations",
                description="Find interface implementation patterns",
                language="typescript",
                query_string="""
                (class_declaration
                  name: (type_identifier) @class_name
                  (class_heritage
                    (implements_clause
                      (type_identifier) @interface_name
                    )
                  ) @implements_clause
                ) @implementing_class
                """,
                expected_captures=[
                    "class_name",
                    "interface_name",
                    "implementing_class",
                ],
            ),
            QueryPattern(
                name="generic_functions",
                description="Find generic function patterns",
                language="typescript",
                query_string="""
                (function_declaration
                  name: (identifier) @function_name
                  type_parameters: (type_parameters
                    (type_parameter
                      name: (type_identifier) @type_param
                    )
                  ) @type_params
                ) @generic_function
                """,
                expected_captures=["function_name", "type_param", "generic_function"],
            ),
        ]

    def _get_java_patterns(self) -> List[QueryPattern]:
        """Get Java-specific query patterns."""
        return [
            QueryPattern(
                name="singleton_pattern",
                description="Find singleton-like classes (getInstance methods)",
                language="java",
                query_string="""
                (class_declaration
                  name: (identifier) @class_name
                  body: (class_body
                    (method_declaration
                      name: (identifier) @method_name
                    ) @get_instance_method
                  )
                ) @singleton_class
                (#match? @method_name "^(getInstance|get_instance)$")
                """,
                expected_captures=["class_name", "method_name"],
            ),
            QueryPattern(
                name="repository_pattern",
                description="Find repository pattern with CRUD operations",
                language="java",
                query_string="""
                (class_declaration
                  name: (identifier) @class_name
                  body: (class_body
                    (method_declaration
                      name: (identifier) @method_name
                      body: (block
                        (expression_statement
                          (method_invocation
                            object: (identifier) @dao_object
                            name: (identifier) @crud_operation
                          )
                        ) @dao_call
                      )
                    ) @crud_method
                  )
                ) @repository_class
                """,
                expected_captures=[
                    "class_name",
                    "method_name",
                    "dao_object",
                    "crud_operation",
                ],
            ),
        ]

    def _get_cpp_patterns(self) -> List[QueryPattern]:
        """Get C++-specific query patterns."""
        return [
            QueryPattern(
                name="raii_pattern",
                description="Find RAII (Resource Acquisition Is Initialization) patterns",
                language="cpp",
                query_string="""
                (class_specifier
                  name: (type_identifier) @class_name
                  body: (field_declaration_list
                    (function_definition
                      declarator: (function_declarator
                        declarator: (identifier) @constructor_name
                      )
                    ) @constructor
                    (function_definition
                      declarator: (function_declarator
                        declarator: (destructor_name) @destructor_name
                      )
                    ) @destructor
                  )
                ) @raii_class
                """,
                expected_captures=["class_name", "constructor_name", "destructor_name"],
            )
        ]

    def _get_go_patterns(self) -> List[QueryPattern]:
        """Get Go-specific query patterns."""
        return [
            QueryPattern(
                name="interface_patterns",
                description="Find interface definition and implementation patterns",
                language="go",
                query_string="""
                (type_declaration
                  (type_spec
                    name: (type_identifier) @interface_name
                    type: (interface_type
                      (method_spec
                        name: (field_identifier) @method_name
                      ) @method_spec
                    ) @interface_type
                  )
                ) @interface_declaration
                """,
                expected_captures=[
                    "interface_name",
                    "method_name",
                    "interface_declaration",
                ],
            ),
            QueryPattern(
                name="error_handling",
                description="Find Go error handling patterns",
                language="go",
                query_string="""
                (if_statement) @error_handling
                """,
                expected_captures=["error_handling"],
            ),
        ]

    def _get_rust_patterns(self) -> List[QueryPattern]:
        """Get Rust-specific query patterns."""
        return [
            QueryPattern(
                name="result_patterns",
                description="Find Result<T, E> return types",
                language="rust",
                query_string="""
                (function_item
                  name: (identifier) @function_name
                  return_type: (generic_type
                    type: (type_identifier) @result_type
                    type_arguments: (type_arguments
                      (_)
                      (_)
                    )
                  ) @return_type
                ) @result_function
                """,
                expected_captures=["function_name", "result_type"],
            ),
            QueryPattern(
                name="trait_implementations",
                description="Find trait implementation patterns",
                language="rust",
                query_string="""
                (impl_item
                  trait: (type_identifier) @trait_name
                  type: (type_identifier) @impl_type
                  body: (declaration_list
                    (function_item
                      name: (identifier) @method_name
                    ) @trait_method
                  )
                ) @trait_impl
                """,
                expected_captures=["trait_name", "impl_type", "method_name"],
            ),
        ]

    def execute_query(
        self, pattern: QueryPattern, code: str, file_path: str = "query_test"
    ) -> List[QueryMatch]:
        """Execute a Tree-sitter query pattern on code."""
        try:
            # Parse the code
            result = self.parser.parse(
                Path(f"{file_path}.{self._get_extension(pattern.language)}"), code
            )

            if not result.parse_success or not result.ast_root:
                logger.warning(f"Failed to parse code for query: {pattern.name}")
                return []

            # Check result cache
            code_hash = self._hashlib.sha256(code.encode("utf-8")).hexdigest()
            cache_key = (pattern.language, pattern.name, code_hash)
            if cache_key in self._result_cache:
                # Move to end (LRU) and return cached
                cached = self._result_cache.pop(cache_key)
                self._result_cache[cache_key] = cached
                return cached

            # Load language and create/lookup compiled query
            language = load_language(pattern.language)
            query = self._get_or_compile_query(language, pattern)
            if query is None:
                return []

            # Execute query on AST
            matches = []
            try:
                # Convert our AST back to tree-sitter format for querying
                ts_parser = self._get_ts_parser(pattern.language)
                if ts_parser:
                    tree = ts_parser.parse(code.encode("utf-8"))
                    # tree-sitter >=0.25 uses QueryCursor for execution
                    try:
                        from tree_sitter import QueryCursor

                        cursor = QueryCursor(query)
                        results = cursor.matches(tree.root_node)
                        for _, cap_map in results:
                            for cap_name, nodes in cap_map.items():
                                for node in nodes:
                                    match = QueryMatch(
                                        pattern_name=pattern.name,
                                        language=pattern.language,
                                        file_path=file_path,
                                        start_line=node.start_point[0] + 1,
                                        end_line=node.end_point[0] + 1,
                                        matched_text=code[
                                            node.start_byte : node.end_byte
                                        ],
                                        captures={
                                            cap_name: code[
                                                node.start_byte : node.end_byte
                                            ]
                                        },
                                        confidence=1.0,
                                    )
                                    matches.append(match)
                    except Exception:
                        # Fallback for older versions
                        captures = query.captures(tree.root_node)
                        for node, capture_name in captures:
                            match = QueryMatch(
                                pattern_name=pattern.name,
                                language=pattern.language,
                                file_path=file_path,
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                matched_text=code[node.start_byte : node.end_byte],
                                captures={
                                    capture_name: code[node.start_byte : node.end_byte]
                                },
                                confidence=1.0,
                            )
                            matches.append(match)
            except Exception as e:
                logger.error(f"Query execution failed for {pattern.name}: {e}")

            # Update cache (LRU)
            try:
                self._result_cache[cache_key] = matches
                if len(self._result_cache) > self._max_result_cache:
                    # Evict LRU
                    self._result_cache.popitem(last=False)
            except Exception:
                pass

            return matches

        except Exception as e:
            logger.error(f"Failed to execute query {pattern.name}: {e}", exc_info=True)
            return []

    def _get_or_compile_query(self, language_obj, pattern: QueryPattern):
        """Get or compile a query and cache it."""
        key = (pattern.language, pattern.name)
        if key in self._compiled_queries:
            return self._compiled_queries[key]
        try:
            # Prefer new Query(language, source) API
            try:
                from tree_sitter import Query as TS_Query

                q = TS_Query(language_obj, pattern.query_string)
            except Exception:
                q = language_obj.query(pattern.query_string)
            self._compiled_queries[key] = q
            return q
        except Exception as e:
            logger.error(
                f"Failed to compile query {pattern.name} for {pattern.language}: {e}"
            )
            return None

    def _get_ts_parser(self, language: str):
        """Get tree-sitter parser for language."""
        try:
            import tree_sitter

            lang = load_language(language)
            parser = tree_sitter.Parser()
            try:
                parser.language = lang
            except Exception:
                parser.set_language(lang)  # type: ignore[attr-defined]
            return parser
        except Exception as e:
            logger.error(f"Failed to create parser for {language}: {e}")
            return None

    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        ext_map = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "go": "go",
            "rust": "rs",
        }
        return ext_map.get(language, "txt")

    def get_patterns_for_language(self, language: str) -> List[QueryPattern]:
        """Get all patterns for a specific language."""
        return self.query_patterns.get(language, [])

    def get_all_patterns(self) -> Dict[str, List[QueryPattern]]:
        """Get all query patterns."""
        return self.query_patterns.copy()

    def demonstrate_patterns(
        self, language: str, code_samples: Dict[str, str]
    ) -> Dict[str, List[QueryMatch]]:
        """Demonstrate query patterns on code samples."""
        results = {}
        patterns = self.get_patterns_for_language(language)

        for pattern in patterns:
            pattern_matches = []
            for sample_name, code in code_samples.items():
                matches = self.execute_query(pattern, code, sample_name)
                pattern_matches.extend(matches)

            results[pattern.name] = pattern_matches

        return results
