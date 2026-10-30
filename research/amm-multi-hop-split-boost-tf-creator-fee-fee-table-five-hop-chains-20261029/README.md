# research: multi-hop split x boost x tf creator-fee x fee-table chains at TRUE 5 hops

#120 pinned the creator fee at 5 hops: it is terminal-hop-only
(the buy's last hop, the sell's first executed hop), a
non-terminal pool's creator_fee_bps is inert, and a P5 10000 sell
overflows 6023. #165 pinned the fee tiers at 5 hops: tier
selection by trade size, the exotic tail accrual following the
tail hop to P5, and window conservation. This packet crosses the
two families on a TRUE 5-hop split x boost x tf chain
(three_amm + g4 + g5, final output U5, five hop events on every
successful swap), and asks whether they compose: does a tier fee
change the terminal creator accrual, does a creator bps move the
exotic tail accrual at P5, does the boost read buckets or rates
under creator-fee+tiers, and does the 10000 sell overflow survive
every table?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 65 cases, 453
receipts, 46 parts (45x10 + 3). Multi-hop buys spend 10^9 quote
unless a case says otherwise; boosts request 10^9 quote with the
main pool vq patched to 10^9 wherever a boost must succeed;
transfer fee is 100 bps unless a case says otherwise. Creator
fees are pool bytes 261..269, patched with the `poolcf` harness
reset; fee-table fixture is #165's (flat (25, 5, 0); tier 0
(threshold 0, 2/93/30), tier 1 (420,000,000,000, 20/5/95); stable
count 25; exotic (20, 5, 5)).

## Cases

- A (6): anchors. 5-hop buy, 5-hop sell, buy then patched boost,
  tier-1 buy then patched boost, exotic buy then patched boost,
  p5 cf300 buy.
- B (7): terminal bps ladder x tier-0 buys, then P5 creator
  sweep: bps 0 / 100 / 300 / 1000 / 5000 / 10000, plus cf300 buy
  then patched boost.
- C (6): terminal bps ladder x tier-1 buys, then P5 creator
  sweep: bps 0 / 100 / 300 / 1000 / 10000, plus cf300 tier-1 buy
  then patched boost.
- D (6): terminal bps ladder x exotic buys, then P5 creator
  sweep: bps 0 / 300 / 1000 / 10000, plus cf300 exotic buy then
  patched boost, plus cf300 exotic buy then P3 creator sweep.
- E (9): non-terminal creator fee inert x tables. Main, P2, P4
  at bps 300, each under tier-0, tier-1 and exotic buys, then
  P5 creator sweep.
- F (6): terminal sells x tables. P5 cf300 sells under tier-0,
  tier-1 and exotic, then P5 creator sweep; P5 cf10000 sells
  under tier-0, tier-1 and exotic.
- G (6): boosts under creator-fee+tiers. Cf300 buy then P5 hop
  boost, cf300 tier-1 buy then P5 hop boost, cf300 exotic buy
  then P5 hop boost, cf300 buy buy then main boost, cf300 sell
  then main boost, main boost under cf300 alone.
- H (5): fee-book legs under creator-fee+tiers. Cf300 buy then
  main creator sweep (Token-2022 path), cf300 tier-1 buy then
  main protocol sweep, cf300 exotic buy then main collect, cf300
  buy then deposit then main boost, cf300 buy then protocol
  sweep then main boost.
- I (5): mid-walk creator-fee changes. Buy then set cf300 then
  buy then boost; tier edit then set cf300 then buy then boost;
  set cf300 then clear then buy then boost; cf300 buy then set
  cf10000 then sell; cf300 buy then clear then boost.
- J (5): tf variants. Cf300 tier-1 buy at tf0 / tf5000 then
  boost; cf300 exotic buy at tf5000 then boost; cf300 tier-0
  sell at tf5000; cf0 tier-1 buy at tf5000 then boost.
- K (4): single-hop controls. Main cf300 legacy buy, main cf300
  buy_v2, p5 cf300 legacy buy (leg runs on the main pool),
  main cf300 tier-1 legacy buy.

## Result

### 1. The terminal creator fee is large, and it displaces rather than stacks on the exotic tail fee

At bps 0 the terminal accrual is the fixture tail accrual
(tier-0: 2,617,733,408; tier-1: 2,640,210,348; exotic:
376,645,119,766). As the terminal bps rises, the P5 creator
bucket after the buy grows and the tail falls:

| terminal bps | tier-0 tail | tier-0 P5 sweep | tier-1 tail | tier-1 P5 sweep | exotic tail | exotic P5 sweep |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 5,207,955,235,891 | 2,617,733,408 | 5,252,440,110,816 | 2,640,210,348 | 4,824,041,766,089 | 376,645,119,766 |
| 100 | 5,159,318,561,494 | 51,860,875,142 | 5,203,390,168,773 | 52,306,193,969 | - | - |
| 300 | 5,059,837,684,614 | 152,567,218,652 | 5,103,063,871,556 | 153,877,284,503 | 5,045,245,482,987 | 152,124,995,187 |
| 1000 | 4,739,955,833,958 | 476,253,124,924 | 4,780,462,400,901 | 480,342,622,682 | 4,727,148,007,638 | 474,960,130,350 |
| 5000 | 3,482,046,089,809 | 1,747,106,673,612 | - | - | - | - |
| 10000 | 2,614,678,042,767 | 2,621,532,629,315 | 2,637,070,599,880 | 2,644,043,251,340 | 2,610,776,020,268 | 2,617,610,136,787 |

