# research: multi-hop split x boost x tf fee-tier chains at TRUE 5 hops

#112 pinned the fee-tier boost window at 3 hops: the window sum
vq + protocol + creator is conserved by every leg, so no trade
or fee-book leg opens the window on its own; a tier edit alone
moves nothing and a threshold crossing is byte-identical to the
same edit; the burn reads vaults, never the tier schedule; and
sweeps move the next burn along the secant while a collect that
pays from the creator ATA leaves it byte-identical. This packet
re-measures that whole family on a TRUE 5-hop split x boost x
tf chain (three_amm + g4 + g5, final output U5, five hop events
on every successful swap), and adds the question depth 3 could
not ask: where does the exotic tail hop's fee accrual land when
the tail hop moves from P3 to P5, and what do the P4/P5 hop
boosts see after tiered buys?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 51 cases, 504
receipts, 51 parts (50x10 + 4). Multi-hop buys spend 10^9 quote
unless a case says otherwise; boosts request 10^9 quote with the
main pool vq patched to 10^9 wherever a boost must succeed;
transfer fee is 100 bps unless a case says otherwise. Fee table
fixture: flat (25, 5, 0); tier 0 (threshold 0, 2/93/30), tier 1
(420,000,000,000, 20/5/95); stable count 25; exotic (20, 5, 5).

## Cases

- A (5): anchors. Patched main boost, second boost without a
  re-patch, buy then patched boost, sell then patched boost,
  buy then sell then patched boost.
- B (8): window conservation. Buy, sell, tier-1 buy, exotic buy,
  buy+sell, buy+protocol sweep, buy+creator sweep, and
  buy+collect, each followed by an UNPATCHED boost: all fail
  6065.
- C (9): tier ladder, patched boost. Tier-1 buy, exotic buy,
  flat-edit buy, stable-fees-edit buy, stable-count-0 buy,
  2-tier-rebuild buy, empty-tier-rebuild buy (fails 6082),
  tier-1 sell, exotic sell.
- D (5): mid-walk tier edits. Buy then tier edit then boost;
  buy then tier edit then buy then boost; threshold-crossing
  buy then buy then boost; boost then tier edit then buy then
  boost; boost then buy then boost.
- E (9): sweep / collect / liquidity walks. Buy then protocol
  sweep, creator sweep, both sweeps, collect, exotic buy then
  P3 creator sweep, exotic buy then P5 creator sweep, deposit,
  withdraw, and sell then protocol sweep, each then patched
  boost.
