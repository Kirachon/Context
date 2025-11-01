"""
Tree-sitter Smoke Tests

Tests that all 7 supported languages can be parsed successfully with non-empty ASTs
and symbol extraction working correctly.
"""

from pathlib import Path
from src.parsing.parser import get_parser
from src.parsing.models import Language


class TestTreeSitterSmoke:
    """Smoke tests for Tree-sitter parsing across all supported languages."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = get_parser()

    def test_python_smoke(self):
        """Test Python parsing with function and class."""
        code = '''
def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
'''
        result = self.parser.parse(Path("test.py"), code)

        # Assert parsing succeeded
        assert result.parse_success, "Python parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.PYTHON

        # Assert symbols were extracted
        assert (
            len(result.symbols) >= 2
        ), "Should extract at least 2 symbols (function + method)"
        assert len(result.classes) >= 1, "Should extract at least 1 class"

        # Check specific symbols
        symbol_names = [s.name for s in result.symbols]
        assert "hello" in symbol_names, "Should find 'hello' function"
        assert "add" in symbol_names, "Should find 'add' method"

        class_names = [c.name for c in result.classes]
        assert "Calculator" in class_names, "Should find 'Calculator' class"

    def test_javascript_smoke(self):
        """Test JavaScript parsing with function and class."""
        code = """
function greet(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }
    
    static multiply(x, y) {
        return x * y;
    }
}
"""
        result = self.parser.parse(Path("test.js"), code)

        # Assert parsing succeeded
        assert result.parse_success, "JavaScript parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.JAVASCRIPT

        # Assert symbols were extracted (at least some)
        assert len(result.symbols) >= 1, "Should extract at least 1 symbol"
        assert len(result.classes) >= 1, "Should extract at least 1 class"

    def test_typescript_smoke(self):
        """Test TypeScript parsing with typed function and interface."""
        code = """
interface User {
    name: string;
    age: number;
}

function createUser(name: string, age: number): User {
    return { name, age };
}

class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
}
"""
        result = self.parser.parse(Path("test.ts"), code)

        # Assert parsing succeeded
        assert result.parse_success, "TypeScript parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.TYPESCRIPT

        # Assert symbols were extracted (at least some)
        assert len(result.symbols) >= 1, "Should extract at least 1 symbol"
        assert len(result.classes) >= 1, "Should extract at least 1 class"

    def test_java_smoke(self):
        """Test Java parsing with class and methods."""
        code = """
public class Calculator {
    private int value;
    
    public Calculator(int initialValue) {
        this.value = initialValue;
    }
    
    public int add(int number) {
        return this.value + number;
    }
    
    public static void main(String[] args) {
        Calculator calc = new Calculator(10);
        System.out.println(calc.add(5));
    }
}
"""
        result = self.parser.parse(Path("Calculator.java"), code)

        # Assert parsing succeeded
        assert result.parse_success, "Java parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.JAVA

        # Assert symbols were extracted
        assert len(result.symbols) >= 2, "Should extract at least 2 symbols"
        assert len(result.classes) >= 1, "Should extract at least 1 class"

    def test_cpp_smoke(self):
        """Test C++ parsing with class and methods."""
        code = """
#include <iostream>
#include <string>

class Calculator {
private:
    int value;

public:
    Calculator(int initialValue) : value(initialValue) {}
    
    int add(int number) {
        return value + number;
    }
    
    void display() const {
        std::cout << "Value: " << value << std::endl;
    }
};

int main() {
    Calculator calc(10);
    calc.display();
    return 0;
}
"""
        result = self.parser.parse(Path("calculator.cpp"), code)

        # Assert parsing succeeded
        assert result.parse_success, "C++ parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.CPP

        # Assert symbols were extracted
        assert len(result.symbols) >= 2, "Should extract at least 2 symbols"
        assert len(result.classes) >= 1, "Should extract at least 1 class"

    def test_go_smoke(self):
        """Test Go parsing with struct and methods."""
        code = """
package main

import "fmt"

type Calculator struct {
    value int
}

func NewCalculator(initialValue int) *Calculator {
    return &Calculator{value: initialValue}
}

func (c *Calculator) Add(number int) int {
    return c.value + number
}

func (c *Calculator) Display() {
    fmt.Printf("Value: %d\\n", c.value)
}

func main() {
    calc := NewCalculator(10)
    result := calc.Add(5)
    fmt.Println(result)
}
"""
        result = self.parser.parse(Path("calculator.go"), code)

        # Assert parsing succeeded
        assert result.parse_success, "Go parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.GO

        # Assert symbols were extracted
        assert len(result.symbols) >= 2, "Should extract at least 2 symbols"

    def test_rust_smoke(self):
        """Test Rust parsing with struct and impl block."""
        code = """
struct Calculator {
    value: i32,
}

impl Calculator {
    fn new(initial_value: i32) -> Self {
        Calculator { value: initial_value }
    }
    
    fn add(&self, number: i32) -> i32 {
        self.value + number
    }
    
    fn display(&self) {
        println!("Value: {}", self.value);
    }
}

fn main() {
    let calc = Calculator::new(10);
    let result = calc.add(5);
    println!("{}", result);
}
"""
        result = self.parser.parse(Path("calculator.rs"), code)

        # Assert parsing succeeded
        assert result.parse_success, "Rust parsing should succeed"
        assert result.ast_root is not None, "AST root should not be None"
        assert result.language == Language.RUST

        # Assert symbols were extracted
        assert len(result.symbols) >= 2, "Should extract at least 2 symbols"

    def test_all_languages_available(self):
        """Test that all 7 languages are available for loading."""
        from src.parsing.ts_loader import get_available_languages, is_language_available

        expected_languages = [
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "go",
            "rust",
        ]
        available_languages = get_available_languages()

        assert set(expected_languages) == set(
            available_languages
        ), "All 7 languages should be available"

        # Test each language individually
        for lang in expected_languages:
            assert is_language_available(lang), f"Language {lang} should be available"

    def test_language_detection(self):
        """Test language detection from file extensions."""
        from src.parsing.parser import detect_language

        test_cases = [
            ("test.py", Language.PYTHON),
            ("app.js", Language.JAVASCRIPT),
            ("component.jsx", Language.JAVASCRIPT),
            ("service.ts", Language.TYPESCRIPT),
            ("component.tsx", Language.TYPESCRIPT),
            ("Main.java", Language.JAVA),
            ("calculator.cpp", Language.CPP),
            ("header.hpp", Language.CPP),
            ("main.go", Language.GO),
            ("lib.rs", Language.RUST),
        ]

        for filename, expected_lang in test_cases:
            detected = detect_language(Path(filename))
            assert (
                detected == expected_lang
            ), f"Should detect {expected_lang.value} for {filename}"
