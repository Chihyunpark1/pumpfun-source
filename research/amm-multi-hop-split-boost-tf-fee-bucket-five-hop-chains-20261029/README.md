# research: split x boost x tf fee bucket and accrual chains at true 5 hops

3rd run packet #153. The #99 fee bucket/accrual findings (protocol
and creator fee buckets, accrual behaviour, sweep/collect effects)
re-measured on a TRUE 5-hop split x boost x tf chain: `three_amm` +
`g4` + `g5`, final output U5. Every successful swap below carries
exactly 5 hop events (buy disc `67f4521f2cf57777` len 508, sell disc
`3e2f370aa503dc2a` len 449); the hop count in this name matches the
route in code.

## Problem

At depth 3 (#99) the fee buckets were pure accounting below 10^12:
they never moved the trade price or the boost burn, they converted
into virtual quote reserves when swept, they re-accrued per trade
from whatever value they held, and they survived every failed step
byte-identical -- except that a hop-1 bucket at 10^12 broke buy,
sell, boost and sweep alike with 6023 Overflow, and the boundary
between the harmless 1e9 seed and the fatal 10^12 was unmeasured.
Depth 5 changes the shape of accrual (a terminal hop now accrues
the creator bucket, and a sell after a buy accrues a different
amount than at depth 3) and the shape of failure (a slippage breach
on a 5-hop buy panics instead of failing clean). This packet pins
the buckets at depth 5: per-hop accrual on buys and sells, accrual
ladders, seeded buckets, the huge-bucket boundary, hop-position
seeds, sweep/collect transitions, boost-vs-bucket independence,
transfer-fee variants, failure rollback, and snapshot-restore walks.

## Cases

71 cases, 402 receipts, 41 parts (40x10 + 2), each run on three
program images (original, control, candidate). Transfer fee is 100
bps unless a case says otherwise. Fixture buckets: protocol 2,488,
creator 123,394 on every pool; virtual quote reserve -125,882.

- **A, accrual ladders (8):** anchor buy/sell; buy-buy; buy-buy-buy;
  sell-sell; buy-sell; sell-buy; buy-sell-buy.
- **B, v2 / legacy legs (6):** v2 buy; v2 buy-buy; v2 sell then sweep;
  legacy buy; legacy buy-buy; legacy buy then sweep.
- **C, seeded buckets (24):** hop-1 protocol/creator zeroed or seeded
  to 1e9, on buys; P2/P4/P5 protocol + creator seeded to 1e9, on
  buys; both buckets seeded to 1e9, on a sell; both seeded to 1e9
  or zeroed, on a boost (vq patched to 1e9); hop-1 protocol or
  creator at 1e12, on buy/sell/boost/sweep; terminal P5 protocol or
  creator at 1e12, on a buy; the boundary series -- hop-1 protocol
  at 1e10, 1e11, 1.5e11, 2e11, 3e11, 4e11, 5e11 -- on buys; hop-1
  creator at 1e11, on a buy.
- **D, sweep / collect (12):** sweep twice; creator sweep + collect
  twice; sweep/collect after a sell; sweep of a 1e9-seeded bucket;
  sweep of a 1e12 bucket; sweep with the quote vault emptied then
  restored; sweep + creator sweep + collect then buy; then sell;
  terminal P5 creator sweep; P2 protocol sweep; P5 creator sweep +
  collect; P4 protocol sweep.
- **E, boost vs buckets (6):** boost after a buy; after a sweep;
  after sweep + collect; boost twice; boost after a sell; boost
  after restoring the main pool to its post-setup snapshot (all
  with vq patched to 1e9).
- **F, transfer-fee variants (6):** tf0 buy; tf0 buy-buy; buyback leg
  after a sweep; tf5000 buy; tf5000 buy + sweep; tf5000 buy-buy.
- **G, failure rollback (4):** slippage breach on a buy, then a
  clean buy; slippage breach on a sell, then a clean sell; token
  claim after a failed buy (seeded UVA); failed empty-vault sweep,
  then vault restore, then a buy.
- **H, snapshot-restore walks (4):** buy, restore protocol bucket
  to fixture, buy, buy; buy, sweep, restore protocol bucket to
  fixture, sweep; buy, restore terminal creator bucket to fixture,
  buy; four-buy walk with the protocol bucket forced to 1e9
  mid-walk and restored after.

## Result

One divergent case (`g-claim-after-fail`, below); all other 70 cases
agree across all three images.

- Anchor buy (tf100): 10^9 quote pays tail U5 **5,207,955,235,891**
  with 5 hop events. Hop-1 protocol accrues **4,561,082** (2,488 ->
  4,563,570); hop-1 creator never moves; middle pools (P2/P3/P4)
  are byte-identical afterwards; terminal P5 creator accrues
  **2,617,610,014** (123,394 -> 2,617,733,408); terminal protocol
  never moves. The buyback leg pays **4,515,471 net** with 45,611
  withheld -- gross 4,561,082, exactly the hop-1 protocol accrual.
- Anchor sell: 10^9 base pays **178,541**; hop-1 protocol accrues
  only **847** (2,488 -> 3,335) and terminal creator **500,000**
  (123,394 -> 623,394) -- the same sell accrual as depth 3.
  Second sell re-accrues 847; a sell after a buy accrues **898**
  on top of the buy's bucket (depth-5 delta vs depth 3's 847).
