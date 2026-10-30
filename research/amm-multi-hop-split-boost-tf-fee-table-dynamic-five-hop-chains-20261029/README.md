# Split x boost x tf dynamic fee-table transitions at TRUE 5 hops

3rd-run packet #149. This packet extends the #95 dynamic fee-table
findings (fee-table edits mid-chain, tier switches during trades,
dynamic fee changes across legs) from the TRUE 3-hop chain to the
TRUE 5-hop split x boost x tf chain: `three_amm + g4 + g5`, final
output U5. Route verified in the builder (`build_route` appends the
g4 and g5 hop groups to `three_amm`); the name, README and title
all say 5-hop because the route really is 5 hops (#61 was 4 hops
despite its 3-hop name; that mistake is not repeated here). The
stable route in this packet is also true 5-hop (main -> P2S -> P3S
-> P4 -> P5, final output U5, per the #147 fix to `build_route_stable`).

## Problem

At depth 3, #95 pinned that the fee table is read live: a patch
between two trades reprices the next trade immediately, and the
change carries into sweep/collect/boost/claim legs. At depth 5 the
open questions were: does a mid-chain edit still reprice the next
5-hop leg immediately, do later buys keep riding the anchor decay
ladder or does each edit compound, does the tier-count failure
mode change with depth, does the stable-route count ladder hold
with two more hops, and does the #146 failing-buy panic survive
under an edited table? This packet measures all of that on the
split chain (quote mint carries a 100 bps transfer-fee config by
default; buyback routes through the TOKEN22 ATA).

## Method

Fee-table patches in this packet are direct account-data writes
applied between legs, with no transaction of their own, so they
leave no receipt -- exactly the #95 method. A patch dict rides in
step[2] and is applied to the fee-table account before that step
runs; a case-level `fee_patch` applies before the first step.
`tiers_rebuild` rewrites the table encoding from scratch (flat
fees, count, tiers, then stable count 0 and zero padding); because
that encoding sets stable count 0, no stable legs run under a
rebuilt table in this packet.

## Cases

46 cases, 131 steps, 393 receipts, 40 parts (39x10 + 3). Anchors:
5-hop buy tail 5,207,955,235,891 (buyback 4,515,471), 5-hop sell net
178,541 (buyback 837), second-buy ladder tail 4,918,089,082,874,
third-buy ladder tail 4,651,768,149,125, fourth-buy ladder tail
4,406,509,597,797. Families:

- **A, tier walks (10 cases):** anchors, tier-1 threshold 0 live
  and from setup, tier-0 lp walk, tier-1 threshold crossing at
  182,353,153,971, tier count 1 / 0 (buy and sell), full tiers
  rebuild (1-tier then 2-tier).
- **B, flat-fee edits (4 cases):** flat inert, flat live under
  exotic-zero (buy and sell), flat-then-tier ordering.
- **C, exotic walks (4 cases):** exotic buy walk, exotic sell
  walk, exotic-zero sell, exotic buy then boost.
- **D, stable-tier walks (6 cases):** stable tier-24 creator 99,
  stable tier-0 inert, stable count 0 / 1, stable sell walk,
  stable tier-24 threshold walk.
- **E, downstream legs (6 cases):** tier-1 sweep/collect, tier-1
  boost, tier-1 token claim, tier-1 cashback claim, tier-1
  deposit/withdraw, exotic sweep/collect.
- **F, slippage under edited tables (4 cases):** failing buy
  under tier 1, failing buy under exotic-zero, failing buy then
  tier-1 buy, failing sell under tier 1.
- **G, combined walks (3 cases):** tier + exotic + flat + restore
  buy walk, tier + exotic + restore sell walk, tier-0 sell walk.
- **H, mixed routes (4 cases):** standard/stable interleaves,
  stable count 0 with a standard buy in between, exotic-zero
  across both routes, tier-1 across both routes.
- **T, transfer-fee variants (5 cases):** tier 1 at tf0 and
  tf5000, exotic at tf5000, stable tier-24 at tf5000, tier
  count 1 at tf5000.

## Result

All cases agree across the original, control and candidate images
(0 divergent cases). `verify.py` re-checks every receipt
independently (signatures, deltas, withheld, event fields, error
codes, rollback, 3-image agreement).

### The table is read live, and most edits stop mattering after the first buy

- Tier-1 threshold 0 from setup prices the first buy at
  5,252,440,110,816 (the #134 tier-1 tail, exact). The same edit
  mid-chain prices the second buy at 4,960,132,739,427, and
  restoring the threshold reprices the third buy at
  4,649,522,527,349.
- Tier-1 threshold planted at 182,353,153,971: the second buy
  already prices as tier 1 (4,960,132,739,427, identical to the
  threshold-0 second buy) -- the crossing happens on the second
  buy at depth 5, same as at depth 3.
- The anchor decay ladder absorbs most edits: the second buy lands
  exactly on 4,918,089,082,874 after a tier-0 lp edit, after a
  stable tier-24 creator-99 edit, after a stable tier-24
  threshold edit, and after an exotic-zero edit on the standard
  route; the third buy lands exactly on 4,651,768,149,125 in the
  same cases. Only edits that change the tier the later buy
  selects (tier-1 threshold 0) or the terminal-hop price
  (exotic) move later buys off the ladder. The mechanism behind
  the ladder convergence is not separately pinned; the values
  are reported as measured.
- Tier-0 lp edit (2 -> 20) is inert on the second buy (ladder
  tail exactly) and moves the second sell by only -2 (178,539,
  the moved-pool drift): the second trade already selects tier 1,
  not tier 0.

### Tier count: count 1 and count 0, plus a new sell-side code

- Tier count 25 -> 1 fails 3003 (Borsh) with 0 events on all
  images -- the #95 count-1 failure, confirmed at depth 5 -- and
  the same failure holds at tf5000. Restoring the count restores
  the anchor buy exactly.
- Tier count 25 -> 0 fails 6082 with 0 events, twice in a row
  (the table stays broken until restored); restoring the count
  restores the anchor buy exactly.
- NEW: a count-0 sell fails 6023 with 0 events, not 6082 -- the
  buy and sell paths reject an empty tier table with different
  codes. The count-0 sell restores to the anchor sell exactly
  (178,541).
- A single-tier tiers_rebuild prices the next buy at
  4,960,132,739,428 -- exactly the tier-1 live buy + 1 (the #134
  rebuild artifact at depth 5, caused by the rebuild encoding
  zeroing the exotic area so the terminal hop falls back to
  flat). A two-tier rebuild prices the following buy at
  4,689,289,959,778.

### Flat and exotic: buy/sell asymmetries

- Flat fees are inert on the canonical buy route while exotic is
  nonzero (flat 100 buy = anchor). With exotic zeroed, the first
  buy falls back to flat at anchor + 1 (5,207,955,235,892, the
  #95/#134 fallback) while later buys land exactly on the
  ladder -- the +1 shows only on the first buy, as at depth 3.
- On the sell side the picture differs: exotic zero does NOT move
  the first sell (178,541, anchor exactly), but flat 100 under
  exotic-zero moves the second sell to 177,196 (-1,345). Flat
  fallback applies to sells where it barely shows on buys.
- Exotic walks move the terminal hop only: exotic (100,0,0)
  second buy 4,881,747,836,435, (0,0,100) third buy
  4,617,544,602,834, restore 4,407,008,745,470. Exotic
  (50,10,777) sell pays 164,184 (buyback 770) vs the 178,541
  anchor; restoring exotic reprices the next sell at 178,537
  (moved-pool drift -4).
- Tier 1 RAISES sell payouts: second sell under tier 1 pays
  180,124 after an anchor sell, and a first sell under tier 1
  on fresh pools pays 180,126; at tf5000 the tier-1 sell pays
  93,725 vs the 90,172 tf5000 anchor sell. Exotic at tf5000
  lowers the sell to 85,376.

### Stable-route count ladder holds exactly at depth 5

- Stable count 0 fails 6082 with exactly 2 ghost events (the main
  hop and the first stable hop emit; the second stable hop
  fails on the empty stable table) -- the #95/#135 ladder,
  exact at depth 5. Stable count 1 fails 6024 with exactly 1
  ghost event (the main hop only) -- the #81 misparse
  rejection, exact at depth 5.
- The standard route under stable count 0 pays the misparse tail
  5,219,868,625,118 (the #134 value, exact): the standard route
  does not fail on stable count 0, it reprices through the
  misparsed slot. The mixed case pins this cleanly: stable buy
  6082, standard buy 5,219,868,625,118, stable buy restored
  5,021,861,930,274.
- Stable tier-24 edits leave the second stable buy exactly on the
  anchor decay ladder (4,918,089,082,874) whether the edit is
  creator 99 or threshold 1,007,000,000,000,000: the second
  stable buy does not reach tier 24 at depth 5. Stable sell
  under creator 99 pays 178,539 (drift -2 only).
- Tier-1 and exotic-zero edits cross routes: a standard buy under
  exotic-zero lands on the ladder (4,918,089,082,874) and the
  following stable buy under exotic-zero pays 4,847,727,372,003;
  a tier-1 standard buy (4,960,132,739,427) is followed by a
  stable buy at 4,887,692,704,022 under the still-active tier-1
  edit.

### Downstream legs under edited tables

- Tier-1 buy shrinks the protocol sweep to 249,865 (anchor
  4,563,570, the #95 value exact) while the creator sweep
  (123,394) and collect (122,160 gross, 120,938 net) are
  unchanged, and the next buy (4,957,670,972,204 after a
  tier-1 first buy) equals the no-sweep tier-1 second buy.
- Exotic buy leaves the protocol sweep at the anchor 4,563,570
  (exotic moves the terminal hop, not the hop-1 protocol
  bucket); creator sweep and collect are unchanged.
- Token claim after a tier-1 buy pays the full 3,334,551 gross
  (net 3,301,205 at 100 bps) and cashback claim after a tier-1
  buy pays 5,475: tier edits do not move claims. Deposit
  (quote 29,312,410) and withdraw (quote 29,312,409) under tier 1;
  a deposit/withdraw round trip
  leaves the next tier-1 buy 41 below the direct tier-1 buy
  (5,252,440,110,775 vs 5,252,440,110,816).
- Boost after a tier-1 buy (patched 10^9 window) burns
  5,254,483,001,415; boost after an exotic buy (patched 10^9
  window) burns 5,255,205,915,165, exactly the buy-first boost
  value -- the exotic buy leaves the boost window where a plain
  buy leaves it, while the tier-1 buy does not.
- The #146 failing-buy panic is table-independent: failing buys
  under tier-1 and exotic-zero tables still panic with
  ProgramFailedToComplete after all 5 hop events, and the next
  buy pays the table's anchor (tier-1: 5,252,440,110,816;
  exotic-zero: 5,207,955,235,892). Failing sells stay clean
  6004 with all 5 hop events under tier 1.

### Transfer-fee variants

- Tier-1 tf0 buy 5,303,948,604,604, tier-1 tf5000 buy
  2,691,196,006,460 (the #134 tf5000
  tier-1 tail, exact), exotic tf5000 buy 2,470,928,850,703 (the
  #134 tf5000 exotic tail, exact), stable tf5000 buy
  2,668,075,748,732 (S24_99 does not move the first stable buy),
  count-1 tf5000 buy fails 3003. Tier-1 tf5000 sell 93,725,
  exotic tf5000 sell 85,376, stable tf5000 sell 92,876.

## Limits

- All amounts are measured on this fixture (seeded pools,
  10^12/10^12 vaults, tf100 default where noted); other pool
  states will give different absolute tails, but the codes
  (3003/6082/6023/6024), the ghost-event ladders, and the
  first-buy-vs-later-buy pattern are structural.
- Fee-table patches are direct account-data writes, not program
  instructions; no claim is made that any on-chain instruction
  performs these edits. The tiers_rebuild encoding sets stable
  count 0 by construction, so no stable leg is measured under
  a rebuilt table.
- The count-0 sell code 6023 and the anchor-ladder convergence
  of later buys are reported as measured behaviour; their
  mechanisms are not traced to source lines.
- No source-change proposal is made and no full-program
  equivalence is claimed; the packet pins measured dynamic
  fee-table behaviour only.

Made via @slopdotcash
