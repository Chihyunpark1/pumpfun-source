# research: multi-hop split x boost x tf extend-account chains at TRUE 5 hops

## Problem

#104 measured what extend_account does to the chain that runs
on the extended accounts, but on a true-3-hop chain. This
packet re-measures the whole extend family on a TRUE 5-hop
split x boost x tf chain (three_amm + g4 + g5, final output
U5), and adds the cases depth 3 could not ask: extending a
hop pool itself -- the terminal P5 and the middle P4 -- and
then running the full 5-hop chain through it. Does extending
a truncated hop pool restore the leg that reads it, or only
its size, and where in the ghost ladder does a corrupted hop
pool surface?

## Setup

- Route: three_amm + g4 + g5 (main -> P2 -> P3 -> P4 -> P5),
  split legs, tf override bps 100 unless a case says
  otherwise. Boosts are on the main pool with the fixture
  boost authority (payer) and boost enabled, except where a
  case truncates the config. Hop pools carry proper pool data
  (bump, pool-authority creator, own base mints, own vaults).
- Truncations are harness setup (applied after the route is
  built, before the first step). cpatch steps are harness
  field resets (pool vq, config boost authority / enabled)
  recorded with an empty transaction, never presented as
  on-chain instructions.
- 71 cases, 387 receipts, 39 parts (38x10 + 7), 0 divergent
  cases across original / control / candidate. Every number
  below is measured on this chain. Depth-5 anchors: fresh buy
  tail 5,207,955,235,891, second buy 4,918,089,082,874, sell
  payout 178,541, anchor boost burn 5,338,379,201,831, second
  boost 5,254,441,549,265, post-buy boost 5,254,679,949,141,
  plain-quote tail 5,259,040,470,738, tf5000 buy tail
  2,668,075,748,732.

## Cases

- `pool*` (27): pool extends at 211 / 260 / 287 / 300 / 301
  bytes, the next buy / sell / boost / deposit / sweep /
  withdraw after each extend, buy-extend-buy,
  buy-extend-buy-boost, extend-then-patch-vq-then-boost twice,
  the signer gates (outsider, unsigned, readonly target,
  readonly outsider user, poor outsider, double extend,
  zeroed discriminator), and a tf5000 extend-then-buy.
- `cfg*` (10): config extends at 500 / 907 / 949 bytes, the
  next buy / boost / sweep after each extend,
  extend-then-restore-authority-then-boost, buy-extend-buy,
  and a tf5000 extend-then-buy.
- `uva*` (9): UVA extends at 50 / 89 / 90 / 136 / 137 bytes
  plus absent, the next token claim / cashback claim /
  multi-hop buy / sync after each extend, and
  buy-extend-buy.
- `gva*` (9): GVA extends at 100 / 543 / 544 / 599 / 600
  bytes plus absent, the next token claim (twice) / sync
  after each extend.
- `fee-ext`, `vault-ext`, `extacc-*` (4): extending the
  fee-table account, a vault token account, a random
  pump-owned account, and an absent account.
- `cclaim-*` / `uva50-ext-cclaim-*` (6): cashback claims on
  the plain quote mint (no_ww guard), funded and unfunded,
  with matched and mismatched earned / balance pairs, and
  after a 50-byte UVA extend.
- `p5-*` / `p4-*` (6): terminal-P5 extends at 211 / 260
  bytes followed by a buy, a sell, and a main-pool boost,
  and a middle-P4 extend at 211 bytes followed by a buy.

## Result

### 1. Extend restores size, never values

Rent is exactly (target - current) * 6960 plus the 5,000 fee
in every extend: pool 211 -> 301 pays 631,400; pool 300 ->
301 pays 11,960; pool 287 -> 301 pays 102,440; config 907 ->
949 pays 297,320; config 500 -> 949 pays 3,130,040; UVA 90 ->
137 pays 332,120; UVA 50 -> 137 pays 610,520; UVA 89 -> 137
pays 339,080; GVA 544 -> 600 pays 394,760; GVA 543 -> 600
pays 401,720; GVA 100 -> 600 pays 3,485,000. Every extend
emits one 96-byte ExtendAccountEvent (disc
6161d7905d92167c, ts 10, old size, new size). An
already-full account is a silent no-op: pool 301, config
949, UVA 137, and GVA 600 all extend with 0 events and only
the 5,000 fee, and a second extend is the same no-op.

### 2. A 211-byte pool extend zeroes the window, and the next legs price off zero

