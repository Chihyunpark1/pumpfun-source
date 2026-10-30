# research: multi-hop split x boost x tf mode x fee-table chains at TRUE 5 hops

#119 pinned the mode-gate split at 5 hops: the original gates
cashback only on the terminal hop while the rebuild gates it on
every hop (6079), mayhem gates on every hop on both images
(6080), and on a both-flagged hop the original fires mayhem
6080 first while the rebuild fires cashback 6079 first. #165
pinned the fee-tier ladder at 5 hops: tier selection by trade
size, the exotic tail accrual following the tail hop to P5, and
window conservation. This packet crosses the two families on a
TRUE 5-hop split x boost x tf chain (three_amm + g4 + g5, final
output U5, five hop events on every successful swap), and asks
whether they interact: does a mode gate mask or unmask a tier
effect, does the terminal-hop cashback gate coincide with the
tail-hop exotic accrual at P5, does a tier edit change a gated
leg's outcome, and does a boost under mode+tiers burn anything
other than the anchor?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; control == candidate everywhere).
62 cases, 294 receipts, 30 parts (29x10 + 4). Multi-hop buys spend
10^9 quote unless a case says otherwise; boosts request 10^9 quote
with the main pool vq patched to 10^9 wherever a boost must succeed;
transfer fee is 100 bps unless a case says otherwise. Pool flags are
pool bytes 243 (mayhem) / 244 (cashback); fee-table fixture is
#165's (flat (25, 5, 0); tier 0 (threshold 0, 2/93/30), tier 1
(420,000,000,000, 20/5/95); stable count 25; exotic (20, 5, 5)).

## Cases

- A (4): anchors. 5-hop buy, 5-hop sell, buy then patched boost,
  tier-1 buy then patched boost.
- B (10): mode x tier-0 buys. Each of main, P2, P4, P5 flagged
  cashback; main, P2, P5 flagged mayhem; main, P4, P5 flagged
  both; then a buy.
- C (8): mode x tier-1 buys. Main, P2, P4, P5 cashback; main,
  P5 mayhem; main, P5 both; then a tier-1 buy.
- D (6): mode x exotic buys. Main, P2, P5 cashback; main, P5
  mayhem; P5 both; then an exotic buy.
- E (8): mode x tier + boost. Main/P5/P2 cashback tier-1 buys
  then patched boost; main/P5 cashback exotic buys then patched
  boost; main mayhem tier-1 buy then boost; P5 both tier-1 buy
  then boost; main cashback tier-1 buy then P5 hop boost.
- F (6): masking / unmasking mid-walk. Main cashback buy, clear
  the flag, tier-1 buy, boost; P5 cashback buy, clear, exotic
  buy, boost; main cashback stable-count-0 buy; P5 cashback flat
  buy; main both tier-1 buy, clear, buy; tier-1 buy, flag main
  cashback mid-walk, buy.
- G (4): global flags. Main cashback pool with global cashback
  off (buy, and tier-1 buy); main mayhem pool with global mayhem
  off (buy); P5 cashback pool with global cashback off (buy).
- H (8): sell-side mode x tier. Main, P2, P5 cashback sells;
  main, P5 mayhem sells; main, P5 both sells; P5 cashback
  tier-1 sell.
- I (4): tf variants. Main cashback tier-1 buy at tf5000; P5
  cashback tier-1 buy at tf0; main mayhem exotic buy at tf5000;
  P5 both tier-1 buy at tf5000.
- J (4): exotic tail accrual under mode flags. Unflagged exotic
  buy then P5 creator sweep; P5 cashback exotic buy then P5
  sweep; main cashback exotic buy then P5 sweep; P5 mayhem
  exotic buy then P5 sweep.

## Result

### 1. The mode-gate split is tier-invariant: 26 of 62 cases diverge, all of them mode-gate cases

The divergent set is exactly the non-terminal cashback and
both-flagged cases, under every fee table. Tier-0, tier-1 and
exotic buys diverge identically at each flag position:

- Non-terminal cashback buy: original succeeds (full 5-hop tail),
  rebuild fails 6079 with a ghost ladder tracking hop position:
  main 0 ghosts, P2 1 ghost, P4 3 ghosts. Tier-1 tails on the
  original are 5,252,440,110,816 at main, P2 and P4 alike;
  exotic tails are 4,824,041,766,089 at main and P2 alike.
- Terminal (P5) cashback buy: both images fail 6079 with 4
  ghosts, under tier-0, tier-1, exotic, flat and stable-count-0
  tables alike. The fee table never rescues or worsens the
  terminal gate.
- Mayhem buy: both images fail 6080 at every position and
  every table (main 0 ghosts, P2 1, P5 4).
- Both-flagged buy: original fails 6080 first, rebuild fails
  6079 first, at main and P4 (3 ghosts each) -- except at the
  terminal hop, where both fail 6079 with 4 ghosts: cashback
  wins at the terminal hop on both images.
