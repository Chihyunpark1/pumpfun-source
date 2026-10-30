# Multi-hop split x boost x tf: cross-pool boost chains at TRUE 5 hops

## Problem

Packet #111 measured boost on the hop pools P2 and P3 of the true-3-hop
split x boost x transfer-fee chain. This packet extends those findings
to the TRUE 5-hop chain (three_amm + g4 + g5, final output U5): every
hop pool on the route (P2, P3, P4, P5) gets proper pool data (bump,
pool-authority creator, its base mints, its vaults), and the questions
are whether the P4 and P5 hop pools boost exactly like P2/P3, whether
the boost authority still rotates globally across all five pools,
which Anchor gates fire on P4/P5 boost ATAs, and how hop boosts move
the 5-hop buy/sell legs — in particular whether the depth-3 effects
(the sell payout +1 after a P2 boost) survive at depth 5.

## Cases

116 cases, 927 receipts, 93 parts, bps 100 unless noted. Every case
runs on original, control and candidate images; all three agree
everywhere (0 divergent cases). Spends are 10^9 quote unless noted;
`vq` patches set a pool's virtual_quote_reserves i128 field to 10^9
to open its boost window (the fixture window sum is 0). Successful
5-hop swaps emit 5 hop events (508-byte buy / 449-byte sell each).

- **A anchors (7).** Multi-hop buy tail 5,207,955,235,891; multi-hop
  sell payout 178,541; main boost burn 5,338,379,201,831 (vq patch +
  request 10^9, vault 10^12); unpatched P2 boost 6065; unpatched P3
  boost 6065; unpatched P4 boost 6065; unpatched P5 boost 6065.
- **B P2 boost core (10).** Fresh P2 boost burns 999,997,999 (used
  10^9, remaining 999,000,000,000, quote_after 1,000,001,000,000,000,
  base_after 999,999,000,002,001); second boost burns 999,995,999;
  min_base exactly 999,997,999 succeeds, +1 fails 6004; request 0 fails
  6002; empty vault fails 6002; vault equal to the request drains and
  **closes the boost ATA** (remaining 0, account gone); vault 10^6
  against a 10^9 request succeeds, burns 999,997 and closes the ATA;
  a re-boost after the close fails 3012; a P2 vq patch alone moves
  the 5-hop buy tail to 5,207,950,135,993 (-5,099,898).
- **C P3 boost core (6).** Fresh P3 boost burns 999,997,999; draining
  its vault exactly closes its ATA (remaining 0); min+1 fails 6004; a
  closed boost followed by a vq patch burns the anchor; a P3 vq patch
  alone moves the buy tail to 5,207,950,108,800 (-5,127,091); a
  P2-then-P3 sequence burns 999,997,999 on both pools.
- **C2 P4 boost core (11).** The 4th hop pool mirrors P2 exactly:
  fresh burn 999,997,999, second 999,995,999, min_base exact succeeds
  and +1 fails 6004, request 0 fails 6002, empty vault fails 6002,
  drain-exact closes the BA4S ATA (remaining 0), drain-short (10^6)
  burns 999,997 and closes BA4S, re-boost after close fails 3012, a
  closed boost followed by a vq patch burns the anchor, and a P4 vq
  patch alone moves the buy tail to 5,207,950,081,605 (-5,154,286).
- **C3 P5 boost core (13).** The terminal hop pool mirrors P2 exactly:
  fresh burn 999,997,999, second 999,995,999, min_base exact succeeds
  and +1 fails 6004, request 0 fails 6002, empty vault fails 6002,
  drain-exact closes the BA5S ATA (remaining 0), drain-short (10^6)
  burns 999,997 and closes BA5S, re-boost after close fails 3012, a
  closed boost followed by a vq patch burns the anchor, and a P5 vq
  patch alone moves the buy tail to 5,207,950,054,411 (-5,181,480). A
  P4-then-P5 sequence burns 999,997,999 on both pools, and a
  P2-P3-P4-P5 sequence burns 999,997,999 on all four hop pools.
- **D authority x pool (17).** Outsider-signed P2, P3, P4 and P5 boosts
  fail 6005. `set_boost_authority` by the payer rotates the authority
  to the outsider (1 event, disc 5980f08d5bca4769, 112 bytes); then
  the outsider P4 boost burns the anchor while the payer P4 boost
  fails 6005, and rotating back restores the payer P4 boost at the
  second burn 999,995,999. The P2, P3 and P5 rotation walks mirror P4
  exactly. One global rotation moves all four hop pools at once:
  after a single rotation the outsider burns 999,997,999 on P2, P3,
  P4 and P5, the payer P2 boost fails 6005, and rotating back
  restores the payer P5 boost at 999,995,999. An outsider-signed
  rotation attempt fails 6005. The same rotation moves the main boost
  too (outsider main boost burns the anchor 5,338,379,201,831), so
  the authority is global, not per pool. With `boost_enabled = 0` a
  P2, P4 and P5 boost each fail 6066; with the buy disable flag (8)
  a P2 and a P5 boost each fail 6020.
