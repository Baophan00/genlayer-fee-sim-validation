# GenLayer fee simulator — independent validation run

Validation of [`genlayerlabs/genlayer-fee-distribution-simulator`](https://github.com/genlayerlabs/genlayer-fee-distribution-simulator)
at commit `101c31e` (2026-10-14), run on a clean environment on 2026-10-24. No simulator code was
modified: this repository holds the run, the extra sweep script and the results, so the numbers
below can be re-checked with two commands.

## Why

The simulator claims exhaustive invariant coverage of every transaction path up to length 7, and its
fee vectors are the reference data the `genlayer-consensus` `fee_finalization_tests` suites consume.
An independent run answers three questions a consumer of those vectors actually cares about:

1. Does the suite pass from a clean checkout, and does it match what the docs say about it?
2. Do the 24 invariants still hold *outside* the path lengths the shipped invariant runner sweeps?
3. Does the environment install as documented?

## Results

### 1. Suite: 1083 passed, 5 skipped (63s)

```
$ .venv/bin/python -m pytest -q
1083 passed, 5 skipped, 6 warnings in 63.30s (0:01:03)
```

`pytest --collect-only` reports 1088 tests. `docs/TESTING.md` still says **146 tests, ~27 seconds,
484 paths** — the test count and duration are stale (the 484-path figure is still correct, see
below).

### 2. Invariants hold beyond the shipped sweep

The shipped runner
(`tests/fee_distributions/check_invariants/test_invariants_in_round_combinations.py:48`) builds paths
of **length 3-5** — the file even notes "not real max length which would be 19". `validate_beyond_suite.py`
here runs the same pipeline (`path_to_transaction_results` → `label_rounds` → `process_transaction`
→ `check_all_invariants`) over every path of length 3-7 and a 400-path sample of lengths 8 and 9,
checking the invariants at the suite's tolerance (20) **and at tolerance 0**:

```
length=3: generated=4    checked=4   violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=4: generated=29   checked=29  violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=5: generated=34   checked=34  violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=6: generated=167  checked=167 violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=7: generated=250  checked=250 violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=8: generated=983  checked=400 violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
length=9: generated=1732 checked=400 violations(tolerance=0)=0 violations(tolerance=20)=0 pipeline_errors=0
```

Lengths 3-7 sum to **484 paths**, matching the README's "484 paths for length ≤7". Two observations
worth recording:

- The **tolerance=20 slack is not load-bearing** on any of these 484 + 800 runs: every path also
  passes at tolerance 0, so no conservation leak is being hidden by the tolerance at these lengths.
- Lengths 8-9 (983 and 1732 generatable paths) are generated without error and their sampled paths
  satisfy the invariants; the suite's exhaustive claim stops at 7 and nothing above it was checked
  before this run.

### 3. Install: the pinned numpy needs Python ≥ 3.12

`requirements.txt` pins `numpy==2.5.2`. On Python 3.10 and 3.11 `pip install -r requirements.txt`
stops with:

```
ERROR: No matching distribution found for numpy==2.5.2
```

Installing under Python 3.13.7 works with no other change. `docs/TESTING.md` only says "pip install
requirements.txt", without a Python floor, so a contributor on the system Python of macOS or Ubuntu
22.04 hits a dead end at step one.

## Reproduce

```bash
gh repo clone genlayerlabs/genlayer-fee-distribution-simulator
cd genlayer-fee-distribution-simulator
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                      # 1083 passed, 5 skipped
cp /path/to/validate_beyond_suite.py .
.venv/bin/python validate_beyond_suite.py          # the sweep above
```

## Scope

This validates the simulator's own model and invariants. It does **not** verify the Solidity
contracts: parity between model and contracts is enforced by the vector-driven suites in
`genlayer-consensus`, which were not run here. Paths are generated with the default
`TRANSACTION_GRAPH` and the default round-size tables; no fee formula was altered.
