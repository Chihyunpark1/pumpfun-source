# Boost window and burn chains at true 5 hops (split x boost x tf)

## Problem

Packet #100 measured the boost window and burn on a 3-hop split x
boost x tf chain: the window is `vq + protocol_fees + creator_fees`
(pool.rs `total_virtual_quote_reserves`), a fresh pool has window
exactly 0, the gate and the burn are two different reads (the burn
reads the vq field, not the buckets), and hop-pool boosts were pinned
only at window 0. This packet re-measures every one of those
findings on a true 5-hop chain (three_amm + g4 + g5, final output
U5) under transfer fee, and asks whether the main-pool burn, the
gate order, the decay ladder, and the trap behaviour survive depth
-- and what a terminal-hop boost actually burns when its own window
is open, when its ATA is short, and when its buckets are seeded to
the trap value.

All measurements are receipts from three program images (original,
control, candidate) run on the same fixture. All three images agree
on every step: 0 divergent cases.

## Cases

81 cases, 372 receipts, 38 parts (37x10 + 2). Anchor (tf100, main
vq field patched to 10^9): a 10^9-quote boost burns
5,338,379,201,831 (used 10^9, quote-after 123,936,690,720,
base-after 668,358,016,710,914, boost ATA remaining
999,000,000,000).

- A (19): window components, single main boost -- vq field ladder
  (10^6/10^8/10^9/10^10/10^12, 0, -10^9, 1, fixture), protocol-bucket
  seeds (0/10^6/10^9/10^11/10^12), creator-bucket seeds
  (0/10^9/10^11/10^12), both buckets 10^9, all at vq 10^9 unless
  noted; plus the fresh-pool boost (window 0).
- F (6): same window sum, different compositions -- window
  1,000,125,882 built as (vq 10^9 + fixture buckets), (vq
  10^9+123,394 + creator 0), (vq 10^9+2,488 + protocol 0), (vq
  10^9+125,882 + both buckets 0); and window 3,000,125,882 built
  as (vq 10^9 + both buckets 10^9) versus (vq 3x10^9 + fixture
  buckets).
- B (17): window motion through legs -- buy/sell then boost,
  buy+sell then boost, buy then sweep then boost, buy then
  sweep+collect then boost, two/three/four boosts in a row, buy
  then two boosts, fresh-pool buy/sell then boost, deposit then
  boost, deposit+withdraw then boost, buy then deposit then
  boost, v2 buy then boost, legacy buy then boost, token claim
  then boost.
- C (8): authority / flag gates -- boost authority outsider,
  zero, restore to payer; boost-enabled off, off-then-on via
  toggle_boost; buy-disabled then boost, sell-disabled then
  boost, buy-disabled then re-enable then boost.
- D (11): transfer fee and requested amount -- boost at tf0 /
  tf5000, buy then boost at tf0 / tf5000, requested
  10^6/10^8/2x10^9/10^10/10^12/1/0.
- E (6): failure and recovery -- base-vault-zero, quote-vault-zero,
  boost-ATA-short, boost-ATA-zero boosts; 10^12 bucket trap then
  field restore then boost; trap then restore then a trade.
- H (10): hop-pool boosts -- P5 fresh, P5 vq 10^9, P5 vq + buy,
  P5 vq twice, P5 vq with short ATA, P5 bucket seeds, P5 bucket
  trap, P5 at tf0 / tf5000, P4 vq patch with a main boost.
- G (4): vault balances at fixed window -- base vault 10^12 /
  10^15, quote vault 10^12, all at vq 10^9; base vault 10^12 buy
  then boost.

## Result

