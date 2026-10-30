# research: multi-hop split x boost x tf epoch chains at TRUE 5 hops

#106 pinned Token-2022 transfer-fee epoch-schedule selection on a
true-3-hop chain: the rule `epoch >= newer.epoch ? newer : older`
selects per leg at the current clock epoch, a buy's net input
reprices the curve while a sell's gross is schedule-blind, and
sweep, collect, boost, deposit, withdraw, harvest and
withdraw-from-mint all read the schedule live at their own leg.
This packet re-measures that whole family on a TRUE 5-hop split x
boost x tf chain (three_amm + g4 + g5, final output U5, five hop
events on every successful swap), and adds the question depth 3
could not ask: does the epoch schedule touch anything beyond the
hop-1 leg when four more hops follow it?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). The quote mint
carries an older schedule (epoch 0, 100 bps) and a newer schedule
(epoch 10, 5000 bps) unless a case says otherwise; the standard
tuple is written (older_epoch, older_bps, newer_epoch, newer_bps)
= (0, 100, 10, 5000). Multi-hop buys spend 10^9 quote unless a case
says otherwise; boosts request 10^9 quote with the main pool vq
patched to 10^9 wherever a boost must succeed.

## Cases (51 cases, 321 receipts, 33 parts)

- E (11): buy-leg boundary ladder — clock epochs 0 / 9 / 10 / 11
  on the standard pair, tied pairs at 9 / 10 / 0, inverted pairs
  (100, 100) / (50, 5000) at 0 / 49 / 50, a future newer epoch
  (10^9) at clock 10^6.
- S (5): sell leg at epochs 0 / 10, buy-then-sell at 0 / 10,
  sell-then-buy at 10.
- W (8): buy-then-sweep at 0 / 10, buy-then-sweep-collect at
  0 / 10, mixed clock-crossing sweep and collect, buy-harvest-
  withdraw-from-mint at 0 / 10 and mixed.
- B (6): boost at 0 / 10, buy-then-boost at 0 / 10,
  boost-then-buy at 0 / 10.
- M (7): mid-walk clock crossing buy-buy and sell-sell,
  mid-walk schedule rewrite buy-buy, mid-walk bps rewrite
  buy-buy, mid-walk clock / schedule boost pairs, mid-walk bps
  rewrite sweep.
- F (6): maximum_fee caps — old/new buy and sell at cap 1000,
  mixed clock-crossing buy under the old cap, sweep under the
  new cap.
- D (4): deposit and deposit-withdraw at epochs 0 / 10.
- X (3): plain-quote buy control, small (10^6) buys at 0 / 10.

## Result

### 1. The selection rule is unchanged at depth 5; only the buy tails move

Boundary inclusive at exactly newer.epoch, in both directions.
Old-100 buy tail 5,207,955,235,891 (the 5-hop fresh anchor, not
the 3-hop 5,262,910,281,902); new-5000 buy tail 2,668,075,748,732
(the tf5000 5-hop anchor). Clock 0 and 9 both take the older
schedule; clock 10 and 11 both take the newer. Tied pairs
(10, 100) / (10, 5000): clock 9 takes older, clock 10 takes newer.
Inverted pairs (100, 100) / (50, 5000): clock 0 and 49 take older,
clock 50 takes newer. A future newer epoch (10^9) never activates
at clock 10^6. A tie at epoch 0 selects newer. Withheld is
hop-1-only and byte-identical to depth 3 in every E case
(old: vq1 10,000,000 + bb22 45,611; new: vq1 500,000,000 + bb22
1,151,789) — the four extra hops add curve, not fee.

### 2. The epoch schedule touches nothing beyond hop 1

This is the depth-5-only pin. After an old-100 buy the main pool
is [-4,686,964, 4,563,570, 123,394] while P2, P3 and P4 stay
fixture-valued [-125,882, 2,488, 123,394] and only the terminal
P5 moves, to [-2,617,735,896, 2,488, 2,617,733,408] (the #153
terminal-creator accrual, vq −2,617,610,014 against creator
+2,617,610,014). No withheld key appears on any intermediate hop
in any receipt: the withheld dicts are vq1 + bb22 only, because
the intermediate hops run on plain SPL mints. The schedule is a
hop-1-leg property, not a chain property.

### 3. Sell gross is schedule-blind at depth 5 too

