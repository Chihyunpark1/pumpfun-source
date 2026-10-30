# amm-multi-hop-split-boost-tf-vault-liquidity-five-hop-chains-20261029

## Problem

3rd #92 pinned the window invariant (vq + protocol + creator
constant) and that sweep/collect are price-neutral, #93 pinned
that chain prices move when a single-hop leg moves the real
vaults, #97 pinned the user's own wallets, and #98 pinned the
pool vaults themselves as priced inputs at true 3 hops. What
none of them pinned is whether those vault findings survive
two more hops: does a hop price off the real vault balance,
the virtual reserve, or both, when five pools are chained?
Which vault empties first at depth 5, what code fires when it
does, and does a restore bring the anchor back? This packet
patches vault amounts, lamports, frozen state, absence, and
LP supply mid-case -- between real trades, with no transaction
of its own, so a patch leaves no receipt -- and pins the price
at each balance, the gate at each empty vault, and the restore
behaviour, on the split x boost x tf chain at true 5 hops
(three_amm + g4 + g5, final output U5).

## Cases

92 cases, 375 receipts, 38 parts (37x10 + 5), three program
images (original, control, candidate) per step. Fixture
vaults: main base vb1 673,696,395,912,745 (SPL 165 bytes),
main quote vq1 122,946,690,720 (Token-2022 178 bytes), middle
vb2/vq2, vb3/vq3, vb4/vq4 and tail vb5/vq5 10^15 each; main LP
supply 4,194,352,106,721. Anchors: buy 10^9 quote pays tail U5
5,207,955,235,891 (hop1 base out 5,332,264,170,203, hop2 out
5,303,981,938,022, buyback 4,515,471); sell 10^9 base pays
178,541.

Family A -- main quote vault vq1: anchor buy/sell; buy with
vq1 0, 1, 10^15; sell with vq1 0, 100,000, 178,541, 10^9;
frozen buy/sell; absent buy/sell; lamports 0 buy; pre-seeded
withheld 999,999 then buy then Token-2022 sweep.

Family B -- main base vault vb1: buy with vb1 0, 10^9, 10^12,
5 x 10^12, 10^15; sell with vb1 0, 10^15; frozen buy/sell;
absent buy/sell; lamports 0 buy.

Family C -- middle vaults: buy with vb2 0, 10^12; sell with
vb2 0; buy with vq2 0; sell with vq2 0; frozen vb2 buy,
frozen vq2 sell; absent vb2 buy; buy/sell with vb3 0 and
vq3 0.

Family D -- terminal vaults: buy with vb4 0, 10^12; sell
with vb4 0; buy/sell with vq4 0; buy with vb5 0, 10^12; sell
with vb5 0; buy/sell with vq5 0; frozen vb5 buy, frozen vq5
buy; absent vb5 buy.

Family E -- LP supply: buy/sell with lp 0; deposit/withdraw
with lp 0; deposit with lp 1 and lp 10^6; buy with lp 10^12,
2^63, P2 lp 0, P5 lp 0; buy with lp 0 then lp restored then
buy; deposit then withdraw then buy.

Family F -- drain chains: vb1 6 x 10^12 then three buys then
vb1 restored then buy; vq1 300,000 then three sells then
vq1 restored then sell; buy/sell/buy/sell cycle; vb5
6 x 10^12 then three buys.

Family G -- downstream legs: buy then protocol sweep then
creator sweep then collect then buy; buy then sweep with
vq1 zeroed then sweep restored; boost with vb1 0, with
vq1 0, anchor boost (vq patch 10^9), boost with boost-ATA
10^6; failed buy (vb1 0) then token claim; deposit then
withdraw with vb1 0 then withdraw restored.

Family H -- restore / hybrid: buy then vb1 restored then
buy; sell then vq1 restored then sell; buy then vb5
restored then buy; buy then sweep then vq1 restored then
buy; buy then vb1 10^15 buy then vb1 restored buy then buy.

Family I -- v2 contrast: v2 buy with vb1 0, with vq1 0, with
vb1 frozen; v2 sell with vq1 0; v2 anchor buy.

Family T -- transfer-fee variants: vb1 0 / vq1 0 gates at
tf0 and tf5000; vb1 10^12 buy at tf5000; vq1 0 sell at
tf5000; tf5000 anchor buy.

## Result

All 92 cases agree on all three images: **0 divergences**.
Error sites are pinned per image, never compared across
images.