- F (9): hop boosts under tier edits. Tier-1 buy then P2 boost,
  exotic buy then P2 boost, flat-edit buy then P2 boost,
  tier-1 buy then P3 boost, tier-1 buy then P4 boost, exotic
  buy then P4 boost, tier-1 buy then P5 boost, exotic buy
  then P5 boost, flat-edit buy then P5 boost (each with the
  hop pool's vq field patched to 10^9).
- G (4): tf variants. Tier-1 buy at tf0 / tf5000, tier-0 buy at
  tf5000 / tf0, each then patched boost.
- H (2): min_base gate on a tier-1-accrual window: exact
  min_base succeeds, +1 fails 6004.

## Result

### 1. The window sum is conserved at depth 5; the anchors that move are only the sell-side ones

The fixture pool starts at vq field -125,882, protocol bucket
2,488, creator bucket 123,394 -- sum exactly 0, so the fresh
boost fails 6065. A tier-0 5-hop buy leaves vq field -4,686,964
and protocol bucket 4,563,570: the vq field moved down by exactly
4,561,082, the hop-1 protocol accrual. A tier-1 buy leaves vq
field -373,259 and protocol bucket 249,865: down by exactly
247,377, again the hop-1 accrual. A sell leaves vq field
-126,729 and protocol bucket 3,335: down by exactly 847, the
sell's protocol accrual. Every B case therefore fails 6065:
the window sum stays 0 through buy, sell, tier-1 buy, exotic
buy, buy+sell, buy+sweep, buy+creator sweep and buy+collect,
and only the vq patch opens it.

The fresh 5-hop buy tails 5,207,955,235,891 (3-hop:
5,262,910,281,902) with 5 hop events; the fresh sell still pays
178,541. The main boost anchor 5,338,379,201,831, the second
boost without a re-patch 5,254,441,549,265, and the buy-then-
patched-boost 5,254,679,949,141 are all depth-invariant. The
sell-side burns move slightly with depth: sell-then-boost
5,338,394,848,076 (#112: 5,338,394,848,092, -16), and
buy-sell-boost 5,254,696,142,668 (#112: 5,254,695,806,281,
+336,387); the sell after a buy pays 189,218, not the fresh
178,541. The deltas are reported as measured; no mechanism is
claimed for why the sell-side burns move while the buy-side
burns do not.

### 2. The burn still reads vaults, not the tier schedule

Patched main boost after each C buy (vq field 10^9 in all):

| buy | tail | main protocol bucket | burn |
| --- | --- | --- | --- |
| tier-0 (anchor) | 5,207,955,235,891 | 4,563,570 | 5,254,679,949,141 |
| tier-1 fees | 5,252,440,110,816 | 249,865 | 5,254,134,170,969 |
| exotic (50, 10, 777) | 4,824,041,766,089 | 4,563,570 | 5,254,679,949,141 |
| flat edit (100, 50, 25) | 5,207,955,235,891 | 4,563,570 | 5,254,679,949,141 |
| stable tier-fee edit | 5,207,955,235,891 | 4,563,570 | 5,254,679,949,141 |
| stable count 0 | 5,219,868,625,118 | 4,563,570 | 5,254,679,949,141 |
| 2-tier rebuild | 5,207,955,235,892 | 4,563,570 | 5,254,679,949,141 |

The exotic tail fee, the flat edit, the stable tier-fee edit,
the stable-count-0 misparse and the 2-tier rebuild all leave
the main hop-1 accrual at 4,563,570, so the main boost is
byte-identical to the tier-0 burn even though the tails differ
by up to 383,913,469,802 (exotic) -- the tail hop's fee
selection never reaches the main pool's burn. The 2-tier
rebuild tail (anchor +1) reproduces #80/#112's rebuild artifact
-- the rebuild encoding zeroes the exotic region, so the tail
hop falls back to the flat fees -- while the main boost stays
tier-0. The empty tier list fails the buy with 6082
FeeTiersEmpty and leaves the anchor boost
(5,338,379,201,831) untouched.

Sell side, patched boost: tier-1 sell pays 180,126 (unchanged
from #112) and burns 5,338,394,882,302 (#112: ...882,318, -16);
exotic sell pays 164,186 (unchanged) and burns
5,338,393,590,100 (#112: ...590,113, -13).

### 3. A tier edit alone moves nothing; a crossing is byte-identical to the edit

- Buy then tier edit (tier 0 fees -> tier-1 fees) then patched
  boost burns exactly the tier-0 post-buy value
  5,254,679,949,141: the edit touches the table, not the
  buckets or the vaults, so the burn cannot see it.
- Buy then tier edit then buy then patched boost burns
  5,172,400,764,059 with cumulative protocol accrual 4,810,947
  (= 4,563,570 tier-0 + 247,377 tier-1): only the second trade's
  accrual moves the burn. The second buy tails 4,960,132,739,427
  at depth 5 (#112: 5,116,788,773,158) but the burn is identical
  -- the burn reads the accrual, not the tail.
- Threshold-crossing buy then buy then patched boost is
  byte-identical to the edit walk: second tail
  4,960,132,739,427, protocol accrual 4,810,947, burn
  5,172,400,764,059. The crossing is the edit -- no separate
  crossing mechanism exists.
- Boost then tier edit then buy then patched boost burns
  5,172,498,540,602; boost then buy then patched boost burns
  5,173,028,765,024 (the buy after the first boost drains a
  smaller vault, so the second burn sits above the
  buy-then-boost ladder). Both are identical to #112.

### 4. Sweeps move the next burn along the secant; collect does not

- Buy then protocol sweep (4,563,570) then patched boost:
  5,254,870,391,988 -- up 190,442,847 over the post-buy burn,
  41.73 per unit swept at the post-buy evaluation point (the
  #102 trade secant -41.69, #109's 41.73).
- Buy then creator sweep (123,394) then patched boost:
  5,254,685,098,328 -- up 5,149,187, again 41.73 per unit.
- Buy then both sweeps then patched boost: 5,254,875,541,549
  -- exactly #109's post-buy sweep boost, reproduced.
- Buy then collect (main pool) then patched boost:
  5,254,679,949,141 -- byte-identical to the post-buy burn.
  The collect is a 0-event no-op here: without a prior creator
  sweep the creator ATA holds nothing to collect, so the bucket
  stays 123,394 and the vaults never move. The contrast is the
  pin: a creator SWEEP pays from the real quote vault (vq1
  -123,394) and moves the burn, while a collect pays from the
  creator ATA and does not touch the burn at all.
- Buy then deposit then patched boost: 5,254,679,968,956
  (+19,815 over post-buy); buy then withdraw then patched
  boost: 5,254,679,929,285 (-19,856) -- near-mirror vault
  effects, two orders of magnitude below the sweep secant.
- Sell then protocol sweep (3,335) then patched boost:
  5,338,394,990,577 (#112: ...990,593, -16) -- up 142,501 over
  the post-sell boost, 42.73 per unit at the fresh-pool slope
  (#100's slope).

### 5. The exotic tail accrual follows the tail hop to P5 (new)

At depth 3 the exotic tail hop was P3, and the exotic buy's
P3 creator sweep paid 380,640,556,187 (#112). At depth 5 the
tail hop is P5, and the accrual moves with it:

- Exotic buy then P3 creator sweep pays only the fixture
  123,394 -- P3's creator bucket never sees the exotic tail
  fee at depth 5.
- Exotic buy then P5 creator sweep pays 376,645,119,766 --
  the tail-hop accrual, now sitting in P5's creator bucket
  (P5 pool state after the exotic buy: vq -376,645,122,254,
  creator 376,645,119,766).
- Both leave the main boost byte-identical to the tier-0
  post-buy burn (5,254,679,949,141): hop-pool fee-book legs
  never reach the main boost, at any hop position.

### 6. Hop boosts see the tier only through vault drainage, and the ladder is monotone in hop depth (new)

With the hop pool's vq field patched to 10^9, after a chain buy:

| buy | P2 boost | P3 boost | P4 boost | P5 boost |
| --- | --- | --- | --- | --- |
| tier-1 | 989,326,626 | 989,383,263 | 989,439,301 | 989,507,744 |
| exotic | 989,418,199 | - | 989,528,958 | 989,978,266 |
| flat edit | 989,418,199 | - | - | 989,596,358 |

The P2 values reproduce #112 exactly (tier-1 989,326,626;
exotic and flat-edit 989,418,199 -- identical, because the flat
edit leaves the buy's vault deltas anchor-identical). The P3
tier-1 burn moves with depth: 989,383,263 at depth 5 (#112:
989,396,393, -13,130), because the 5-hop buy drains VB3
differently. The new P4/P5 rungs extend the ladder
monotonically for tier-1 buys (P2 < P3 < P4 < P5), and the
exotic P5 burn (989,978,266) sits above the flat-edit P5 burn
(989,596,358) because the exotic tail fee changes VB5's
drainage. No tier schedule is read by a hop boost: the burn
differences are exactly the vault-drainage differences of the
preceding buy.

### 7. tf variants: tails move with depth, burns do not

- Tier-1 buy at tf0 then patched boost: 5,305,935,661,947
  (tail 5,303,948,604,604, #112 tail 5,360,959,279,511).
- Tier-1 buy at tf5000 then patched boost: 2,685,024,002,564
  (tail 2,691,196,006,460, #112 tail 2,705,796,070,079).
- Tier-0 buy at tf5000 then patched boost: 2,685,165,599,125
  (#109's tf5000 anchor boost, reproduced; tail
  2,668,075,748,732, the #160 anchor).
- Tier-0 buy at tf0 then patched boost: 5,306,492,329,463
  (tail 5,259,040,470,738, the plain tail; #109's tf0 boost,
  reproduced).
- On a tier-1-accrual window, min_base exactly
  5,254,134,170,969 succeeds and +1 fails 6004 with 0 events:
  the boost slippage gate is tier-blind, it only sees the burn.

### 8. The boost itself is vault-neutral

After every successful boost in this packet, the pool's vq
field and both buckets are byte-identical to before the boost
(anchor: vq 10^9, protocol 2,488, creator 123,394): the boost
burns base and moves quote through the vaults, but it never
writes the vq field or either fee bucket. A second boost
without a re-patch therefore burns the #100 decay-ladder
second value 5,254,441,549,265 -- the window stays open because
the boost never closes it.

## Limits

- `cpatch` steps are harness field resets (fee table, pool vq
  field), never instructions; they carry empty transactions by
  design. The `tiers_rebuild` patch encoding writes the stable
  count immediately after the tier list, which zeroes the
  exotic region (2073..); the 2-tier rebuild's +1 tail
  difference is that artifact (flat fallback), not a program
  behaviour, as disclosed in #80.
- The window-sum conservation is measured on the fixture pools;
  the gate input itself (vq + protocol + creator) is the
  #100 window definition, and this packet pins its
  conservation, not the gate's internal arithmetic.
- The sell-side burn deltas (-16 on the sell boost, +336,387
  on buy-sell-boost, -13 on the exotic sell boost, -13,130 on
  the P3 tier-1 hop boost) are reported as measured differences
  against #112; the packet does not trace them to a source line.
- No source change is proposed. No claim is made about the
  program beyond the measured legs above.

Made via @slopdotcash
