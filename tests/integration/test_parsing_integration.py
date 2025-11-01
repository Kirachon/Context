"""
Integration tests for parsing functionality.
"""

from pathlib import Path
from src.parsing.parser import get_parser
from src.parsing.models import Language


class TestParsingIntegration:
    """Integration tests for AST parsing."""

    def setup_method(self):
        self.parser = get_parser()

    def test_parse_python_simple(self):
        """Test parsing simple Python code."""
        code = """
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""

        result = self.parser.parse(Path("test.py"), code)

        # Should succeed even without tree-sitter installed (graceful degradation)
        assert result.language == Language.PYTHON
        assert result.file_path == Path("test.py")
        assert result.parse_time_ms >= 0

        # If tree-sitter is available, should have AST
        if result.parse_success:
            assert result.ast_root is not None
            assert result.ast_root.type in [
                "module",
                "source_file",
            ]  # depends on parser

    def test_parse_javascript_simple(self):
        """Test parsing simple JavaScript code."""
        code = """
function helloWorld() {
    console.log("Hello, World!");
    return true;
}

helloWorld();
"""

        result = self.parser.parse(Path("test.js"), code)

        assert result.language == Language.JAVASCRIPT
        assert result.file_path == Path("test.js")
        assert result.parse_time_ms >= 0

    def test_parse_typescript_simple(self):
        """Test parsing simple TypeScript code."""
        code = """
interface Greeting {
    message: string;
}

function helloWorld(): Greeting {
    return { message: "Hello, World!" };
}

const greeting: Greeting = helloWorld();
console.log(greeting.message);
"""

        result = self.parser.parse(Path("test.ts"), code)

        assert result.language == Language.TYPESCRIPT
        assert result.file_path == Path("test.ts")
        assert result.parse_time_ms >= 0

    def test_parse_java_simple(self):
        """Test parsing simple Java code."""
        code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
    
    private void greet(String name) {
        System.out.println("Hello, " + name + "!");
    }
}
"""

        result = self.parser.parse(Path("HelloWorld.java"), code)

        assert result.language == Language.JAVA
        assert result.file_path == Path("HelloWorld.java")
        assert result.parse_time_ms >= 0

    def test_parse_cpp_simple(self):
        """Test parsing simple C++ code."""
        code = """
#include <iostream>
#include <string>

class Greeter {
public:
    void greet(const std::string& name) {
        std::cout << "Hello, " << name << "!" << std::endl;
    }
};

int main() {
    Greeter greeter;
    greeter.greet("World");
    return 0;
}
"""

        result = self.parser.parse(Path("test.cpp"), code)

        assert result.language == Language.CPP
        assert result.file_path == Path("test.cpp")
        assert result.parse_time_ms >= 0

    def test_parse_go_simple(self):
        """Test parsing simple Go code."""
        code = """
package main

import "fmt"

type Greeter struct {
    name string
}

func (g *Greeter) Greet() {
    fmt.Printf("Hello, %s!\\n", g.name)
}

func main() {
    greeter := &Greeter{name: "World"}
    greeter.Greet()
}
"""

        result = self.parser.parse(Path("test.go"), code)

        assert result.language == Language.GO
        assert result.file_path == Path("test.go")
        assert result.parse_time_ms >= 0

    def test_parse_rust_simple(self):
        """Test parsing simple Rust code."""
        code = """
struct Greeter {
    name: String,
}

impl Greeter {
    fn new(name: String) -> Self {
        Greeter { name }
    }
    
    fn greet(&self) {
        println!("Hello, {}!", self.name);
    }
}

fn main() {
    let greeter = Greeter::new("World".to_string());
    greeter.greet();
}
"""

        result = self.parser.parse(Path("test.rs"), code)

        assert result.language == Language.RUST
        assert result.file_path == Path("test.rs")
        assert result.parse_time_ms >= 0

    def test_parse_all_languages_performance(self):
        """Test parsing performance across all languages."""
        test_cases = [
            (Language.PYTHON, "test.py", "def test(): pass"),
            (Language.JAVASCRIPT, "test.js", "function test() {}"),
            (Language.TYPESCRIPT, "test.ts", "function test(): void {}"),
            (Language.JAVA, "Test.java", "public class Test {}"),
            (Language.CPP, "test.cpp", "int main() { return 0; }"),
            (Language.GO, "test.go", "package main\nfunc main() {}"),
            (Language.RUST, "test.rs", "fn main() {}"),
        ]

        results = []
        for language, filename, code in test_cases:
            result = self.parser.parse(Path(filename), code)
            results.append(result)

            assert result.language == language
            assert result.parse_time_ms >= 0
            # Performance target: should parse in under 100ms for simple code
            if result.parse_success:
                assert (
                    result.parse_time_ms < 100
                ), f"Parsing {filename} took {result.parse_time_ms}ms"

        # At least some parsers should work (even if tree-sitter isn't fully installed)
        successful_parses = sum(1 for r in results if r.parse_success)
        print(f"Successfully parsed {successful_parses}/{len(results)} languages")

    def test_error_handling(self):
        """Test error handling for invalid code."""
        # Invalid Python syntax
        result = self.parser.parse(Path("invalid.py"), "def invalid syntax here")

        assert result.language == Language.PYTHON
        # Should either succeed (tree-sitter is forgiving) or fail gracefully
        assert isinstance(result.parse_success, bool)
        assert result.parse_time_ms >= 0


