# research: multi-hop split x boost x tf created-pool boost lifecycle at TRUE 5 hops

#103 pinned the created-pool boost lifecycle at 3 hops: a directly
created pool keeps its boost window pinned at exactly 0, a patched
window passes the gate but the quote leg fails `IncorrectProgramId`
unless BOTH the quote mint and the quote vault are Token-2022, and
a created tail pool cannot join the route (6078). This packet
re-measures that whole lifecycle at TRUE 5 hops and pins what is
new at depth 5: a directly created pool can sit at EVERY hop
position of the 5-hop route — P2, P3, P4 and the P5 terminal hop —
and fails 6078 at each of them, with a ghost-event ladder that
mirrors the execution order; patching a created terminal pool's
stored creator to its pool-authority PDA passes the 6078 gate but
the leg then fails `PrivilegeEscalation`; and the fixture 5-hop
chain runs byte-identical after creating a pool at any position,
while a 5-hop trade never touches a created pool's window.

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). The split chain is
the genuine 5-hop route `three_amm` + g4 + g5, final output U5 (the
route #62/#119/#121 pinned); created-pool steps run standalone
beside it, except for the H5 cases where a created pool replaces
one hop group.

## Method note: cpatch steps

Several cases use `cpatch` steps. A `cpatch` is NOT an instruction: it
is a harness field reset between instructions (pool virtual-quote /
bucket fields, GlobalConfig boost authority / enabled flag, boost-ATA
amount, quote-vault conversion, quote-mint transfer-fee extension,
created-tail stored creator). Its receipt carries an empty
transaction (`transaction_base64: ""`) and zero events, and
`verify.py` asserts exactly that instead of verifying a signature.
Every other receipt is a real signed transaction. The `cpatch`
kinds:

- `cpool`: rewrite pool fields (vq / protocol_fees / creator_fees).
- `config`: rewrite GlobalConfig boost authority (907..939) and/or
  boost enabled (939).
- `cba`: rewrite the boost ATA amount (offset 64).
- `mint_tf`: rewrite the created quote mint to carry a transfer-fee
  extension (`transferfee(quote, bps, 2**64-1)(h, [])`).
- `conv_cvq`: convert the created quote vault CVQ to a Token-2022
  account (owner changed, 178-byte extension layout).
- `ctail5` / `ctail4` / `ctail2` / `ctail`: rewrite a created tail
  pool's fields (vq / protocol_fees / creator_fees) or its stored
  creator bytes (11..43, `creator_bytes`).

## Cases (74 cases, 753 receipts, 76 parts)

### L — natural lifecycle: the window is pinned at exactly 0 (10 cases)

`cpool` is reported as `[vq, protocol_fees, creator_fees, lp_supply]`
after each step; the window is `vq + protocol_fees + creator_fees`.
Re-measured at depth 5; every value reproduces #103 exactly (the
standalone lifecycle is depth-independent).

- `L-fresh`: create 10^12/10^12, cpool `[0, 0, 0, 10^12]`, boost 6065.
- `L-buy`: v2 buy 10^9 -> cpool `[-250251, 250251, 0, 10^12]`
  (vq drift -250,251 exactly cancels the protocol accrual 250,251),
  boost 6065. Buy deltas: userbase +10^9, userquote -1,004,004,006,
  buyback +250,250, cvb -10^9, cvq +1,003,753,756.
- `L-buy-sweep`: protocol sweep 250,251 out -> cpool `[0, 0, 0, 10^12]`
  (vq rises by the bucket), boost 6065.
- `L-buy-sweep-collect`: creator sweep and collect are both silent
  (creator bucket 0), boost 6065.
- `L-sell`: sell 10^6 -> cpool `[-250, 250, 0, 10^12]`, boost 6065.
- `L-dep`: deposit 10^9 -> cpool `[0, 0, 0, 1,001,000,000,000]`
  (liquidity is vq-neutral), boost 6065.
- `L-dep-wd`: deposit + withdraw -> cpool `[0, 0, 0, 10^12]`, boost 6065.
- `L-roundtrip`: buy + sell -> cpool `[-250502, 250502, 0, 10^12]`,
  boost 6065.
- `L-failed-boosts`: failed boost, then a second buy ->
  cpool `[-501004, 501004, 0, 10^12]`, boost still 6065 (no residue).
- `L-small`: 100/100 small pool, boost 6065.

### P — patched window: the gate passes, the leg fails (17 cases)

Every case below passes the window gate (window != 0) and then fails
`IncorrectProgramId` with 0 events. The window is a gate input only
(#100's fixture conclusion, reproduced on created pools, and again
at depth 5).