- Main-pool burn does not move with depth: the anchor
  5,338,379,201,831, the vq ladder (10^6 -> 5,381,409,217,895;
  10^8 -> 5,377,114,041,125; 10^9 -> 5,338,379,201,831; 10^10 ->
  4,979,661,866,360; 10^12 -> 593,413,700,956), vq 0 ->
  5,381,452,638,525, vq -10^9 -> 5,425,226,816,983, and vq 1 ->
  5,381,452,638,482 are all identical to the #100 3-hop values.
  There is no zero/negative clamp on the burn; only the
  exact-zero window sum gates with 6065.
- The burn does NOT read the fee buckets at depth 5 either:
  protocol or creator seeds from 0 to 10^11 leave the anchor burn
  byte-identical, and a 10^9 + 10^9 bucket seed burns exactly the
  anchor. Buckets enter only the gate: a bucket at 10^12 fails
  the boost with 6023 Overflow and 0 events (protocol and
  creator alike).
- Same window sum, different compositions, at depth 5: the #100
  splits reproduce exactly -- vq 10^9 + fixture buckets
  5,338,379,201,831; vq 10^9+123,394 + creator 0
  5,338,373,929,374; vq 10^9+2,488 + protocol 0
  5,338,379,095,522; vq 10^9+125,882 + both buckets 0
  5,338,373,823,065 (slope about -42.73 per vq-field unit).
  Window 3,000,125,882 as vq 10^9 + both buckets 10^9 burns the
  anchor, while as vq 3x10^9 + fixture buckets it burns
  5,254,268,308,887 -- the window sum is a gate input, not the
  burn input.
- Window motion through legs: a fresh-pool 5-hop buy leaves the
  window at 0 (vq -4,686,964 + protocol 4,563,570 + creator
  123,394), so the next boost still fails 6065; a fresh-pool
  sell likewise. Buy then boost (vq patch 10^9):
  5,255,205,915,165. Sell then boost: 5,338,394,947,549.
  Buy+sell then boost: 5,255,222,206,552. Buy then sweep then
  boost and buy then sweep+collect then boost are
  burn-identical to buy then boost -- a sweep is burn-neutral
  at depth 5 too.
- Boost decay at depth 5: 5,338,379,201,831 ->
  5,254,441,549,265 -> 5,172,468,136,601 -> 5,092,398,150,835
  (about 1.56% per 10^9-quote boost, as at depth 3). After a buy
  the second boost is 5,173,214,684,656 on the drained vault.
- Deposit nudges the burn: deposit 10^6 LP then boost
  5,338,379,211,910 (vq +238, burn +10,079); deposit+withdraw
  then boost restores the anchor burn exactly
  (5,338,379,201,831, vq field 999,999,999 vs 10^9 -- a 1-unit
  rounding residue). Buy then deposit then boost:
  5,255,205,925,004. v2 and legacy buys move the main burn by
  the same -15,829 (5,338,379,186,002); a token claim leaves it
  byte-identical.
- Authority/flag gates, in check order: boost authority outsider
  or zero -> 6005 InvalidAdmin, 0 events (before the window
  check); boost-enabled off -> 6066, 0 events (off-then-on via
  toggle_boost restores the anchor burn exactly); buy-disabled
  config -> 6020 on boost, and re-enabling restores the anchor
  burn; sell-disabled config leaves the boost at the anchor.
  Restoring the payer authority after a 6005 failure restores
  the anchor burn.
- Transfer fee (gross requested 10^9): tf0 ->
  5,391,870,655,895; tf100 -> 5,338,379,201,831 (net 990,000,000
  credited); tf5000 -> 2,706,767,012,738 (net 500,000,000
  credited). Buy then boost at tf0: 5,307,028,789,111; at
  tf5000: 2,685,302,061,999.
- Requested-amount ladder (tf100, vq 10^9): 10^6 ->
  5,380,970,054; 10^8 -> 537,672,386,159; 2x10^9 ->
  10,592,820,756,404; 10^10 -> 49,830,102,507,836. Requested
  10^12 uses the full 10^12, burns 598,735,502,793,632, drains
  the boost ATA to 0 remaining, and then fails 6088 with both
  events emitted (transaction rolls back). Requested 0 and
  requested 1 both fail 6002 with 0 events -- a small request
  is a gate failure, not a small burn.
