# research: split x boost x tf wallet and user state chains at true 5 hops

3rd run packet #151. The #97 wallet/user-state findings (user wallet
balances, user token accounts, wallet funding/rent effects) re-measured
on a TRUE 5-hop split x boost x tf chain: `three_amm` + `g4` + `g5`,
final output U5. Every successful swap below carries exactly 5 hop
events (buy disc `67f4521f2cf57777` len 508, sell disc
`3e2f370aa503dc2a` len 449); the hop count in this name matches the
route in code.

## Problem

At depth 3 (#97) the paying user's wallet behaved as a strict input
gate and a lax output: bad inputs fail before any leg runs, while a
foreign-owned output still gets paid. Depth 5 changes the shape of
failure: a bad output now fails only after most legs have already run
(ghost events), and the native rent check fires after execution, not
before it. This packet pins the wallet rules at depth 5: buy-input
amount and rent floor, buy-input state/owner/mint/absence,
sell-input U5 and output-owner asymmetry, userbase invariance,
payer-funded UVA auto-init, cashback-claim destination wallet,
deposit/withdraw wallet legs, wallet exhaustion chains, v2 wallet
legs, and transfer-fee variants.

## Cases

94 cases, 351 receipts, 36 parts (35x10 + 1), each run on three
program images (original, control, candidate). Families:

- **A, buy-input amount (7):** anchor; exact-rent; exact-floor
  (1,000,090,480); minus-1; half; zero; withheld 12,345.
- **B, buy-input lamports (6):** floor minus-1 / exact / 2,129,280 /
  2,157,600; rent-only custom-14; rent-only rent-fail.
- **C, buy-input state (6):** frozen; uninitialized; outsider-owned;
  absent; wrong-mint; fail-sweep-restore.
- **D, sell-input and output asymmetry (14):** sell anchor; sell
  amount exact / minus-1 / half / zero; frozen U5 input; U5 lamports
  0 / 1; outsider-owned U5 input; outsider-owned output on buy;
  frozen output on buy; frozen output on sell; outsider-owned
  output on sell; frozen-output buy then restore.
- **E, userbase untouched (5):** absent/frozen/outsider/zero userbase
  on buys and sells.
- **F, payer-funded UVA auto-init (15):** first buy; second buy;
  first sell; seeded buy; payer-exact; payer-minus-1;
  payer-seeded-exact; payer-seeded-minus-1; sweep without init;
  v2 buy init; boost without init; collect without init;
  fail-noinit; close cycle; init cost.
- **G, cashback claim destination, plain mode (6):** anchor;
  frozen; outsider-owned; absent; twice; after buy.
- **H, deposit/withdraw wallet legs (16):** deposit anchor; base
  exact/short; quote exact/short/zero; frozen LP; absent LP;
  frozen base; withdraw anchor; LP short; frozen LP/base/quote;
  withdraw too much; deposit-withdraw dust.
- **I, wallet exhaustion chains (5):** buy chain x3; buy amount
  chain; buy rent chain; sell chain; sell top-up.
- **J, v2 wallet legs (6):** v2 buy anchor/outsider/frozen/short;
  v2 sell anchor/frozen.
- **T, transfer-fee variants (8):** tf0 buy/sell; tf5000 buy/sell;
  tf5000 half; tf5000 withheld; tf5000 rent floor; tf0 frozen
  output.

## Result

All three images agree: **0 divergent cases**. Measured at depth 5:

- Anchor: buy 10^9 quote pays tail U5 **5,207,955,235,891** with 5
  hop events; sell 10^9 base pays **178,541** (restore sell
  178,539); second buy 4,918,089,082,874; third buy
  4,651,768,149,125.
- Buy-input strictness (gate codes unchanged from #97): amount
  below 10^9 gross fails Token custom 1 with 0 events; frozen
  input Token custom 17, 0 events; uninitialized input
  UninitializedAccount, 0 events; absent input 3012; wrong-mint
  input 6084 MultiHopDiscontinuousPath; outsider-owned input
  Token custom 4; withheld 12,345 on the input does not block
  the buy (anchor tail).
- Post-trade rent floor: in this harness a buy debits the input
  account's lamports by the spent amount as well as its tokens,
  so the runtime rent check applies to post-trade lamports
  against the 2,129,760 floor for a 178-byte Token-2022 account:
  10^9 + 2,129,759 fails InsufficientFundsForRent after all 5
  hop events with full rollback; 10^9 + 2,129,760 exactly
  passes; 10^9 + 2,129,280 fails the same way; 10^9 + 2,157,600
  passes; lamports 2,039,280 alone fails Token custom 14 with
  0 events.
- Frozen-output ghost ladder at depth 5: frozen U5 on a buy
  fails Token custom 17 after **4** hop events (vs 2 at depth
  3); frozen userquote on a sell fails custom 17 after **4**
  events (sells execute terminal-first, so the output leg is
  last in both directions); frozen U5 input on a sell fails
  custom 17 with 0 events; restoring the frozen output lets
  the buy succeed at the anchor tail.
- Output leg laxity: outsider-owned U5 still receives the full
  buy tail; outsider-owned userquote still receives the full
  sell payout; only a frozen output fails.
- Sell-input: U5 amount below 10^9 fails custom 1; frozen U5
  custom 17; outsider-owned U5 custom 4; 0-lamport U5 fails
  3012 while 1 lamport succeeds (anchor payout).
- Userbase never touched: absent, frozen, outsider-owned, or
  zero-amount userbase all leave multi-hop buys and sells at
  anchor tails.
- Payer-funded UVA auto-init: first buy/sell creates the
  137-byte UVA at 1,844,400 lamports; payer-exact 1,849,400
  succeeds, 1,849,399 fails custom 1 with 0 events; seeded
  UVA: payer-exact 5,000 succeeds, 4,999 fails
  InsufficientFunds (fee) with 0 events; close then buy
  re-creates the UVA and lands on the second-buy ladder tail;
  sweep moves 2,488 without init; boost and collect run
  without init; a failed buy leaves no UVA and the restore
  buy succeeds.
- Cashback claim destination (plain mode, funded uvata 5,475):
  claim pays +5,475 to userquote; frozen destination custom
  17; outsider-owned destination custom 2015; absent
  destination 3012; second claim succeeds with 0 delta; claim
  after a tf0 buy still pays +5,475 (tf0 buy tail
  5,259,040,470,738).
- Deposit/withdraw wallet legs: deposit 10^6 LP costs exactly
  160,619,896 base and 29,610 quote (short by 1 on either side
  fails custom 1); frozen LP/base fail custom 17, absent LP
  3012; withdraw 10^6 LP pays 160,619,895 base and 29,018
  quote; frozen LP/base/quote fail custom 17; withdrawing
  10^15 LP fails custom 1; deposit-then-withdraw round trip
  is not lossless (base -1, quote -592).
- Wallet exhaustion chains: a 2x10^9-funded wallet buys twice
  then fails custom 1 on the third; a sell chain funded with
  2x10^9 sells twice (178,541 then 178,539) then fails custom
  1; top-up restores the sell; rent chain: a wallet at
  2x10^9 + 2,039,280 lamports passes the first buy but the
  second fails InsufficientFundsForRent with 5 ghost events,
  and restoring lamports to 3x10^9 lets the buy succeed at
  the ladder tail.
- v2 legs: v2 buy 10^6 pays 1,000,000 base for 189 quote;
  outsider input custom 4, frozen custom 17, short input
  custom 1; v2 sell pays 176 quote for 1,000,000 base; frozen
  v2 sell input custom 17.
- Transfer-fee variants: tf0 buy tail 5,259,040,470,738, tf0
  sell payout 180,345; tf5000 buy tail 2,668,075,748,732,
  tf5000 sell payout 90,172; tf5000 half-amount buy fails
  custom 1; withheld 12,345 on the input does not change the
  tf5000 tail; the rent floor applies under tf5000 (10^9 +
  2,129,759 RentFail, 5 events); frozen output under tf0
  fails custom 17 after 4 events.

## Limits

- Receipts are litesvm replays of the three program images, not
  mainnet transactions; the lamport/token coupling observed on
  token accounts (a buy debits input lamports by the spent
  amount) is a property of this harness and is stated as
  measured here, not as a mainnet claim.
- Wallet patches (amount, lamports, state, owner, mint,
  withheld, absence) are applied directly to account state
  before each step; they pin gate behavior, not the path by
  which a wallet could reach that state on-chain.
- No source change is proposed; no claim is made about the
  program beyond the measured cases.

Made via @slopdotcash
