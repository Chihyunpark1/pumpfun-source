# research: multi-hop five-hop fee-table split — hop 1 follows fee-tier cap selection, the tail hop follows exotic flat fees, intermediate pools stay byte-identical

## Problem

`multi_hop_swap` executes each hop through the AMM's internal swap,
and each hop reads a fee table. 3rd #37 pinned the split for a
3-hop route: hop 1 follows the cap-based fee-tier selection,
the tail hop follows the exotic flat fees, and a tiers-only
feeconfig rebuild zeroes the tail fee. This packet generalizes
that split to a 5-hop route (main -> POOL2 -> P3 -> P4 -> P5),
where the extra depth changes every absolute amount and adds
three intermediate pools whose accrual behavior must be pinned:

- Does hop 1 still cross tiers mid-chain when the main cap
  moves, with two more hops downstream?
- Do the three intermediate pools (POOL2, P3, P4) accrue
  anything at all, or stay byte-identical as in 3rd #16/#17?
- Does the tail hop still follow the exotic flat fees at
  depth 5, and do the stable-count and tiers-rebuild effects
  reproduce?

## Cases

15 cases, 56 steps, 168 receipts (each step run on the original,
control (#424), and candidate (#427) images). All amounts are
token amounts unless noted. Pool state is
(virtual_quote_reserves i128, protocol_fees, creator_fees,
lp_supply). The fixture pools are main, POOL2, P3, P4, P5, each
(-125,882, 2,488, 123,394, 4,194,352,106,721) at setup. The main
pool's starting cap is exactly 182,350,153,971. The two custom
tiers are A = (lp 10, protocol 111, creator 333) and B = (lp 20,
protocol 222, creator 444); feeconfig is patched in place (tiers
replaced, stable and exotic sections preserved) unless a case
says otherwise. The default exotic flat fees are (lp 20,
protocol 5, creator 5); the default flat fees are (25, 5, 0).
The 5-hop buy of 10^9 quote pays 5,259,040,470,738 to the tail
user under the default config (vs 5,305,797,837,698 for the
3-hop route in 3rd #37) -- the extra hops cost ~46.8B.

Family A -- hop-1 tier crossing inside a 5-hop chain:

- `a-buy-cross-swc`: tiers [(100, A), (cap0 + 10^9, B)]. buy1 pays
  A (tail out 5,249,948,235,212, buyback 5,489,071, main protocol
  5,491,560); buy2 pays B (tail out 4,903,136,904,404, buyback
  10,858,932, main protocol 16,350,492). The full sweep-all
  drains exactly: tail creator 5,128,763,359, tail protocol
  2,488, and each of P4, P3, POOL2, main contributes its seed
  creator 123,394 plus protocol 2,488 (main protocol
  16,350,492). Intermediate pools accrue nothing from the
  multi-hop trades themselves: POOL2, P3, P4 stay at their
  fixture state through both buys.
- `a-buy-cross-exact`: threshold set exactly to the post-buy1 cap
  (185,295,721,063). buy2 still pays B (buyback 10,858,932) --
  the inclusive boundary holds for the 5-hop hop-1 selector too.
- `a-buy-cross-loop`: buy A, buy B, buy B (third tail out
  4,638,349,859,364, buyback 10,858,932, main protocol
  27,209,424); tail sweep/collect drain 7,506,951,102.
- `a-sell-cross`: threshold set midway between cap0 and the
  post-sell1 cap (182,349,613,986 is the sell1 cap). sell1 pays
  B (receipt 177,996, buyback 2,021); sell2 pays A (receipt
  180,015, buyback 1,010). Tail creator after both sells is
  1,123,393; sweep/collect drain it exactly.
- `a-sell-cross-exact`: threshold set exactly to the post-sell1
  cap (182,349,613,986). sell2 still pays B (receipt 177,994,
  buyback 2,021) -- the inclusive boundary holds in the sell
  direction too, and the 2-unit receipt gap vs the A case
  (180,015) is the tier difference, not rounding noise.
- `a-buy-cross-sell-stays-B`: buy A, buy B, then two sells.
  Both sells still pay B (buyback 2,267 each, receipts 199,658
  and 199,656) -- once the chain has crossed into B, the
  hop-1 selector does not fall back to A for sells at these
  caps.

Family B -- the tail hop follows the exotic flat fees at depth 5:

- `b-default-tail`: default config, one 5-hop buy. Tail creator
  2,643,545,493 (vs 2,671,742,901 for the 3-hop route -- the
  deeper route feeds a smaller tail input); sweep/collect drain
  it exactly.
- `b-exotic-zero`: exotic (0, 0, 0). Tail creator stays at the
  seed 123,394 and the tail out is unchanged
  (5,259,040,470,738) -- the tail fee is exactly zero, not
  merely small.
- `b-exotic-creator333`: exotic (25, 5, 333). Tail creator
  170,392,131,081 (vs 172,217,534,628 for 3-hop); sweep/collect
  drain it exactly. The creator rate, not the tier table, sets
  the tail fee.
- `b-exotic-lp-proto`: exotic (50, 10, 0). Tail creator stays at
  the seed 123,394, but the tail out drops to 5,246,026,910,035
  -- lp/protocol flat fees are still charged at the tail hop
  (they land in the vault/supply, not the creator bucket).
- `b-stable-allA`: all 25 stable tiers replaced by A. Byte
  identical to `b-default-tail` (tail creator 2,643,545,493,
  same out) -- stable tiers are not consulted by the tail hop.
- `b-stable-allC`: all 25 stable tiers replaced by C. Also
  byte identical to the default buy (same out and tail
  creator) -- stable tiers are inert for multi-hop at any
  value.
- `b-tiers-allA`: all 25 fee tiers replaced by A. Hop 1 pays A
  (buyback 5,489,071, tail out 5,249,948,235,212) while the tail
  rate stays at the exotic level (tail creator 2,638,951,221,
  ~0.0503% of the tail input) -- tiers and exotic are
  independent tables, and only hop 1 reads tiers.
- `b-stable-count0`: stable count set to 0 (stable entries
  left in place). Tail creator moves to 1,059,923,696 and the
  tail out rises to 5,271,070,100,122 -- the count field itself
  shifts the tail fee, even though the stable entries are
  inert. The mechanism is not asserted here.
- `b-tiers-rebuild-only`: feeconfig rebuilt with tiers only
  (stable and exotic zeroed, as the 3rd #35/#36 builders did).
  Tail creator stays at the seed 123,394 and the tail out is
  5,249,948,235,213 (+1 vs `b-tiers-allA`) -- rebuilding with
  tiers only zeroes the tail fee at depth 5 exactly as at
  depth 3.

## Result

The fee-table split generalizes exactly to 5 hops, on all
three images (original, control #424, candidate #427 -- no
divergence in any case):

1. Hop 1 of a 5-hop route follows the same cap-based tier
   selection as a v2 trade, crossing mid-chain in both
   directions, with the inclusive boundary holding at the
   exact post-trade cap in both directions.
2. The tail hop follows the exotic flat fees only: exotic
   creator 333 scales the tail bucket ~64x, exotic zero
   zeroes it, and tiers/stable changes leave the tail rate
   untouched.
3. Intermediate pools POOL2, P3, P4 accrue nothing from
   multi-hop trades -- they stay byte-identical through buys
   and sells, and their sweep drains are exactly the fixture
   seed (creator 123,394, protocol 2,488) each.
4. Stable tiers are inert at any value, but the stable-count
   field moves the tail fee (1,059,923,696 at count 0 vs
   2,643,545,493 at count 25 under the default config).
5. A tiers-only feeconfig rebuild zeroes the tail fee at
   depth 5, reproducing the 3-hop result.

## Limits

- Feeconfig patches are applied to the fixture account data
  in the harness, not through `update_fee_config`; the
  packet pins the fee-table read path, not the setter.
- The stable-count-0 mechanism is measured but not explained;
  no claim is made about which read path the count gates.
- Amounts are specific to the fixture reserves and the 10^9
  trade size; the split (hop 1 = tiers, tail = exotic) is
  the general claim, the absolute numbers are not.
- No source change, no build, and no whole-binary identity
  claim is made. The three images agree on every receipt
  surface in this packet.