- **E ATA / program gates (17).** P4 boost with another pool's vault
  ATA fails 2015 ConstraintTokenOwner; a P4 vault ATA owned by the
  payer fails 2015; a P4 boost passing the TOKEN22 program for an SPL
  ATA fails 2023 ConstraintAssociatedTokenTokenProgram; a Token-2022
  ATA on an SPL mint passes the Anchor checks and fails in the
  Token-2022 TransferChecked CPI with fieldless IncorrectProgramId;
  a P4 boost with a TOKEN-owned, BP4-owned, BASE3-mint account at a
  non-derived address fails 2009 ConstraintAssociated. The P5 gate
  map is identical (2015 / 2015 / 2023 / IncorrectProgramId / 2009).
  A main boost with a foreign ATA and the TOKEN22 program fails 2023.
- **F chain interactions (21).** P2 boost then buy: tail
  5,207,939,910,316 (-15,325,575). Buy then P2 boost: burn 989,418,204
  (fresh 999,997,999 minus 10,579,795). P2 boost then sell: payout
  178,541, unchanged — the +1 seen at depth 3 is gone at depth 5; a
  P2 vq patch alone also leaves the sell payout at 178,541. P2 boost
  then sweep/collect: protocol sweep 2,488 in full, creator sweep
  123,394 in full, collect 123,394 in full - no Token-2022 withholding
  split. P2 boost then main boost burns the main anchor; main boost
  then P2 boost burns the P2 anchor. A failed (6065) P2 boost leaves
  the buy tail at the anchor. P4 boost then buy: tail
  5,207,939,747,168 (-15,488,723). Buy then P4 boost: burn 989,528,964
  (fresh minus 10,469,035). P4 boost then sell: payout 178,541,
  unchanged; a P4 vq patch alone leaves it at 178,541. P4 boost then
  sweep/collect pay 2,488 / 123,394 / 123,394 in full. P5 boost then
  buy: tail 5,207,939,665,660 (-15,570,231). Buy then P5 boost: burn
  989,598,940 (fresh minus 10,399,059). P5 boost then sell: payout
  178,541, unchanged; a P5 vq patch alone leaves it at 178,541. P5
  boost then sweep/collect pay 2,488 / 123,394 / 123,394 in full. P5
  boost then main boost burns the main anchor; main boost then P5
  boost burns the P5 anchor. A failed (6065) P5 boost leaves the buy
  tail at the anchor. P4 boost then P5 boost then buy: tail
  5,207,924,176,983 (-31,058,908).
- **G init_boost (7).** init_boost on P4 with no boost ATA succeeds
  with 0 events and creates the empty ATA (rent 2,039,280, balance 0)
  but leaves the vq field unchanged; a patched boost on that empty
  vault then fails 6002. init_boost on P4 followed by an unpatched
  boost fails 6065. init_boost on P5 behaves identically (creates
  BA5S, patched empty boost 6002, unpatched boost 6065). init_boost
  on P2 mirrors #111, and init_boost on the main pool (ATA already
  present) succeeds with 0 events and the following unpatched boost
  fails 6065.
- **H transfer-fee independence (6).** P2, P4 and P5 boosts at bps 5000
  and at bps 0 all burn 999,997,999 with no withheld amounts: the main
  pool's transfer-fee rate does not touch hop-pool boosts, whose
  quote mints are plain SPL.

## Result

Hop-pool boosts at depth 5 are the same object as at depth 3, with two
depth effects worth pinning. First, the P4 and P5 boost cores are
numerically identical to P2/P3 (fresh 999,997,999, second 999,995,999,
same min_base / request-0 / empty-vault codes, same drain-close and
3012 re-boost, same Anchor gate map), and the authority stays a
single global field: one rotation moves main, P2, P3, P4 and P5 boosts
together. Second, chain-leg effects scale monotonically with hop
depth while the sell leg goes flat: vq patches move the buy tail by
-5,099,898 (P2), -5,127,091 (P3), -5,154,286 (P4), -5,181,480 (P5);
hop boosts move the buy tail by -15,325,575 (P2), -15,488,723 (P4),
-15,570,231 (P5); buy-then-boost burns rise with depth (989,418,204
on P2, 989,528,964 on P4, 989,598,940 on P5). But every hop boost
leaves the 5-hop sell payout at exactly 178,541 — the +1 a P2 boost
added to the sell payout at depth 3 is absorbed somewhere in the
deeper chain, so at depth 5 the sell leg is hop-boost-blind while the
buy leg is not. Hop-pool sweeps and collects on P4/P5 pay the full
accrued amounts with no withholding split, and init_boost creates a
missing P4/P5 boost ATA without opening the window. All 116 cases
agree across original, control and candidate images (0 divergent
cases).

## Limits

- All measurements are synthetic harness states (patched vq fields,
  seeded vaults); no on-chain pool was boosted.
- The vq patch is a harness field reset, not an on-chain state
  transition: it models a pool whose window sum is already nonzero.
- The 2009 cases use hand-seeded accounts at non-derived addresses;
  they pin the Anchor address check, not a reachable user flow.
- Boost burns are measured at vault scale 10^12 with request 10^9;
  other scales were not swept.
- The sell-payout flatness at depth 5 is measured at the 10^9 spend;
  the absorbing leg was not isolated.

Made via @slopdotcash
