"""
Setup configuration for Context CLI
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    req_path = Path(__file__).parent / "requirements" / filename
    if req_path.exists():
        with open(req_path, "r") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    return []


setup(
    name="context",
    version="2.0.0",
    description="Multi-project workspace management with intelligent indexing and search",
    author="Context Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=read_requirements("base.txt"),
    extras_require={
        "dev": read_requirements("dev.txt"),
        "analysis": read_requirements("analysis.txt"),
        "security": read_requirements("security.txt"),
        "profiling": read_requirements("profiling.txt"),
        "integrations": read_requirements("integrations.txt"),
    },
    entry_points={
        "console_scripts": [
            "context=src.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