After pool 211 -> 301, the pool state is [0, 0, 0,
4194352106721]: vq, protocol fees, and creator fees are all
zero, because every one of those fields sits beyond byte 211
and realloc zero-fills the new bytes. The next 5-hop buy
tails 5,207,950,056,210 -- byte-identical to the buy on the
unextended 211-byte pool, and exactly the #150 vq0 tail at
depth 5 (the full-pool anchor is 5,207,955,235,891). The next
sell pays 178,541, the full anchor. The next protocol sweep
is a silent no-op (0 events, buckets zeroed). Withdraw pays
the anchor (base 160,619,895, quote 29,018) and deposit
costs the anchor (quote -29,610, base -160,619,896, LP
+1,000,000): neither reads the zeroed fields. A 287-byte
extend preserves everything (the next buy is the anchor)
and a post-trade extend (300 -> 301) leaves the second buy
at the plain second-buy value 4,918,089,082,874.

### 3. A 260-byte pool extend corrupts the vq sign byte and breaks everything after it

The vq field is 245..261, so a 260-byte pool keeps 15 of its
16 bytes and loses only the top byte -- which, for the
negative fixture vq (-125,882), is the 0xFF sign byte.
Extending to 301 zero-fills that byte, so the pool's vq
becomes 1,329,227,995,784,915,872,903,807,060,280,218,694
(about 1.33e36, i.e. 2^120 - 125,882) instead of the
intended value. The next buy fails 6023 Overflow with 0
events, the next sell fails 6023 with 4 ghost hop events
at depth 5 (the sell executes terminal-first, so four hops
run before the failing main hop; depth 3 showed 2), the
next boost fails 6023 with 0 events, and the next deposit
fails 6023 with 0 events. Before the extend, the same
260-byte pool trades fine at the vq0 tail: the program
reads a short pool's vq as 0, but once the account is
grown to full size it reads the corrupted 16-byte value.
Extend is not a repair for a truncated pool; at 260 bytes
it is strictly worse than leaving the pool truncated.

### 4. A 500-byte config extend breaks the next buy with 6053; a 907-byte extend breaks the next boost with 6005

After config 500 -> 949, every field beyond byte 500 is
zero, including the buyback recipients (643..899). The
extend itself succeeds, but the next multi-hop buy fails
6053 (the buyback recipient gate) -- at tf5000 as well as
tf100 -- while the next protocol sweep still pays the
fixture bucket in full (2,488 gross, 2,463 net at tf100):
the sweep does not read the lost list. After config 907 ->
949, the fields below 907 are intact, so the next buy is
the anchor (5,207,955,235,891) -- but the boost authority
(907..939) and boost enabled (939) are zeroed, so the next
boost (vq patched to 10^9) fails 6005 InvalidAdmin,
authority before enabled, as in #101. Restoring the
authority and enabled flag with a harness reset makes the
next boost burn the anchor 5,338,379,201,831. A 907-byte
config extend therefore splits the chain: trades keep
working, boosts stop.

### 5. A 50-byte UVA extend preserves only needs / unclaimed / claimed

The UVA layout is discriminator (8) + user (32) + fields
from byte 40, so a 50-byte cut keeps needs, unclaimed, and
claimed (claimed's low byte survives because the seed value
222 fits in one byte) and zeroes volume, last_update,
has_total_claimed, earned, and total_cashback_claimed.
After 50 -> 137, the next token claim pays the 111
unclaimed only (claimed becomes 333, volume stays 0),
where the 89- and 90-byte extends pay the full 3,334,551
(claimed 3,334,773). The next multi-hop buy after a 50-byte
extend is the anchor (5,207,955,235,891, payer -5,000, no
auto-create, UVA untouched by the trade -- the #86
trade-reads-UVA pin, extended to a post-extend UVA). The
next sync after a 50-byte extend (seed last 10) still
fires the pre-start reset: claimed 222 -> 0, 64-byte event
disc c57aa77c74515bff, volume untouched (0 here).

### 6. A 100-byte GVA extend pays 111-only claims, strands the volume, and the second claim is silent

After GVA 100 -> 600, the sol-volume and token-supply
tables are zero (sol_head and tok_head read 0, where the
intact tables read 1000 / 100). The next token claim pays
111 only, leaves needs_claim set (1), and leaves the
333,444 volume stranded: the event reports
current_sol_volume 333,444 unchanged. The second claim is
a silent no-op (0 events, UVA byte-identical) even though
needs_claim is still set -- the flag alone does not force
a claim event when the payout is zero. The 543- and
544-byte extends pay the full 3,334,551 (the 543-byte cut
loses only a zero top byte), and sync after either a
100-byte or a 544-byte extend still fires the reset
(claimed 222 -> 0, has 1 -> 0) while preserving the volume
(333,444 in both cases).

### 7. Cashback claims pay the ATA balance, not the earned field

On the plain quote mint, a cashback claim with earned
5,475 and a funded cashback ATA (5,475) pays 5,475; with
the same earned but an unfunded ATA it pays 0 and emits a
0-amount 72-byte event. Mismatched pairs settle it: earned
5,475 / balance 1,000 pays 1,000, earned 1,000 / balance
5,475 pays 5,475, earned 0 / balance 1,000 pays 1,000. The
event's total_earned echoes the stored earned field, but
the amount and total_cashback_claimed track the balance.
That is why a 50-byte UVA extend -- which zeroes earned --
does not reduce the cashback claim at all: with a funded
ATA it still pays the full 5,475 (total_earned 0 in the
event), and the following token claim pays the 111
unclaimed only. #76's "pays the seeded earned" reading is
the coincidence case where balance equaled earned.

