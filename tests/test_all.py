from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure project root is importable when running this file directly:
# python scrape_deepseek_project/tests/test_all.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_all_tests() -> int:
    """
    Discover and run all tests under the current tests directory.
    Return process exit code:
    - 0: all passed
    - 1: has failures/errors
    """
    test_dir = Path(__file__).resolve().parent
    module_names = [
        "tests.test_deepseek_module",
        "tests.test_sulwhasoo_scrapling_module",
        "tests.test_sulwhasoo_product_list_scrapling_module",
        "tests.test_thesaemcosmetic_scrapling_module",
        "tests.test_thesaemcosmetic_product_list_scrapling_module",
    ]
    suite = unittest.TestSuite()
    for module_name in module_names:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module_name))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n=== Test Summary ===")
    print(f"Ran: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Successful: {result.wasSuccessful()}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run_all_tests())
