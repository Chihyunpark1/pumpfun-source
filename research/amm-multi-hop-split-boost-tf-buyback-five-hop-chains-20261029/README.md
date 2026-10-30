# research: multi-hop split x boost x tf buyback chains at TRUE 5 hops

#113 pinned the buyback leg at 3 hops: the hop-1 quote credit is a
fixed 9,122,164 at 10^9 quote in and the buyback leg and the
protocol accrual split it by bps; a prior boost leaves the buy
leg byte-identical but moves the sell leg 837 -> 858; the route
buyback account gates by program (6027 for SPL or absent), mint
(6009) and owner membership (6053); a hop boost leaves the
buyback leg unchanged on both sides; bps 10001 patched past the
setter panics the buy while the sell succeeds with the 10000
leg. This packet re-measures that whole buyback family on a TRUE
5-hop split x boost x tf chain (three_amm + g4 + g5, final
output U5, five hop events on every successful swap), and adds
the question depth 3 could not ask: whether P4/P5 hop boosts
move the buyback leg the way P2/P3 boosts do, and whether the
sell-side buyback effects survive two more hops.

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 50 cases, 465
receipts, 47 parts (46x10 + 5). Multi-hop buys spend 10^9 quote
unless a case says otherwise; boosts request 10^9 quote with the
pool vq patched to 10^9 wherever a boost must succeed; transfer
fee is 100 bps unless a case says otherwise.

## Cases

- A anchors: fixture buy, sell, boost, boost-then-buy.
- B buyback ladder after a boost: bps 0 / 2500 / 7500 / 10000
  then buy, boost-then-sell, boost-buy-buy.
- C route buyback-account gates: non-owner, payer, SPL,
  wrong-mint, absent accounts on buys; non-owner on a sell;
  failed buy then boost.
- D hop boosts: P2 / P3 / P4 / P5 boosts then buy, P2 / P4 / P5
  boosts then sell, main + P2 / P4 / P5 boosts then buy,
  P4 / P5 boost then buy then sweep.
- E sizes: 10^12 and 10^6 buys and sells.
- F out-of-range config: bps 10001 patched past the setter,
  then buy, sell, boost, and buy-then-sweep; restore to 5000
  and repeat.
- G setter mid-walk after a boost: 7500 after boost, buy then
  boost then setter then buy, outsider setter, excluded-owner
  setter, None setter.
- H harvest / sweep after a boost: boost-buy-sweep,
  boost-buy-harvest-boost, buy-harvest-boost,
  boost-buy-creator-sweep-collect, boost-buy-buy-sweep.
- I tf variants, boost first: tf0 buy, tf5000 buy, tf5000 sell.

## Result

### 1. The hop-1 credit split is depth-invariant