### 8. Extend gates: owner, discriminator, signer, mutability, funds

- Owner: extending the fee-table account (owner: fees
  program), a vault token account (owner: SPL Token), an
  absent UVA, an absent GVA, or an absent extend-target
  account all fail 2004 with 0 events -- the Anchor owner
  check, not the 3007 code other instructions use for the
  same mismatch.
- Discriminator: extending a pump-owned pool with a zeroed
  discriminator, or a random pump-owned 100-byte account,
  fails 6027 AccountTypeNotSupported with 0 events.
- Signer: any signer may extend -- an outsider extend
  succeeds and pays the full rent (outsider -631,400,
  payer 0). A genuinely unsigned extend (payer key as a
  non-signer meta, outsider as fee payer) fails 3010
  AccountNotSigner.
- Mutability: a readonly target fails 2000. A readonly
  outsider user (signer, non-writable, payer as fee payer)
  also fails 2000 and costs the payer 10,000 (two
  signatures at 5,000 each). A readonly user with the
  fee-payer key is not a distinct case: the runtime makes
  the fee payer writable.
- Funds: an outsider with 100,000 lamports extending a
  211-byte pool (rent 626,400 + fee 5,000) fails with
  InstructionErrorCustom(1) and 0 events, paying only the
  5,000 fee.

### 9. Hop-pool extends: the extended hop is never written back, and the tail barely moves

This is the depth-5-only finding. After P5 211 -> 301, the
next 5-hop buy tails 5,210,540,474,247 and the next sell
pays 178,630 (anchor + 89, the #122 zero-terminal-creator
sell delta exactly) -- but the terminal pool itself stays
[0, 0, 0] after both legs: no vq movement, no bucket
accrual, while the main pool moves normally (post-buy
[-4,686,964, 4,563,570, 123,394]). The buy tail sits 653
below #122's zero-creator P5 tail (5,210,540,474,900),
where the P5 buckets were fixture-valued rather than
zeroed: zeroing the terminal pool's vq, buckets, creator,
and fee bps together moves the tail by only 653. After
P4 211 -> 301, the next buy tails 5,207,955,235,241 --
only 650 below the anchor -- and the middle pool likewise
stays [0, 0, 0]. A corrupted terminal pool is louder: P5
260 -> 301 gives the same 1.33e36 vq, the buy fails 6023
with 4 ghost events (the four hops before the failing
terminal hop) and the sell fails 6023 with 0 ghosts (the
terminal hop executes first). Extending the terminal pool
does not open the main window either: a main-pool boost
after a P5 extend still fails 6065, and a boost after
buy-extend-buy still fails 6065 (buys are window-neutral,
#130). The tf5000 extend-then-buy after a 211-byte pool
extend tails 2,668,073,057,012, the #150 tf5000 pool-211
tail: the zero-window pricing survives the fee rate.

### 10. Extend leaves no residue on the next leg

Buy-extend-buy, buy-extend-config-buy, and
buy-extend-UVA-buy all land on the plain second-buy value
4,918,089,082,874. Extend-then-patch-vq-then-boost burns
the anchor 5,338,379,201,831 and the second boost burns
5,254,441,549,265, the plain #100 decay ladder, even
though the pool's buckets were zeroed by the truncation.
Failed extends roll back fully (only the fee payer's
lamports move).

## Limits

- Truncations and cpatch resets are harness setup, not
  on-chain instructions: no claim is made that a truncated
  account can be produced on-chain, only that
  extend_account behaves this way when handed one.
- The 260-byte corruption is measured at the fixture vq
  (-125,882, sign byte 0xFF). A pool whose vq top byte is
  already 0x00 would not corrupt the same way; the general
  rule is that realloc zero-fills the grown bytes, and any
  field straddling the cut keeps its low bytes and loses
  its high bytes.
- The cashback balance rule is measured on the plain quote
  mint (no_ww guard). Under the transfer-fee override the
  cashback claim fails 2021 before any amount is computed
  (#67), so the balance rule is not measured there.
- The hop-pool write-back observation (section 9) is
  reported as measured: the extended hop pool's state is
  byte-identical before and after the trade. The packet
  does not separate whether the program skips the
  write-back for a zero-creator / zero-bps hop pool or the
  zeroed fields make the computed update itself zero; the
  653 / 650 tail deltas are the measured size of the
  effect either way.
- No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements on the original, control, and candidate
  images; the three images agree on every surface in
  every case (0 divergent).

Made via @slopdotcash
