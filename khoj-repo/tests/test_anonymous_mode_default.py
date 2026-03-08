"""
Tests for anonymous mode default behavior.

This module tests:
1. state.anonymous_mode defaults to True
2. CLI parser returns anonymous_mode=True with no arguments
3. --anonymous-mode flag sets anonymous_mode=True
4. --no-anonymous-mode flag sets anonymous_mode=False
"""

# Standard Modules
import argparse
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from khoj.utils import cli


def create_parser():
    """Helper to create a parser with CLI arguments."""
    parser = argparse.ArgumentParser()
    cli._setup_parser(parser)
    return parser


# Test 1: Default anonymous mode in state module
# ----------------------------------------------------------------------------------------------------
def test_default_anonymous_mode_is_true():
    """Verify that state.anonymous_mode defaults to True.
    
    Note: This test verifies the source code default value. The state module
    imports Django models, so we verify by reading the source file directly
    rather than importing the module (which would require Django setup).
    """
    # Read the state.py file to verify the default value
    state_file = Path(__file__).parent.parent / "src" / "khoj" / "utils" / "state.py"
    content = state_file.read_text()
    
    # Verify the default value is set to True
    assert "anonymous_mode: bool = True" in content, \
        "state.anonymous_mode should default to True"


# Test 2: CLI default anonymous mode
# ----------------------------------------------------------------------------------------------------
def test_cli_default_anonymous_mode():
    """Verify CLI parser returns anonymous_mode=True with no arguments."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args([])

    # Assert
    assert args.anonymous_mode is True, \
        f"Expected anonymous_mode=True, got {args.anonymous_mode}"


# Test 3: CLI explicit anonymous mode flag
# ----------------------------------------------------------------------------------------------------
def test_cli_explicit_anonymous_mode():
    """Verify --anonymous-mode flag sets anonymous_mode=True."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--anonymous-mode"])

    # Assert
    assert args.anonymous_mode is True, \
        f"Expected anonymous_mode=True, got {args.anonymous_mode}"


# Test 4: CLI no anonymous mode flag
# ----------------------------------------------------------------------------------------------------
def test_cli_no_anonymous_mode():
    """Verify --no-anonymous-mode flag sets anonymous_mode=False."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--no-anonymous-mode"])

    # Assert
    assert args.anonymous_mode is False, \
        f"Expected anonymous_mode=False, got {args.anonymous_mode}"
