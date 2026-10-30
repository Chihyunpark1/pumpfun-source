# research: multi-hop split x boost x tf boost vault exhaustion chains at TRUE 5 hops

#107 pinned boost vault exhaustion at 3 hops: the burn is linear
in the main base vault, vb1 = 0 is a hard boundary with a
per-leg error code, the boost ATA must end strictly positive
(6088), deposit cannot rescue a zero base vault, and the real
quote vault steers the burn. This packet re-measures that whole
family on a TRUE 5-hop split x boost x tf chain (three_amm + g4
+ g5, final output U5, five hop events on every successful
swap), and adds the cases depth 3 could not ask: draining a
hop pool's own base/quote vault (P4, P5) and running the full
5-hop chain through it, and boosting the terminal hop pool on
a drained vault.

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 88 cases, 693
receipts, 70 parts (69x10 + 3). Boosts request 10^9 quote unless
a family says otherwise; the main pool virtual_quote_reserves
field is patched to 10^9 wherever a main boost must succeed;
transfer fee is 100 bps unless a family says otherwise.

## Setup

- Route: three_amm + g4 + g5 (main -> P2 -> P3 -> P4 -> P5), split
  legs, tf override bps 100 unless a case says otherwise. Plain
  cases use no tf override and the `no_ww` guard.
