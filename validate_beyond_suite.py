"""Validate the fee simulator's invariants beyond the path lengths its own suite sweeps.

The shipped invariant runner (tests/fee_distributions/check_invariants/
test_invariants_in_round_combinations.py) builds paths of length 3-5 only, while README claims
exhaustive coverage up to length 7. This script closes the gap on the reader's side: it sweeps
lengths 3-7 exhaustively and samples 8-9, running the same pipeline the suite runs
(path_to_transaction_results -> label_rounds -> process_transaction) and checking all 24 invariants
twice, at the suite's tolerance (20) and at tolerance 0.

Usage: python validate_beyond_suite.py [--cap N]
"""
import argparse
import itertools

from src.fee_simulator.core.transaction_processing import process_transaction
from src.fee_simulator.core.round_labeling import label_rounds
from src.fee_simulator.core.path_to_transaction import path_to_transaction_results
from src.fee_simulator.specification.state_machine.path_analysis.path_generator import (
    generate_all_paths,
)
from src.fee_simulator.specification.state_machine.path_analysis.path_types import PathConstraints
from src.fee_simulator.specification.invariants.checker import check_all_invariants
from src.fee_simulator.specification.state_machine.graph import TRANSACTION_GRAPH
from src.fee_simulator.utils import generate_random_eth_address

LEADER_TIMEOUT = 100
VALIDATORS_TIMEOUT = 200

POOL = [generate_random_eth_address() for _ in range(4000)]
SENDER, APPEALANT = POOL[3998], POOL[3999]


def sweep(length: int, cap: int | None) -> tuple[int, int, int]:
    paths = generate_all_paths(
        TRANSACTION_GRAPH,
        PathConstraints(min_length=length, max_length=length, source_node="START", target_node="END"),
    )
    total = len(paths)
    sample = list(itertools.islice(paths, cap)) if cap else paths
    strict_fail, loose_fail, errors = 0, 0, 0

    for path in sample:
        try:
            tx, budget = path_to_transaction_results(
                path=path,
                addresses=POOL,
                sender_address=SENDER,
                appealant_address=APPEALANT,
                leader_timeout=LEADER_TIMEOUT,
                validators_timeout=VALIDATORS_TIMEOUT,
            )
            labels = label_rounds(tx)
            events, _ = process_transaction(addresses=POOL, transaction_results=tx, transaction_budget=budget)
        except Exception:
            errors += 1
            continue

        for tolerance in (0, 20):
            try:
                check_all_invariants(events, budget, tx, labels, tolerance=tolerance)
            except AssertionError:
                if tolerance == 0:
                    strict_fail += 1
                else:
                    loose_fail += 1

    print(
        f"length={length}: generated={total} checked={len(sample)} "
        f"violations(tolerance=0)={strict_fail} violations(tolerance=20)={loose_fail} pipeline_errors={errors}"
    )
    return total, strict_fail, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", type=int, default=400, help="sample size for lengths >= 8 (0 = all)")
    args = parser.parse_args()

    checked_total = 0
    for length in (3, 4, 5, 6, 7):
        total, fails, errors = sweep(length, None)
        checked_total += total
        assert fails == 0 and errors == 0, f"length {length} produced failures"

    for length in (8, 9):
        sweep(length, args.cap or None)

    print(f"\nexhaustive lengths 3-7: {checked_total} paths, no invariant violation, no pipeline error")


if __name__ == "__main__":
    main()