The fresh 5-hop buy tails 5,207,955,235,891 (3-hop:
5,262,910,281,902) with the same hop-1 leg: buyback 4,515,471
with 45,611 withheld, on the fixed 9,122,164 credit. The bps
ladder after a boost reproduces #113 exactly: bps 0 pays no
leg (protocol takes the whole credit, main pool state
[990877836, 9124652, 123394]); bps 2500 pays 2,257,735
(withheld 22,806); bps 7500 pays 6,773,206 (withheld 68,417);
bps 10000 pays 9,030,942 and the protocol bucket does not grow
(main pool state [1000000000, 2488, 123394]). The main boost
still burns the anchor 5,338,379,201,831, and the boost-first
buy still takes the identical leg 4,515,471 with tail
5,087,534,167,771 (the #156 boost-then-buy tail). The second
buy after a boost takes the same leg again. The setter
mid-walk reproduces too: boost then setter 7500 then buy pays
6,773,206, buy-boost-setter-buy pays 6,773,206, the outsider
setter fails 6005 with the following buy at the anchor leg,
the excluded-owner setter then buy fails 6053, and the None
setter is a no-op with the following buy at the anchor leg.

### 2. Hop boosts leave the buyback leg unchanged at every hop

P2, P3, P4 and P5 boosts all burn the anchor 999,997,999, and
the buy after any of them takes the identical leg 4,515,471.
The buy tails move monotonically with hop depth, matching the
#164 ladder exactly: P2 5,207,939,910,316, P3 5,207,939,828,742,
P4 5,207,939,747,168, P5 5,207,939,665,660. Main + hop boost
then buy also takes the anchor leg, with tails 5,087,519,189,811
(P2), 5,087,519,034,118 (P4), 5,087,518,956,337 (P5). A hop
boost then buy then protocol sweep discharges 4,563,570 to
4,517,934 net on P4 and P5 alike — the hop boost does not
change the sweep.

### 3. The sell leg goes hop-boost-blind at depth 5 (new)

The boost-then-sell leg still moves 837 -> 858 with payout
182,879, exactly as at depth 3 — the main boost still moves
the sell. But every hop boost leaves the 5-hop sell payout at
exactly 178,541 with leg 837: P2, P4 and P5 alike. At depth 3
a P2 boost added +1 to the sell payout (178,542); at depth 5
that +1 is gone, the same absorption #164 pinned for the
sell leg generally. The buyback leg is therefore
boost-invariant on both sides at depth 5, while the sell
payout is main-boost-sensitive but hop-boost-blind.

### 4. The route gates are unchanged; the sell ghost count grows

Non-owner and payer route accounts fail 6053, SPL and absent
accounts fail 6027, wrong-mint fails 6009 — all as at depth 3.
The buy failures leave 0 events; the non-owner sell failure
leaves 4 ghost events at depth 5 (2 at depth 3 — the sell
executes terminal-first, so four hops run before the failing
hop-1 leg). A failed route-account buy leaves the next main
boost at the anchor burn.

### 5. The bps-10001 asymmetry survives, with two depth-5 deltas

The buy at bps 10001 panics with ProgramFailedToComplete and
0 events (the panic fires before any hop event is emitted —
contrast #162's min_out panic, which left 5 ghosts), and the
restore buy returns the anchor leg 4,515,471 and tail. The
sell at bps 10001 succeeds paying 178,541 with leg 1,676, as
if capped at 10000, and the boost at bps 10001 still burns
the anchor. The sweep after a panicked buy discharges only
the fixture 2,488. Two depth-5 deltas: the restore sell after
the capped sell pays 178,539, 2 less than the anchor — the
capped sell moves the pools slightly — and the tf5000
boost-first sell pays 91,640, 1 less than #113's 91,641
(leg 430, withheld 430, unchanged).

### 6. Sizes, harvest, and tf variants reproduce, except the huge sell

The 10^12 buy tails 175,991,970,811,038 (the #145 depth-5
saturation value) with leg 4,515,471,118 and withheld
45,610,820; the 10^6 buy tails 5,361,233,911 with leg 4,515
and withheld 46. The 10^6 sell pays 178 with the leg rounding
to 0 net and 1 withheld, as at depth 3. The 10^12 sell is the
one size that moves: payout 177,570,967 with leg 833,456
(depth 3: 177,923,993 / 835,113). Harvest clears the BB22
withheld (-45,611) without moving the next burn: the
boost-buy-harvest-boost second burn is 5,173,028,765,024 and
the buy-harvest-boost burn is 5,254,679,949,141 (the #154
post-buy burn). The creator sweep followed by collect is a
0-event no-op, and the boost-buy-buy sweep discharges the
cumulative 9,124,652 to 9,033,405 net. tf0 boost-first buy
pays leg 4,607,153 with no withholding (tail 5,136,667,160,892);
tf5000 boost-first buy pays leg 1,151,788 with withheld
1,151,789 (tail 2,625,898,824,386) — both identical to #113.

## Limits

- `cpatch` steps are harness field resets (pool vq, config
  bps, clock), not instructions and not on-chain reachable
  states in this packet: they isolate the buyback rules, and
  the leg / payout numbers above are receipt-level
  measurements on the three program images.
- The bps-10001 panic mechanism is not traced to a source
  line: the packet reports the error kind, the 0 ghost
  events, and the full rollback on all three images, and
  notes the contrast with #162's 5-ghost min_out panic
  without claiming its cause.
- The restore-sell -2 and tf5000-sell -1 deltas are reported
  as measured differences against #113; the packet does not
  trace them to a source line.
- No source change is proposed and no full-program
  equivalence is claimed. All three images agree on every
  receipt (0 divergent cases).

Made via @slopdotcash
