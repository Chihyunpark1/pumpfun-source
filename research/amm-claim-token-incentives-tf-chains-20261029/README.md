# claim_token_incentives under a transfer fee on the incentive mint

## Problem

3rd #20 chained trades into `claim_token_incentives` and then into
sweep -> collect, but every incentive transfer there ran on a plain
SPL-token mint with no fee. This packet puts a Token-2022
transfer-fee extension on the incentive mint itself and asks what
the claim actually delivers: the handler computes a gross reward
and transfers it, so the Token-2022 program withholds part of it
into the user's own ATA -- while the claim event and the
accumulator's `total_claimed` keep reporting the gross amount.
The packet pins the gross/net split at tf100, tf5000, and
tf10000, the ceil rounding on a 111-token claim, the maxfee cap,
the `needs_claim` flag not gating the claim, the program/ATA
binding errors, and the full chain into trade -> sweep ->
collect, in single VMs, one signed transaction per step, on
three program images (original, #424 control, #427 candidate).

## Fixture

The repository liquidity fixture: pool
`GseMAnNDvntR5uFePZ51yZBXzNSn7GdFPkfHwfr6d77J`, base vault
673,696,395,912,745, quote vault 122,946,690,720, LP supply
4,194,352,106,721, pool protocol_fees 2,488, creator_fees 123,394,
virtual_quote_reserves -125,882, disable_flags 0, clock slot 100.
Trade steps run at timestamp 1234567890; token-claim steps run
at timestamp 21 so the claim's day math is exercisable (global
accumulator start 20, end 49, period 1, supplies [1000]*30,
volumes [100]*30, incentive mint
`GGfoM4FJeQ8CXTXhaWiekqRQAtYVDNAKHDdJAu8PrHtm`, vault 10^9,
user incentive ATA 17). The incentive mint carries a
synthesized Token-2022 transfer-fee extension (post-hoc: the
claim path cannot put a fee on an incentive mint by itself);
its vault and user ATAs are 182-byte Token-2022 accounts
(withheld at offset 174) owned by Token-2022, and the claim's
token-program account is Token-2022. The Token-2022 ATA
addresses differ from the SPL-token ATAs in 3rd #20 because the
ATA derivation seeds the token program: vault ATA
`9pVmg8pt6PR5UL8FphDN6QSfEvTiPbgUvA7YBUwPrgi`, user ATA
`HM5XNiWUtZACr5dE6FRAvZeUDE4cUfbXNHdR7N9RwmCS`. A trade step
funds the user volume accumulator on the first trade of a VM
(1,844,400 lamports, 137 bytes); later steps in the same VM
reuse it and cost 5,000 only. The collect destination DEST is
pre-created with 0 tokens. The seeded accumulator is
(needs 1, unclaimed 111, claimed 222, volume 333,444, last 20,
has 1, earned 555, cb_claimed 666).

Event layouts (verified byte-for-byte):
- ClaimTokenIncentivesEvent, 104 bytes, disc `4facf631cd5bcee8`:
  user @8..40, mint @40..72, amount @72 (GROSS transfer),
  timestamp @80, total_claimed_tokens @88 (GROSS cumulative),
  current_sol_volume @96.
- BuyEvent (v2 buy, 500 bytes, disc `67f4521f2cf57777`): out
  @16, max @24, curve @64, lp_bps @72, lp_fee @80, proto_bps
  @88, proto_fee @96, quote @104, user_quote_in @112,
  creator_bps @344, creator_fee @352.
- BuyEvent (legacy cashback buy, 497 bytes, disc
  `67f4521f2cf57777`): same slots plus track @360,
  cashback_bps @408, cashback @416, buyback_bps @424,
  buyback_fee @432.
- SweepPoolFeeEvent, 185 bytes, disc `82a42461e48287a5`:
  timestamp @8, recipient @112, amount @176 (GROSS), bucket
  @184 (0 protocol, 1 creator).
- CollectCoinCreatorFeeEvent, 120 bytes, disc
  `e8f5c2eeeada3a59`: timestamp @8, coin_creator @16, fee
  @48, vault ATA @56, token account @88.
