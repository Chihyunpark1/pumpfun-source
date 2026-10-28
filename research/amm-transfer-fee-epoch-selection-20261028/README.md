# PumpSwap transfer-fee epoch schedule selection, pinned at runtime

## Problem

A Token-2022 mint can carry two transfer-fee schedules, older and newer.
`from_mint` selects the schedule active at the current epoch with
`if epoch >= newer.epoch { newer } else { older }`. The rule's two edge
behaviors are easy to get wrong: the boundary is inclusive (the newer
schedule already applies at exactly `newer.epoch`), and an inverted pair
(`older.epoch > newer.epoch`) applies the future-dated older schedule
while the clock is before the newer epoch. Nothing in the decoder
validates the epoch ordering.

## Cases

Eight fresh-VM triples (original / #424 control / #427 candidate), 24
signed executions, built on the repository's own liquidity differential
harness (`scripts/pump_amm_liquidity_differential.py`) with a custom
fee-entry override carrying distinct older/newer epochs and basis
points. Each case burns `supply // 100` LP in a withdraw and reads the
fee actually withheld from the vault-to-user quote transfer, so the
selected schedule is observable in the after balances. The clock slot is
100; only the epoch varies. `producer.py` reproduces every receipt from
the repository files.

| Case | Older (epoch, bps) | Newer (epoch, bps) | Clock epoch | Selected |
| --- | ---: | ---: | ---: | ---: |
| epoch-0-before-newer | 0, 100 | 10, 200 | 0 | older (100) |
| epoch-9-before-newer | 0, 100 | 10, 200 | 9 | older (100) |
| epoch-10-at-newer | 0, 100 | 10, 200 | 10 | newer (200) |
| inverted-epoch-0 | 100, 100 | 50, 200 | 0 | older (100) |
| inverted-epoch-49 | 100, 100 | 50, 200 | 49 | older (100) |
| inverted-epoch-50 | 100, 100 | 50, 200 | 50 | newer (200) |
| tie-epoch-10 | 10, 100 | 10, 200 | 10 | newer (200) |
| tie-epoch-9 | 10, 100 | 10, 200 | 9 | older (100) |

`verify.py` rechecks every receipt independently: signature validity,
the clock epoch, the older/newer epoch and bps pairs in the mint's
before snapshot, the withheld fee recomputed from the vault outflow
minus the user inflow against `ceil(sent * bps / 10000)`, and agreement
of the received amount across all three images in every case.

## Result

- **The boundary is inclusive:** at exactly `newer.epoch` the newer
  schedule already applies, and at one epoch before it the older
  schedule still applies.
- **Inverted pairs apply the future-dated schedule:** with
  `older.epoch = 100` and `newer.epoch = 50`, a clock at epoch 0 or 49
  still takes the older (epoch-100) schedule; only at epoch 50 does the
  newer schedule take over.
- **All three images select identically** in every case: the rule is
  unchanged across the #424 and #427 artifacts.

## Limits

- No source change, no build, no whole-program identity claim. The images
  are the merged #424 and #427 artifacts; only the new runtime cases are
  added.
- The inverted and tied epoch pairs are synthetic boundary conditions,
  not mainnet mint states: they isolate the selection rule, the same way
  the bps-overflow packets isolated theirs. No live transaction was
  submitted. All executions are offline LiteSVM replays with normally
  signed transactions.
