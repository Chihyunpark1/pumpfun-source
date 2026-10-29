# research: multi-hop four-hop fee-table split under transfer fee — hop 1 follows fee-tier cap selection, the tail hop follows exotic flat fees, tf pipes report gross with isolated withheld

## Problem

3rd #37/#38/#39 pinned the multi-hop fee-table split with no
transfer fee at depths 3, 5, and 4: hop 1 follows the cap-based
fee-tier selection, the tail hop follows the exotic flat fees,
intermediate pools accrue nothing, and a tiers-only feeconfig
rebuild silently zeroes the tail fee. 3rd #40 pinned the split
under transfer fee at depth 3 and 3rd #41 at depth 5. This packet
closes the combination at depth 4: does the split survive tf on
the 4-hop route (main -> POOL2 -> P3 -> P4), and do the depth
rounding observations of #41 (sell legs 1 unit below depth 3,
tiers-rebuild out +1 vs the tier-A out) reproduce at the even
depth?

The quote mint carries tf100 (and tf5000 in Family D); the
hop-1 legs move through TOKEN22 accounts (user quote, main
vault quote, buyback ATA, creator/protocol vault ATAs, dest
ATA), while the tail hop (BASE3) stays on plain SPL accounts.
The fee-tier rule is the same as in 3rd #35/#36: the tier is
the last tier whose threshold is `<= cap`, where
`cap = base_mint_supply * effective_quote / vault_base` and
effective quote is the vault quote amount plus
virtual_quote_reserves.

## Cases