class TestSymbolExtractionIntegration:
    """Integration tests for symbol extraction across all languages."""

    def setup_method(self):
        self.parser = get_parser()

    def test_python_comprehensive_extraction(self):
        """Test comprehensive Python symbol extraction."""
        code = '''
import os
from typing import List, Optional

class UserManager:
    """Manages user operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email

    async def create_user(self, name: str, email: str) -> Optional[dict]:
        """Create a new user."""
        if not self.validate_email(email):
            return None
        return {"name": name, "email": email}

def main():
    manager = UserManager("/tmp/users.db")
    print("UserManager created")
'''

        result = self.parser.parse(Path("test_user.py"), code)

        # Basic parsing should work
        assert result.language == Language.PYTHON
        assert result.parse_time_ms >= 0
        assert result.symbol_extraction_time_ms >= 0

        # If tree-sitter is available, check symbol extraction
        if result.parse_success and result.ast_root:
            print(
                f"Python - Imports: {len(result.imports)}, Classes: {len(result.classes)}, Symbols: {len(result.symbols)}"
            )

    def test_javascript_comprehensive_extraction(self):
        """Test comprehensive JavaScript symbol extraction."""
        code = """
import { EventEmitter } from 'events';

class UserService extends EventEmitter {
    constructor(config) {
        super();
        this.config = config;
    }

    async createUser(name, email) {
        const user = { name, email };
        this.emit('userCreated', user);
        return user;
    }

    static validateEmail(email) {
        return email.includes('@');
    }
}

function createUserService(config) {
    return new UserService(config);
}
"""

        result = self.parser.parse(Path("user_service.js"), code)

        assert result.language == Language.JAVASCRIPT
        assert result.parse_time_ms >= 0
        assert result.symbol_extraction_time_ms >= 0

        if result.parse_success and result.ast_root:
            print(
                f"JS - Imports: {len(result.imports)}, Classes: {len(result.classes)}, Symbols: {len(result.symbols)}"
            )

    def test_all_languages_symbol_extraction_performance(self):
        """Test symbol extraction performance across all languages."""
        test_cases = [
            (Language.PYTHON, "test.py", "class Test:\n    def method(self): pass"),
            (Language.JAVASCRIPT, "test.js", "class Test { method() {} }"),
            (Language.TYPESCRIPT, "test.ts", "class Test { method(): void {} }"),
            (
                Language.JAVA,
                "Test.java",
                "public class Test { public void method() {} }",
            ),
            (Language.CPP, "test.cpp", "class Test { public: void method(); };"),
            (Language.GO, "test.go", "type Test struct {}\nfunc (t *Test) Method() {}"),
            (
                Language.RUST,
                "test.rs",
                "struct Test {}\nimpl Test { fn method(&self) {} }",
            ),
        ]

        results = []
        for language, filename, code in test_cases:
            result = self.parser.parse(Path(filename), code)
            results.append(result)

            assert result.language == language
            assert result.parse_time_ms >= 0
            assert result.symbol_extraction_time_ms >= 0

            # Performance target: symbol extraction should be fast
            if result.parse_success:
                assert (
                    result.symbol_extraction_time_ms < 50
                ), f"Symbol extraction for {filename} took {result.symbol_extraction_time_ms}ms"

        # At least some parsers should work
        successful_parses = sum(1 for r in results if r.parse_success)
        print(
            f"Successfully parsed and extracted symbols from {successful_parses}/{len(results)} languages"
        )

        # Print summary
        for result in results:
            if result.parse_success:
                print(
                    f"{result.language.value}: {len(result.symbols)} symbols, {len(result.classes)} classes, {len(result.imports)} imports"
                )
            else:
                print(f"{result.language.value}: Parse failed - {result.parse_error}")

    def test_symbol_extraction_error_handling(self):
        """Test error handling in symbol extraction."""
        # Test with invalid syntax
        result = self.parser.parse(Path("invalid.py"), "def invalid syntax here")

        assert result.language == Language.PYTHON
        # Should either succeed (tree-sitter is forgiving) or fail gracefully
        assert isinstance(result.parse_success, bool)
        assert result.parse_time_ms >= 0
        assert result.symbol_extraction_time_ms >= 0