- `P-vq1e9`, `P-vq1e6`, `P-vq1e10`, `P-vq1e12`: vq patches of
  10^6 / 10^9 / 10^10 / 10^12 -> `IncorrectProgramId`.
- `P-vqneg`: vq -10^9 (negative window) -> `IncorrectProgramId`.
- `P-proto1e9`: vq 0, protocol bucket 10^9 -> `IncorrectProgramId`
  (a bucket-only window also passes the gate).
- `P-creator1e9`: vq 0, creator bucket 10^9 -> `IncorrectProgramId`.
- `P-vq-trade`: vq patch, then buy -> cpool
  `[999749499, 250501, 0, 10^12]`, boost `IncorrectProgramId`.
- `P-trade-vq`: buy, then vq patch -> cpool `[10^9, 250251, 0, 10^12]`,
  boost `IncorrectProgramId`.
- `P-vq-sweep`: vq patch, then sweep (silent, bucket 0) ->
  `IncorrectProgramId`.
- `P-req1e6`, `P-req1e10`: request size does not matter ->
  `IncorrectProgramId` (the leg fails before any amount check).
- `P-shortata`: boost ATA 10^6, request 10^9 -> `IncorrectProgramId`,
  NOT 6088 (#100's 6088 is only reached after the leg succeeds).
- `P-zeroata`: boost ATA 0 -> 6002 (the ATA-0 gate precedes the leg
  check; consistent with #101's order 6065 > 6002).

### F — converted + transfer-fee: the burn succeeds (13 cases)

All burns use the created pool's own 10^12/10^12 vaults, so they
differ from the fixture anchor 5,338,379,201,831 (#100) in scale, not
in kind. Event fields are the 208-byte boost event
(disc `3f451c16305cc2b9`). Every value reproduces #103 exactly.

- `F-conv-boost`: vq 10^9 + `conv_cvq` + `mint_tf` 100 + boostc
  (10^9, 0) -> burn **988,033,811**, used 10^9, vq 10^9,
  quote_after 1,000,990,000,000, base_after 999,011,966,189,
  remaining 999,000,000,000. Deltas: cvb -988,033,811,
  cvq +990,000,000 (net of tf100), cba -10^9, withheld cvq +10,000,000.
- `F-conv-only`: vq 10^9 + `conv_cvq` WITHOUT `mint_tf` ->
  `IncorrectProgramId` (vault-only conversion is not enough).
- `F-conv-boost-twice`: 988,033,811 -> **986,083,317**
  (decay -1,950,494, about -0.20%/round, smaller than the fixture's
  about 1.56%/round because the vaults are 10^12-scale).
- `F-conv-boost-tf5000`: burn **499,251,122** (net 500,000,000 in).
- `F-conv-boost-vqneg`: vq -10^9 -> burn **990,009,899** (larger than
  the positive-vq burn, matching `q = vq + real quote balance`).
- `F-conv-boost-proto`: vq 0, protocol bucket 10^9 -> burn
  **989,020,868**. The bucket passes the gate but the burn reads the
  vq field (0), not the window sum (#100's correction, reproduced
  on a created pool).
- `F-conv-boost-req1e6`: burn **989,009**.
  `F-conv-boost-req1e10`: burn **9,793,253,535**.
- `F-trade-conv-boost`: buy, then convert + `mint_tf`, NO vq patch ->
  window still 0 -> 6065. Conversion itself creates no window.
- `F-trade-vq-conv-boost`: buy, then vq 10^9 patch + convert + tf100
  -> burn **986,057,984** (cpool at boost time
  `[10^9, 250251, 0, 10^12]`, quote_after 1,001,993,753,756,
  base_after 998,013,942,016).
- `F-conv-boost-trade`: after a successful burn, `buy2c` ->
  `InvalidAccountData` (the converted state breaks trade
  deserialization).
- `F-trade-conv-sweep`: buy, then convert + tf100, then `swpc`
  (bucket 250,251 exists) -> `InvalidAccountData` (the pre-conversion
  bucket is stranded by the conversion).
- `F-buy-claim`: created-pool v2 buy, then token claim -> silent
  no-op, 0 events, 0 payout, log "No tokens to claim". A created-pool
  buy does not move UVA volume (volume stays 0), unlike #73's seeded
  claim of 3,334,551.

### G — gate order on a created pool (10 cases)

- `G-off`: boost-off -> 6066, re-enable -> 6065.
  `G-disbuy`: buy-disable -> 6020, release -> 6065.
  `G-auth`: boost authority patched to outsider -> 6005,
  payer restored -> 6065.
- `G-off-dis`: off + buy-disable -> **6066** (off beats disable).
  `G-auth-off`: authority + off -> **6005**.
  `G-auth-dis`: authority + disable -> **6005**.
- `G-vq-off`: vq 10^9 + off -> 6066.
  `G-vq-dis`: vq 10^9 + disable -> 6020.
  `G-vq-auth`: vq 10^9 + outsider authority -> 6005.
- Head of #101's total order holds on created pools:
  6005 > 6066 > 6020 > 6065, and 6002 sits after the window gate
  (`P-zeroata`).

### T — transfer fee alone does not open the leg (4 cases)

- `T-fresh100`, `T-fresh5000`: `mint_tf` only, window 0 -> 6065
  (the gate is tf-blind).
- `T-vq100`, `T-vq5000`: vq patch + `mint_tf` (vault NOT converted)
  -> `IncorrectProgramId`. The mint side alone is not enough.

### C — create rejects a transfer-fee quote mint (3 cases)

- `C-tf100`, `C-tf0`, `C-tf5000`: `std` create under a tf quote mint
  (tf-only isolation, no withdraw-withheld authority) ->
  `IncorrectProgramId`, 0 events, full rollback (fee 5,000 only).
  Even a 0-bps extension is rejected: a created pool cannot be born
  under transfer fee.

### H — created pools at every 5-hop position (12 cases)

The new depth-5 pin. A created pool replaces ONE hop group of the
5-hop route (buy groups main/P2/P3/P4/P5, sell groups run
terminal-first), keeping 5 hops and final output U5. Every
unpatched created hop fails **6078 OnlyPumpPools** with a ghost
ladder that counts the hops that executed before the failing one:

| position | buy ghosts | sell ghosts |
| --- | --- | --- |
| P2 (second hop) | 1 | 3 |
| P3 (middle hop) | 2 | 2 |
| P4 (fourth hop) | 3 | 1 |
| P5 (terminal hop) | 4 | 0 |

- `h-buy2` / `h-sell2`: created (BASE2/base) pool at P2 -> 6078,
  1 / 3 ghosts.
- `h-buy3` / `h-sell3`: created (BASE3/BASE2) pool at P3 -> 6078,
  2 / 2 ghosts (the #103 H cases, re-measured at depth 5).
- `h-buy4` / `h-sell4`: created (BASE4/BASE3) pool at P4 -> 6078,
  3 / 1 ghosts.
- `h-buy5` / `h-sell5`: created (BASE5/BASE4) pool at P5 -> 6078,
  4 / 0 ghosts.
- `h-buy5-patched` / `h-sell5-patched`: created P5 pool with its
  stored creator patched to its pool-authority PDA (C5) -> the 6078
  gate passes and the leg then fails **`PrivilegeEscalation`**
  (the #129 terminal result, re-measured at depth 5 in both
  directions). Buy side: 4 ghost buy events (508 bytes each, the
  four fixture hops; the P5 leg emits nothing before failing).
  Sell side: **1 ghost sell event** (449 bytes, disc
  `3e2f370aa503dc2a`) — the P5 sell leg emits its hop event
  BEFORE the failing vault-signer CPI, while the buy leg fails
  before emitting. Directional asymmetry inside the same failure.
- `h-tail5-boost`: created P5 pool boosts standalone -> 6065
  (window 0, same as the `std` created pool).
- `h-tail5-patched-boost`: created P5 pool, vq patched to 10^9,
  boosts standalone -> `IncorrectProgramId` (gate passes, quote leg
  fails: the P5 pool's quote mint BASE4 and vault are SPL Token —
  the #103 P result at the P5 position).

### A — depth-5 anchors (8 cases)

- `a-chain5-after-create`: create (BASE3/BASE2 tail), then the
  fixture 5-hop buy -> tail **5,207,955,235,891** (5 hop events,
  508 bytes each; full leg deltas in the receipts).
- `a-chain5-after-create5` / `a-chain5-after-create4`: create a
  P5-position / P4-position pool, then the fixture 5-hop buy ->
  tail **5,207,955,235,891** in both cases — byte-identical to the
  no-create anchor. Creating a pool at any position does not move
  the fixture chain.
- `a-boost-after-chain5`: vq 10^9 patch, 5-hop buy (tail
  5,167,125,538,753, the #156 patched-buy tail), then main-pool
  boost -> burn **5,255,205,915,165** (#154's post-buy burn,
  reproduced at depth 5 with the created-pool packet's route).
- `a-created-boost-after-chain5`: create `std` (plain), 5-hop buy
  (plain-mode tail 5,259,040,470,738), then created-pool boost ->
  6065. The fixture chain does not open the created pool's window.
- `a-tail5-boost-after-chain5`: create P5 pool, 5-hop buy (tail
  5,207,955,235,891), then P5-pool boost -> 6065. Same conclusion
  at the P5 position.
- `A-fixture-boost`: fixture pool, vq 10^9 patch, tf100 boost ->
  burn **5,338,379,201,831** (#100's anchor, reproduced).
- `A-fixture-boost-plain`: fixture pool, vq 10^9 patch, NO tf ->
  `IncorrectProgramId`. The Token-2022 requirement is not
  created-pool-specific: a plain fixture pool fails the leg too.

## Result

Depth 5 adds three pins to #103's lifecycle, all receipt-backed:

1. **Hop membership is position-independent**: a created pool fails
   6078 at P2, P3, P4 and P5 alike; only the ghost count moves,
   tracking execution order (buys main-first, sells
   terminal-first). The ladder is buy 1/2/3/4 and sell 3/2/1/0
   across P2/P3/P4/P5.
2. **The creator patch is a second gate, not a fix**: patching the
   stored creator to the pool-authority PDA passes 6078 but the leg
   fails `PrivilegeEscalation` — and the failure's event footprint
   is directional (buy: 4 ghosts, no P5 event; sell: 1 ghost, the
   P5 sell event emitted before the failing CPI).
3. **Boostability and hop membership stay orthogonal at depth 5**:
   a created pool boosts standalone exactly like at 3 hops
   (window 0 -> 6065; patched window -> `IncorrectProgramId`),
   the fixture chain is byte-identical after creating at any
   position, and a 5-hop trade moves no created pool's window
   (boost after the chain is still 6065).

Everything else reproduces #103 at depth 5 without change: the
window pinned at exactly 0 through the natural lifecycle, the 2x2
quote mint x quote vault matrix (only Token-2022 x Token-2022
burns, tf100: 988,033,811 on 10^12/10^12 vaults, second burn
986,083,317), the converted pool becoming boost-only (trade and
sweep -> `InvalidAccountData`), the gate head order
6005 > 6066 > 6020 > 6065 (+ 6002 after the window gate), and create
rejecting a transfer-fee quote mint at any bps (0/100/5000).
Relation to earlier packets: #72 (created-pool 6078 + window-0
observation), #98 (vault gates), #100 (window is a gate input,
burn reads the vq field, tf ladder), #101 (gate total order),
#102 (boost-trade interaction), #103 (the 3-hop lifecycle this
packet extends), #129 (created-pool 5-hop 6078 +
`PrivilegeEscalation` on patch), #154 (post-buy burn
5,255,205,915,165), #156 (patched-buy tail 5,167,125,538,753 and
the true 5-hop route).

## Limits

- `cpatch`, `conv_cvq` and `mint_tf` are harness field rewrites, not
  instructions and not on-chain reachable states in this packet:
  a directly created pool's vaults are SPL Token accounts and its
  quote mint is whatever it was created with (a tf quote mint is
  rejected at create, case C). The converted-burn numbers describe
  the burn formula on 10^12/10^12 vaults, not a state an on-chain
  created pool is shown to reach here (a migration path that
  converts vault and mint is not demonstrated).
- `IncorrectProgramId` is a Fieldless error with no site line, so
  the Token-2022 `transfer_checked` mechanism is inferred from the
  2x2 matrix plus the boost program's quote-leg structure, not from
  a recorded site.
- The burn formula was spot-checked against
  `base_for_quote(net, old_base, vq + old_quote)` on the F cases;
  it is not a full re-derivation of the curve.
- 6088 was NOT re-triggered on a created pool: the short-ATA case
  (`P-shortata`) fails earlier at the quote leg. The 6088 pin still
  rests on #100.
- The vault-only fixture cell (plain mint + converted fixture vault)
  is not receipt-backed here; only the created-pool 2x2 and the two
  fixture diagonal cells are.
- The sell-side patched-terminal ghost (1 sell event before
  `PrivilegeEscalation`) is reported as a measured log fact; the
  buy/sell handler ordering that produces it is not traced to a
  source line (mayhem/pump sources are not in this sparse checkout).
- No source change, no build, and no whole-program identity claim is
  made. All three images agree on every receipt.

Made via @slopdotcash
