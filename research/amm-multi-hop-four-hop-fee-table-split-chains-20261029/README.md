# research: multi-hop four-hop fee-table split — hop 1 follows fee-tier cap selection, the tail hop follows exotic flat fees, intermediate pools stay byte-identical

## Problem

`multi_hop_swap` executes each hop through the AMM's internal swap,
and each hop reads a fee table. 3rd #37 pinned the split for a
3-hop route and 3rd #38 for a 5-hop route: hop 1 follows the
cap-based fee-tier selection, the tail hop follows the exotic
flat fees, and a tiers-only feeconfig rebuild zeroes the tail
fee. This packet is the even-hop check of that split: a 4-hop
route (main -> POOL2 -> P3 -> P4), where the hop-count parity
must not change the rule, and where the absolute amounts differ
from both the 3-hop and the 5-hop routes:

- Does hop 1 still cross tiers mid-chain at depth 4, with the
  main cap moving the same ~2.9B per buy as at other depths?
- Do the two intermediate pools (POOL2, P3) accrue anything at
  all, or stay byte-identical as in 3rd #16/#17/#37/#38?
- Does the tail hop still follow the exotic flat fees at
  depth 4, and do the stable-count and tiers-rebuild effects
  reproduce?

## Cases

15 cases, 54 steps, 162 receipts (each step run on the original,
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
creator 5); the default flat fees are (25, 5, 0). The 4-hop buy
of 10^9 quote pays 5,286,914,075,404 to the tail user under the
default config (vs 5,305,797,837,698 for the 3-hop route in 3rd
#37 and 5,259,040,470,738 for the 5-hop route in 3rd #38) --
depth 4 sits strictly between the two odd depths.

Family A -- hop-1 tier crossing inside a 4-hop chain:

- `a-buy-cross-swc`: tiers [(100, A), (cap0 + 10^9, B)]. buy1 pays
  A (tail out 5,277,725,288,579, buyback 5,489,071, main protocol
  5,491,560); buy2 pays B (tail out 4,979,765,376,019, buyback
  10,858,932, main protocol 16,350,492). The full sweep-all
  drains exactly: tail creator 5,182,048,698, tail protocol
  2,488, and each of P3, POOL2, main contributes its seed
  creator 123,394 plus protocol 2,488 (main protocol
  16,350,492). Intermediate pools accrue nothing from the
  multi-hop trades themselves: POOL2 and P3 stay at their
  fixture state through both buys.
- `a-buy-cross-exact`: threshold set exactly to the post-buy1 cap
  (185,295,721,063). buy2 still pays B (buyback 10,858,932) --
  the inclusive boundary holds for the 4-hop hop-1 selector too.
- `a-buy-cross-loop`: buy A, buy B, buy B (third tail out
  4,756,579,132,460, buyback 10,858,932, main protocol
  27,209,424); tail sweep/collect drain 7,621,664,358.
- `a-sell-cross`: threshold set midway between cap0 and the
  post-sell1 cap (182,349,613,986 is the sell1 cap). sell1 pays
  B (receipt 177,996, buyback 2,021); sell2 pays A (receipt
  180,015, buyback 1,010).
- `a-sell-cross-exact`: threshold set exactly to the post-sell1
  cap (182,349,613,986). sell2 still pays B (receipt 177,994,
  buyback 2,021) -- the inclusive boundary holds on the sell
  side too.
- `a-buy-cross-sell-stays-B`: buy A, buy B, then sell B
  (receipt 195,615, buyback 2,221), sell B again (receipt
  195,613, buyback 2,221). The buys lift the main cap far above
  the threshold, so the sells stay on B even though a fresh
  sell chain would start on A-side pricing.

Family B -- the tail hop follows the exotic flat fees, not the
tier tables:

- `b-default-tail`: default config buy (tail out
  5,286,914,075,404, buyback 4,607,153, tail creator
  2,657,630,443); sweep/collect drain the tail creator bucket
  in full.
- `b-exotic-zero`: exotic flat fees (0, 0, 0). The tail creator
  bucket holds only the seed 123,394 and the tail out is
  5,286,914,075,405 -- exactly +1 vs default. Zeroing the
  exotic creator fee removes the tail accrual without moving
  the output by more than 1.
- `b-exotic-creator333`: exotic flat fees (25, 5, 333). The tail
  creator bucket jumps to 171,300,031,073 and the tail out
  falls to 5,117,814,610,491.
- `b-exotic-lp-proto`: exotic flat fees (50, 10, 0). The tail
  creator bucket holds only the seed 123,394, but the tail out
  falls to 5,273,831,906,799 -- the lp/proto legs move the
  output even with creator 0.
- `b-stable-allA` / `b-stable-allC`: all 25 stable tiers
  replaced with A (resp. C). Both are byte-identical to the
  default buy (tail out 5,286,914,075,404, tail creator
  2,657,630,443). The stable table is inert for the tail hop.
- `b-tiers-allA`: all 25 fee tiers replaced with A. Hop 1 pays
  A (buyback 5,489,071, main protocol 5,491,560), tail out
  5,277,725,288,579, tail creator 2,652,987,124. Changing the
  tier table moves hop 1 but leaves the tail rate on its
  exotic path.
- `b-stable-count0`: only the stable count patched to 0
  (exotic untouched). The tail creator bucket falls to
  1,065,570,632 and the tail out rises to 5,299,007,123,758.
  The mechanism is recorded as observed only, not asserted.
- `b-tiers-rebuild-only`: feeconfig rebuilt with fee tiers
  only (one tier A, stable and exotic zeroed, as the 3rd
  #35/#36 builders did). Hop 1 pays A exactly (buyback
  5,489,071, main protocol 5,491,560), but the tail creator
  bucket collapses to the seed 123,394 while the tail out is
  5,277,725,288,579 -- exactly equal to the tiers-allA out. A
  reimplementation that copies only the tier table gets the
  tail hop wrong at depth 4 exactly as at depths 3 and 5.

## Result

Hop 1 follows the fee-tier cap rule (last threshold <= cap,
inclusive on both the buy and the sell side) at depth 4; the
intermediate pools POOL2 and P3 accrue nothing from multi-hop
trades; the tail hop follows the exotic flat fees and ignores
both the fee-tier and stable tables; the stable-count patch
moves the tail fee without touching the exotic section; and a
tiers-only feeconfig rebuild silently zeroes the tail fee.
All 15 cases agree across the original, control, and candidate
images (divergence 0). The 4-hop multi-hop buy event is
disc 67f4521f2cf57777 / 508 bytes (4 events per buy) and the
sell event is disc 3e2f370aa503dc2a / 449 bytes (4 events per
sell).

## Limits

- This packet pins the fee-table split at hop depth 4 only; it
  does not re-derive the cap formula (see 3rd #35/#36) or the
  hop-1 tier selection from source.
- The stable-count effect is observed, not explained: no
  mechanism is asserted for why patching the count to 0 moves
  the tail creator bucket from 2,657,630,443 to 1,065,570,632.
- P5 is present in snapshots at fixture state only; no claim
  is made about a 5th hop in this packet (see 3rd #38).
- No source files were modified; all results are measured
  from LiteSVM executions of the original, control, and
  candidate program images.