- Buy ladder: second buy re-accrues the same hop-1 4,561,082
  (-> 9,124,652), third the same again (-> 13,685,734); terminal
  creator re-accrues 2,497,231,000 then 2,384,969,345. Accrual is
  per-trade, not saturating, on both ends. Sell ladder: second sell
  re-accrues 847 (-> 4,182), terminal creator +499,999.
- Buy-sell cycle: sell after a buy pays 189,218 (vs anchor
  178,541); buy after a sell pays 5,208,011,418,184 (vs anchor
  5,207,955,235,891) and re-accrues the full buy gross on top of
  the sell's bucket.
- v2 legs accrue **1 protocol + 1 creator per trade** (buy and sell
  alike); sweeping either bucket then pays it out gross-minus-
  withheld (2,489 -> 2,464 net, 25 withheld). Legacy buys accrue
  **nothing** -- both buckets stay at fixture values after two
  legacy buys, and a sweep after a legacy buy pays only the
  fixture 2,488 (-> 2,463 net). Legacy trades are bucket-invisible.
- Seeded buckets never move price or burn at depth 5: seeding any
  bucket to 0 or 1e9 -- hop-1 protocol, hop-1 creator, P2/P4/P5
  protocol + creator -- leaves the buy, the sell, and every delta
  byte-identical to the anchor. Seeded accrual stacks: a P5
  creator seed of 1e9 ends at 3,617,610,014 after a buy (seed +
  2,617,610,014). With vq patched to 1e9, the boost burn is
  **5,338,379,201,831** whether the buckets are seeded to 1e9 each
  or zeroed.
