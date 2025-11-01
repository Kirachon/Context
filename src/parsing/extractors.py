"""
Symbol Extractors

Language-specific symbol extraction from AST nodes.
Extracts functions, classes, imports, and relationships.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from .models import (
    Language, ASTNode, SymbolInfo, ClassInfo, ImportInfo, 
    RelationshipInfo, ParameterInfo
)

logger = logging.getLogger(__name__)


class SymbolExtractor:
    """Extract symbols, classes, imports, and relationships from AST."""
    
    def __init__(self):
        """Initialize symbol extractor."""
        self.language_extractors = {
            Language.PYTHON: PythonExtractor(),
            Language.JAVASCRIPT: JavaScriptExtractor(),
            Language.TYPESCRIPT: TypeScriptExtractor(),
            Language.JAVA: JavaExtractor(),
            Language.CPP: CppExtractor(),
            Language.GO: GoExtractor(),
            Language.RUST: RustExtractor(),
        }
    
    def extract_symbols(self, ast_root: ASTNode, language: Language) -> tuple[
        List[SymbolInfo], List[ClassInfo], List[ImportInfo], List[RelationshipInfo]
    ]:
        """
        Extract all symbols from AST.
        
        Returns:
            Tuple of (symbols, classes, imports, relationships)
        """
        extractor = self.language_extractors.get(language)
        if not extractor:
            logger.warning(f"No symbol extractor for {language.value}")
            return [], [], [], []
        
        try:
            return extractor.extract(ast_root)
        except Exception as e:
            logger.error(f"Symbol extraction failed for {language.value}: {e}")
            return [], [], [], []


class BaseExtractor:
    """Base class for language-specific extractors."""
    
    def extract(self, ast_root: ASTNode) -> tuple[
        List[SymbolInfo], List[ClassInfo], List[ImportInfo], List[RelationshipInfo]
    ]:
        """Extract symbols from AST root."""
        symbols = []
        classes = []
        imports = []
        relationships = []
        
        self._extract_recursive(ast_root, symbols, classes, imports, relationships)
        
        return symbols, classes, imports, relationships
    
    def _extract_recursive(self, node: ASTNode, symbols: List[SymbolInfo], 
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Recursively extract symbols from AST nodes."""
        # Extract from current node
        self._extract_from_node(node, symbols, classes, imports, relationships)
        
        # Recursively process children
        for child in node.children:
            self._extract_recursive(child, symbols, classes, imports, relationships)
    
    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract symbols from a single AST node. Override in subclasses."""
        pass
    
    def _get_node_text(self, node: ASTNode) -> str:
        """Get clean text from node."""
        return node.text.strip() if node.text else ""
    
    def _get_line_number(self, node: ASTNode) -> int:
        """Get line number from node (1-based)."""
        return node.start_point[0] + 1
    
    def _get_end_line_number(self, node: ASTNode) -> int:
        """Get end line number from node (1-based)."""
        return node.end_point[0] + 1
    
    def _find_child_by_type(self, node: ASTNode, node_type: str) -> Optional[ASTNode]:
        """Find first child node of given type."""
        for child in node.children:
            if child.type == node_type:
                return child
        return None
    
    def _find_children_by_type(self, node: ASTNode, node_type: str) -> List[ASTNode]:
        """Find all child nodes of given type."""
        return [child for child in node.children if child.type == node_type]
    
    def _extract_docstring(self, node: ASTNode) -> Optional[str]:
        """Extract docstring from node. Override in subclasses."""
        return None


class PythonExtractor(BaseExtractor):
    """Python-specific symbol extractor."""
    
    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract Python symbols from AST node."""
        
        if node.type == "function_definition":
            self._extract_python_function(node, symbols)
        elif node.type == "class_definition":
            self._extract_python_class(node, classes, symbols)
        elif node.type in ["import_statement", "import_from_statement"]:
            self._extract_python_import(node, imports)
        elif node.type == "call":
            self._extract_python_call(node, relationships)
    
    def _extract_python_function(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract Python function definition."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return
        
        name = self._get_node_text(name_node)
        parameters = self._extract_python_parameters(node)
        return_type = self._extract_python_return_type(node)
        docstring = self._extract_python_docstring(node)
        decorators = self._extract_python_decorators(node)
        
        # Check if it's async
        is_async = any(child.type == "async" for child in node.children)
        
        symbol = SymbolInfo(
            name=name,
            type="function",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            decorators=decorators,
            is_async=is_async
        )
        symbols.append(symbol)
    
    def _extract_python_class(self, node: ASTNode, classes: List[ClassInfo], symbols: List[SymbolInfo]):
        """Extract Python class definition."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return
        
        name = self._get_node_text(name_node)
        base_classes = self._extract_python_base_classes(node)
        docstring = self._extract_python_docstring(node)
        decorators = self._extract_python_decorators(node)
        
        # Extract methods and fields
        methods = []
        fields = []
        
        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            base_classes=base_classes,
            methods=methods,
            fields=fields,
            docstring=docstring,
            decorators=decorators
        )
        classes.append(class_info)
    
    def _extract_python_import(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract Python import statement."""
        if node.type == "import_statement":
            # import module [as alias]
            for child in node.children:
                if child.type == "dotted_name":
                    module = self._get_node_text(child)
                    imports.append(ImportInfo(
                        module=module,
                        line=self._get_line_number(node),
                        import_type="import"
                    ))
        elif node.type == "import_from_statement":
            # from module import items
            module_node = self._find_child_by_type(node, "dotted_name")
            if module_node:
                module = self._get_node_text(module_node)
                items = []
                # Extract imported items
                imports.append(ImportInfo(
                    module=module,
                    items=items,
                    line=self._get_line_number(node),
                    import_type="from"
                ))
    
    def _extract_python_call(self, node: ASTNode, relationships: List[RelationshipInfo]):
        """Extract Python function call."""
        # Extract function call relationships
        pass
    
    def _extract_python_parameters(self, node: ASTNode) -> List[ParameterInfo]:
        """Extract function parameters."""
        params = []
        params_node = self._find_child_by_type(node, "parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "identifier":
                    params.append(ParameterInfo(name=self._get_node_text(child)))
        return params
    
    def _extract_python_return_type(self, node: ASTNode) -> Optional[str]:
        """Extract return type annotation."""
        # Look for -> type annotation
        return None
    
    def _extract_python_docstring(self, node: ASTNode) -> Optional[str]:
        """Extract Python docstring."""
        # Look for string literal as first statement in body
        return None
    
    def _extract_python_decorators(self, node: ASTNode) -> List[str]:
        """Extract Python decorators."""
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._get_node_text(child))
        return decorators
    
    def _extract_python_base_classes(self, node: ASTNode) -> List[str]:
        """Extract base classes from class definition."""
        base_classes = []
        args_node = self._find_child_by_type(node, "argument_list")
        if args_node:
            for child in args_node.children:
                if child.type == "identifier":
                    base_classes.append(self._get_node_text(child))
        return base_classes


class JavaScriptExtractor(BaseExtractor):
    """JavaScript-specific symbol extractor."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract JavaScript symbols from AST node."""

        if node.type == "function_declaration":
            self._extract_js_function(node, symbols)
        elif node.type == "class_declaration":
            self._extract_js_class(node, classes)
        elif node.type in ["import_statement", "import_clause"]:
            self._extract_js_import(node, imports)
        elif node.type == "call_expression":
            self._extract_js_call(node, relationships)

    def _extract_js_function(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract JavaScript function."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_js_parameters(node)

        # Check if async
        is_async = any(child.type == "async" for child in node.children)

        symbol = SymbolInfo(
            name=name,
            type="function",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            is_async=is_async
        )
        symbols.append(symbol)

    def _extract_js_class(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract JavaScript class."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        base_classes = self._extract_js_extends(node)

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            base_classes=base_classes
        )
        classes.append(class_info)

    def _extract_js_import(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract JavaScript import."""
        # Handle ES6 imports
        pass

    def _extract_js_call(self, node: ASTNode, relationships: List[RelationshipInfo]):
        """Extract JavaScript function call."""
        pass

    def _extract_js_parameters(self, node: ASTNode) -> List[ParameterInfo]:
        """Extract JavaScript function parameters."""
        params = []
        params_node = self._find_child_by_type(node, "formal_parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "identifier":
                    params.append(ParameterInfo(name=self._get_node_text(child)))
        return params

    def _extract_js_extends(self, node: ASTNode) -> List[str]:
        """Extract extends clause from class."""
        extends_clause = self._find_child_by_type(node, "class_heritage")
        if extends_clause:
            extends_node = self._find_child_by_type(extends_clause, "identifier")
            if extends_node:
                return [self._get_node_text(extends_node)]
        return []


class TypeScriptExtractor(JavaScriptExtractor):
    """TypeScript-specific symbol extractor (extends JavaScript)."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract TypeScript symbols."""
        # Call parent JavaScript extractor
        super()._extract_from_node(node, symbols, classes, imports, relationships)

        # Handle TypeScript-specific nodes
        if node.type == "interface_declaration":
            self._extract_ts_interface(node, classes)
        elif node.type == "type_alias_declaration":
            self._extract_ts_type_alias(node, symbols)

    def _extract_ts_interface(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract TypeScript interface."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            is_interface=True
        )
        classes.append(class_info)

    def _extract_ts_type_alias(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract TypeScript type alias."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)

        symbol = SymbolInfo(
            name=name,
            type="type_alias",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node)
        )
        symbols.append(symbol)


class JavaExtractor(BaseExtractor):
    """Java-specific symbol extractor."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract Java symbols from AST node."""

        if node.type == "method_declaration":
            self._extract_java_method(node, symbols)
        elif node.type == "class_declaration":
            self._extract_java_class(node, classes)
        elif node.type == "interface_declaration":
            self._extract_java_interface(node, classes)
        elif node.type == "import_declaration":
            self._extract_java_import(node, imports)
        elif node.type == "method_invocation":
            self._extract_java_call(node, relationships)

    def _extract_java_method(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract Java method."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_java_parameters(node)
        return_type = self._extract_java_return_type(node)
        visibility = self._extract_java_visibility(node)
        is_static = self._has_modifier(node, "static")
        is_abstract = self._has_modifier(node, "abstract")

        symbol = SymbolInfo(
            name=name,
            type="method",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            is_static=is_static,
            is_abstract=is_abstract
        )
        symbols.append(symbol)

    def _extract_java_class(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract Java class."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        base_classes = self._extract_java_extends(node)
        interfaces = self._extract_java_implements(node)
        visibility = self._extract_java_visibility(node)
        is_abstract = self._has_modifier(node, "abstract")

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            base_classes=base_classes,
            interfaces=interfaces,
            visibility=visibility,
            is_abstract=is_abstract
        )
        classes.append(class_info)

    def _extract_java_interface(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract Java interface."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        interfaces = self._extract_java_extends_interfaces(node)

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            interfaces=interfaces,
            is_interface=True
        )
        classes.append(class_info)

    def _extract_java_import(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract Java import."""
        # Handle Java imports
        pass

    def _extract_java_call(self, node: ASTNode, relationships: List[RelationshipInfo]):
        """Extract Java method call."""
        pass

    def _extract_java_parameters(self, node: ASTNode) -> List[ParameterInfo]:
        """Extract Java method parameters."""
        params = []
        params_node = self._find_child_by_type(node, "formal_parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    name_node = self._find_child_by_type(child, "identifier")
                    type_node = self._find_child_by_type(child, "type")
                    if name_node:
                        param = ParameterInfo(
                            name=self._get_node_text(name_node),
                            type_hint=self._get_node_text(type_node) if type_node else None
                        )
                        params.append(param)
        return params

    def _extract_java_return_type(self, node: ASTNode) -> Optional[str]:
        """Extract Java method return type."""
        type_node = self._find_child_by_type(node, "type")
        return self._get_node_text(type_node) if type_node else None

    def _extract_java_visibility(self, node: ASTNode) -> Optional[str]:
        """Extract Java visibility modifier."""
        modifiers = self._find_child_by_type(node, "modifiers")
        if modifiers:
            for child in modifiers.children:
                if child.type in ["public", "private", "protected"]:
                    return child.type
        return None

    def _has_modifier(self, node: ASTNode, modifier: str) -> bool:
        """Check if node has specific modifier."""
        modifiers = self._find_child_by_type(node, "modifiers")
        if modifiers:
            return any(child.type == modifier for child in modifiers.children)
        return False

    def _extract_java_extends(self, node: ASTNode) -> List[str]:
        """Extract extends clause."""
        extends_node = self._find_child_by_type(node, "superclass")
        if extends_node:
            type_node = self._find_child_by_type(extends_node, "type")
            if type_node:
                return [self._get_node_text(type_node)]
        return []

    def _extract_java_implements(self, node: ASTNode) -> List[str]:
        """Extract implements clause."""
        implements_node = self._find_child_by_type(node, "super_interfaces")
        if implements_node:
            interfaces = []
            for child in implements_node.children:
                if child.type == "type":
                    interfaces.append(self._get_node_text(child))
            return interfaces
        return []

    def _extract_java_extends_interfaces(self, node: ASTNode) -> List[str]:
        """Extract extends clause for interfaces."""
        extends_node = self._find_child_by_type(node, "extends_interfaces")
        if extends_node:
            interfaces = []
            for child in extends_node.children:
                if child.type == "type":
                    interfaces.append(self._get_node_text(child))
            return interfaces
        return []


class CppExtractor(BaseExtractor):
    """C++-specific symbol extractor."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract C++ symbols from AST node."""

        if node.type == "function_definition":
            self._extract_cpp_function(node, symbols)
        elif node.type in ["class_specifier", "struct_specifier"]:
            self._extract_cpp_class(node, classes)
        elif node.type == "preproc_include":
            self._extract_cpp_include(node, imports)

    def _extract_cpp_function(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract C++ function."""
        # Find function declarator
        declarator = self._find_child_by_type(node, "function_declarator")
        if not declarator:
            return

        name_node = self._find_child_by_type(declarator, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_cpp_parameters(declarator)
        return_type = self._extract_cpp_return_type(node)

        symbol = SymbolInfo(
            name=name,
            type="function",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type
        )
        symbols.append(symbol)

    def _extract_cpp_class(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract C++ class/struct."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        base_classes = self._extract_cpp_base_classes(node)

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            base_classes=base_classes
        )
        classes.append(class_info)

    def _extract_cpp_include(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract C++ #include."""
        # Find the included file
        for child in node.children:
            if child.type in ["string_literal", "system_lib_string"]:
                module = self._get_node_text(child).strip('"<>')
                imports.append(ImportInfo(
                    module=module,
                    line=self._get_line_number(node),
                    import_type="include"
                ))
                break

    def _extract_cpp_parameters(self, declarator: ASTNode) -> List[ParameterInfo]:
        """Extract C++ function parameters."""
        params = []
        params_node = self._find_child_by_type(declarator, "parameter_list")
        if params_node:
            for child in params_node.children:
                if child.type == "parameter_declaration":
                    name_node = self._find_child_by_type(child, "identifier")
                    if name_node:
                        params.append(ParameterInfo(name=self._get_node_text(name_node)))
        return params

    def _extract_cpp_return_type(self, node: ASTNode) -> Optional[str]:
        """Extract C++ function return type."""
        # Look for type specifier before function declarator
        for child in node.children:
            if child.type in ["primitive_type", "type_identifier"]:
                return self._get_node_text(child)
        return None

    def _extract_cpp_base_classes(self, node: ASTNode) -> List[str]:
        """Extract C++ base classes."""
        base_classes = []
        base_clause = self._find_child_by_type(node, "base_class_clause")
        if base_clause:
            for child in base_clause.children:
                if child.type == "type_identifier":
                    base_classes.append(self._get_node_text(child))
        return base_classes


class GoExtractor(BaseExtractor):
    """Go-specific symbol extractor."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract Go symbols from AST node."""

        if node.type == "function_declaration":
            self._extract_go_function(node, symbols)
        elif node.type == "method_declaration":
            self._extract_go_method(node, symbols)
        elif node.type == "type_declaration":
            self._extract_go_type(node, classes, symbols)
        elif node.type == "import_declaration":
            self._extract_go_import(node, imports)

    def _extract_go_function(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract Go function."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_go_parameters(node)
        return_type = self._extract_go_return_type(node)

        symbol = SymbolInfo(
            name=name,
            type="function",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type
        )
        symbols.append(symbol)

    def _extract_go_method(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract Go method."""
        name_node = self._find_child_by_type(node, "field_identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_go_parameters(node)
        return_type = self._extract_go_return_type(node)

        # Extract receiver type
        receiver = self._extract_go_receiver(node)

        symbol = SymbolInfo(
            name=name,
            type="method",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type,
            parent_class=receiver
        )
        symbols.append(symbol)

    def _extract_go_type(self, node: ASTNode, classes: List[ClassInfo], symbols: List[SymbolInfo]):
        """Extract Go type declaration."""
        # Handle struct types as classes
        pass

    def _extract_go_import(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract Go import."""
        pass

    def _extract_go_parameters(self, node: ASTNode) -> List[ParameterInfo]:
        """Extract Go function parameters."""
        return []

    def _extract_go_return_type(self, node: ASTNode) -> Optional[str]:
        """Extract Go return type."""
        return None

    def _extract_go_receiver(self, node: ASTNode) -> Optional[str]:
        """Extract Go method receiver type."""
        return None


class RustExtractor(BaseExtractor):
    """Rust-specific symbol extractor."""

    def _extract_from_node(self, node: ASTNode, symbols: List[SymbolInfo],
                          classes: List[ClassInfo], imports: List[ImportInfo],
                          relationships: List[RelationshipInfo]):
        """Extract Rust symbols from AST node."""

        if node.type == "function_item":
            self._extract_rust_function(node, symbols)
        elif node.type in ["struct_item", "enum_item", "trait_item"]:
            self._extract_rust_type(node, classes)
        elif node.type == "use_declaration":
            self._extract_rust_use(node, imports)

    def _extract_rust_function(self, node: ASTNode, symbols: List[SymbolInfo]):
        """Extract Rust function."""
        name_node = self._find_child_by_type(node, "identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        parameters = self._extract_rust_parameters(node)
        return_type = self._extract_rust_return_type(node)
        visibility = self._extract_rust_visibility(node)

        symbol = SymbolInfo(
            name=name,
            type="function",
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            parameters=parameters,
            return_type=return_type,
            visibility=visibility
        )
        symbols.append(symbol)

    def _extract_rust_type(self, node: ASTNode, classes: List[ClassInfo]):
        """Extract Rust struct/enum/trait."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if not name_node:
            return

        name = self._get_node_text(name_node)
        visibility = self._extract_rust_visibility(node)

        # Determine type
        is_interface = node.type == "trait_item"

        class_info = ClassInfo(
            name=name,
            line_start=self._get_line_number(node),
            line_end=self._get_end_line_number(node),
            visibility=visibility,
            is_interface=is_interface
        )
        classes.append(class_info)

    def _extract_rust_use(self, node: ASTNode, imports: List[ImportInfo]):
        """Extract Rust use statement."""
        pass

    def _extract_rust_parameters(self, node: ASTNode) -> List[ParameterInfo]:
        """Extract Rust function parameters."""
        return []

    def _extract_rust_return_type(self, node: ASTNode) -> Optional[str]:
        """Extract Rust return type."""
        return None

    def _extract_rust_visibility(self, node: ASTNode) -> Optional[str]:
        """Extract Rust visibility."""
        vis_node = self._find_child_by_type(node, "visibility_modifier")
        if vis_node:
            return self._get_node_text(vis_node)
        return None


# Global extractor instance
_global_extractor: Optional[SymbolExtractor] = None


def get_symbol_extractor() -> SymbolExtractor:
    """Get the global symbol extractor instance."""
    global _global_extractor
    if _global_extractor is None:
        _global_extractor = SymbolExtractor()
    return _global_extractor