- Vault gates: empty base vault -> 6001, empty quote vault ->
  6023, zero boost ATA -> 6002, all 0 events. A boost ATA
  holding only 10^6 spends exactly 10^6 (burn 5,380,970,054,
  identical to the requested-10^6 burn), emits both events,
  then fails 6088 and rolls back -- so 6088 means "requested
  exceeds the boost ATA balance", with the partial spend
  visible in the event but not in state.
- Recovery from the 10^12 bucket trap: restoring the bucket
  fields to the post-setup snapshot recovers the anchor burn
  exactly. A trade after that recovery pays 5,087,534,167,771
  -- lower than the pre-boost buy tail 5,167,125,538,753
  because the successful boost drained the base vault; the
  trap failure itself left no other state behind. On-chain
  this is not an escape: the sweep that would drain the
  bucket also fails 6023.
- Hop-pool boosts (P5 terminal, SPL-derived ATA): a fresh P5
  boost fails 6065; with P5 vq patched to 10^9 it burns
  999,997,999 (used 10^9, quote-after 1,000,001,000,000,000,
  base-after 999,999,000,002,001, remaining 999,000,000,000).
  A second P5 boost burns 999,995,999 (decay of only 2,000,
  not 1.56% -- the hop burn curve is far flatter). After a
  5-hop buy the P5 boost burns 989,598,940. P5 boosts are
  tf-blind (tf0 and tf5000 both 999,997,999 -- the hop quote
  mint is SPL, outside the quote-mint transfer-fee
  override).
- Hop-pool differences (genuine depth-5 pins): a P5 protocol
  bucket at 10^12 does NOT trap the hop boost -- it burns the
  anchor 999,997,999, where the same seed on the main pool
  fails 6023. And a short hop boost ATA does NOT fail 6088:
  a P5 boost with a 10^6 ATA succeeds, spending exactly 10^6
  (used 10^6, burned 999,997, remaining 0), closing the SPL
  ATA and refunding its lamports to the payer (dPAYER
  +1,000,999,995,000). The main-pool 6088 rule does not
  extend to hop boosts. A P4 vq patch leaves the main boost
  at the anchor -- hop windows do not move the main burn.
- Vault balances at fixed window: vb1 10^12 ->
  7,924,013,300; vb1 10^15 -> 7,924,013,300,677 (1000x the
  vault, 1000x the burn -- linear in the base vault). A 10^12
  quote vault at vq 10^9 burns 665,634,817,992. A 10^12 base
  vault buy then boost burns 7,799,482,130.

## Limits

- These burns were measured on one fixture route (the split x
  boost x tf 5-hop chain with this pool set, this fee table,
  and these token programs). Other routes, other pool states,
  and other fee-table shapes may burn differently; the packet
  pins this route's behaviour, not a general rule.
- No closed-form burn formula is claimed: the packet pins the
  empirical slopes (vq field -42.73/unit at fixture vaults,
  linear in vb1) and the sweep-neutral sum, not a derived curve
  equation.
- The hop-boost trap-blindness and short-ATA success are
  recorded as measured code and event outcomes; the packet
  does not pin the mechanism linking the hop pool's SPL quote
  mint to the missing 6023/6088 gates.
- The 10^12 bucket recovery uses a harness field restore; it
  does not demonstrate an on-chain recovery instruction.
- Agreement across the three images is agreement on these 372
  receipts only. It is not a claim about the whole program.

## Reproduce

`python3 producer.py` rebuilds the receipts under `runtime/` (10
per part, 38 parts); `python3 verify.py` re-checks signatures,
deltas, withheld, pool/UVA/GVA/GlobalConfig states, decoded
events, error codes, rollback, and three-image agreement from
the packet files alone.

Made via @slopdotcash
