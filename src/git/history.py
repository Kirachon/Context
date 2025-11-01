"""
Git History Integration & Change Analysis (Story 3-5)

Provides lightweight utilities to read git history and analyze changes.
"""

import logging
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def run_git_command(args: List[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return stdout"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception as e:
        logger.warning(f"git command failed: git {' '.join(args)} -> {e}")
        return ""


def get_recent_commits(n: int = 10, cwd: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get last n commits with basic info"""
    fmt = "%H|%an|%ad|%s"
    out = run_git_command(
        ["log", f"-n{n}", f"--pretty=format:{fmt}", "--date=iso"], cwd
    )
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                }
            )
    return commits


def get_changed_files(ref: str = "HEAD", cwd: Optional[str] = None) -> List[str]:
    """List files changed in a commit or range"""
    out = run_git_command(["diff", "--name-only", f"{ref}~1..{ref}"], cwd)
    return [line.strip() for line in out.splitlines() if line.strip()]


def summarize_changes(cwd: Optional[str] = None) -> Dict[str, Any]:
    """High-level change summary for the working tree"""
    status = run_git_command(["status", "--porcelain"], cwd)
    summary = {
        "modified": 0,
        "added": 0,
        "deleted": 0,
        "renamed": 0,
    }
    for line in status.splitlines():
        code = line[:2].strip()
        if code == "M":
            summary["modified"] += 1
        elif code == "A":
            summary["added"] += 1
        elif code == "D":
            summary["deleted"] += 1
        elif code.startswith("R"):
            summary["renamed"] += 1
    return summary
