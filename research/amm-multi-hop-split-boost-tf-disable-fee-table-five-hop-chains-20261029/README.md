# research: multi-hop split x boost x tf disable x fee-table chains at TRUE 5 hops

#121 pinned the disable-priority map at 5 hops: disable masks the
mode divergence, the boost gate order is 6005 > 6066 > 6020, the
create bit blocks new pools only (6017), and ungated bits 32/64/128
do nothing. #165 pinned the fee-tier ladder at 5 hops: tier
selection by trade size, the exotic tail accrual following the tail
hop to P5, window conservation, and the sweep secant. This packet
crosses the two families on a TRUE 5-hop split x boost x tf chain
(three_amm + g4 + g5, final output U5, five hop events on every
successful swap), and asks whether the disable flags and the fee
table interact at all: does a disable bit mask or unmask a tier
effect, does a failed (disabled) leg still accrue a tier fee, does
the tier gate outrank or yield to the disable gate, and does the
exotic tail accrual land anywhere when the buy itself is disabled?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 64 cases, 402
receipts, 41 parts (40x10 + 2). Multi-hop buys spend 10^9 quote
unless a case says otherwise; boosts request 10^9 quote with the
main pool vq patched to 10^9 wherever a boost must succeed;
transfer fee is 100 bps unless a case says otherwise. Disable bits
live in GlobalConfig byte 56 (1 create, 2 deposit, 4 withdraw, 8 buy,
16 sell). Fee table fixture: flat (25, 5, 0); tier 0 (threshold 0,
2/93/30), tier 1 (420,000,000,000, 20/5/95); stable count 25; exotic
(50, 10, 777) where patched.

## Cases

- A (6): anchors. Fresh buy, fresh sell, tier-1 buy, exotic buy,
  buy then patched boost, tier-1 buy then patched boost.
- B (12): disable bits x tier-0 legs. Buy bit buy, sell bit sell,
  buy bit sell, sell bit buy, deposit bit deposit, withdraw bit
  withdraw, all-bits buy/sell, create bit buy, ungated bits 32 buy,
  64 sell, 128 buy.
- C (9): disable bits x tier-1 / exotic legs. Buy bit tier-1 buy,
  sell bit tier-1 sell, buy bit exotic buy, sell bit exotic sell,
  buy bit tier-1 buy-boost, sell bit tier-1 sell-boost, buy bit
  exotic buy-boost, deposit bit tier-1 deposit, withdraw bit exotic
  withdraw.
- D (13): boosts under disable + tiers, gate order. Buy/sell/
  deposit/withdraw/all-bits main boosts, buy bit tier-1 boost, buy
  bit + boost_enabled=0 boost, buy bit + rotated-authority boost,
  buy bit P2/P4/P5 hop boosts, sell bit P5 hop boost, deposit bit
  P4 hop boost.
- E (6): disable x stable / flat / rebuild tables. Buy bit
  stable-count-0 buy, flat-edit buy, 2-tier-rebuild buy,
  empty-tier buy, undisabled empty-tier buy, sell bit tier-1
  sell-boost.
- F (6): mid-walk toggle x tier. Disabled buy, clear, tier-1 buy,
  boost; buy, set buy bit, boost, clear, boost; tier-1 buy, set buy
  bit, buy, clear, buy; disabled exotic buy, clear, exotic buy, P5
  creator sweep; disabled deposit, clear, deposit, boost; disabled
  sell, clear, sell, boost.
- G (4): fee-book legs after disabled failures. Disabled buy then
  protocol sweep then boost; disabled buy then creator sweep then
  collect then boost; disabled tier-1 buy then protocol sweep then
  boost; disabled sell then protocol sweep then boost.
- H (4): tf variants under disable + tiers. Buy bit tier-1 tf5000
  buy, sell bit tier-1 tf0 sell, buy bit exotic tf5000 buy, buy bit
  tf5000 boost.
- I (4): exotic tail accrual under disable. Unflagged exotic buy
  then P5 creator sweep; disabled exotic buy then P5 creator sweep;
  disabled exotic sell then P5 creator sweep; disabled tier-1 buy
  then protocol sweep.

## Result

### 1. The disable bits gate by direction, on every table

Buy bit (8): buy fails 6020 with 0 events, under tier-0, tier-1,
exotic, stable-count-0, flat-edit, 2-tier-rebuild and empty-tier
tables alike. Sell bit (16): sell fails 6021 under tier-0, tier-1
and exotic tables alike. Deposit bit (2): deposit fails 6018
(tier-0 and tier-1). Withdraw bit (4): withdraw fails 6019
(tier-0 and exotic). All-bits (31): buy fails 6020, sell fails
6021 -- the buy bit dominates the buy, the sell bit the sell.
Cross-direction legs are untouched: a buy-bit sell still pays the
fresh 178,541, a sell-bit buy still tails the fresh
5,207,955,235,891. The create bit (1) gates no trade leg (buy
tails the anchor), and ungated bits 32, 64, 128 gate nothing
either. All of this agrees on all three images (0 divergent cases)
-- unlike the #119/#167 mode gates, the disable gates do not split
the original from the rebuilds.

