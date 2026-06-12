#!/usr/bin/env python3
"""Tests for claude_review.py."""

from __future__ import annotations

from claude_review import analyze_diff, confidence, parse_pr_url, render_review


def test_parse_pr_url() -> None:
    assert parse_pr_url("https://github.com/owner/repo/pull/123") == ("owner", "repo", "123")


def test_analyze_diff_detects_tests_and_docs() -> None:
    diff = """\
diff --git a/README.md b/README.md
+++ b/README.md
@@ -1 +1,2 @@
+docs
diff --git a/tests/test_app.py b/tests/test_app.py
+++ b/tests/test_app.py
@@ -0,0 +1,2 @@
+def test_app():
+    assert True
"""
    stats = analyze_diff(diff)
    assert stats.files == ["README.md", "tests/test_app.py"]
    assert stats.additions == 3
    assert stats.hunks == 2
    assert stats.has_tests
    assert stats.has_docs
    assert confidence(stats) == "High"


def test_render_review_has_required_sections() -> None:
    stats = analyze_diff("+++ b/app.py\n@@ -0,0 +1 @@\n+print('hi')\n")
    review = render_review("owner", "repo", "1", stats)
    assert "### Summary" in review
    assert "### Identified Risks" in review
    assert "### Improvement Suggestions" in review
    assert "### Confidence Score:" in review


if __name__ == "__main__":
    test_parse_pr_url()
    test_analyze_diff_detects_tests_and_docs()
    test_render_review_has_required_sections()
    print("claude_review tests passed")