- Sell direction mirrors buy with the ladder reversed (sells
  run terminal-first): main cashback sell diverges (original
  succeeds, rebuild 6079 with 4 ghosts), P2 cashback sell
  diverges (rebuild 6079 with 3 ghosts), P5 cashback sell
  agrees (both 6079 with 0 ghosts -- the terminal hop executes
  first), main both sell splits 6080 vs 6079 with 4 ghosts
  each, P5 both sell agrees at 6079 with 0 ghosts.

The fee table moves only the numbers on the legs that succeed:
it never moves a gate code, a ghost count, or the divergent
set. That is the packet's central negative result: the two
families are orthogonal at the gate.

### 2. The terminal gate and the tail accrual coincide at P5, and the gate wins

At depth 5 the terminal hop is also the exotic tail hop, so
the P5 cashback gate and the P5 exotic accrual sit on the
same pool -- but they never meet, because the gate fires
before any accrual exists:

- Unflagged exotic buy then P5 creator sweep pays
  376,645,119,766 (the #165 tail-hop accrual).
- P5 cashback exotic buy fails 6079 on both images, and the
  following P5 creator sweep pays only the fixture 123,394:
  no accrual was ever created.
- P5 mayhem exotic buy fails 6080 on both images, same
  fixture-only sweep.
- Main cashback exotic buy diverges, and the divergence
  propagates into the fee-book leg: the original accrues to
  P5 and sweeps 376,645,119,766, while the rebuild's buy
  fails 6079 and its sweep pays only 123,394.

So the mode gate, not the fee table, decides where the
exotic accrual lands: wherever the buy succeeds, the accrual
follows the tail hop; wherever the buy fails, there is
nothing to sweep.

### 3. Boosts under mode+tiers are mode-blind; only a failed buy moves the next burn

- Main cashback tier-1 buy then patched boost: original
  burns 5,254,134,170,969 (the #165 tier-1 post-buy value);
  rebuild burns 5,338,379,201,831 (the fresh anchor -- its
  buy failed, so its window never accrued).
- P5 cashback tier-1 buy then boost: both burn the anchor
  5,338,379,201,831 (both buys failed).
- Main cashback exotic buy then boost: original burns the
  #165 exotic post-buy value; rebuild burns the anchor.
- Main cashback tier-1 buy then P5 hop boost: original
  burns 989,507,744 (the #165 tier-1 P5 value); rebuild
  burns 999,997,999 (fresh hop boost after its failed buy).
- A boost on a flagged pool itself was already shown
  mode-blind in #119; here the same holds under tier-1 and
  exotic tables: no boost in this packet burns anything
  other than the value its preceding legs dictate.

### 4. Masking and unmasking are immediate and tier-blind

- Main cashback buy, clear the flag, tier-1 buy, boost:
  original accrues twice (protocol 497,242) and burns
  5,171,867,765,352; rebuild accrues once (its first buy
  failed) and burns 5,254,134,170,969. Clearing unmasks the
  second buy on both images; it does not repair the first
  buy's divergence.
- P5 cashback buy, clear, exotic buy, boost: both buys
  after the clear succeed, the second exotic buy tails
  4,824,041,766,089, and the boost burns the #165 exotic
  post-buy value on both images -- the divergence is gone
  the moment the flag is gone.
- Tier-1 buy, flag main cashback mid-walk, buy: the second
  buy succeeds on the original and fails 6079 on the
  rebuild. Flagging mid-walk gates immediately, on the
  rebuild only, exactly as flagging at case start does.
- Main both tier-1 buy, clear, buy: the first buy splits
  6080 vs 6079, the second buy succeeds on both images.

### 5. Global flags do not gate the multi-hop leg

- Main cashback pool with global cashback off: still
  divergent (original succeeds, rebuild 6079), for tier-0
  and tier-1 buys alike.
- Main mayhem pool with global mayhem off: still both
  6080.
- P5 cashback pool with global cashback off: still both
  6079 with 4 ghosts.

The multi-hop gate reads the pool flags, not the GlobalConfig
mode bytes: toggling the global flags changes nothing on
either image, under any table.

### 6. tf variants do not move the gates

- Main cashback tier-1 buy at tf5000: original tails
  2,691,196,006,460, rebuild fails 6079.
- P5 cashback tier-1 buy at tf0: both fail 6079 with 4
  ghosts.
- Main mayhem exotic buy at tf5000: both fail 6080 with
  0 ghosts.
- P5 both tier-1 buy at tf5000: both fail 6079 with 4
  ghosts.

## Limits

- `cpatch` steps are harness field resets (fee table, pool
  flags, pool vq field, global flags), never instructions;
  they carry empty transactions by design. The flag and
  table patches isolate the gate/table rules, and the
  numbers above are receipt-level measurements on the three
  program images.
- The gate/table orthogonality is measured at the fixture
  route and the #165 fee-table fixture; other routes or
  tables were not swept.
- The 26 divergent cases are original-vs-rebuild
  divergences of the kind #109/#119 already pinned; this
  packet adds only that the fee table does not change them.
  No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements; control == candidate in every case.

Made via @slopdotcash