- Hops price off real vault balances, both sides, at depth
  5. The anchor buy moves vb1 -5,332,264,170,203, vq1
  +985,438,918 (10^9 in, 10,000,000 withheld at the vault,
  4,561,082 protocol accrual absorbed into main vq), vb2
  -5,303,981,938,022, vq2 +5,332,264,170,203, vb3
  -5,275,998,139,846, vq3 +5,303,981,938,022, vb4
  -5,248,308,076,854, vq4 +5,275,998,139,846, vb5
  -5,207,955,235,891, vq5 +5,248,308,076,854, tail
  +5,207,955,235,891. Patching vb1 rescales the whole
  chain: vb1 10^9 pays tail 7,964,077, 10^12 pays
  7,963,832,881, 5 x 10^12 pays 39,814,081,760, fixture
  6.7 x 10^14 pays 5,207,955,235,891, 10^15 pays
  7,653,055,729,062. Patching vq1 rescales it the other
  way: vq1 10^15 pays tail 664,961,271 (hop1 base out
  666,625,458, as at depth 3; the tail is lower than the
  3-hop 664,962,160 by the two extra hops). Patching vb2
  10^12 pays 5,290,670,932, vb4 10^12 pays 5,235,192,616,
  vb5 10^12 pays 5,207,955,235 -- the terminal vault caps
  the tail through the hop-5 ratio. The virtual reserve
  (-125,882) is a rounding-scale adjustment next to real
  balances of 10^11-10^15, not the price driver.
- Sells price off the same real balances, mirrored. The
  anchor sell moves vb1 +997,496,013, vq1 -181,191,
  userquote +178,541. Patching vq1 to 10^9 collapses the
  payout to 1,451 (vq1 -1,473); patching vb1 to 10^15
  drops it to 120,282 -- both identical to depth 3. A sell
  after a buy pays more than the anchor sell (189,218
  after one buy, 200,204 after buy/sell/buy), and a buy
  after a sell pays more than the plain second buy
  (4,918,143,722,940 vs 4,918,089,082,874) -- the cycle
  ratchets because each leg moves the real vaults the
  next leg prices off.
- Empty base vault: 6025 DivisionByZero, every hop, both
  directions. Empty quote vault: 6023 Overflow, every
  hop, both directions. Ghost ladder for zero vaults at
  depth 5: buy main 0 / P2 1 / P3 2 / P4 3 / P5 4 events,
  sell exactly reversed (main 4 / P2 3 / P3 2 / P4 1 /
  P5 0). Frozen vaults fail Token custom 17 with no site
  line, one event later than zero at buy vb1 (1 vs 0),
  buy vb2 (2 vs 1) and sell vq2 (4 vs 3), and at the same
  count elsewhere (buy vq1 0, buy vb5/vq5 4, sell vb1/vq1
  4). Absent or lamports-0 vaults fail 3012 with the
  zero-vault ghost ladder.
- Sell quote-vault ladder, finer than buy: vq1 0 and
  100,000 fail 6023 (4 ghosts), vq1 178,541 fails 6002
  ZeroQuoteAmount (4 ghosts) -- the computed payout rounds
  to zero after fees -- vq1 10^9 pays 1,451, fixture pays
  178,541. Buy quote-vault ladder has no 6002 step: vq1 0
  and 1 fail 6023 with 0 events, vq1 10^15 succeeds at the
  collapsed price above.
- LP supply is invisible to multi-hop but gates
  liquidity. Buy/sell with lp 0, 10^12, 2^63, P2 lp 0, P5
  lp 0 are all anchor-identical. Deposit with lp 0 fails
  6025 (fees.rs:21/:19, the LP math divides by supply);
  lp 1 fails 6024 Truncation (deposit.rs:77/:14); lp 10^6
  succeeds and the amounts prove proportional minting:
  base leg exactly the full vb1 balance
  673,696,395,912,745, quote leg gross 124,188,449,332
  (vault net 122,946,564,838, withheld 1,241,884,494 -- the
  tf100 gross-up on the full available quote), LP minted
  1,000,000, supply 10^6 -> 2 x 10^6. Withdraw with lp 0
  fails 6067 SeedLockViolation (withdraw.rs:6/:62:
  lp_supply must never drop below the circulating LP
  mint supply). The anchor deposit/withdraw pair
  (160,619,896 base + 29,610 quote in, 160,619,895 base
  + 29,018 quote out) leaves the next buy 42 below the
  anchor (5,207,955,235,849), the #91/#95 flooring dust.
