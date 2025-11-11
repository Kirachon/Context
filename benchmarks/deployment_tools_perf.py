import time
import tracemalloc
import os
import sys

# Ensure project root on sys.path
sys.path.insert(0, os.path.abspath("."))

# Use a minimal fake to avoid importing FastMCP during benchmark
class FakeMCP:
    def tool(self):
        def decorator(fn):
            return fn
        return decorator


def run_benchmark(iterations: int = 200) -> None:
    from src.mcp_server.tools.deployment_integrations import register_deployment_tools

    # Warm-up
    register_deployment_tools(FakeMCP())

    tracemalloc.start()
    t0 = time.perf_counter()
    for _ in range(iterations):
        register_deployment_tools(FakeMCP())
    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    per_reg_us = (t1 - t0) * 1e6 / iterations
    print("Deployment Tools Registration Performance\n")
    print(f"iterations: {iterations}")
    print(f"avg/reg:    {per_reg_us:.1f} µs")
    print(f"peak mem:   {peak/1024:.1f} KB")


if __name__ == "__main__":
    run_benchmark()