The exotic row is the composite pin: at cf300 the exotic tail
RISES to 5,045,245,482,987, above the no-fee exotic tail
4,824,041,766,089 (+221,203,716,898), while the P5 creator
accrual FALLS to 152,124,995,187, below the no-fee exotic
accrual 376,645,119,766. The creator fee does not stack on top
of the exotic tail fee at the terminal hop: it replaces the
tail hop's fee computation, so the exotic fee's large cut is
gone and the user keeps more base even while the creator
bucket still accrues 152 billion. At bps 1000 and 10000 the
exotic tails fall back below the no-fee exotic tail, so the
displacement is visible only at low bps; the packet does not
trace the fee-computation order that produces it.

### 2. Non-terminal creator fees are inert on every table

Main, P2 and P4 at bps 300 leave every buy tail and every P5
creator sweep byte-identical to the no-fee values, under
tier-0, tier-1 and exotic tables alike (tier-0 tail
5,207,955,235,891, sweep 2,617,733,408; tier-1 tail
5,252,440,110,816, sweep 2,640,210,348; exotic tail
4,824,041,766,089, sweep 376,645,119,766). The terminal-hop
rule from #120 survives crossing with the fee table
unchanged: only the P5 bps field moves a 5-hop leg.

### 3. The sell creator accrual is table-blind; the 10000 sell overflow survives every table

P5 cf300 sells pay 173,260 (tier-0), 174,799 (tier-1) and
172,724 (exotic), against the fresh 178,541 -- and the
following P5 creator sweep pays exactly 30,123,364 on all
three tables. The sell-side terminal creator accrual does not
see the fee table at all, unlike the buy side where the
exotic table changes the accrual by hundreds of billions.
P5 cf10000 sells fail 6023 Overflow (trade_v2.rs:385) with
0 events on tier-0, tier-1 and exotic alike, and a cf300 buy
followed by a mid-walk cf10000 patch then sell also fails
6023: the overflow is a property of the terminal bps, not of
the table.

### 4. The main boost is creator-fee-blind; the P5 boost is not

Cf300 buy then patched main boost burns 5,254,679,949,141
(the tier-0 anchor); cf300 tier-1 buy then main boost burns
5,254,134,170,969 (the tier-1 anchor); cf300 exotic buy then
main boost burns 5,254,679,949,141 (the tier-0 anchor); a main
boost under cf300 alone burns 5,338,379,201,831 (the fresh
anchor). The terminal fee never reaches the hop-1 vaults the
main burn reads, so the main boost cannot see it. The P5 hop
boost does move: cf300 buy then P5 boost burns 989,743,701,
cf300 tier-1 buy then P5 boost burns 989,656,334, cf300 exotic
buy then P5 boost burns 989,758,217 -- against the no-fee P5
values (fresh 999,997,999; #165 tier-1 989,507,744, exotic
989,978,266). The terminal fee changes the P5 vault drainage
the hop boost reads, in both directions by table.

Fee-book legs after a cf300 buy are likewise main-blind: the
main creator sweep (Token-2022 path) pays the untouched
fixture 122,160 net, the tier-1 protocol sweep pays 247,366
net, the exotic collect is a 0-event no-op, and deposit /
protocol-sweep then main boost burn exactly the #165 values
(5,254,679,968,956 / 5,254,870,391,988).

### 5. Mid-walk creator-fee changes take effect immediately, and clearing restores the anchor

Buy then set cf300 then buy tails 4,778,179,428,711 with a
post-buy burn of 5,172,933,848,347; tier edit then set cf300
then buy tails the cf300 tier-1 value 5,103,063,871,556 with
burn 5,254,134,170,969; set cf300 then clear (bps 0) then buy
restores the anchor tail 5,207,955,235,891 and burn
5,254,679,949,141; cf300 buy then clear then boost also
burns the anchor. The bps field is read per leg, with no
residue from an earlier setting.

### 6. tf variants and single-hop controls

Cf300 tier-1 buy at tf0 tails 5,153,115,083,250 with burn
5,305,935,661,947 (the #165 tier-1 tf0 anchor burn); at
tf5000 it tails 2,614,468,565,769 with burn 2,685,024,002,564
(the tier-1 tf5000 anchor burn). Cf300 exotic buy at tf5000
tails 2,584,512,123,201 with burn 2,685,165,599,125 (the
tier-0 tf5000 anchor burn). Cf300 tier-0 sell at tf5000 pays
87,505. The cf0 tier-1 tf5000 control reproduces #165
exactly (tail 2,691,196,006,460, burn 2,685,024,002,564).
Single-hop legs: main cf300 legacy buy costs 191,550
(fresh 186,623, +4,927), main cf300 buy_v2 costs 191,614
(fresh 186,637, +4,977), main cf300 tier-1 legacy buy costs
190,276, while a p5 cf300 legacy buy on the main pool costs
exactly the fresh 186,623 -- the terminal bps of another
pool is inert on a single-hop leg, as the multi-hop rule
predicts.

## Limits

- `cpatch` steps are harness field resets (pool creator_fee_bps
  field, fee table, pool vq field), never instructions; they
  carry empty transactions by design. The bps and table
  patches isolate the fee rules, and the numbers above are
  receipt-level measurements on the three program images.
- The exotic-fee displacement at cf300 (section 1) is reported
  as measured: the packet does not trace the terminal fee
  computation order that replaces the exotic tail fee at low
  bps, nor why the displacement vanishes at bps 1000+.
- The plain-SPL main-pool creator sweep construction fails
  InvalidAccountData in this harness lineage even on a fresh
  fixture (probed: it fails with no buy and no fee patch, while
  the Token-2022-path creator sweep succeeds); the packet
  therefore measures the main creator sweep through the
  Token-2022 path only, and makes no claim about the plain
  sweep instruction itself.
- No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements on the original, control, and candidate
  images; the three images agree on every surface in
  every case (0 divergent).

Made via @slopdotcash