- Withdraw with an empty base vault silently pays 0
  base. Withdraw 10^6 LP with vb1 0 burns the LP and
  pays the full quote leg (userquote +29,018, event
  base 0 / quote 29,312) with no failure; restoring vb1
  makes the next withdraw pay the full 160,619,895
  base. Proportional math gives 0, not an error -- the
  only silent-zero leg in the packet.
- Drain chains never partially fill. vb1 6 x 10^12 buys
  pay 47,775,373,553 -> 47,000,676,372 -> 46,244,670,694
  (tails shrink as vb1 drains); vb5 6 x 10^12 buys pay
  31,247,731,415 -> 29,508,534,497 -> 27,910,608,894
  (the tail vault caps the tail through the hop-5
  ratio, not through exhaustion). vq1 300,000 sells
  fail 6002 three times in a row; restoring vq1 pays
  the anchor 178,541 and the next sell pays 178,539,
  the plain second-sell value -- failed sells move
  nothing.
- Sweep needs vault funds, not just a bucket. After a
  buy the protocol sweep pays 4,563,570 gross (net
  4,517,934 to the protocol Token-2022 ATA), the creator
  sweep pays 123,394 (net 122,160), collect pays 122,160
  (net 120,938), and the next buy is the plain second
  buy 4,918,089,082,874 -- sweep/collect price-neutral at
  depth 5, as #92 pinned. But sweeping with vq1 zeroed
  fails 6023: the bucket is a bookkeeping field, the
  transfer still draws the real vault. Restoring vq1
  makes the sweep pay the full 4,563,570. A pre-seeded
  vault withheld 999,999 leaves the buy anchor-identical
  and the sweep unchanged (vault withheld 10,999,999
  after the buy: seed + buy 10,000,000). Note: in this
  transfer-fee fixture the sweep legs are the Token-2022
  variants (swp22/swc22/col22); the plain SPL sweep
  metas fail InvalidAccountData against the Token-2022
  vault, as the vault's owning program differs.
- Boost reads both vaults. Anchor boost (vq patch
  10^9) burns 5,338,379,201,831 base from vb1 against
  990,000,000 quote into vq1 (10^9 requested, 10,000,000
  withheld). vb1 0 fails 6001 ZeroBaseAmount
  (boost_burn.rs:50 / boost.rs:273); vq1 0 fails 6023
  (pool.rs:417 / boost_burn.rs:47). Boost with a
  10^6 boost-ATA against a 10^9 request fails 6088
  QuoteMintNotWritable after 2 events, with full
  rollback -- recorded as measured; the packet does not
  pin why a short ATA surfaces as a mint-writability
  error.
- Vaults are irrelevant to claims. A buy failed by
  vb1 0 (6025) is followed by a full token claim
  3,334,551 (claimed 222 -> 3,334,773, volume -> 0,
  last -> 21).
- Single-account restore is hybrid, as #96 pinned for
  pool bytes. Buy then vb1-restored buy pays
  4,956,530,009,526; buy then vb5-restored buy pays
  4,943,836,361,337; buy then sweep then vq1-restored
  buy pays 4,956,225,703,059. Only the sell-side vq1
  restore is inert: sell then vq1-restored sell pays
  178,539, the plain second-sell value (the sell
  moves vq1 by only 181,191 against a 10^11 balance).
  A pool-only restore is weaker still: buy with lp 0
  then lp-restored buy pays 4,917,913,117,978, below the
  plain second buy -- restoring the pool account alone
  cannot un-move the vaults. The vault walk shows the
  same split at scale: anchor buy -> vb1 10^15 buy
  7,285,628,298,925 -> vb1 restored buy 4,632,427,386,816
  -> buy 4,387,207,908,405 (the 10^15 buy drained the
  middle and tail vaults, and restoring vb1 alone cannot
  un-drain them).
- v2 mirrors multi-hop's vault gates with its own
  codes: v2 buy with vb1 0 fails 6016
  BuyMoreBaseAmountThanPoolReserves
  (constant_product.rs:21/:8) instead of multi-hop's
  6025; v2 buy/sell with vq1 0 fail 6023 as multi-hop
  does; v2 buy with vb1 frozen fails custom 17 with 0
  events (no ghost ladder on the single-hop leg). The
  v2 anchor buy spends 189 quote (vault quote +186,
  buyback 1) for 10^6 base.
