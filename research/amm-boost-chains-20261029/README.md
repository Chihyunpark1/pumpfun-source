# research: boost_buy_and_burn chained into trades, liquidity, sweeps, and collects

## Problem

`boost_buy_and_burn` was pinned before only in isolation (2nd
#26: vault drain, transfer-fee legs, gates; 2nd #37: partial
spend under tf; 2nd #40: small band and virtual-reserve drift),
never chained into the fee pipes. Three questions were open.
First, after a boost burns base out of the pool vault and tops
up the quote vault, do the following trade legs move, and does
the trade bucket still sweep/collect cleanly? Second, does the
boost window itself survive trades, sweeps, and liquidity --
which of those change `total_virtual_quote_reserves`
(vq + protocol_fees + creator_fees), the value `can_boost`
tests? Third, how does a boost behave under transfer fee, and
what does a full vault drain cost in the Token-2022 world?

## Cases

23 cases, 57 steps, 171 receipts (each step run on the original,
control (#424), and candidate (#427) images). All amounts are
token amounts unless noted. Pool state is
(virtual_quote_reserves i128, protocol_fees, creator_fees,
lp_supply). The boostable fixture pool is (1,000,000,000, 2,488,
123,394, 4,194,352,106,721): the fixture vq is patched from
-125,882 to 10^9, because the unpatched fixture sums to exactly
0 (-125,882 + 2,488 + 123,394) and cannot boost at all. The
boost vault authority is the fee payer (global config boost
authority patched to the payer, boost enabled). The quote mint
is Token-2022 (transfer-fee override, bps 0 unless noted), so
the boost vault ATA is a 178-byte Token-2022 account; it is
native, so its token transfers carry lamports 1:1. Transfer fee
is applied to the quote mint only, via the
`transferfee(quote, bps, 2**64-1)` override.

Family A -- boost anchors on the boostable pool:

- `a-boost-1e9`: boost(10^9, 0) burns 5,391,870,655,895 base,
  vault quote +10^9, boost vault 10^12 -> 999x10^9. Pool fields
  byte-identical. Two events: a 512-byte BuyEvent (disc
  67f4521f2cf57777) and a 208-byte BoostBuyAndBurnEvent (disc
  3f451c16305cc2b9, requested 10^9, used 10^9, burned
  5,391,870,655,895, vq 10^9, quote_after 123,946,690,720,
  base_after 668,304,525,256,850, remaining 999x10^9).
- `a-boost-2e9`: boost(2x10^9, 0) burns 10,698,119,843,084 --
  less than twice the 10^9 burn (curve convexity), vault quote
  +2x10^9, remaining 998x10^9.
- `a-boost-amount1`: boost(1, 0) fails 6001 ZeroBaseAmount
  (boost.rs:273) with full rollback.
- `a-boost-amount2`: boost(2, 0) burns 5,435, vault quote +2,
  remaining 999,999,999,998.
- `a-boost-drain-writable`: boost(10^12, 0) with a writable
  quote mint burns 599,402,446,286,043, closes the boost vault
  ATA, and splits its lamports: 10^12 ride the native token
  transfer into the pool quote vault, and 10^9 - 5,000 fee
  refunds to the payer (payer +999,995,000).
- `a-boost-drain-nowrite-fail`: the same drain with a
  read-only quote mint fails 6088 QuoteMintNotWritable
  (boost.rs:403) AFTER emitting both events -- ghost events
  with full rollback (the harvest-to-mint step needs the
  writable mint even at bps 0, because the mint carries a
  transfer-fee extension).
- `a-boost-min-exact` / `a-boost-min-plus1`: min == burned
  succeeds; min == burned+1 fails 6004 ExceededSlippage
  (boost.rs:274) with full rollback.

Family B -- boost into trades, sweeps, collects:

- `b-boost-buy-swc-col`: boost, then buy_v2(10^10) spends
  1,893,007 (vs 1,862,827 unboosted on the same vq=10^9 pool),
  vaults 1,884,313, buyback 8,694, pool (999,985,697, 11,182,
  129,003); sweep drains 129,003, collect pays 129,003.
- `b-boost-sell-swc-col`: boost, then sell_v2(10^9) receipts
  184,622 (vault -185,491, buyback 869, pool (999,998,569,
  3,358, 123,955)); sweep/collect drain 123,955.
- `b-boost-buyx-swc-col`: boost, then buy_exact_v2(10^7, 1)
  outs 52,822,650,212 (vault +9,954,074, buyback 45,926, pool
  (999,924,444, 48,414, 153,024)); sweep/collect drain
  153,024.
- `b-buy-boost-buy`: buy, boost, buy. The first buy spends
  the anchor 1,862,827; the boost burns 5,391,711,213,454
  (slightly less than the fresh boost -- the vaults moved);
  the second buy spends 1,893,064 (pool (999,971,619, 19,739,
  134,524)). A trade does not close the boost window.
- `b-boost-boost-buy`: two boosts (burns 5,391,870,655,895
  then 5,306,249,181,882), then buy spends 1,923,431 (pool
  (999,985,466, 11,322, 129,094)). Boosts compose: pool
  fields never change, so the window never closes.
- `b-boost-buy-buy`: boost, buy, buy. Second buy spends
  1,893,065 (pool (999,971,392, 19,877, 134,613)) -- one
  more than the buy-boost-buy second buy, because the boost
  ran before both trades.

Family C -- liquidity drifts the window on a boostable pool:

- `c-dep-boost-buy-swc-col`: dep-1e9 moves vq 10^9 ->
  1,000,238,445 (floor: effective_virtual x amount / supply),
  then boost burns 5,391,880,941,907, then buy spends
  1,892,999 (pool (1,000,224,142, 11,182, 129,003));
  sweep/collect drain 129,003.
- `c-wd-boost-sell-swc-col`: wd-1e9 moves vq 10^9 ->
  999,761,554 (ceil), then boost burns 5,391,860,365,016,
  then sell receipts 184,623 (pool (999,760,123, 3,358,
  123,955)); sweep/collect drain 123,955.
- `c-dep-wd-boost-buy`: dep then wd leaves vq at 999,999,999
  (drift -1: floor in, ceil out) and vault amounts +1 lamport
  each; the post-round-trip boost still burns exactly
  5,391,870,655,895, and the buy spends 1,893,007 (pool
  (999,985,696, 11,182, 129,003)).

Family D -- boost under transfer fee:

- `d-boost-tf100`: boost(10^9, 0) under tf100 burns only
  5,338,379,201,831 (the curve sees the net 990,000,000),
  vault nets 990,000,000, withheld 10,000,000, boost event
  quote_after 123,936,690,720 (net). Vault lamports move the
  gross 10^9 (native transfer).
- `d-boost-tf100-buy-swc-col`: tf boost, then tf buy spends
  1,911,735 gross (vault net +1,884,012, buyback net +8,605,
  withheld 19,031 + 87; event reports the pre-tf uin
  1,892,704); sweep nets 127,712 (gross 129,003, withheld
  1,291), collect nets 126,434 (withheld 1,278, vault
  withheld 1,291 stranded). Events report gross per hop.
- `d-boost-tf10000-fail`: boost under tf10000 fails 6002
  ZeroQuoteAmount (boost.rs:255) -- net 0 -- with full
  rollback.

Family E -- boost gates in chain:

- `e-fresh-boost-fail`: on the unpatched fixture pool (sum
  exactly 0), boost fails 6065 PoolCannotBoost
  (boost.rs:245) with full rollback. No trade, sweep, or
  liquidity step on the fixture pool opens the window,
  because all of them preserve the sum at 0.
- `e-sweep-boost-collect`: sweep moves the seed 123,394 into
  the creator vault ATA (vq 10^9 -> 1,000,123,394, cf -> 0,
  sum unchanged), then boost still succeeds (burns
  5,391,870,655,895 -- boost ignores buckets), then collect
  pays 123,394.
- `e-mayhem-boost-buy-swc-col`: mayhem pool boost, then buy
  spends the same 1,893,007 with buyback 0 (vault takes the
  full 1,893,007, pool (999,977,003, 19,876, 129,003));
  sweep/collect drain 129,003.

## Result

- Boost is a price mover, not a fee pipe: it burns base and
  tops up quote without touching pool fields or accruing
  anything, so the next trade reprices (buy +30,180 spend
  vs the unboosted anchor on the same pool) while the trade
  bucket sweeps/collects exactly as usual.
- The boost window is a sum, not a flag: `can_boost` tests
  vq + protocol_fees + creator_fees != 0. The fixture pool
  sits at exactly 0, so it can never boost; trades and
  sweeps preserve the sum (they move vq and buckets by equal
  and opposite amounts), while liquidity drifts it by
  floor/ceil rounding (+238,445 in, -238,446 out at this
  scale), which is the only in-protocol way the window
  opens or moves on a boostable pool.
- Boosts compose freely: pool fields are untouched, so a
  second boost burns on the moved vaults (second burn
  smaller: 5,306,249,181,882 after the first 5,391,870,655,895)
  and a boost after a trade or a sweep works unchanged.
- Under tf the boost curve sees the net, not the gross
  (burn drops 5,391,870,655,895 -> 5,338,379,201,831 at
  tf100), and the drain-close path needs a writable quote
  mint whenever the mint carries a transfer-fee extension --
  even at bps 0 -- failing 6088 after emitting both events
  if the mint is read-only.
- No original-vs-rebuilt divergence: all 23 cases agree
  across the original, control (#424), and candidate (#427)
  images (observed surface, error codes, rollback, events).
  Error sites are recorded per image in the report and are
  not compared across images, because original and rebuilt
  sources differ in line numbers.

## Verification

Run `python3 verify.py` from this directory. It checks, from the
packet files alone (plus the three program images):

- MANIFEST.json lists every packet file with a matching sha256.
- runtime/report.json.gz: 23 cases, 171 receipts, 18 parts
  (17x10 + 1), part sha256/byte counts match the part files.
- Every receipt transaction parses (solders) and all signatures
  verify.
- Every receipt's recorded before/after snapshots reproduce the
  report's expected values: fee-payer lamport deltas, the
  token-leg deltas, lamport deltas for the quote accounts,
  withheld balances after each step, pool state, volume
  accumulator state, and decoded event fields.
- Failure steps roll back every watched account except the fee
  payer (fee 5,000) and carry the expected error code plus the
  recorded per-image site line in their logs.
- The observed surface of every case is identical across the
  original, control, and candidate images.
- The three program images hash to the values recorded in the
  report.

## Limits

- The boostable pool patches vq to 10^9 at setup (the
  unpatched fixture cannot boost); the mayhem case patches
  the is_mayhem flag. The mayhem program itself is not in the
  sparse checkout, so the mayhem buyback-zero result is
  recorded as observed behavior only.
- The boost vault ATA is a native Token-2022 account in this
  fixture, so token transfers carry lamports 1:1 and the
  drain close splits lamports (10^12 to the pool quote vault,
  10^9 - fee to the payer); a non-native boost vault ATA
  would show different lamport legs.
- The transfer-fee override applies to the quote mint only
  with max fee 2**64-1; the tf10000 boost failure and the
  tf100 sweep/collect legs are specific to that
  configuration.
- No source change is proposed: this packet pins behavior only.
