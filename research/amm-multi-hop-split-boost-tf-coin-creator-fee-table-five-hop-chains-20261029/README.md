# research: split x boost x tf coin-creator x fee-table chains at true 5 hops

## Problem

Two previously pinned mechanisms meet on one chain and their interaction had
not been measured. Coin-creator reassignment (#116/#122) moves the main burn
by exactly +5,272,467 on a fresh rerouted sweep, leaves hop burns unchanged,
and gates migrate behind the sweep; fee-table tier selection (#112/#134/#165)
moves buy tails by table and pushes the exotic tail accrual to the tail hop
(P5 at depth 5). The open question was whether those two mechanisms compose
cleanly at depth 5, or whether one distorts the other: does a tier change the
rerouted-sweep effect, does reassignment move tier accruals, does a zero
terminal creator waive the same fee on every table, and does the tiered chain
leave the same boost ladder as the untiered one?

This packet runs a true 5-hop split x boost x tf chain
(`three_amm + g4 + g5`, final output U5) under tier-0, tier-1, exotic, and
stable-count-0 fee tables, crossed with main/P4/P5 reassignment walks
(zero, set, rerouted sweep, collect, migrate), and compares original, control,
and candidate images on every case. 59 cases, 906 receipts, 91 parts.

## Cases

- **A (anchors, 7):** tier-0 / tier-1 / exotic / stable-count-0 buys and
  sells with burns, plus a tier-1 double burn and a tier-1 buy twice.
- **B (main rerouted sweep, 8):** fresh rerouted sweep under tier-1 and
  exotic; buy-then-set rerouted sweep; set-first rerouted sweep; buy-then-set
  migrate (both tables); set-then-migrate-then-buy; migrate-then-tier-1-buy.
- **C (main migrate, 7):** migrate-before-sweep failures under tier-1 and
  exotic; sweep+collect+migrate burns; migrate-then-collect-blocked;
  migrate-then-buy burns under tier-1 and exotic.
- **D (P4 reassignment, 7):** zero P4 + tiered buy + set4 + P4 boost; zero P4
  rerouted sweep+collect; P4 sweep+collect+migrate4 under tier-1 and exotic;
  migrate4-then-buy P4 boost.
- **E (P5 reassignment, 10):** zero P5 + tiered buy + set5 + P5 boost; zero P5
  rerouted sweep+collect; P5 sweep+collect+migrate5 under tier-1 and exotic;
  migrate5-then-buy P5 boost; zero P5 tier-1 and exotic sells.
- **F (mid-chain tier change, 5):** set-then-tier-1 buy; buy-set-tier-1 buy;
  zero-set-exotic buy; migrate-then-tier-1 buy; tier-1 buy-set-exotic buy.
- **G (claim / long walks, 4):** cashback claim before and after set under
  tier-1; tier-1 buy-set-sell-boost; exotic boost-set-sell-boost.
- **H (tf variants, 4):** tf5000 rerouted sweep under tier-1; tf0 migrate
  under exotic; tf5000 zero-P5 set5 boost; tf0 zero-P4 set4 boost.
- **I (exotic tail accrual, 7):** exotic and tier-1 P5 sweeps; set5 no-op
  then exotic P5 sweep; zero-P5 exotic buy then P5 sweep; zero-P5 tier-1 buy
  then set5 then P5 sweep; zero-P5 exotic buy then set5 then P5 sweep then
  P5 boost; exotic P5 sweep+collect then P5 boost.

## Result

All 59 cases agree across original, control, and candidate: **0 divergent
cases.** The interaction is measured, not assumed:

- **Rerouted sweep is table-blind on a fresh pool, state-dependent after a
  buy.** A fresh rerouted sweep moves the burn by exactly +5,272,467 under
  tier-1 and under exotic alike (5,338,384,474,298), the same value as at
  tier-0. After a buy, the same walk moves the burn only by the sweep secant:
  tier-1 post-buy burn 5,254,134,170,969 becomes 5,254,139,319,445
  (+5,148,476), exotic post-buy 5,254,679,949,141 becomes 5,254,685,098,328
  (+5,149,187). The sweep effect depends on pool state, not on the table.
- **Set on a nonzero pool is a no-op under tiers, and its reroute sweep
  fails 2006.** A set after a buy emits 0 events, the rerouted sweep then
  fails 2006, and the boost stays at the tier-1 post-buy burn
  (5,254,134,170,969). A set before the buy behaves the same way. The #122
  rule (set fires only on a zero pool) holds under tier-1 and exotic.
- **Migrate gates hold under tiers.** Migrate before sweeping fails 6081
  under tier-1 and exotic alike, and the boost after sweep+collect+migrate
  equals the rerouted-sweep burn under both tables (tier-1
  5,254,139,319,445; exotic 5,254,685,098,328). Collect after migrate fails
  6048 under tier-1 and exotic alike.
- **Migrate leaves a residue on the next tiered buy's boost.** A
  migrate-then-tier-1-buy chain and a buy-set-tier-1-buy chain have the
  identical second-buy tail (4,960,132,739,427), but their boosts differ by
  5,029,031 (5,172,405,793,090 vs 5,172,400,764,059). The set no-op leaves
  no residue; migrate does. The mechanism behind the residue was not
  traced; the value is reported as measured.
- **P4 reassignment leaves hop burns at the #165 ladder.** Zero P4 + tiered
  buy + set4 + P4 boost burns 989,439,301 (tier-1) and 989,528,958
  (exotic), exactly the #165 P4 values. P4 rerouted sweep+collect pay the
  fixture 123,394 and leave the fresh P4 boost at the anchor 999,997,999.
  P4 boost after migrate4 is byte-identical under tier-1 (989,439,301) and
  +1 under exotic (989,528,959, the same +1 as at tier-0).
- **The zero-terminal-creator waiver scales with the table, on both
  sides.** A zero P5 lifts the tier-1 buy tail by +2,607,204,736 (to
  5,255,047,315,552) but the exotic buy tail by +371,025,659,959 (to
  5,195,067,426,048); the tier-0 lift was +2,585,239,009. Sells show the
  same direction: zero-P5 tier-1 sell pays 180,216 (+90 over the tier-1
  sell 180,126), zero-P5 exotic sell pays 178,094 (+13,908 over the exotic
  sell 164,186). The P5 boost after a waived-fee buy also moves with the
  table: tier-1 989,505,151 (2,593 below the #165 tier-1 P5 burn
  989,507,744), exotic 989,609,178 (369,088 below the #165 exotic P5 burn
  989,978,266). The exotic tail fee is mostly terminal-creator-fee in
  character; the mechanism was not traced and is reported as measured.
- **A zero terminal creator blocks the P5 sweep entirely: the fee is
  waived, not rerouted.** An exotic buy with a zero P5 leaves the P5
  creator bucket at the fixture 123,394 (no accrual is created at all) and
  the P5 sweep fails 2006, even after set5. By contrast, an unflagged
  exotic buy accrues 376,645,119,766 to P5 and a tier-1 buy accrues
  2,640,210,348; set5 on a nonzero P5 is a 0-event no-op and leaves the
  exotic accrual untouched at 376,645,119,766.
- **Tier anchors at depth 5 (for reference):** tier-0 buy tail
  5,207,955,235,891, post-buy burn 5,254,679,949,141; tier-1 buy tail
  5,252,440,110,816, post-buy burn 5,254,134,170,969; exotic buy tail
  4,824,041,766,089, post-buy burn 5,254,679,949,141 (the exotic table does
  not move the main burn); stable-count-0 buy tail 5,219,868,625,118,
  post-buy burn 5,254,679,949,141; tier-1 sell 180,126, exotic sell 164,186;
  tier-1 sell-boost burn 5,338,394,882,302, exotic sell-boost burn
  5,338,393,590,100.
- **Tf variants compose unchanged.** The tf5000 rerouted sweep under
  tier-1 halves twice (61,697 then 30,848) and burns 2,706,769,696,611, as
  at tier-0; tf5000 zero-P5 set5 boosts and tf0 zero-P4 set4 boosts are
  both the anchor 999,997,999 (tf-blind). Cashback claim fails 2021 under
  tier-1 before and after set; reassignment does not rescue the claim
  gate.

## Limits

- The migrate residue (+5,029,031 on the next tiered buy's boost) and the
  table-scaled zero-terminal-creator waiver are reported as measured
  values only; the internal fee path that produces them was not traced.
- The fee is waived, not rerouted, only in the sense that no P5 accrual
  appears and the P5 sweep fails 2006; no claim is made about any other
  destination of the waived amount.
- All chains are synthetic harness executions against the original,
  control, and candidate program images; no on-chain state was used.
- This packet measures the interaction of two previously pinned
  mechanisms; it does not propose any program change.

Made via @slopdotcash
