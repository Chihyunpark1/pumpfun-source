# research: split x boost x tf boost gate and authority chains at true 5 hops

3rd run packet #155. The #101 boost gate/authority findings (boost
gates, authority checks, gate ordering, authority rotation effects)
re-measured on a TRUE 5-hop split x boost x tf chain: `three_amm` +
`g4` + `g5`, final output U5. Every successful swap below carries
exactly 5 hop events (buy disc `67f4521f2cf57777` len 508, sell disc
`3e2f370aa503dc2a` len 449); the hop count in this name matches the
route in code.

## Problem

At depth 3 (#101) the boost gates formed one total order, the
authority check was a signature check, set_boost_authority moved
the stored authority, and admin / fee authority / boost authority
were three separate fields. Depth 5 adds two questions #101 could
not answer: does that order survive two more hops, and does it
apply to hop-pool boosts at all -- where #154 already showed two
differences from the main pool (a 10^12 hop bucket does not trap,
and a short hop ATA is spent rather than failing 6088)? This
packet pins the gates at depth 5: authority basics and rotation
on the main pool, admin/fee-authority separation, the
disable/toggle/pool-flag matrix, all gate-order duels and
triples, hop-pool (P5 terminal, P3 middle) gate order,
failure recovery, transfer-fee variants, and post-trade /
multi-user boosts.

## Cases

108 cases, 588 receipts, 59 parts (58x10 + 8), each run on three
program images (original, control, candidate). Transfer fee is 100
bps unless a case says otherwise. Main boosts use a vq patch of
10^9 unless a case says otherwise; the anchor boost burns
**5,338,379,201,831**. Hop boosts use a P5 vq patch of 10^9 unless
a case says otherwise; the P5 anchor burns **999,997,999**.

- **A, authority basics, main (14):** anchor; stored outsider /
  zero with payer-signed boost; stored outsider with
  outsider-signed boost; stored payer with outsider-signed
  boost; readonly authority meta (payer / outsider / zero key);
  authority restore by field patch; rotation chain
  (admin-signed rotation to outsider, outsider-signed anchor,
  payer-signed failure, outsider-signed rotation failure,
  admin-signed rotation back, payer-signed decay burn);
  unsigned rotation; outsider-signed rotation; zero-key
  rotation and admin-signed recovery.
- **B, admin / fee-authority separation (8):** update_admin to
  outsider then boost; admin rotation with disable; admin
  rotation with boost toggle; admin rotation with
  update_fee_config; fee authority patched to outsider / zero
  then update_fee_config; fee authority patched then disable;
  fee authority patched then boost.
- **C, disable / toggle / pool-flag matrix, main (14):**
  sell / create / deposit / withdraw bits; buy bit (with
  clear-and-reboost); buy+sell bits; all five bits; boost
  toggle off/on; mayhem toggle off/on; cashback toggle off/on;
  main-pool cashback / mayhem / both flags; P5 cashback flag.
- **D, gate-order duels and triples, main (30):** every pair
  among authority, enabled-off, buy-disable, window-0,
  ATA-zero, quote-vault-zero, base-vault-zero, bucket-10^12,
  and short ATA that the order predicts, plus six triples
  (auth+off+buydis, off+buydis+window0, buydis+vb0+vq0,
  auth+off+window0, ata0+vq0+vb0, window0+vb0+vq0).
- **E, hop-pool gates (21):** P5 fresh / anchor / authority /
  outsider-signed / payer-signed-outsider / enabled-off /
  buy-disable / sell-disable / window-0 with vb5 emptied /
  ATA-zero / ATA-zero with vb5 emptied / quote-vault-zero
  with base-vault-zero / bucket-trap with vb5 emptied /
  short-ATA with buy-disable / auth+off / off+buydis; P3
  fresh / authority / enabled-off / buy-disable / auth+off.
- **F, failure recovery / leak checks (9):** baseline buy;
  failed boost then buy; failed boost then protocol sweep;
  failed boost then token claim; bucket-trap failure then
  field restore then boost; zero-ATA failure then restore;
  empty-base-vault failure then restore; window-0 failure
  then mid-case vq patch then boost; four-step failure
  sequence.
- **G, transfer-fee variants (8):** authority at tf0 / tf5000;
  enabled-off at tf5000; buy-disable at tf0; outsider-signed
  boost at tf5000; window-0 at tf5000; P5 authority at
  tf5000; P5 outsider-signed boost at tf5000.
- **H, post-trade / multi-user (4):** buy then payer-signed
  boost; buy then outsider-signed boost (stored outsider);
  buy then two outsider-signed boosts; two outsider-signed
  boosts on a fresh pool.

## Result

All three images agree: **0 divergent cases**.

- Anchor: main boost **5,338,379,201,831** (tf100, vq patch
  10^9); P5 boost **999,997,999** (P5 vq patch 10^9).
- Authority is a signature check, not a key-equality check.
  Stored outsider or zero with a payer-signed boost fails
  **6005 InvalidAdmin**, 0 events. Stored outsider with an
  outsider-signed boost burns the anchor exactly. Stored
  payer with an outsider-signed boost fails 6005. A readonly
  authority meta passes only when the key is the fee payer
  (anchor burn) and fails **3010 AccountNotSigner** for an
  outsider or zero key -- the payer case passes only because
  the payer signed as fee payer.
- set_boost_authority (112-byte event, disc
  `5980f08d5bca4769`) is **admin-gated, not
  boost-authority-gated** -- the depth-5 correction to a
  loose reading of #101. Rotation to outsider by the admin
  succeeds and the outsider-signed boost then burns the
  anchor; a rotation back attempted by the outsider fails
  6005, while a rotation back by the admin succeeds and
  the payer boost then burns the decay value
  5,254,441,549,265. Rotation to the zero key is recoverable
  the same way: admin-signed rotation back succeeds and
  the next boost burns the anchor -- a zero boost authority
  is not a bricked state while the admin key is intact. An
  unsigned rotation fails 3010 and leaves the stored
  authority unchanged.
- Admin, fee authority, and boost authority are three
  separate fields. After update_admin to the outsider, a
  payer-signed boost still burns the anchor, while disable,
  boost toggle, and update_fee_config by the payer fail
  6005 and by the outsider succeed (disable by outsider
  sets the buy bit, toggle by outsider turns boost off
  then on, update_fee_config by outsider writes lp 30 /
  proto 40 and restores to fixture lp 20 / proto 5).
  Patching the fee authority to outsider, zero, or
  0x63x32 changes no outcome: update_fee_config by the
  payer still succeeds, disable by the payer still sets
  the buy bit (boost then 6020, cleared then anchor), and
  the boost still burns the anchor.
- Only the buy disable bit gates a boost. Sell / create /
  deposit / withdraw bits, both global mode toggles, main
  pool cashback / mayhem / both flags, and a P5 cashback
  flag all leave the anchor burn byte-identical. Buy bit
  alone, buy+sell, or all five bits all fail **6020**;
  clearing the bit restores the anchor. Boost toggle off
  fails **6066**, on restores the anchor.
- The gate order from #101 holds exactly at depth 5 on the
  main pool, across all 30 duel/triple cases: **6005
  (authority) > 6066 (boost enabled) > 6020 (buy-disable) >
  6065 (window zero) > 6002 (boost ATA zero) > 6023
  (quote-side: empty quote vault or hop-1 bucket at 10^12)
  > 6001 (base vault empty).** Authority beats off,
  buy-disable, window-0, bucket-10^12, empty base vault,
  and zero ATA. Enabled-off beats buy-disable, window-0,
  bucket, base vault, and ATA. Buy-disable beats window-0,
  both vaults, bucket, and short ATA (the 6088 check never
  surfaces against an earlier gate). Window-0 beats empty
  base vault and zero ATA. ATA-zero beats both vaults and
  bucket-10^12. Quote-vault-zero beats base-vault-zero
  (6023), bucket-10^12 beats base-vault-zero (6023), and
  quote-vault-zero beats short ATA (6023). Triples agree:
  auth+off+buydis 6005, off+buydis+window0 6066,
  buydis+vb0+vq0 6020, auth+off+window0 6005,
  ata0+vq0+vb0 6002, window0+vb0+vq0 6065.
- Hop-pool boosts use the same order, with the two
  depth-5 exceptions. P5 matches main exactly except
  where #154 already diverged: authority 6005,
  enabled-off 6066, buy-disable 6020, window-0 6065
  (including window-0 with vb5 emptied), ATA-zero 6002
  (including ATA-zero with vb5 emptied), quote-vault-zero
  with base-vault-zero 6023, auth+off 6005,
  off+buydis 6066, sell-disable anchor, and a short ATA
  under buy-disable 6020. The bucket exception is pinned
  as a duel: **P5 bucket 10^12 with vb5 emptied fails
  6001, not 6023** -- the hop bucket does not feed the
  overflowing computation, so the vault gate surfaces
  where the main pool would fail 6023. The middle hop P3
  (window closed on this fixture) matches too: fresh
  6065, authority 6005, enabled-off 6066, buy-disable
  6020, auth+off 6005.
- Failure recovery: a failed boost leaves nothing behind.
  The next 5-hop buy pays the vq-patched buy tail
  5,167,125,538,753 (the vq-patched baseline from #154, not
  the unpatched anchor tail 5,207,955,235,891 -- the two
  buy cases differ by the vq patch, not by the failed
  boost); a protocol sweep after a failed boost pays
  2,488 gross (2,463 net); a token claim after a failed
  boost still pays the full 3,334,551. Bucket-10^12
  (6023), zero-ATA (6002), empty-base-vault (6001), and
  window-0 (6065, then a mid-case vq patch to 10^9)
  failures all recover the anchor burn exactly. A
  four-step failure sequence composes step to step with
  no residue: 6005, 6005, 6066, anchor.
- Transfer-fee blindness of the gates: authority 6005 at
  tf0 and tf5000, enabled-off 6066 at tf5000, buy-disable
  6020 at tf0, window-0 6065 at tf5000, and an
  outsider-signed boost with stored outsider authority at
  tf5000 burns 2,706,767,012,738 (the tf5000 anchor). Hop
  gates are tf-blind too: P5 authority 6005 at tf5000 and
  an outsider-signed P5 boost at tf5000 burns 999,997,999.
- Post-trade / multi-user: after a 5-hop buy, a
  payer-signed boost and an outsider-signed boost (stored
  outsider) both burn the post-buy value 5,255,205,915,165;
  two outsider-signed boosts in a row after a buy burn
  5,255,205,915,165 then 5,173,214,684,656; two
  outsider-signed boosts on a fresh pool burn the anchor
  then the decay value 5,254,441,549,265. The buyer of the
  previous trade is irrelevant to the burn.

## Limits

- Gate patches (stored authority values, disable bits,
  toggle states, bucket seeds, vault amounts) are applied
  directly to account state before or between steps; they
  pin gate behavior, not the path by which an account
  could reach that state on-chain. Field restores in the
  recovery cases are harness resets, not on-chain
  instructions.
- The set_boost_authority event is pinned by disc and
  length only (112 bytes, disc `5980f08d5bca4769`); its
  fields are not decoded in this packet.
- Only the TRUE 5-hop route (three_amm + g4 + g5, final
  output U5) is used; 3-hop routes are covered by #101
  and are not re-run here.
- No source change is proposed; no claim is made about
  the program beyond the measured cases.

Made via @slopdotcash