- ClaimCashbackEvent, 72 bytes, disc `e2d6f62107f293e5`:
  user @8..40, amount @40..48, timestamp @48..56,
  total_claimed @56..64, total_cashback_earned @64..72.

Pool states below are (virtual_quote_reserves, protocol_fees,
creator_fees); lp_supply is 4,194,352,106,721 throughout and is
asserted on every step. User volume accumulator fields below
are (needs_claim, total_unclaimed, total_claimed,
current_sol_volume, last_update_timestamp,
has_total_claimed_tokens, cashback_earned,
total_cashback_claimed).

## Cases (15 cases, 29 steps per image, 87 receipts)

Family A -- tf100 claim anchors (seeded accumulator: reward
333,444 * 1000 / 100 = 3,334,440, amount 111 + 3,334,440 =
3,334,551, claimed 222 -> 3,334,773, volume -> 0, last -> 21,
needs -> 0):
- `a-claim-tf100`: claim under tf100. Vault sends the gross
  3,334,551 (10^9 -> 996,665,449, withheld stays 0); user ATA
  nets 3,301,205 (17 -> 3,301,222) with withheld 33,346 =
  ceil(3,334,551 * 100 / 10000). Event amount 3,334,551 and
  total_claimed 3,334,773 are GROSS -- the user holds
  33,346 less than `total_claimed` says.
- `a-claim-tf100-second`: a second claim is a zero claim
  (0 events, log "No tokens to claim", payer -5,000, last
  stays 21, user ATA untouched -- the stranded 33,346 is not
  re-withheld and not released).
- `a-claim-tf100-prewh`: user ATA pre-seeded with withheld
  500 claims the same way: amount net 3,301,205, withheld
  500 -> 33,846. Withheld accumulates; the claim never
  harvests it.

Family B -- heavier fees:
- `b-claim-tf5000`: claim under tf5000. Vault sends gross
  3,334,551; user ATA nets 1,667,275 (17 -> 1,667,292) with
  withheld 1,667,276 = ceil(3,334,551 / 2). Event and claimed
  still report the gross 3,334,551 / 3,334,773.
- `b-claim-tf10000`: claim under tf10000. Vault sends gross
  3,334,551; user ATA amount stays 17 and withheld becomes
  3,334,551 -- the user receives literally nothing, yet the
  event reports amount 3,334,551 and `total_claimed` becomes
  3,334,773. The claim "succeeds" while delivering zero.

Family C -- rounding, cap, gate:
- `c-claim-small111-tf100`: unclaimed 111, volume 0. Claim
  pays 111 gross; user ATA nets 109 (17 -> 126) with withheld
  2 = ceil(111 * 100 / 10000) -- the ceil rounds a 1.11 fee
  up to 2. Claimed 222 -> 333 (gross).
- `c-claim-maxfee1000-tf100`: tf100 with maxfee 1000. Fee
  caps at 1000: user ATA nets 3,333,551 (17 -> 3,333,568),
  withheld 1000, vault sends gross 3,334,551.
- `c-claim-needs0-tf100`: `needs_claim` 0 with unclaimed 111
  and volume 333,444 still pays the full 3,334,551 gross
  (user net 3,301,205, withheld 33,346). The flag does not
  gate the claim; only the computed amount does.

Family D -- failure and program/ATA binding:
- `d-claim-shortvault-tf100`: seeded claim with vault 1000
  -> Token program custom error 1 (insufficient funds),
  full rollback, payer -5,000, accumulator untouched.
- `d-claim-tokenprog-2023`: Token-2022 ATAs passed with the
  SPL-token program as the claim's token program ->
  2023 ConstraintAssociatedTokenTokenProgram (site:
  user_ata), full rollback.
- `d-claim-splata-3014`: SPL-token-program-derived ATA
  addresses passed with Token-2022 as the token program ->
  3014 AccountNotAssociatedTokenAccount (site: user_ata),
  full rollback. The two binding failures split cleanly:
  wrong program on the right ATAs is 2023, right program on
  wrong-program ATAs is 3014.

