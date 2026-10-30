# research: multi-hop split x boost x tf GVA lifecycle chains at TRUE 5 hops

#110 pinned the GlobalVolumeAccumulator lifecycle at 3 hops: there
is NO init or close instruction for the GVA in the program (only
close_user_volume_accumulator exists, for the UVA), so the GVA is
a PDA account that must pre-exist and its lifecycle is driven by
admin_update_token_incentives plus claim/sync reads. This packet
re-measures that whole lifecycle on a TRUE 5-hop split x boost x
tf chain (three_amm + g4 + g5, final output U5, five hop events
on every successful swap), so the depth-5 GVA numbers stand on
their own receipts instead of being extrapolated from depth 3.

All numbers below are measured receipts from this packet (3 images:
original, control, candidate; 0 divergent cases). 60 cases, 294
receipts, 30 parts (29x10 + 4). Multi-hop buys spend 10^9 quote
unless a case says otherwise; boosts request 10^9 quote with the
main pool vq patched to 10^9 wherever a boost must succeed;
transfer fee is 100 bps unless a case says otherwise. The fixture
GVA is start 20, end 49, sec 1, supplies 1000, sol_volumes 100;
the seeded UVA is (needs 1, unclaimed 111, claimed 222, volume
333444, last 20, has 1, earned 555, cb_claimed 666).

## Cases

- A anchors: fixture-GVA buy, sell, boost, token claim, sync
  no-op, sync reset, claim twice.
- B GVA absent / zeroed / truncated / wrong-owner: buy, boost,
  claim, sync, admin, sweep/collect/deposit beside each GVA
  state.
- C admin gates and effects: same-start, new-end, start-change
  wipe, supply day-0, supply all-days, mid-range zeroing, the
  seven gate failures (6030/6031/6032/6033/6035/6036/6037),
  outsider, unsigned, mint rotation and restoration,
  admin-then-boost, admin-then-buy.
- D claim lifecycle: claim after buy / boost / sweeps, claim
  with absent incentive-ATA vault, empty vault, absent user
  ATA, wrong-mint GVA.
- E sync lifecycle: sync after claim + start-change admin,
  sync with absent GVA, sync with zeroed GVA.
- F UVA close lifecycle: close seeded, close-then-claim,
  close-then-buy, close-buy-claim, close-init-claim, close by
  another user, unsigned close, close-then-boost.
- G GVA-blind chain legs: deposit/withdraw with absent GVA,
  admin-buy-boost, sell with zeroed GVA.

## Result

### 1. The only depth-5 number that moves is the buy tail

The fresh 5-hop buy tails **5,207,955,235,891** (3-hop:
5,262,910,281,902), emitting exactly 5 hop events of 508 bytes
each; the fresh 5-hop sell still pays **178,541** (5 sell events
of 449 bytes). Every other anchor reproduces #110 exactly: the
vq-patched boost burns **5,338,379,201,831**, the post-buy boost
burns **5,254,679,949,141**, the seeded token claim pays
**3,334,551** (claimed 222 -> 3,334,773, volume -> 0, last ->
21), and the claim after a buy, after a boost, or after sweeps
pays the same 3,334,551 — the chain legs never add volume to
the claim beyond the seed.

### 2. No init/close path for the GVA, at depth 5 too

An absent GVA breaks claim, sync and admin with **3012** (the
admin step fails instead of creating the account), while the
5-hop buy still tails the anchor, the boost still burns the
anchor, and sweep/collect/deposit beside an absent GVA pay the
fixture values (protocol sweep 2,463 net, collect 120,938
net). A truncated (100-byte) GVA breaks claim and admin with
**3003** while the buy stays anchor; a wrong-owner GVA breaks
the claim with **3007** while the buy stays anchor. A zeroed
GVA pays the unclaimed-only 111 on claim (volume 333,444
stranded, needs stays 1) and syncs as a no-op (start 0).

### 3. The admin gate map is depth-independent

Start in the past 6030, end in the past 6031, end before start
6032, range too large 6033, supply for a finished range 6035,
day after end 6036, day in the active range 6037, outsider
6005, unsigned 3010 — all reproduced at depth 5. A start
change wipes all 30 supplies and all 30 sol_volumes to 0 and
the next claim pays only the seeded unclaimed 111 (volume
stays 333,444); the following sync resets that 111 to 0. A
mid-range admin zeroes future sol_volumes only (vol[5] stays
100, vol[6] and vol[29] go to 0) and sets one supply slot
(supply[7] = 777), and the next day-0 claim pays the normal
3,334,551. Supply-slot edits move the next claim reward
exactly as at depth 3: day-0 supply 2000 -> claim 6,668,991
(claimed 6,669,213); all-days supply 500 -> claim 1,667,331
(claimed 1,667,553).

### 4. Mint rotation, sync gate, and UVA close all reproduce

Mint rotation breaks the next claim with **6038**
(InvalidIncentiveMint) and restoring the mint re-enables the
full 3,334,551 claim; the rotation admin itself costs the
payer 2,162,600 (new incentive-ATA rent). Sync fires only
when now < start AND last < start: last == start is a
0-event no-op, last 10 < start 20 resets claimed 222 -> 0,
and sync after a claim + start-change admin resets 3,334,773
-> 0. Closing the seeded UVA refunds 999,995,000 and strands
the unclaimed 111 forever: the next claim fails 3012, a
re-init (1,849,400 rent) never restores it, and the claim
after close + buy is a fresh 0-event no-op (claimed 0) —
while the buy after close recreates a fresh UVA and tails
the 5-hop anchor, and the boost after close still burns the
anchor. Close by another user fails 2006, unsigned close
fails 3010.

### 5. Chain legs are GVA-blind at depth 5

Deposit/withdraw beside an absent GVA pay the fixture values
(LP +1,000,000 / -1,000,000), admin-then-buy-then-boost burns
the post-buy 5,254,679,949,141, and the sell beside a zeroed
GVA pays the anchor 178,541. The GVA state never moves a
trade, a boost, a sweep, a collect, or a deposit at depth 5
— only claim, sync and admin read it.

## Limits

- `cpatch` steps are harness field resets (clock epoch, mint
  schedules, pool vq, GVA/UVA seeds), not instructions and not
  on-chain reachable states in this packet: they isolate the
  lifecycle rules, and the admin/claim/sync numbers above are
  receipt-level measurements on the three program images.
- The GVA has no init/close instruction in the checked-out
  program surface; the packet does not claim no such path
  exists in any other program version.
- No source change is proposed and no full-program
  equivalence is claimed. All three images agree on every
  receipt (0 divergent cases).

Made via @slopdotcash
