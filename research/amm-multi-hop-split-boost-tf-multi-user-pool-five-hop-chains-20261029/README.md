# Split x boost x tf multi-user and multi-pool chains at TRUE 5 hops

3rd-run packet #147. This packet extends the #93 multi-user /
multi-pool findings (a second user trading the same pools, two
chains in parallel, cross-user state effects, user isolation)
from the TRUE 3-hop chain to the TRUE 5-hop split x boost x tf
chain: `three_amm + g4 + g5`, final output U5. The outsider route
is a full second-user route: the signer is OUTSIDER, the UVA slot
is the outsider's real UVA PDA, the quote input is the outsider's
quote ATA, and the tail output is OU5 (outsider-owned BASE5 ATA).
Route verified in the builder (`build_route_out` appends the g4
and g5 hop groups to `three_amm`, same as the payer route); the
name, README and title all say 5-hop because the route really is
5 hops (#61 was 4 hops despite its 3-hop name; that mistake is
not repeated here).

## Problem

At depth 3, #93 pinned that the second user's trades pay the same
anchors, that claims and sweeps are per-user / first-come, and
that failures isolate across users. At depth 5 the open questions
were: does user identity still not move the trade when two more
hops of drift separate the users, do the outsider's claim and
sync legs stay isolated from the payer's buy, does the stable
middle chain still price identically at depth 5, and does the
#146 failing-buy divergence also cover outsider-signed buys?
This packet measures all of that on the split chain (quote mint
carries a 100 bps transfer-fee config by default; buyback routes
through the TOKEN22 ATA).

## Cases

67 cases, 143 steps, 429 receipts, 43 parts (42x10 + 9). Families:

- **A, two users on the same 5-hop route (16 cases):** outsider
  buy/sell anchors, both orders for buy/buy, sell/sell,
  buy/sell and sell/buy, three- and four-leg alternating
  chains, and failing-buy isolation in both directions.
- **B, outsider claims and syncs (10 cases):** token claim
  before/after the payer's claim, cashback claim both orders,
  payer sync then outsider claim, outsider sync then payer
  claim, outsider sync firing then outsider claim, payer
  close then outsider claim, payer buy then outsider claim,
  outsider buy then payer claim.
- **C, outsider-fee sweeps (8 cases):** protocol and creator
  sweeps in both fee-payer orders, outsider sweep then
  collect, sweep then outsider buy, buy then outsider sweep
  then buy, buy then outsider creator sweep then collect
  then buy, failed outsider buy then sweep.
- **D, single-leg interleaves (10 cases):** v2 buy/sell and
  legacy buy/sell legs before, between, and after 5-hop
  buys.
- **E, the stable chain in parallel (8 cases):** stable buy
  and sell anchors, standard/stable pairs in both orders,
  buy -> stable-buy -> buy, stable-buy -> stable-sell,
  buyback-config and disable-bit cases across both routes.
- **F, setters then outsider trades (5 cases):** buyback
  config then outsider buy, admin rotation to the outsider
  then outsider buy, outsider buy then patched-window
  boost, buyback config then outsider sweep, disable buy
  bit then outsider buy then re-enable then outsider buy.
- **G, failure isolation (5 cases):** payer buy then failed
  outsider sell then payer buy, failed outsider sell then
  outsider buy, failed outsider buy then outsider sell,
  failed payer buy then outsider buy, outsider buy then
  failed payer buy then outsider buy.
- **T, transfer-fee variants (5 cases):** outsider buy at
  tf 0 and tf 5000, outsider sell at tf 5000, payer buy
  then outsider buy at tf 5000, outsider token claim at
  tf 5000.

## Result

All cases agree across the original, control and candidate
images except the four divergent steps below. `verify.py`
re-checks every receipt independently (signatures, deltas,
withheld, event fields, error codes, rollback, 3-image
agreement, plus the outsider UVA state).

### User identity does not move the trade

- Outsider buy anchor = payer buy anchor exactly: tail
  5,207,955,235,891, buyback leg 4,515,471, withheld vq1
  10,000,000 / bb22 45,611. The only difference is the fee
  payer (dOUT -5,000, dPAYER 0). Outsider sell anchor =
  payer sell anchor exactly: 178,541, buyback 837.
- Trade order between users does not matter: buy-then-
  outsider-buy and outsider-buy-then-buy both end at the
  second-buy tail 4,918,089,082,874. The alternating 4-leg
  chain pays 5,207,955,235,891 -> 4,918,089,082,874 ->
  4,651,768,149,125 -> 4,406,509,597,797. Second sells pay
  178,539 in both orders (anchor -2 drift). Buy-then-
  outsider-sell and outsider-buy-then-sell both pay 189,218
  (the moved-pool value, not the 178,541 anchor).

### Claims and syncs are per-user and isolated

- Outsider token claim pays 1,050 gross (unclaimed 50 +
  volume 100 x supply 1000 / sol 100, 11 withheld at 100
  bps) whether it runs before or after the payer's
  3,334,551 claim, and the payer's claim is likewise
  untouched by the outsider's buy (still 3,334,551 after
  an outsider buy, and still 3,334,551 after a payer buy).
- Outsider cashback claim pays exactly its UVA-owned ATA
  balance 777, in either order relative to the payer's
  5,475 cashback claim.