Family E -- claim-tf chained into trade -> sweep -> collect
(quote side has no fee, so the fee pipes run at their 3rd #20
values; the token claim's withheld never touches them):
- `e-claim-tf100-v2buy-swc-col`: claim first (user net
  3,301,205, withheld 33,346), then v2 buy 10^10 (spend
  1,847,796, pool (-139,844, 10,975, 128,869)), sweep creator
  128,869, collect 128,869. The claim's withheld survives
  the trade and the pipes unchanged.
- `e-v2buy-claim-tf100-swc-col`: trade first, then the
  identical tf100 claim, then sweep/collect -- same finals.
- `e-v2buy-swc-col-claim-tf100`: trade, sweep, collect,
  then the identical tf100 claim -- order independence holds
  under the fee too.
- `e-cbbuy-tclaim-tf100-cbclaim-swc-col`: cashback buy
  10^10 (earned 5,475, uvata 5,475, uvata lamports 2,044,755),
  tf100 token claim (user net 3,301,205, earned stays
  5,475), cashback claim pays 5,475 (uvata lamports back to
  2,039,280, last stays 21 -- the cashback claim does not
  stamp last_update_timestamp), sweep 123,394, collect
  123,394. Totals: 5,475 + 123,394 = 128,869, the
  non-cashback total, conserved; the token claim is a third
  pipe that touches neither.

## Result

- A token-incentive claim under a transfer fee transfers the
  gross reward and withholds into the user's own ATA: tf100
  withholds 33,346 of 3,334,551, tf5000 withholds 1,667,276,
  tf10000 withholds all of it -- while the event amount and
  `total_claimed` always report the gross. `total_claimed`
  over-reports the user's holdings by exactly the stranded
  withheld, permanently: nothing in the claim path ever
  harvests withheld, and a second claim does not re-withhold
  or release it.
- The fee rounds up (ceil) per transfer: a 111-token claim
  withholds 2, not 1. The maxfee cap binds: tf100 with
  maxfee 1000 withholds exactly 1000 on a 3,334,551 claim.
- `needs_claim` does not gate the claim: a zero flag with a
  nonzero computed amount still pays in full.
- The program/ATA binding splits cleanly: SPL-token program
  on Token-2022 ATAs is 2023, Token-2022 program on
  SPL-token-derived ATAs is 3014, both with site user_ata
  and full rollback; a short vault is Token custom 1.
- The token pipe and the fee pipes stay independent under
  the fee: the tf100 claim pays the same net whether it runs
  before the trade, between the trade and the sweep, or
  after the collect, and the sweep/collect drain their full
  buckets either way. The cashback claim and the token claim
  still touch disjoint fields, and the three pipes conserve
  the non-cashback total exactly.

## Limits

- Offline LiteSVM reproduction on synthetic fixtures only; no
  claim about on-chain behavior beyond these measured
  transactions, no source change, no build, and no whole
  program equivalence claim.
- All amounts, error codes, and site lines are exact values
  for this fixture state, not claims about other pool states.
  Error site line numbers differ between the original and the
  rebuilt images; verify.py checks each image's recorded site
  line against that image's own logs and never compares site
  lines across images (2nd #36 lesson). The README cites
  error codes, which agree across images.
- The incentive mint's transfer-fee extension is synthesized
  post-hoc (as in 3rd #5/#8); this pins handler transfer
  behavior, not a reachable mainnet state.
- The withheld-field offset depends on how the account was
  built: the packet's Token-2022 incentive ATAs are 182 bytes
  with withheld at offset 174; a reader that assumes the
  178-byte override layout (offset 170) will misread it.
- Token-claim steps run at clock timestamp 21 (global
  accumulator start 20, end 49, period 1) so the reward-day
  math is exercisable; trade steps run at timestamp
  1234567890. Timestamps are part of the asserted events.
- Transfer-fee variants of the cashback claim on the quote
  mint were pinned in 3rd #15; this packet covers the
  incentive-mint fee only.