- Huge-bucket overflow, boundary narrowed (the #99 gap, closed):
  a hop-1 bucket at **1e11 still buys clean**, but 1.5e11, 2e11,
  3e11, 4e11, 5e11 and 1e12 all fail **6023 Overflow** -- buy, sell,
  boost and sweep alike (buy 0 events, sell 4 ghosts, sweep 0
  events), and the seeded bucket stays put; a huge bucket cannot
  be drained to escape. The boundary sits between 1e11 and 1.5e11.
  Terminal (P5) buckets at 1e12 do **not** break the buy
  (anchor-identical, accrual stacks on the seed: P5 creator ends
  at 1,002,617,610,014). Only the hop-1 pool's buckets feed the
  overflowing computation.
- Sweep/collect: post-buy protocol sweep pays 4,563,570 gross ->
  **4,517,934 net (45,636 withheld)**; a second sweep is a silent
  no-op (0 events). Creator sweep pays 123,394 -> **122,160 net
  (1,234 withheld)**; collect then pays 122,160 -> **120,938 net
  (1,222 withheld)**; a second collect is a silent no-op. After a
  sell, protocol sweep pays 3,335 -> 3,301 net and creator sweep
  pays the untouched 123,394 -> 122,160 net. Sweeping a 1e9-seeded
  bucket pays the whole 1,000,000,000 gross -> 990,000,000 net
  (10,000,000 withheld). Hop sweeps work: P5 creator sweep pays
  2,617,733,408 gross (SPL, no withheld), P2/P4 protocol sweeps
  pay the untouched fixture 2,488, and P5 collect moves the full
  2,617,733,408 to DEST5.
- Empty-vault sweep fails 6023 (0 events); restoring the vault to
  the post-setup snapshot and sweeping again pays the full
  4,563,570 -> 4,517,934 net. The bucket survives the failed sweep.
  After a failed empty-vault sweep and vault restore, the next buy
  pays 4,956,404,517,853, not the second-buy tail -- the snapshot
  predates the first buy's quote inflow into the vault, while the
  bucket itself is untouched (4,563,570 preserved, then re-accrues
  to 9,124,652).
- After a full sweep + creator sweep + collect (main pool at
  [0, 0, 0]), the next buy accrues exactly the gross per-trade
  amount (0 -> 4,561,082) and pays the same buyback leg 4,515,471
  net at the second-buy tail 4,918,089,082,874 -- the buyback leg
  tracks per-trade accrual, not the bucket balance, and the price
  follows the vaults, not the books. Sweeping the protocol bucket
  to zero does not change the next buy's leg. A sell after a
  full sweep pays 189,218 and accrues 898 from zero.
- Boost vs buckets: after a buy (vq patch 1e9), the burn is
  **5,255,205,915,165**; a full sweep, or sweep + collect, leaves
  that burn byte-identical. The second boost burns
  5,254,441,549,265 -- less only because the first boost drained
  the base vault. After a sell the burn is 5,338,394,947,549
  (16 below the depth-3 value), essentially the fresh burn.
  Restoring the main pool to its post-setup snapshot after a buy,
  then boosting, burns 5,255,015,563,992: bucket restoration does
  not restore the fresh burn (the vaults still reflect the buy),
  and the burn differs from the post-buy burn because the restore
  also resets the vq field to its pre-buy patched 1e9 -- the burn
  tracks vq plus vaults, not buckets.
- Transfer fee: at tf0 the buy accrues more (4,607,154 vs
  4,561,082) and the second tf0 buy re-accrues the same amount
  (-> 9,216,796). At tf5000 the buy accrues 2,303,577 and its
  sweep pays 2,306,065 gross -> 1,153,032 net (1,153,033 withheld,
  the 50% split).
- Failure rollback: a slippage breach on a 5-hop buy panics
  (**ProgramFailedToComplete**, 5 ghost events) in all three
  images when no UVA is seeded, and leaves every bucket
  byte-identical; the next buy lands on the anchor tail. A
  slippage breach on a 5-hop sell is a clean **6004** (5 events)
  in all images, buckets unchanged, next sell on anchor.
- **Divergent case `g-claim-after-fail` (1 step):** with a seeded
  UVA, the failed buy is a clean **6004 in original** but a
  **panic in control/candidate** -- the #146 panic-vs-6004 split
  depends on UVA seeding (without a seeded UVA, all three images
  panic). The failed trade neither accrues nor blocks the claim:
  a token claim after the failed buy still pays the full
  3,334,551 in all images.
- Restore walks: restoring the protocol bucket to its post-setup
  2,488 after a buy, then buying again, re-accrues to 4,563,570
  (not to 9,124,652) but pays the second-buy tail -- the restore
  erases the first accrual from the books while the price still
  follows the vaults' movement. Restoring then sweeping pays the
  resurrected 2,488 gross -> 2,463 net a second time. Restoring
  the terminal creator bucket to 123,394 after a buy, then buying
  again, re-accrues with the second-buy amount (to 2,497,354,394).
  A four-buy bucket walk (forced 1e9 mid-walk, restored after)
  gives after-buy buckets 4,563,570 -> 1,004,561,082 -> 4,563,570
  -> 9,124,652, while the tails follow the plain vault walk
  (5,207,955,235,891 / 4,918,089,082,874 / 4,651,768,149,125 /
  4,406,509,597,797).

## Limits

- The overflow boundary is narrowed to (1e11, 1.5e11] for the hop-1
  protocol bucket on buys; the creator bucket was only bisected to
  1e11 (passes) vs 1e12 (fails), and the overflowing computation
  itself is not identified from these receipts alone (the 6023
  site line is the same pool.rs:417 as #99).
- Bucket patches and snapshot restores are fixture-level
  mutations, not on-chain instructions; the restore cases
  describe harness state transitions, not program behaviour.
- The seeded-UVA panic-vs-6004 divergence is reported as
  measured; its mechanism (why a seeded UVA changes original's
  failure mode but not the rebuilds') is not identified here.
- No source change is proposed; no claim is made about the
  program beyond the measured cases.

Made via @slopdotcash
