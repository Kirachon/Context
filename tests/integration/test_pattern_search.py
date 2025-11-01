import pytest

from src.search.pattern_search import PatternSearchService


@pytest.fixture(scope="module")
def service():
    return PatternSearchService()


def test_python_decorator_and_repository(service):
    code = """
@cache
def compute(x):
    return x * 2

class UserRepository:
    def save(self, user):
        self.db.add(user)
        return user
"""
    res = service.search_code(
        "python", code, patterns=["decorator_patterns", "repository_crud"]
    )
    names = {r.pattern_name for r in res}
    assert "decorator_patterns" in names
    assert "repository_crud" in names


def test_javascript_factory_and_async(service):
    code = """
class UserFactory {
  create(type) {
    return new AdminUser();
  }
}

async function fetchUser() {
  try {
    await fetch('/api/user');
  } catch (e) {}
}
"""
    res = service.search_code(
        "javascript", code, patterns=["factory_classes", "async_functions"]
    )
    names = {r.pattern_name for r in res}
    assert "factory_classes" in names
    assert "async_functions" in names


def test_typescript_interface_impl(service):
    code = """
interface IRepo {}
class Repo implements IRepo {}
"""
    res = service.search_code(
        "typescript", code, patterns=["interface_implementations"]
    )
    assert any(r.pattern_name == "interface_implementations" for r in res)


def test_go_error_handling(service):
    code = """
func read() (string, error) {
  if err != nil {
    return "", err
  }
  return "ok", nil
}
"""
    res = service.search_code("go", code, patterns=["error_handling"])
    assert any(r.pattern_name == "error_handling" for r in res)


def test_rust_result_patterns(service):
    code = """
fn run() -> Result<i32, E> { Ok(1) }
"""
    res = service.search_code("rust", code, patterns=["result_patterns"])
    assert any(r.pattern_name == "result_patterns" for r in res)