- Transfer-fee variants: vault gates are tf-independent
  (vb1 0 -> 6025 and vq1 0 -> 6023 at tf0 and tf5000;
  vq1 0 sell -> 6023 at tf5000); tf5000 vb1 10^12 buy
  pays 4,038,158,575; tf5000 anchor buy pays
  2,668,075,748,732.

## Relation to earlier packets

- #3 established liquidity/trade interaction through
  available quote; this packet shows the trade leg
  itself prices off real vault balances on both sides
  of every hop at depth 5.
- #34 established the boost burn anchor
  (5,338,379,201,831 at vq 10^9); this packet adds the
  boost vault gates at depth 5 (vb1 0 -> 6001, vq1 0 ->
  6023, short boost-ATA -> 6088).
- #88 established vault/token-account validation
  slots; this packet extends the same slots to vault
  balances at depth 5 (zero -> 6025/6023, frozen ->
  custom 17, absent/lamports-0 -> 3012) with
  hop-position ghost ladders 0-4.
- #91 established amount thresholds and ceiling
  rounding; this packet shows the vault-side thresholds
  are CPMM ratios, not fixed amounts (tails rescale
  smoothly with vb1/vq1, then gate at zero).
- #92 established the window invariant and sweep/
  collect price neutrality; this packet quantifies the
  buy's vault rewrite per hop at depth 5, shows sweep
  still needs real vault funds, and re-confirms
  neutrality after sweep/collect.
- #96 established byte-level restore hybridity for
  pool accounts; this packet shows the same hybridity
  for single-vault restores (and the one inert case:
  sell-side vq1 restore).
- #98 established all of the above at true 3 hops; this
  packet is the depth-5 re-measurement. The depth-5
  deltas are: ghost ladders extended to 0-4 with exact
  sell reversal, lower tails on patched-vault buys (two
  extra hops of dust and fees), sell-side patched values
  identical to depth 3 (vq1 10^9 -> 1,451, vb1 10^15 ->
  120,282), and the terminal vault (vb5) as a tail cap
  through the hop-5 ratio.
- #124 established deposit/withdraw vq and burn ladders
  at depth 5; this packet adds the LP-supply gates and
  the silent-zero withdraw leg at the same depth.
- #151 established wallet-side thresholds at depth 5;
  this packet is the pool-side counterpart -- vault
  balances, not user balances, gate and price the chain.

## Limits

- Patches are applied directly to account data between
  steps; they are not transactions and leave no receipt.
  The receipt stream pins the before/after state of every
  real step, and producer.py records every patch in the
  case definitions, so the sequence is reproducible from
  the packet files -- but a patch itself has no signature
  to verify.
- The "restore" steps rewrite one account only (vault
  restores rewrite the vault token account; the LP
  restore step rewrites the full main-pool snapshot,
  including vq and fee buckets). The hybrid-state values
  they produce are harness artifacts of that method, not
  program behaviour on a real chain; they are reported
  here because they identify exactly which accounts feed
  the next trade's price.
- The boost short-ATA 6088 is recorded as a measured
  code and site only; the packet does not pin the
  mechanism linking a short boost-ATA balance to a
  mint-writability error.
- The CPMM ratio reading of the vault patches (output
  scaling with vb1/vq1) is inferred from the measured
  ladder, not from a source line: the checked-out
  source does not expose the hop pricing formula in a
  single pinned line.
- Only the TRUE 5-hop route (three_amm + g4 + g5, final
  output U5) is used; 3-hop routes are covered by #98
  and are not re-run here.
- In this transfer-fee fixture the sweep legs measured
  are the Token-2022 variants (swp22/swc22/col22). The
  plain SPL sweep metas fail InvalidAccountData against
  the Token-2022 vault; that failure is a fixture
  property of the metas, not a program finding, and is
  reported here so the packet's sweep numbers are not
  misread as plain-sweep numbers.

## Reproduce

`python3 producer.py` rebuilds the receipts under
`runtime/` (10 per part, 38 parts); `python3 verify.py`
re-checks signatures, deltas, withheld, pool/UVA/GVA/
GlobalConfig states, decoded events, error codes, rollback,
and three-image agreement from the packet files alone.

Made via @slopdotcash