15 cases, 50 steps, 150 receipts (each step run on the original,
control (#424), and candidate (#427) images). All amounts are
token amounts unless noted. Pool state is
(virtual_quote_reserves i128, protocol_fees, creator_fees,
lp_supply). The fixture pools are main, POOL2, P3, P4, each
(-125,882, 2,488, 123,394, 4,194,352,106,721) at setup; P5 is
kept at fixture state but is NOT part of the 4-hop route, and
its pool state stays (-125,882, 2,488, 123,394,
4,194,352,106,721) in every receipt. The main pool's starting
cap is exactly 182,350,153,971. The two custom tiers are A =
(lp 10, protocol 111, creator 333) and B = (lp 20, protocol 222,
creator 444); feeconfig is patched in place (tiers replaced,
stable and exotic sections preserved) unless a case says
otherwise. The default exotic flat fees are (lp 20, protocol 5,
creator 5); the default flat fees are (25, 5, 0). Buyback legs
are reported as net / withheld / gross triples, because the
buyback ATA is a TOKEN22 account under tf.

Family A -- hop-1 tier crossing under tf100:

- `a-buy-cross-swc`: tiers [(100, A), (cap0 + 10^9, B)]. buy1 pays
  A (tail out 5,226,187,326,059, buyback gross 5,434,181 = net
  5,379,839 + withheld 54,342, main protocol 5,436,669, vault
  quote withheld 10,000,000); buy2 pays B (tail out
  4,933,411,252,464, buyback gross 10,750,342 = net 10,642,838 +
  withheld 107,504, main protocol 16,187,012). The full drain
  is exact: tail creator 5,132,087,295, P3/P2 seeds 123,394
  each, main creator seed 123,394 -> creator sweep net 122,160
  (withheld 1,234) -> collect dest net 120,938 (withheld 1,222,
  vault ATA withheld 1,234 isolated), main protocol 16,187,012
  -> protocol sweep net 16,025,141 (withheld 161,871) -> the
  following collect is a silent no-op (0 events, payer -5,000
  only): a protocol sweep's output still cannot be collected.
- `a-buy-cross-exact`: threshold set exactly to the post-buy1
  tf cap (185,266,148,570, lower than the no-fee 185,295,721,063
  because the tf gross-up shifts the curve input, and identical
  to the 3-hop and 5-hop tf caps: the hop-1 leg does not depend
  on route depth). buy2 still pays B (buyback gross 10,750,342)
  -- the inclusive boundary holds for the 4-hop hop-1 selector
  under tf too.
- `a-buy-cross-loop`: buy A, buy B, buy B (third tail out
  4,714,365,831,123, buyback gross 10,750,342, main protocol
  26,937,355); tail sweep/collect drain 7,549,468,597.
- `a-sell-cross`: threshold set midway between cap0 and the
  post-sell1 cap. sell1 pays B (user net 176,216, withheld
  1,780, gross 177,996, buyback gross 2,021); sell2 pays A (user
  net 178,214, withheld 1,801, gross 180,015, buyback gross
  1,010). Tail sweep/collect drain 1,123,393. The sell legs at
  depth 4 run 1 unit below the 3-hop tf legs (A receipt
  178,214 vs 178,215 in 3rd #40), matching the 5-hop depth
  rounding in 3rd #41; the buy legs are identical to depths 3
  and 5, so the depth rounding bites only on sells.
- `a-sell-cross-exact`: threshold set exactly to the post-sell1
  cap (182,349,613,986, identical to the no-fee, 3-hop tf, and
  5-hop tf caps). sell2 still pays B (user net 176,214,
  withheld 1,780, gross 177,994, buyback gross 2,021) --
  inclusive on the sell side under tf too, again 1 unit below
  the 3-hop tf leg.
- `a-buy-cross-sell-stays-B`: buy A, buy B, then two sells.
  Both sells still pay B (user net 193,480 / 193,478, withheld
  1,955 each, buyback gross 2,219 each): after the buy crossing
  the cap is far above the threshold, and sells at this depth
  do not fall back to A within two sells.

Family B -- the tail hop follows the exotic flat fees under
tf100 at depth 4 (all cases: one 10^9 buy, then tail
sweep/collect unless noted):

- `b-default-tail`: default config. Out 5,235,288,546,505
  (between the 3-hop tf out 5,262,910,281,902 and the 5-hop tf
  out 5,207,955,235,891), buyback gross 4,561,082 (net 4,515,471
  + withheld 45,611), vault quote withheld 10,000,000, tail
  creator 2,631,543,913 (seed + 2,631,420,519, below the 3-hop
  tf 2,645,500,920 and above the 5-hop tf 2,617,733,408);
  sweep/collect drain it exactly.
- `b-exotic-zero`: exotic (0, 0, 0). Tail creator stays at the
  seed 123,394 and the tail out is 5,235,288,546,505 --
  exactly equal to the default out, not +1 as at depths 3 and
  5. The tail fee is exactly zero under tf; the depth-4
  rounding leaves the output unchanged. Recorded as observed.
- `b-exotic-333`: exotic (25, 5, 333). Tail creator
  169,618,522,754 (seed + 169,618,399,360), out
  5,067,831,887,327; sweep/collect drain the full amount.
- `b-exotic-lpproto`: exotic (50, 10, 0). Tail creator stays at
  the seed 123,394, but the tail out drops to
  5,222,333,451,670 -- lp/protocol flat fees are still charged
  at the tail hop (they land in the vault/supply, not the
  creator bucket).
- `b-stable-allA`: all 25 stable tiers replaced by A. Byte
  identical to `b-default-tail` (same out and tail creator)
  -- stable tiers are not consulted by the tail hop under tf
  at depth 4 either.
- `b-stable-count0`: stable count set to 0 (stable entries
  left in place). Tail creator moves to 1,055,112,025 and the
  tail out rises to 5,247,264,131,879 -- the count field itself
  shifts the tail fee under tf, even though the stable entries
  are inert. The mechanism is not asserted here.
- `b-tiers-rebuild`: feeconfig rebuilt with tiers only
  (stable and exotic zeroed, as the 3rd #35/#36 builders did).
  Hop 1 pays A exactly (buyback gross 5,434,181, main protocol
  5,436,669), but the tail creator bucket collapses to the
  seed 123,394 while the tail out is 5,226,187,326,060 --
  exactly +1 vs the tier-A cross buy1 out. A reimplementation
  that copies only the tier table gets the tail hop wrong
  under tf at depth 4 exactly as at depth 5 (where the
  rebuild out was also +1, vs exactly equal at depth 3).

Family D -- tf5000 anchors:

- `d-tf5000-default`: one 10^9 buy. Out 2,675,231,312,484,
  vault quote withheld 500,000,000, buyback net 1,151,788
  (withheld 1,151,789, gross 2,303,577), main protocol
  2,306,065, tail creator 1,341,327,081. The seed sweep moves
  gross 123,394 -> net 61,697 (withheld 61,697); the collect
  moves gross 61,697 -> dest net 30,848 (withheld 30,849),
  and the sweep's withheld 61,697 stays isolated in the vault
  ATA. At tf5000 the two hops withhold exactly half each.
- `d-tf5000-cross`: tiers [(100, A), (cap0 + 10^9, B)]. buy1
  pays A (tail out 2,670,525,904,612, buyback gross 2,744,536
  = net 1,372,268 + withheld 1,372,268); buy2 pays B (tail out
  2,579,206,309,173, buyback gross 5,429,466 = net 2,714,733 +
  withheld 2,714,733). The hop-1 tier crossing survives
  tf5000 at depth 4 as well as tf100.

## Result

The fee-table split generalizes exactly to transfer fee at
depth 4, on all three images (original, control #424,
candidate #427 -- no divergence in any case):

1. Hop 1 of a 4-hop route follows the same cap-based tier
   selection as a v2 trade under tf100 and tf5000, crossing
   mid-chain in both directions, with the inclusive boundary
   holding at the exact post-trade cap in both directions
   (buy cap 185,266,148,570 under tf100, sell cap
   182,349,613,986).
2. The tail hop follows the exotic flat fees only under tf:
   exotic creator 333 scales the tail bucket ~64x, exotic zero
   zeroes it, and tiers/stable changes leave the tail rate
   untouched.
3. Intermediate pools POOL2, P3 accrue nothing from
   multi-hop trades -- they stay byte-identical through buys
   and sells, and their sweep drains are exactly the fixture
   seed (creator 123,394, protocol 2,488) each.
4. The tf pipes report gross and isolate withheld at every hop:
   vault quote withheld 10,000,000 (tf100) / 500,000,000
   (tf5000) per buy, buyback withheld alongside, sweep and
   collect each withhold again, and each hop's withheld stays
   in its own account -- the first hop's withheld is never
   released by a later collect.
5. A tiers-only feeconfig rebuild zeroes the tail fee under tf
   at depth 4 exactly as at depths 3 and 5, and a protocol
   sweep's output still cannot be collected (silent no-op
   after the protocol sweep).
6. Depth rounding: buy legs are identical to depths 3 and 5,
   while sell legs at depth 4 run 1 unit below the 3-hop tf
   legs (as at depth 5) and the tiers-rebuild out runs +1 vs
   the tier-A cross buy1 out (as at depth 5, vs exactly equal
   at depth 3); the exotic-zero out at depth 4 is exactly
   equal to the default out (vs +1 at depths 3 and 5).

## Verification

Run `python3 verify.py` from this directory. It checks, from the
packet files alone (plus the three program images):

- MANIFEST.json lists every packet file with a matching sha256.
- runtime/report.json.gz: 15 cases, 150 receipts, 15 parts
  (15x10), part sha256/byte counts match the part files.
- Every receipt transaction parses (solders) and all signatures
  verify.
- Every receipt's recorded before/after snapshots reproduce the
  report's expected values: fee-payer lamport deltas, the
  token-leg deltas (user base/quote/LP, vault base/quote per
  hop, tail output, TOKEN22 buyback), the Token-2022 withheld
  deltas (vault quote, buyback ATA, creator/protocol vault
  ATAs, dest ATA), the five pool states, volume accumulator
  state, and decoded event fields.
- The observed surface of every case is identical across the
  original, control, and candidate images.
- The three program images hash to the values recorded in the
  report.

## Limits

- Feeconfig patches and the transfer-fee override are applied
  to the fixture account data in the harness, not through
  `update_fee_config` or a transfer-fee setter; the packet pins
  the fee-table read path and the tf pipe behavior, not the
  setters.
- The stable-count-0 mechanism is measured but not explained;
  no claim is made about which read path the count gates.
- The tail fee rate is reported as an observed accrual, not as
  a claimed formula: the exact rounding path through the curve
  feedback is not pinned here.
- Amounts are specific to the fixture reserves and the 10^9
  trade size; the split (hop 1 = tiers, tail = exotic) and the
  gross/withheld pipe behavior are the general claims, the
  absolute numbers are not.
- No source change, no build, and no whole-binary identity
  claim is made. The three images agree on every receipt
  surface in this packet.
