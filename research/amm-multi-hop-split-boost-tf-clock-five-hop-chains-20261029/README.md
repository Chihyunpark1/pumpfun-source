# Split x boost x tf time and clock chains at TRUE 5 hops

## Problem

The 3-hop clock packet (#94) pinned how the clock moves (and does
not move) the split x boost x tf chain: trade amounts are
clock-blind, event timestamps follow the clock, token-claim
conversion follows the incentive day, and sync fires only under a
pre-start gate. This packet re-measures the same families on a TRUE
5-hop route (three_amm + g4 + g5, final output U5): does the extra
depth move any clock boundary, does the 5-hop failing-buy panic
(#146) depend on the clock, and do the GVA window patches behave
the same at depth 5? Every case runs on the original, control, and
candidate images; all three agree on every case in this packet
(0 divergent cases).

## Cases

78 cases, 93 steps, 279 receipts, 28 parts (27x10 + 9):

- **A — trade/event clock-independence (15 cases):** 5-hop buys at
  ts 0, 10, 21, 777, -1, 2**62; 5-hop sells at ts 0, 777, -1;
  v2 buy, deposit, protocol sweep, creator sweep + collect, and
  boosts (patched 10**9 window) at ts 777 and -1.
- **B — token-claim clock sweep (18 cases):** claims at ts 0, 10,
  19, 20, 21, 22, 49, 50, 100, 1000, 2**62, -1, with seed last 20,
  volume 333,444, unclaimed 111 (GVA start 20, end 49, seconds 1);
  last 49/50/100/0 variants; claim chains ts 0-21-22 and ts 21
  twice.
- **C — sync clock sweep (12 cases):** syncs at ts 0, 10, 19, 20,
  21, 50, -1 with seed last 10; last 20/19/21 variants;
  sync-fire-then-claim chains (sync 10, claim 21, claim 22;
  sync 10, claim 10, claim 21, claim 22).
- **D — GVA start/end/seconds patches (12 cases):** start 100
  claims at 99/100/101 and syncs at 99/101; end 30 claim at 31
  and last-31 claim at 40; seconds 0 claim at 21 and sync at 10;
  seconds 86400 claim at 86420, last-86420 claim at 90000, and
  sync at 10.
- **E — lifecycle/cashback event clock (5 cases):** cashback
  claims at ts 777 and 0 (plain quote, seeded ATA balance
  5,475); init, close, and 90-byte extend at ts 777.
- **F — setter/sweep clock (4 cases):** buyback-config 7500 then
  5-hop buy at ts 777; disable buy-bit then 5-hop buy at
  ts 777; admin rotation at ts 777; sweep + creator sweep +
  collect at ts 777.
- **G — 5-hop-specific clock interactions (6 cases):** 5-hop sell
  at ts -1; failing 5-hop buys (min_out far above the tail) at
  ts 777 and ts 0; failing 5-hop sell at ts 777; buy-then-claim
  and claim-then-buy across ts 21/22.
- **T — transfer-fee variants across the clock (6 cases):**
  5-hop buys at tf 0 and tf 5000 at ts 777, 5-hop sell at
  tf 5000 at ts 777, token claims at claim bps 5000 at ts 21
  and 22, 5-hop buy at tf 0 at ts 21.

## Result

**Route confirmation.** Successful 5-hop swaps emit exactly 5 hop
events: buys disc 67f4521f2cf57777 (len 508), sells disc
3e2f370aa503dc2a (len 449). The failing 5-hop buy emits all 5 hop
events before panicking (see below).

### Trade amounts are clock-blind at depth 5; hop event timestamps are not

- The 5-hop buy anchor (tail U5 5,207,955,235,891, buyback leg
  4,515,471, withheld vq1 10,000,000 / bb22 45,611) is
  byte-identical at ts 0, 10, 21, 777, -1, and 2**62, and all 5
  hop events carry the step timestamp (0, 10, 21, 777, -1,
  4611686018427387904 respectively).
- The 5-hop sell anchor (net 178,541, buyback 837) is identical
  at ts 0, 777, and -1, with all 5 sell events timestamped
  accordingly.
- The v2 buy (cost 186,637, buyback 840), the 10**6-LP deposit
  (161 base + 2 quote gross legs), the protocol sweep (2,488
  gross, net 2,463), and the patched-window boost (burn
  5,338,379,201,831) are all clock-blind in amounts at ts 777
  and -1.

### Token-claim conversion follows the day index, not the raw clock

- With GVA start 20, end 49, seconds 1, seed last 20, volume
  333,444, unclaimed 111: claims at ts 0, 19, and 20 pay only
  the 111 unclaimed (volume stays 333,444, last updates to
  now); claims at ts 21, 22, 49, 50, 100, and 1000 pay the full
  3,334,551 gross (net 3,301,205 at 100 bps, withheld 33,346),
  volume goes to 0, claimed becomes 3,334,773.
- The conversion rule that fits every measured pair: let
  prev_day = (last_update - start) / seconds and
  now_day = (now - start) / seconds. The volume converts
  exactly when prev_day is inside the window [0, end - start]
  AND now_day > prev_day. Otherwise the claim pays only the
  unclaimed balance (and still advances last_update to now).
  Evidence: last 49 claim at 50 converts (prev_day 29, now_day
  30); last 50 claim at 60 pays 111 only (prev_day 30, past
  the window end 29); last 100 claim at 200 pays 111 only
  (prev_day 80); last 0 claim at 21 pays 111 only (prev_day
  -20); last 20 claim at 20 pays 111 only (now_day == prev_day
  == 0, no advance).
- The ts 0-21-22 chain shows the rule in motion: claim at 0
  pays 111 (prev_day 0, now_day -20, no advance; last becomes
  0); claim at 21 is silent (0 events: unclaimed already 0,
  prev_day -20 outside the window; last becomes 21); claim at
  22 converts the volume, paying 3,334,440 = 333,444 x 1000 /
  100 (prev_day 1, now_day 2).
- The ts 21-twice chain: first claim at 21 pays the full
  3,334,551, second claim at 22 is silent (0 events, last 22,
  volume already 0).
- A negative-clock claim panics with ProgramFailedToComplete
  (0 events, full rollback, UVA byte-identical) — the only
  negative-clock leg that fails; negative-clock buys, sells,
  syncs, and boosts all succeed with timestamps of -1.
- A 2**62-clock claim succeeds and pays the full 3,334,551
  with event ts 4611686018427387904.

### Sync fires exactly when now < start AND last < start

- With seed last 10, start 20: syncs at ts 0, 10, 19, and -1
  fire (64-byte event disc c57aa77c74515bff, claimed 222 -> 0,
  has 1 -> 0, volume 333,444 stranded, last unchanged at 10);
  syncs at ts 20, 21, and 50 do not fire (0 events, claimed
  stays 222, has stays 1).
- Last-side gate confirmed: last 20 sync at 10 does not fire,
  last 21 sync at 10 does not fire, last 19 sync at 19 fires.
- A fired sync strands the volume for the next claim: sync at
  10, claim at 21 pays only the 111 unclaimed (prev_day -10
  outside the window, last advances to 21), and the following
  claim at 22 converts the full volume 3,334,440 (claimed
  total 3,334,551).
- The ladder chain (sync 10, claim 10, claim 21, claim 22):
  claim at 10 pays 111 (prev_day 0, now_day -10, no advance),
  claim at 21 is silent (unclaimed already 0, prev_day -10
  outside the window; last becomes 21, 0 events), claim at 22
  pays 3,334,440 (prev_day 1, now_day 2).

### GVA window patches move the boundaries with start/end/seconds

- Start 100, end 1000: claims at 99, 100, and 101 all pay only
  111 (last 20 < start blocks conversion in every case, last
  advances to now); sync at 99 fires (now < start, last 50 <
  start), sync at 101 does not fire (now >= start).
- End 30: claim at 31 converts fully (3,334,551, last 20 inside
  the window), but last-31 claim at 40 pays only 111 — the
  volume's day (from last_update 31, past end 30) no longer
  converts even though the day index advances.
- Seconds 0: claim at 21 pays only 111 (no panic, volume
  stranded, last advances to 21); sync at 10 fires normally.
  A zero seconds-per-day disables conversion without failing
  the leg.
- Seconds 86400: claim at 86420 converts fully (day advances
  0 -> 1); last-86420 claim at 90000 pays only 111 (same day
  1, no advance); sync at 10 fires (now < start, last < start
  unchanged by the seconds patch).

### Lifecycle, cashback, and setter event timestamps follow the clock

- Cashback claim (plain quote, ATA balance 5,475) pays exactly
  5,475 at ts 777 and ts 0, with the 72-byte event timestamped
  accordingly (disc e2d6f62107f293e5).
- Init (80 bytes, disc 86240d48e86582d8), close (80 bytes,
  disc 929fbdac925838f4), and 90-byte extend (96-byte event,
  disc 6161d7905d92167c) all carry ts 777.
- Disable (53 bytes, disc 6bfdc14ce4ca1b68) and admin rotation
  (80 bytes, disc e198ab57f63f42ea) events carry ts 777 after
  the builder fix below; the buy-bit disable then fails the
  5-hop buy with 6020 (0 events) at ts 777, and re-enable
  restores the anchor.
- Buyback-config is silent (0 events) at any clock; the
  following 5-hop buy at ts 777 moves the buyback leg to
  6,773,206 with the tail unchanged.
- Sweep (185 bytes, disc 82a42461e48287a5) and collect (120
  bytes, disc e8f5c2eeeada3a59) events carry no timestamp
  field, and neither does the boost event pair (512-byte
  BuyEvent + 208-byte boost event) — the clock does not appear
  in those legs' events at any timestamp.

### The 5-hop failing-buy panic is clock-blind; the failing sell stays 6004

- A 5-hop buy with any unmet min_out panics with
  ProgramFailedToComplete ("memory allocation failed, out of
  memory") after all 5 hop events, at both ts 777 and ts 0,
  with full rollback — the #146 depth-5 behaviour, unchanged
  by the clock, on all three images.
- A 5-hop sell with an unmet min_out fails cleanly with 6004
  at ts 777, also after all 5 hop events, with full rollback.
- Buy-then-claim (buy at 21, claim at 22) and claim-then-buy
  (claim at 21, buy at 22) both pay the anchor tail and the
  full claim; trade and claim legs do not interfere across
  the clock boundary.

### Transfer-fee variants are clock-blind

- tf0 5-hop buy tail 5,259,040,470,738 (buyback 4,607,153) at
  ts 777 and ts 21; tf5000 buy tail 2,668,075,748,732
  (buyback 1,151,788) at ts 777; tf5000 sell 90,172 (buyback
  423) at ts 777; tf5000 token claims at ts 21 and 22 pay the
  full 3,334,551 gross, net 1,667,275 (withheld 1,667,276).
  All hop/claim events carry the step timestamp.

## Limits

- The day-index conversion rule is pinned from measured
  claim/sync pairs only; the exact day-index arithmetic
  inside the program was not traced to a source line, and no
  source change is proposed.
- The end-30 pair (last 20 converts, last 31 does not) is
  reported as measured; the window bound is described as
  last_update vs end, not as a traced code path.
- Seconds 0 disables conversion without panicking; the
  division guard behind that behaviour was not traced.
- The negative-clock claim panic is reported as observable
  behaviour only; its site was not traced.
- No claim is made about the whole program: only the measured
  clock behaviour on this chain, on these three images, is
  pinned.
- All 78 cases agree on all three images (original, control,
  candidate): there is no rebuild divergence in this packet.

## Build note

- The first MEASURE run showed disable/admin events timestamped
  1234567890 despite a step timestamp of 777: the setter
  branches (bbcfg/tog/dis/uadm) in the builder are early-return
  paths that hardcoded the clock. The builder was patched so
  every clock-setting site respects the per-step timestamp
  (defaults: 10 for close/init/sync/extend, 21 for token
  claims, 1234567890 otherwise), MEASURE and the full build
  were re-run, and the shipped receipts carry the correct
  step timestamps. Verify re-validates every receipt
  independently, so the shipped artifacts are unaffected.

Made via @slopdotcash