- Anchors on this chain: fresh buy tail 5,207,955,235,891, fresh
  sell payout 178,541, anchor boost burn 5,338,379,201,831
  (identical to #100/#154/#155), second boost 5,254,441,549,265.
- Vault seeds are harness field resets (`cpatch` steps, empty
  transactions, never presented as on-chain instructions):
  `VB`/`VQ1` rewrite the main vaults, `VB4`/`VQ4`/`VB5`/`VQ5`
  rewrite the hop vaults, `BATAP` rewrites the main boost ATA,
  `BA5SP` rewrites the terminal boost ATA, `VQ5POOL` rewrites
  the P5 pool's vq field.

## Cases

- Z anchors: main boost, 5-hop buy, 5-hop sell.
- L base-vault ladder: vb1 = 10^15 down to 10^6, 0, and
  0-then-restore, each followed by a boost.
- R repeated boosts: 5x at the fixture vault, 3x at vb1 = 10^12.
- Q request ladder: requests 0, 1, 10, 1000, 10^5, 10^6, 10^8,
  10^10, 10^12 at the fixture vault.
- A boost-ATA exhaustion: ATA 10^6, 0, exactly 10^9, 10^9+1,
  2x10^9 twice, 2x10^9+1 twice, short ATA at vb1 = 10^9, ATA 0
  with vb1 = 0.
- T trade legs on a drained main vault: buys/sells at vb1 =
  10^12/10^11/10^10/10^9/10^6/0, single-hop buy/sell and legacy
  buy/sell at vb1 = 0 and 10^12, plain buys/sells at vb1 =
  10^12/0.
- D deposit/withdraw on a drained vault: deposit, withdraw,
  deposit-then-boost, deposit-then-buy, withdraw at 10^9,
  deposit-then-boost at 10^9.
- F fee-book legs after the drain: sweep/collect on vb1 = 0,
  token claim on vb1 = 0, buy-then-drain-then-sweep, failed
  6088 boost then buy.
- V real quote-vault ladder: vq1 = 0 / 10^9 / 10^12 boosts,
  vq1 = 0 buy.
- X tf variants and walks: vb1 = 10^12 at tf0/tf5000, vb1 =
  10^12 with request 10^10, buy-then-boost at 10^12,
  boost-then-drain-then-boost, unpatched-window boost at
  10^12.
- H hop-vault exhaustion (new at depth 5): vb5/vq5/vb4/vq4 = 0
  buys and sells, vb5 = 10^12 buy/sell, vq5 = 10^12 buy,
  vb5 = 0 buy then restore then buy, terminal-hop boosts
  (patched P5 window, vb5 = 0, vq5 = 0, short ATA 10^6,
  tf5000).

## Result

### 1. The burn ladder is depth-invariant; the trade tails are not quite

Main-pool boosts reproduce #107 exactly at depth 5: vb1 ladder
burns 7,924,013,300,677 (10^15), 792,401,330,067 (10^14),
79,240,133,006 (10^13), 7,924,013,300 (10^12), 792,401,330
(10^11), 79,240,133 (10^10), 7,924,013 (10^9), 7,924 (10^6) —
the burn is 0.79240133% of vb1 at request 10^9, unchanged.
Repeated boosts decay ~1.56%/round (5,338,379,201,831 ->
5,254,441,549,265 -> 5,172,468,136,601 -> 5,092,398,150,835
-> 5,014,173,114,355); at vb1 = 10^12 the rounds are
7,924,013,300 -> 7,799,420,601 -> 7,677,743,517. The request
ladder is identical too (0/1 -> 6002, 10 -> 43,482, 1000 ->
5,375,583, 10^5 -> 538,095,981, 10^6 -> 5,380,970,054, 10^8
-> 537,672,386,159, 10^10 -> 49,830,102,507,836, 10^12 ->
6088 with ghost burn 598,735,502,793,632).

Trade tails on a drained main vault move slightly with depth.
Buy tails at vb1 = 10^12 / 10^11 / 10^10 / 10^9 / 10^6 are
7,963,832,881 / 796,406,156 / 79,640,837 / 7,964,077 / 7,959
— against #107's 7,963,960,047 / 796,407,430 / 79,640,853 /
7,964,081 / 7,961, i.e. depth deltas of -127,166 / -1,274 /
-16 / -4 / -2. Sell payouts at vb1 = 10^12 / 10^9 / 10^6 are
121,230,686 / 60,751,868,441 / 121,534,401,153 — against
121,230,928 / 60,751,929,177 / 121,534,401,396, i.e. -242 /
-60,736 / -243. Plain buy at vb1 = 10^12 tails 8,043,624,371
(#107: 8,043,754,098, -129,727). The deltas are reported as
measured; no mechanism is claimed for why the 10^12 and
10^9 sell legs move more than the small-vault legs.

### 2. vb1 = 0 is still a hard boundary, with the same per-leg codes

- Main boost on vb1 = 0: 6001, 0 events; restore to 10^15
  burns 7,924,013,300,677 again.
- 5-hop buy on vb1 = 0: 6025, 0 events. 5-hop sell on vb1 =
  0: 6025, **4 ghost events** (depth 3 showed 2 — the sell
  executes terminal-first, so four hops run before the
  failing main hop). Plain buy/sell on vb1 = 0: 6025, 0 / 4
  ghosts, same split.
- Single-hop buy / legacy buy on vb1 = 0: 6016. Single-hop
  sell / legacy sell on vb1 = 0: 6025. Single-hop buy at vb1
  = 10^12 costs userquote -124,685,392; single-hop sell at
  vb1 = 10^12 pays 121,230,716 (bb22 30,398).
- Deposit on vb1 = 0 still pays quote only (base 0, quote
  29,313) and cannot rescue the vault: deposit-then-boost
  still fails 6001, deposit-then-buy still fails 6025.
  Withdraw on vb1 = 0 pays base 0, quote 29,312 (the #107
  values, unchanged); withdraw at vb1 = 10^9 pays base 238,
  quote 29,018, and deposit-then-boost at 10^9 burns
  7,924,013.

### 3. The ATA rule and the quote-vault rule are unchanged

- ATA 10^6 with request 10^9: 6088, ghost burn 5,380,970,054.
  ATA 0: 6002 (the ATA gate beats the vault gate — ATA 0
  with vb1 = 0 also fails 6002, not 6001). ATA exactly 10^9:
  6088, ghost burn 5,338,379,201,831. ATA 10^9+1: success,
  remaining 1, burn 5,338,379,201,831. ATA 2x10^9 twice:
  second boost 6088; ATA 2x10^9+1 twice: second burn
  5,254,441,549,265. Short ATA at vb1 = 10^9: 6088, ghost
  burn 7,987.
- Real quote vault: vq1 = 0 boost fails 6023, vq1 = 0 buy
  fails 6023 (0 events); vq1 = 10^9 burns 223,063,355,017,720,
  vq1 = 10^12 burns 665,634,817,992 — the #107 values
  exactly. tf variants at vb1 = 10^12: tf0 burns
  8,003,413,241, tf5000 burns 4,017,784,612, request 10^10
  burns 73,965,220,550, buy-then-boost burns 7,798,964,344,
  boost-then-drain-then-boost fails 6001, unpatched-window
  boost fails 6065 — all #107 values.
- Fee-book legs survive the drain unchanged: sweep pays
  2,463 net (protocol) and 122,160 net (creator), collect
  pays 120,938, token claim pays 3,334,551, buy-then-drain
  sweep pays 4,517,934 net. A failed 6088 boost leaves the
  next buy at the patched tail 5,167,125,538,753 (#156).

### 4. Hop-vault exhaustion fails at the drained hop (new)

A drained hop vault fails with the drained hop's own code
and a ghost ladder that counts the hops executed before
it:

| drained vault | buy | sell |
| --- | --- | --- |
| vb5 = 0 (terminal base) | 6025, 4 ghosts | 6025, 0 ghosts |
| vq5 = 0 (terminal quote) | 6023, 4 ghosts | 6023, 0 ghosts |
| vb4 = 0 (middle base) | 6025, 3 ghosts | 6025, 1 ghost |
| vq4 = 0 (middle quote) | 6023, 3 ghosts | 6023, 1 ghost |

The pattern mirrors #152's vault ghost ladder: buys run
main-first (a terminal failure leaves 4 ghosts, a P4
failure 3), sells run terminal-first (a terminal failure
leaves 0, a P4 failure 1). Base drains fail 6025, quote
drains fail 6023, at every position — the same code split
as the main vault (#107) and the #152 vault gates.
Restoring vb5 to 10^15 after a failed buy returns the
next buy to the anchor tail 5,207,955,235,891 exactly.

Small terminal vaults reprice the tail hard. vb5 = 10^12:
buy tails only 5,207,955,235 (the terminal leg caps the
output — against the 5,207,955,235,891 anchor) while sell
pays 177,570,967 (against the 178,541 anchor — the
terminal leg pays far more quote per base when its base
vault is small). vq5 = 10^12: buy tails 839,620,752,754,337
(the terminal quote vault steers the terminal leg's price
by orders of magnitude). These are measured snapshot
deltas; the packet does not re-derive the curve.

### 5. The terminal-hop boost mirrors the main boost (new)

With the P5 window patched to 10^9 and the SPL-derived
BA5S boost ATA (#120), the terminal boost burns
999,997,999 — the #120 anchor, reproduced. Its exhaustion
map is the main map at hop scale: vb5 = 0 fails 6001 (0
events), vq5 = 0 fails 6023 (0 events), tf5000 burns
999,997,999 (tf-blind at this scale, like the main
tf5000 ladder's shape). One asymmetry: a short terminal
ATA (10^6, request 10^9) does NOT fail 6088 — it burns
999,997, spending exactly the 10^6 available (#154's
short-ATA success, reproduced at the terminal hop; the
main-pool short ATA fails 6088).

## Limits

- Vault seeds and pool patches are harness field resets, not
  on-chain instructions: no claim is made that a drained
  vault can be produced on-chain, only that the program
  behaves this way when handed one.
- The depth deltas in section 1 (buy tails -127,166 at
  vb1 = 10^12, sell payouts -60,736 at vb1 = 10^9) are
  reported as measured differences against #107; the packet
  does not trace them to a source line.
- The terminal-vault repricing values in section 4 are
  snapshot deltas on the fixture route; the packet does not
  re-derive the multi-hop curve.
- The short-ATA asymmetry (main 6088 vs terminal success)
  is reported as measured; the packet does not separate
  whether the terminal boost path skips the ATA-balance
  check or computes a smaller burn first.
- No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements on the original, control, and candidate
  images; the three images agree on every surface in
  every case (0 divergent).

Made via @slopdotcash