### 2. The disable gate fires before the tier gate, and before any tier accrual

The undisabled empty-tier buy fails 6082 FeeTiersEmpty, but the
same buy under the buy bit fails 6020, not 6082: the disable check
runs before the fee-table read. A disabled leg accrues nothing at
all: the disabled exotic buy leaves the P5 creator sweep at the
fixture 123,394 (no tail-hop accrual is ever created), the disabled
exotic sell leaves it at 123,394 too, and the disabled tier-1 buy
leaves the protocol sweep at the fixture 2,488. Contrast the
unflagged exotic buy, whose P5 creator sweep pays 376,645,119,766
(the #165 tail-hop accrual; P5 pool state after the buy: vq
-376,645,122,254, creator 376,645,119,766). The fee table cannot
accrue through a disabled leg, at any hop position.

### 3. Only the buy bit gates boosts, with the #121 order intact under tiers

Main boost under the buy bit fails 6020 (tier-0, tier-1 and tf5000
alike); under the sell, deposit or withdraw bit it succeeds at the
anchor; under all-bits it fails 6020 (the buy bit). Hop boosts
P2/P4/P5 under the buy bit all fail 6020; under the sell bit the P5
hop boost succeeds, under the deposit bit the P4 hop boost succeeds.
The head of the gate order is unchanged under tiers:
boost_enabled=0 + buy bit fails 6066 (6066 beats 6020), rotated
authority + buy bit fails 6005 (6005 beats 6020). So a boost reads
exactly one disable bit -- the buy bit -- which is consistent with
a boost being a buy-like leg: the sell, deposit and withdraw bits
never touch it, on any table.

### 4. Toggling the bit mid-walk unmasks the tier leg immediately, with no residue

Disabled buy, clear, tier-1 buy, boost: the second buy tails
5,252,440,110,816 (the tier-1 tail) and the boost burns
5,254,134,170,969 (the #165 tier-1 post-buy burn) -- the failed
first leg left nothing behind. Tier-1 buy, set buy bit, buy, clear,
buy: the middle buy fails 6020 and the final buy tails
4,957,670,972,204 (the second buy on the moved pool). Buy, set buy
bit, boost, clear, boost: the middle boost fails 6020 and the final
boost burns 5,254,679,949,141 (the post-buy burn). Disabled exotic
buy, clear, exotic buy, P5 creator sweep: the sweep pays the full
376,645,119,766 -- clearing the bit restores the accrual in full.
Disabled deposit, clear, deposit, boost burns 5,338,379,222,079;
disabled sell, clear, sell, boost burns 5,338,394,848,076 (the #165
sell-boost value). A disabled leg is a pure gate: it moves no
bucket, no vault and no tail.

### 5. Fee-book legs after disabled failures accrue nothing either

Disabled buy then protocol sweep then boost: the boost still fails
6020 while the bit stays set -- the sweep (fixture values only)
does not clear the gate. Disabled buy then creator sweep then
collect then boost: same, 6020. Disabled tier-1 buy then protocol
sweep then boost: same, 6020. Disabled sell then protocol sweep
then boost: the boost succeeds (the sell bit never gated it) and
burns 5,338,379,308,140 -- the swept fixture value moved the burn
along the #165 secant, while the failed sell itself contributed
nothing. Tf variants do not move the gates: buy bit tier-1 tf5000
buy fails 6020, sell bit tier-1 tf0 sell fails 6021, buy bit exotic
tf5000 buy fails 6020, buy bit tf5000 boost fails 6020.

## Limits

- `cpatch` steps are harness field resets (GlobalConfig disable byte,
  fee table, pool vq field), never instructions; they carry empty
  transactions by design. The disable-byte and fee-table numbers
  above are receipt-level measurements on the three program images.
- The create-bit result (6017) is carried over from #121: this packet
  pins only that the create bit gates no trade leg at depth 5, not a
  new create_pool measurement.
- The dep-then-boost (5,338,379,222,079) and sell-then-boost
  (5,338,394,848,076) burns are reported as measured; the packet does
  not re-derive them from the vault deltas.
- No source change is proposed and no full-program equivalence is
  claimed. All three images agree on every receipt (0 divergent
  cases).

Made via @slopdotcash