- The payer's sync strands only the payer's volume
  (claimed 222 -> 0, has 1 -> 0) and leaves the outsider
  claim at 1,050. The outsider's sync fires the same way
  (claimed 100 -> 0, has 1 -> 0, volume 100 stranded) and
  leaves the next outsider claim paying only the 50
  unclaimed (1 withheld). The payer's close does not touch
  the outsider's claim, and neither does the payer's buy.

### Sweeps are first-come, fee-payer-blind

- Whoever sweeps first takes the bucket: protocol 2,488
  gross (net 2,463 + 25 withheld), creator 123,394
  (collect net 120,938). The second sweep, by either user,
  is a silent 0-event no-op. An outsider creator sweep
  followed by a payer collect still pays 120,938.
- A sweep by either user leaves the next buy at the
  buy-x2 second tail 4,918,089,082,874: sweeps are
  trade-neutral at depth 5, same as at depth 3.

### Single-leg interleaves move only the main pool

- Buy2-first and legacy-buy-first both leave the next
  5-hop buy at 5,207,940,156,120 (anchor -15,079,771):
  the two single-leg buys move the main pool identically.
  Legacy-sell-first leaves it at 5,207,970,312,616
  (anchor +15,076,725).
- A v2 buy between two 5-hop buys costs the third leg
  14,365,413 versus a straight second buy
  (4,918,074,717,461 vs 4,918,089,082,874). After a 5-hop
  buy, v2 buy costs 189,628 (standalone 186,637) and v2
  sell pays 181,267 (standalone v2 sell 178,409).

### The stable 5-hop chain prices identically

- Stable buy anchor = standard buy anchor exactly:
  5,207,955,235,891. Stable sell anchor = 178,541.
  The stable middle hops (USDC chain) do not move the
  5-hop tail at all.
- The buy/stable-buy pair is order-independent: the
  second leg pays 5,021,929,866,125 either way.
  Buy -> stable-buy -> buy ends at 4,745,460,948,884.
  Stable-buy -> stable-sell pays 189,218.
- A buyback-config setter moves the stable leg's buyback
  leg to 6,773,206 but not its tail; the disable buy bit
  blocks both routes with 6020.
- Builder note: the #146 stable-route builder sliced with
  3-hop indices (`metas[:21] + g2s + g3s`), which drops the
  g4/g5 groups and breaks route continuity (6084 on all
  images, 0 events). It was never exercised in #146
  because no case used `stable=True`. It is fixed here
  to the true 5-hop layout (main -> P2S -> P3S -> P4 ->
  P5, final output U5), and every stable leg in this
  packet runs on the fixed route.

### Setter authority transfers exactly

- After admin rotation to the outsider, the payer's
  buyback setter fails 6005 while the outsider's succeeds
  (0 events), and the outsider buy still pays the anchor.
- A buyback setter before an outsider buy moves its
  buyback leg to 6,773,206 with the tail unchanged. A
  disable buy bit blocks the outsider buy with 6020 and
  the anchor returns on re-enable.
- An outsider buy under a patched 1e9 window pays
  5,167,125,538,753 (the VQ-patch price, not the anchor)
  and the following boost burns 5,255,205,915,165,
  exactly the payer's buy-first boost value.

### Failure isolation is complete in both directions

- A failed outsider sell (6023, 0 events) or a failed
  outsider buy leaves the next payer buy at the buy-x2
  tail 4,918,089,082,874. A failed payer buy leaves the
  next outsider buy at the anchor 5,207,955,235,891.
- A failed buy in the middle of an
  outsider/payer/outsider chain leaves the final outsider
  buy at the buy-x2 tail. Every failed leg rolls back
  every watched account except the 5,000 fee.

### Transfer-fee variants hold for the outsider

- tf0 outsider buy tail 5,259,040,470,738 (buyback
  4,607,153, no withheld). tf5000 outsider buy tail
  2,668,075,748,732 (buyback 1,151,788, withheld vq1
  500,000,000 / bb22 1,151,789). tf5000 outsider sell
  90,172. tf5000 outsider token claim withholds 525 of
  1,050 gross. Payer buy then outsider buy at tf5000
  pays 2,590,950,921,881 for the outsider leg.

### Divergent cases (4 steps, all failing outsider buys)

- `a-obuy-fail-buy`, `a-obuy-fail-obuy`, `c-ofail-swp`,
  `g-obuy-fail-osell`: on each failing outsider buy, the
  original image returns clean 6004 ExceededSlippage
  after all 5 hop events, while the rebuilt images panic
  with ProgramFailedToComplete (the #146 failing-buy
  divergence, now pinned for outsider-signed buys too).
  Every other case agrees on all three images, including
  all event fields above.

## Limits

- The outsider's seeded UVA (unclaimed 50, claimed 100,
  volume 100, last 20, earned 777) and cashback balance
  (777) are fixture values; other seeds give different
  absolute claim amounts, but the isolation pattern
  (per-user UVA, per-user ATA balance) is structural.
- The stable route's middle hops are the USDC pools
  P2S/P3S from the #93 fixture; the P4/P5 hops are the
  standard hop pools, shared with the standard route.
- No source-change proposal is made and no full-program
  equivalence is claimed; the packet pins measured
  multi-user / multi-pool behaviour only.

Made via @slopdotcash
