# research: multi-hop split x boost x tf exact-out chains at TRUE 5 hops

#108 pinned the pump program's exact legs on a 3-hop split chain:
buy / buy_v2 take (base_amount_out, max_quote_amount_in) and ARE
the exact-out legs, while buy_exact_quote_in(_v2) take
(spendable_quote_in, min_base_amount_out) and are exact-IN; there
is no exact-quote-out sell, only a tight min_quote_amount_out
gate; and the exact-out cost spent as exact-in falls short of the
target because the exact-in leg re-fees the input before the
curve sees it. This packet re-measures that whole exact family
on a TRUE 5-hop split x boost x tf chain (three_amm + g4 + g5,
final output U5, five hop events on every successful swap), and
adds the question depth 3 could not ask: what happens to the
multi-hop min_out gate when the failing leg has already emitted
four hop events before it fails?

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). The split chain
is the genuine 5-hop route (#62/#119/#121/#156/#157). Single-hop
legs run on the main pool; multi-hop legs run the full route.

## Setup

- Route: three_amm + g4 + g5 (main -> P2 -> P3 -> P4 -> P5), split
  legs, tf override bps 100 unless a case says otherwise. Plain
  cases use no tf override and the `no_ww` guard (plain mint, no
  withdraw-withheld authority patch).
- Anchors on this chain: tf100 5-hop buy (10^9 quote) tails
  5,207,955,235,891, second buy tails 4,918,089,082,874; tf100
  fresh sell (10^9 base) pays 178,541; plain buy tails
  5,259,040,470,738; tf5000 buy tails 2,668,075,748,732, tf5000
  sell pays 90,172; anchor boost burn 5,338,379,201,831.
- 72 cases, 330 receipts, 33 parts (33x10), 0 divergent cases
  across original / control / candidate.

## Cases

### A — exact-out anchors, single hop on the main pool (9 cases)

`A-legbuy-1e9` / `A-buy2m-1e9` / `A-legbuy-1e6` / `A-legbuy-1e8` /
`A-legbuy-twice` / `A-legbuy-tf0` / `A-legbuy-tf5000` /
`A-buy2m-tf0` / `A-buy2m-tf5000`.

### B — exact-in anchors (8 cases)

`B-lexact-1e9` / `B-bexact2-1e9` / `B-lexact-1e6` /
`B-bexact2-1e6` / `B-bexact2-1e8` / `B-bexact2-twice` /
`B-bexact2-tf5000` / `B-lexact-tf5000`.

### C — exact-out max_quote gates, 6004 (4 cases)

`C-legbuy-max-1` / `C-legbuy-max-ok` / `C-buy2m-max-1` /
`C-buy2m-max-ok`.

### D — exact-in min_base gates, 6040 (4 cases)

`D-lexact-min-ok` / `D-lexact-min-plus1` / `D-bexact2-min-ok` /
`D-bexact2-min-plus1`.

### E — round trip: exact-out cost spent as exact-in (4 cases)

`E-lexact-186623` / `E-bexact2-186637` / `E-lexact-tf0-184779` /
`E-bexact2-tf0-184779`.

### F — sell-side gates (6 cases)

`F-legsell-ok` / `F-legsell-plus1` / `F-sell2m-ok` /
`F-sell2m-plus1` / `F-legsell-tf5000` / `F-sell2m-tf5000`.

### G — multi-hop tight min_amount_out gates at TRUE 5 hops (12 cases)

`G-mhbuy5-tail` / `G-mhbuy5-tail-plus1` / `G-mhsell5-pay` /
`G-mhsell5-pay-plus1` / `G-mhbuy5-plain-tail` /
`G-mhbuy5-plain-tail-plus1` / `G-mhbuy5-tf5000-tail` /
`G-mhbuy5-tf5000-tail-plus1` / `G-mhsell5-tf5000-pay` /
`G-mhsell5-tf5000-pay-plus1` / `G-mhbuy5-small` /
`G-mhsell5-small`.

### H — chain interaction: exact legs between chain legs (6 cases)

`H-mh5-mh5` / `H-mh5-legbuy-mh5` / `H-mh5-bexact2-mh5` /
`H-mh5-lexact-mh5` / `H-mhsell5-legsell` / `H-mhsell5-sell2m`.

### I — boost interaction (6 cases)

`I-legbuy-boost` / `I-bexact2-boost` / `I-boost-legbuy` /
`I-boost-bexact2` / `I-mh5-boost` / `I-boost-mh5`.

### J — sweep / collect / deposit after exact legs (5 cases)

`J-legbuy-swp` / `J-bexact2-swp` / `J-legbuy-col` /
`J-bexact2-dep` / `J-legbuy-dep`.

### K — failed exact legs leave no residue (3 cases)

`K-fail-legbuy-mh5` / `K-fail-bexact2-mh5` /
`K-fail-mhbuy5-mh5`.

### R — round trips at depth 5 (5 cases)

`R-mhbuy5-then-sell5` / `R-mhsell5-then-buy5` /
`R-mhbuy5-then-sell5-tf5000` / `R-exactout-cost-as-mh5-input` /
`R-mhbuy5-then-legsell`.

## Result

### 1. Single-hop exact legs reproduce #108 exactly at depth 5

The route change touches no single-hop leg. Legacy exact-out
10^9 base costs 186,623 (vq1 +182,533, withheld 1,844);
v2 exact-out costs 186,637 (+14). Exact-in 10^9 quote spends
999,878,519 (legacy) vs 999,954,075 (v2, +75,556) for the same
5,315,544,542,190 base. tf0 exact-out costs 184,779 on both
legs; tf5000 costs 367,312 (legacy) vs 368,709 (v2). The gate
split is unchanged and +-1 sharp: max_quote -1 -> 6004 with
0 events (legacy and v2), min_base +1 -> 6040 with 0 events
(legacy and v2). The round trip is still not a round trip:
the legacy exact-out cost 186,623 spent as exact-in buys
999,869,711 (shortfall 130,289); the v2 cost 186,637 buys
999,946,425 (shortfall 53,575); at tf0 the 184,779 cost buys
999,995,741 (shortfall 4,259) on both legs. Sell-side gates
are unchanged: 10^9 base sells for 178,409 (legacy and v2),
min_quote +1 -> 6004.

### 2. The 5-hop buy gate panics; the 5-hop sell gate stays clean

This is the depth-5-only pin, and it is directional. Every
successful 5-hop swap emits exactly 5 hop events, and the
per-hop outputs on a fresh tf100 buy are 5,332,264,170,203
-> 5,303,981,938,022 -> 5,275,998,139,846 -> 5,248,308,076,854
-> 5,207,955,235,891.

- Buy: min_out exactly the tail (5,207,955,235,891) succeeds;
  tail+1 fails with ProgramFailedToComplete (panic) and all
  5 hop events left as ghosts, full rollback — on ALL THREE
  images (0 divergent cases). The same panic holds for the
  plain tail+1 (5,259,040,470,739) and the tf5000 tail+1
  (2,668,075,748,733).
- Sell: min_out exactly the payout (178,541, tf5000 90,172)
  succeeds; payout+1 fails clean 6004 with 5 ghost events,
  full rollback, on all three images.

So at depth 5 the buy/sell gate asymmetry is error-kind, not
just ghost-count: the buy leg's min_out check never gets to
return 6004 (the #146 "memory allocation failed" panic, all
five hop events already emitted), while the sell leg returns
the clean code. Contrast with #159: there the failing buy
(min_out 10^15) split original-6004 vs rebuild-panic. Here,
with no UVA seed in the failing-buy cases, the original
panics too — so the #159 split does not reproduce in this
packet's context, and the panic-vs-6004 split appears to
depend on case context (UVA seeding is the #153 candidate),
not on depth alone. That dependence is reported as measured
contrast, not traced to a source line.

### 3. Small legs scale, and the chain hop outputs are visible

Small 5-hop buy (10^6 quote) tails 5,361,233,911 (withheld
vq1 10,000 + bb22 46, the #160 small-buy values); small
5-hop sell (10^6 base) pays 178. The exact-out cost
186,623 spent as a 5-hop buy input tails 1,000,542,480 —
the single-hop exact-out price and the chain price are
different curves, and neither is a substitute for the other.

### 4. Exact legs between chain legs move the next tail

Second 5-hop buy after a first: 4,918,089,082,874. A legacy
exact-out leg between two chain buys costs 189,614 (vs
186,623 fresh, +2,991 of moved-pool drift) and the third
buy tails 4,918,074,717,461. A v2 or legacy exact-in leg
between two chain buys (spending 10^9 quote for
5,232,059,887,295 base on the moved pool) leaves the third
buy at 4,843,196,047,716 — identical for legacy and v2,
since both exact-in legs buy the same base on the same
moved pool. After a chain sell, a single-hop sell pays
178,408 (1 less than the fresh 178,409) on both leg
families.

### 5. Exact legs move the next burn; a burn moves the next exact leg

- Legbuy then boost (vq patched to 10^9): burn
  5,338,363,478,447 (anchor −15,723,384, the same delta
  #117/#123 measured after a reserved-member legbuy).
- Exact-in (v2) then boost: burn 5,254,810,797,338 — the
  v2 leg accrues into the buckets, so the burn reads a
  different vq + quote balance than after a legacy leg.
- Boost then legbuy: cost 191,159 (+4,536 vs fresh).
- Boost then exact-in (v2): 5,190,075,630,656 base for
  10^9 quote (vs 5,315,544,542,190 fresh).
- Chain buy then boost: 5,254,679,949,141 (the #154
  post-buy burn). Boost then chain buy: 5,087,534,167,771
  (the #156 boost-then-buy tail).

### 6. Legacy exact legs pay fees out; v2 exact legs accrue

After a legacy exact-out leg, protocol sweep pays only the
fixture 2,463 net and creator sweep only 122,160 net — the
leg's fees went straight to recipient ATAs, not the pool
buckets. After a v2 exact-in leg, protocol sweep pays
4,503,663 net and creator sweep 3,026,160 net — the leg
accrued into the buckets. Collect after a legacy leg
drains 122,702 to a 121,474 net destination (withheld
1,228). Deposit after an exact leg costs the anchor
(legacy: base −160,619,657, quote −29,610; v2:
base −159,352,586, quote −29,845).

### 7. Failed legs leave no residue; depth-5 round trips are lossy

A failed legacy exact-out (6004), a failed exact-in
(6040), and a failed 5-hop buy (panic) all roll back
fully: the next 5-hop buy tails exactly the fresh anchor
5,207,955,235,891. Round trips at depth 5: buying the
full 5-hop tail (5,207,955,235,891 base) back through the
chain pays 957,362,033 against the 10^9 spent (loss
42,637,967); at tf5000 the same round trip pays
244,184,875. Selling the full tail through a single-hop
leg instead pays 936,748,372 — 20,613,661 less than the
chain sell, because the single-hop leg prices off the
main pool alone. Sell-then-buy lands at 5,208,011,418,184,
56,182,293 above the fresh tail (the #146 path-dependence
value, reproduced at depth 5).

## Limits

- The failing-buy panic mechanism is not traced to a source
  line: the packet reports the error kind, the 5 ghost
  events, and the full rollback on all three images, and
  notes the contrast with #159's split without claiming
  its cause (UVA seeding is an untested candidate from
  #153, not a measured variable here).
- `IncorrectProgramId` and panic errors carry no site line,
  so no handler line is claimed for the buy-gate panic.
- Exact-out / exact-in terminology follows the instruction
  argument order (base_amount_out first = exact-out,
  spendable_quote_in first = exact-in), as in #108; no
  claim is made about any other naming in the codebase.
- No source change is proposed and no full-program
  equivalence is claimed. All amounts are receipt-level
  measurements on the original, control, and candidate
  images; the three images agree on every surface in
  every case (0 divergent).

Made via @slopdotcash