Fresh sell nets are identical to depth 3: 178,541 at epoch 0
(gross 180,345 = 178,541 net + 1,804 withheld) and 90,172 at
epoch 10 (gross 180,345 = 90,172 net + 90,173 withheld); the
buyback leg moves 9 → 423. Buy-then-sell is the 5-hop moved-pool
value (189,218 at epoch 0, 92,876 at epoch 10, vs 185,288 /
91,885 at depth 3). Sell-then-buy at epoch 10: the second buy
tails 2,668,104,735,018 (vs 2,682,443,927,826 at depth 3).
Clock-crossing sell-sell: the second sell nets 90,171 — one
below the fresh 90,172, the only 1-unit depth delta in the
packet (withheld 90,172 + bb22 423); it is reported as measured,
not smoothed over.

### 4. Sweep, collect, harvest and withdraw-from-mint are depth-blind

Every hop-1 value reproduces #106 exactly. Sweep after buy:
4,517,934 net + 45,636 withheld at epoch 0; 1,153,032 net +
1,153,033 withheld at epoch 10. Collect after sweep: 120,938
net + 1,222 withheld at epoch 0; 30,848 net + 30,849 withheld
at epoch 10. Mixed clock-crossing sweep: 2,281,785 net +
2,281,785 withheld (the 50% split at the new rate); mixed
collect: 61,080 net + 61,080 withheld. Harvest + withdraw-
from-mint totals: 10,045,611 at epoch 0, 501,151,789 at epoch
10, and the mixed walk pays 10,045,611 then 501,151,789 —
harvest moves whatever was withheld, schedule-agnostic, and
the second mixed buy tails 2,518,568,049,835 (vs
2,585,193,161,051 at depth 3: same schedule, deeper curve).

### 5. Boosts are schedule-priced but depth-blind in burn

Main-pool burns reproduce #106 exactly: fresh boost
5,338,379,201,831 at epoch 0, 2,706,767,012,738 at epoch 10;
buy-then-boost 5,254,679,949,141 at epoch 0, 2,685,165,599,125
at epoch 10. Boost-then-buy tails are the #156 depth-5 values:
5,087,534,167,771 at epoch 0, 2,625,898,824,386 at epoch 10.
Mid-walk clock-crossing and schedule-rewrite boost pairs both
land on 2,664,124,872,647 for the second burn — crossing ≡
rewrite, as at depth 3. Mid-walk bps rewrite buy-buy: second
tail 4,869,780,080,299 with withheld vq1 20,000,000 + bb22
90,301 (withheld identical to depth 3; tail differs only by
depth).

### 6. Maximum_fee caps per leg, bps-irrelevant while it binds

Cap 1000 on either schedule: buy withheld is exactly
vq1 1,000 + bb22 1,000 at both bps, and the capped buy tail is
5,259,035,362,587 regardless of which schedule is capped (vs
5,315,079,504,355 at depth 3). Capped sell nets 179,345 with
userquote withheld exactly 1,000 at both epochs (buyback leg
9 at epoch 0, 423 at epoch 10 — the cap binds the input leg,
not the buyback leg). Mixed clock-crossing capped buy: second
tail 2,517,122,712,779. Capped sweep: net 4,562,570 with
withheld exactly 1,000.

### 7. Deposit, withdraw, plain and small amounts

Deposit / withdraw reproduce #106 exactly: deposit costs
29,610 quote (withheld 297) at epoch 0 and 58,626 quote
(withheld 29,313) at epoch 10; withdraw pays 29,018 net
(withheld 294) at epoch 0 and 14,656 net (withheld 14,656)
at epoch 10. Plain-quote buy tails 5,259,040,470,738 (the
5-hop plain anchor) with no withheld. Small (10^6) buys:
tail 5,361,233,911 with withheld vq1 10,000 + bb22 46 at epoch
0; tail 2,707,728,352 with withheld vq1 500,000 + bb22 1,152
at epoch 10 (withheld identical to depth 3; tails differ by
depth only).

## Limits

- `cpatch` steps are harness field resets (clock epoch and mint
  schedules rewritten between legs), not instructions and not
  on-chain reachable states in this packet: they isolate the
  selection rule, and the clock-crossing ≡ schedule-rewrite
  equivalence is the evidence the rewrite is faithful.
- The sell-sell second-net 90,171 (vs fresh 90,172) is a
  1-unit depth delta reported as measured; its mechanism is
  not traced to a source line.
- The intermediate hops run on plain SPL mints in this
  fixture, so "schedule touches nothing beyond hop 1" is a
  statement about this route shape; a route whose intermediate
  hops also carried transfer-fee mints would select per leg
  there too, by the same rule, but is not measured here.
- No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements on the original, control, and candidate
  images; the three images agree on every surface in
  every case (0 divergent).

Made via @slopdotcash
