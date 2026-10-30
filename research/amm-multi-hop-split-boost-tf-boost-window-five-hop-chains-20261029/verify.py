"""Independent re-verification for amm-multi-hop-split-boost-tf-boost-window-five-hop-chains-20261029.

Checks, from the packet files alone (plus the three program images):
- MANIFEST.json lists every packet file (except itself) with a matching sha256.
- runtime/report.json.gz: 81 cases, 372 receipts, 38 parts
  (37x10 + 2), part sha256/byte counts match the part files.
- Every receipt transaction parses (solders) and all signatures verify.
- Every receipt's recorded before/after snapshots reproduce the
  report's per-image expected values: fee-payer and outsider lamport
  deltas, the token-leg deltas (user base/quote/LP, tail output U5,
  vault base/quote per hop, TOKEN22 buyback in transfer-fee mode,
  main and hop boost ATAs, Token-2022 sweep/collect ATAs), the
  Token-2022 withheld deltas and the mint-level withheld balance,
  the native-mint token-account lamport deltas, the five pool states
  (virtual_quote_reserves i128, protocol_fees, creator_fees,
  lp_supply) plus the pool coin_creator bytes after every step,
  the payer and outsider user volume accumulator states, the
  GlobalConfig state after every step, the GlobalVolumeAccumulator
  state after every step, and the decoded event fields (multi-hop
  disc/len/ts per hop event, v2 buy/sell fields, deposit/withdraw
  fields, sweep/collect fields, boost requested/used/burned/vq/
  quote-after/base-after/remaining plus the leading 512-byte
  BuyEvent, token claim fields).
- Failure steps roll back every watched account except the fee
  payer (fee 5,000) and carry the expected error code. Error
  sites are pinned per image, never compared across images.
- Boost window/burn findings pinned by this packet (0 divergent cases):
  - Anchor (tf100, vq patch 10^9): a 10^9-quote boost burns
    5,338,379,201,831 (used 10^9, quote-after 123,936,690,720,
    base-after 668,358,016,710,914, boost ATA remaining
    999,000,000,000) -- identical to the #100 3-hop anchor: the
    main-pool burn does not move with depth.
  - The burn does NOT read the fee buckets at depth 5 either:
    protocol or creator seeds from 0 to 10^11 leave the anchor
    burn byte-identical, and a 10^9 + 10^9 bucket seed burns
    exactly the anchor. Buckets enter only the gate: a bucket
    at 10^12 fails the boost with 6023 Overflow and 0 events
    (protocol and creator alike).
  - Same window sum, different compositions, at depth 5: the
    #100 splits reproduce exactly -- vq 10^9 + fixture buckets
    5,338,379,201,831; vq 10^9+123,394 + creator 0
    5,338,373,929,374; vq 10^9+2,488 + protocol 0
    5,338,379,095,522; vq 10^9+125,882 + both buckets 0
    5,338,373,823,065 (slope about -42.73 per vq-field unit).
    Window 3,000,125,882 as vq 10^9 + both buckets 10^9 burns
    the anchor, while as vq 3x10^9 + fixture buckets it burns
    5,254,268,308,887 -- the window sum is a gate input, not
    the burn input.
  - Vq ladder (tf100): 10^6 -> 5,381,409,217,895; 10^8 ->
    5,377,114,041,125; 10^9 -> 5,338,379,201,831; 10^10 ->
    4,979,661,866,360; 10^12 -> 593,413,700,956. vq 0 burns
    5,381,452,638,525 and a negative vq (-10^9) still burns
    5,425,226,816,983 -- no zero/negative clamp on the burn;
    only the exact-zero window sum gates with 6065.
  - Window motion through legs: a fresh-pool 5-hop buy leaves
    the window at 0 (vq -4,686,964 + protocol 4,563,570 +
    creator 123,394), so the next boost still fails 6065; a
    fresh-pool sell likewise. Buy then boost (vq patch 10^9):
    5,255,205,915,165. Sell then boost: 5,338,394,947,549.
    Buy+sell then boost: 5,255,222,206,552. Buy then sweep
    then boost and buy then sweep+collect then boost are
    burn-identical to buy then boost -- a sweep is
    burn-neutral at depth 5 too.
  - Boost decay at depth 5: 5,338,379,201,831 ->
    5,254,441,549,265 -> 5,172,468,136,601 (about 1.56% per
    10^9-quote boost, as at depth 3); a fourth boost
    continues the ladder. After a buy the second boost is
    5,173,214,684,656 on the drained vault.
  - Deposit nudges the burn: deposit 10^6 LP then boost
    5,338,379,211,910 (vq +238, burn +10,079); deposit+withdraw
    then boost restores the anchor burn exactly
    (5,338,379,201,831, vq field 999,999,999 vs 10^9 -- a
    1-unit rounding residue). Buy then deposit then boost:
    5,255,205,925,004. v2 and legacy buys move the main burn
    by the same -15,829 (5,338,379,186,002); a token claim
    leaves it byte-identical.
  - Authority/flag gates, in check order: boost authority
    outsider or zero -> 6005 InvalidAdmin, 0 events (before
    the window check); boost-enabled off -> 6066, 0 events
    (off-then-on via toggle_boost restores the anchor burn
    exactly); buy-disabled config -> 6020 on boost, and
    re-enabling restores the anchor burn; sell-disabled
    config leaves the boost at the anchor. Restoring the
    payer authority after a 6005 failure restores the
    anchor burn.
  - Transfer fee (gross requested 10^9): tf0 ->
    5,391,870,655,895; tf100 -> 5,338,379,201,831 (net
    990,000,000 credited); tf5000 -> 2,706,767,012,738
    (net 500,000,000 credited). Buy then boost at tf0:
    5,307,028,789,111; at tf5000: 2,685,302,061,999.
  - Requested-amount ladder (tf100, vq 10^9): 10^6 ->
    5,380,970,054; 10^8 -> 537,672,386,159; 2x10^9 ->
    10,592,820,756,404; 10^10 -> 49,830,102,507,836.
    Requested 10^12 uses the full 10^12, burns
    598,735,502,793,632, drains the boost ATA to 0
    remaining, and then fails 6088 with both events
    emitted (transaction rolls back). Requested 0 and
    requested 1 both fail 6002 with 0 events -- a small
    request is a gate failure, not a small burn.
  - Vault gates: empty base vault -> 6001, empty quote
    vault -> 6023, zero boost ATA -> 6002, all 0 events.
    A boost ATA holding only 10^6 spends exactly 10^6
    (burn 5,380,970,054, identical to the requested-10^6
    burn), emits both events, then fails 6088 and rolls
    back -- so 6088 means "requested exceeds the boost
    ATA balance", with the partial spend visible in the
    event but not in state.
  - Recovery from the 10^12 bucket trap: restoring the
    bucket fields to the post-setup snapshot recovers the
    anchor burn exactly. A trade after that recovery pays
    5,087,534,167,771 -- lower than the pre-boost buy tail
    5,167,125,538,753 because the successful boost drained
    the base vault; the trap failure itself left no other
    state behind. On-chain this is not an escape: the sweep
    that would drain the bucket also fails 6023.
  - Hop-pool boosts (P5 terminal, SPL-derived ATA): a
    fresh P5 boost fails 6065; with P5 vq patched to 10^9
    it burns 999,997,999 (used 10^9, quote-after
    1,000,001,000,000,000, base-after 999,999,000,002,001,
    remaining 999,000,000,000). A second P5 boost burns
    999,995,999 (decay of only 2,000, not 1.56% -- the hop
    burn curve is far flatter). After a 5-hop buy the P5
    boost burns 989,598,940. P5 boosts are tf-blind (tf0
    and tf5000 both 999,997,999 -- the hop quote mint is
    SPL, outside the quote-mint transfer-fee override).
  - Hop-pool differences (genuine depth-5 pins): a P5
    protocol bucket at 10^12 does NOT trap the hop boost
    -- it burns the anchor 999,997,999, where the same
    seed on the main pool fails 6023. And a short hop
    boost ATA does NOT fail 6088: a P5 boost with a 10^6
    ATA succeeds, spending exactly 10^6 (used 10^6,
    burned 999,997, remaining 0), closing the SPL ATA and
    refunding its lamports to the payer (dPAYER
    +1,000,999,995,000). The main-pool 6088 rule does not
    extend to hop boosts. A P4 vq patch leaves the main
    boost at the anchor -- hop windows do not move the
    main burn.
  - Vault balances at fixed window: vb1 10^12 ->
    7,924,013,300; vb1 10^15 -> 7,924,013,300,677 (1000x
    the vault, 1000x the burn -- linear in the base
    vault). A 10^12 quote vault at vq 10^9 burns
    665,634,817,992.

"""


import base64
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

from solders.pubkey import Pubkey
from solders.transaction import Transaction

ROOT = Path(__file__).resolve().parent
WS = Path.home() / "workspace/slop-verify"
SPARSE = Path.home() / "workspace/pumpfun-sparse"
IMAGE_PATHS = {
    "original": SPARSE / "evidence/original/pump_amm/deployed.so",
    "control": WS / "control.so",
    "candidate": WS / "candidate.so",
}
PAYER_KEY = Pubkey.from_string("DXyM8yAHqpMzDtvwz5DXoEUQmPxjJPMKCASCPhLMKpEx")
POOL = Pubkey.from_string("GseMAnNDvntR5uFePZ51yZBXzNSn7GdFPkfHwfr6d77J")
POOL2 = Pubkey.from_string("Fpyw25Qi4beJtjo22e1iLZ8PeGkKXFBkF2WbdSuxsaZa")
P3 = Pubkey.from_string("3tvv2kFkoHENFctvg9VKJi2z6pagcMPoHMFP3m9FfruF")
P4 = Pubkey.from_string("5gZTf2A6UPeYZCq1mkdiYquMQqmjNcz9pknbABkWif9c")
P5 = Pubkey.from_string("5TdRYVo7We7hYSXDS3ryvUvouL7hoaMLTGMRqMrzBhcE")
BASE4 = Pubkey.from_string("6ws1bVyu3F8wGy1fPHhrc2v8UyWiGbRAAuek8SwikKPD")
BASE5 = Pubkey.from_string("75hbt6uvDqjPZ9WgFtMhBnTeyHw7cinoHiz4FD2vEz2d")
VB4 = Pubkey.from_string("3qw1dQGA7eW3m2BsiAhUB5R3sXEYnr7NbMFBuqUSotYn")
VQ4 = Pubkey.from_string("6WdSUBTULBFY4FE31WymuxQqJcWeLoLBCucMFsprkUAM")
VB5 = Pubkey.from_string("EbswyL8rkPriwr3sfAftkGBRutDHAtQWK1pT7GMcJH9t")
VQ5 = Pubkey.from_string("5m89K1EMCbe1PYwQ7aJeZ8vEsSYrCRkcGMzf53Nxhvs8")
U4 = Pubkey.from_string("71nJjoSudYSAR4GApb2mtugtj8iuwf6yjKKQBpzKVehv")
U5 = Pubkey.from_string("79cu2QNvp92chEmBhBgcUfERDT9KHnUcr8eiJb5WzKML")
USERBASE = Pubkey.from_string("5jKh25biPsnrmLWXXuqKNH2Q67j69T4Q7Zew5c8wJKaV")
USERQUOTE = Pubkey.from_string("5oEzAP4izB65uRm2yDAEf9oALGwHpWkDfyKb8zBY3euC")
USERLP = Pubkey.from_string("5sAHJgXjaUPK3X1YQWV9x2ZvaS9VVaS3ENzFCNE8nzDu")
VAULTBASE = Pubkey.from_string("5jMpkf4JF4noHftLgNKyPNh6roVfPSGSjuEk3U4eLKRa")
VAULTQUOTE = Pubkey.from_string("43DVcZR4kQFjh4Xm2i3DcneRxNjZp7HMud8yDrJWrDr8")
VB2 = Pubkey.from_string("3WojBK9kk5fHnhZfDb16jNJxGu6RtVdKpxYfFUKExGjg")
VQ2 = Pubkey.from_string("7S39XJ3FdyipvwLvgrf65cDWxC1dFaXUSaoNR6wvy59t")
VB3 = Pubkey.from_string("HWrvLRAYVW6NC4QK4mofY6wcuztVZXLNm4syGwQarZnM")
VQ3 = Pubkey.from_string("8fXWArssNK14eGw3puZgFqRRDrXjMMxuWX63nYUggKXi")
U3 = Pubkey.from_string("6swiTCWtSwqi8sm9wzNwKA9NEpJWbXjLcVz654u7zz4W")
P2S = Pubkey.from_string("22ASwHQiu9k6v9Ph8qTotBvoaHYUbDiBqDeovq1ucpEn")
P3S = Pubkey.from_string("8zVcWQui5FJsNni2VtsLza2vUCQXJsjBw5CxvrrRJr1x")
USDC = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
VB2S = Pubkey.from_string("D2e27UhbE2wf4DUY1a9wFZYxXebD6Unb8aV6HGJQXDq7")
VQ2S = Pubkey.from_string("4GHAT63xGUeJgk2JXN8DAs9K34wQCRrPHNHpS78bhu8T")
VB3S = Pubkey.from_string("2E4BSAY4VjvVFXCcQWdjCrjdjM9hQ3rJ7gtDqLo2Dmox")
VQ3S = Pubkey.from_string("G8ARPQc2abcLGECnsKZcGRN7eN4JJ9Qwxo9KcqQSxy3K")
PROTO_ATA_S = Pubkey.from_string("BqcWAXkSdknwQxvqXYVGKtttZynYNHACPVJmTaoqgfv8")
CREAT_ATA_S = Pubkey.from_string("GcY1P3epNorqbvpnGaHM8P6qb2A6xtbUgHybbKNsvxVr")
DEST_S = Pubkey.from_string("7HTVK1Jwzjd4yRGCZnLT4QmwhmZidurFxwz2RMAiUyzk")
BUYBACK = Pubkey.from_string("HjQjngTDqoHE6aaGhUqfz9aQ7WZcBRjy5xB8PScLSr8i")
VOLUME = Pubkey.from_string("8NyBnxo9mS5MsqY4qoKmrt7MS89d7MNV6rh5fu2YsQPT")
PROTOCOL_ATA = Pubkey.from_string("94qWNrtmfn42h3ZjUZwWvK1MEo9uVmmrBPd2hpNjYDjb")
CREATOR_ATA = Pubkey.from_string("3E6RtRCxo7Yz64zi8aSmC9DtNKcaMp5rFUcBnJKsc2fg")
DEST = Pubkey.from_string("7MNnTJmxb2vJ7WWi15fNMHYhwvmvJyY5XMegUjDKEKKT")
PROTOCOL_ATA_P2 = Pubkey.from_string("FHJxZKyxVkCC9d4wKWs97VAYY6b9JYFjqhLBgbGnjrFA")
CREATOR_ATA_P2 = Pubkey.from_string("DwhA1oGtJr1TXh7Ubs3V31evWEkomMbaU4Bhsbqr1Vde")
DEST2 = Pubkey.from_string("7VDNjuhymdWkPh1isgKCw36ESFCKf6uieAyzbVJWiyxs")
PROTOCOL_ATA_P3 = Pubkey.from_string("Ec3s4QjSwS71dgHCBxk1H1Q8gDfWD2Qy5XzZA34wdYQi")
CREATOR_ATA_P3 = Pubkey.from_string("CGTxrQSoWdAxMRAajQHKoCuBVoKbDrczzUddHVdRdwPH")
DEST3 = Pubkey.from_string("7RJ5bcEyBLDXFbmDSNzHeAKUC5z7z3Du5mKLY7FuyeeA")
PROTOCOL_ATA_P4 = Pubkey.from_string("2W8N7FVcdvQYvTthT6xgmnKoPCBKGMRscfM6pzvQD9Zg")
CREATOR_ATA_P4 = Pubkey.from_string("AWpQ4QeMTAv4UWkkUvMymkWcBT7xDovAQDtHymwc2C9v")
DEST4 = Pubkey.from_string("7Z8ftDAzMvoyXnGEJye8DurzgQQXLAbYCaeeesM7UKHa")
PROTOCOL_ATA_P5 = Pubkey.from_string("JBAC3QYSgSavuqrPocD353ZuXJqU3YbfRvzSYEMBvGpu")
CREATOR_ATA_P5 = Pubkey.from_string("6sGd476UhAawRUjd4K4vFwopnGo9ftbmywrND12R99Qa")
DEST5 = Pubkey.from_string("7gyGAp71YXQRoxmFBaHxofQXAipvgHyBKPyxmdSJxyvz")
BB22 = Pubkey.from_string("8imwZyx4D4zdUQ67TvftjjyGattafMNWMLs6HV8WNn1Y")
PROTO22 = Pubkey.from_string("2tZUDAsQqirqn1pdnYBVM7pDao57zsTSUspuFD2tAwTS")
CREAT22 = Pubkey.from_string("HShRmMRVQBgRz1eCD1aSr1hUm2BdrALVimjNXRduJwZB")
DEST22 = Pubkey.from_string("7d3y2WdzxE7CfsWjkGy3WndkvZcj1EHMkzKJiFPiDecH")
BOOST = Pubkey.from_string("5HkYU1vqHFZDZTz5LWcDynGvbg84aiGPVG8kNUcnbbC1")
BATA = Pubkey.from_string("Cd8K5QT4ninw4jnWP7nhmPbEJb8VsECTHUzeBf7KueMS")
BP3 = Pubkey.from_string("9Kn4eTXdasQr6ELbrd7fHT4JcPTSS9LoGW2sbh8CwZPZ")
BA3 = Pubkey.from_string("5mWEub2Js9ep2Em82qCPacPcBtEaPhxyQhU9QtT9V5Tn")
BP5 = Pubkey.from_string("DpSZ85LgqSLnvZjJWTBSRmGyKYr7j4NZZiLSjP3KCBt3")
BA5S = Pubkey.from_string("HNqA6bw1dhv32QZJURSbhtd98dmH2y8goYAEyL4V4B7R")
GVOL = Pubkey.from_string("C2aFPdENg4A2HQsmrd5rTw5TaYBX5Ku887cWjbFKtZpw")
IMINT = Pubkey.from_string("GGfoM4FJeQ8CXTXhaWiekqRQAtYVDNAKHDdJAu8PrHtm")
GA_ATA = Pubkey.from_string("9pVmg8pt6PR5UL8FphDN6QSfEvTiPbgUvA7YBUwPrgi")
UA_ATA = Pubkey.from_string("HM5XNiWUtZACr5dE6FRAvZeUDE4cUfbXNHdR7N9RwmCS")
UVATA = Pubkey.from_string("BEaaJNs1cVZKv29qYcXaaDSgm6Defa5b6kt5pRcUkHWe")
QUOTE = Pubkey.from_string("So11111111111111111111111111111111111111112")
OUTSIDER_KEY = Pubkey.from_string("5jotNjSnm9ZJRefVfqHato9FC4d9t6CHb2xS1726MTyY")
OUVA = Pubkey.from_string("7SAc5aXoXiRQeoXMnhmw7ZhAh9oZFdH8LqjtAoJqHuQJ")
OU5 = Pubkey.from_string("9ahYBF9J6simiVmTPwRgxB1t1AiZY5C8xpeLQGh5tJxn")
OQUOTE = Pubkey.from_string("9ecqKYcJhB1zrb1xqEkcF3neFKvmD8sxXEJzTejgdeHV")
OUVATA = Pubkey.from_string("HMtk5tHt8EeKmn1mKszLuowuEurDTcqXojrRAk52X3nt")
OUA_ATA = Pubkey.from_string("1rnEG36m9fSFBp7xXkYP7ViB7QxwiaidoPgDz3NLpAL")
WDEST = Pubkey.from_string("43HYZhSLzJVSwUAccwX2dmWmKBxhHDxjA1LQKJkzTg7w")
BASE22 = Pubkey.from_string("6Gg4AVKo8GAft4Wb2JSfhHCW3PQhXxYxapzBYeVjGzA9")
PLAIN = Pubkey.from_string("6Ckm2BrnXxsSjyG5b17kQQRjoECVrts92RKXVGT8XeqS")
CREATOR0 = Pubkey.from_string("29d2S7vB453rNYFdR5Ycwt7y9haRT5fwVwL9zTmBhfV2")
BC_CREATOR = Pubkey.from_string("4Ss5JMkXAD9Z7cktFEdrqeMuT6jGMF1pVozTyPHZ6zT4")
NEWVAULT = Pubkey.from_string("Gag9L2gntnWxsH4uB24Cs7rmKHgHexqVBHDmtv2443UA")
NEWVAULT22 = Pubkey.from_string("5GWYW1giwv9JvNFLjbWA4yUG6STzp93E3jRybpTXDBTy")
NEWDEST22 = Pubkey.from_string("HiaDPjMojq8s9nxZfR7A8WLFpc6fvBXe2uBk4TYRyCjc")
BCVAULT = Pubkey.from_string("6XPmtWMyuHivDoEXaDJF43utbMHopjoBieCkq6XrQxve")
BCVAULT22 = Pubkey.from_string("AsXUCL3rpZmKgqXUsX3TFffsy6tjk78EbycoQ8aoRq1k")
BCDEST22 = Pubkey.from_string("3D6PeVh59L9i8GNhYWjKDqyKyPTrnvJFevyvFT3z9ivN")
SHARING_PDA = Pubkey.from_string("1XVkGUKWHkGEnvhwiHMtTgwjs1RkdjahTMnSwrqop5D")
SHVAULT = Pubkey.from_string("12bftMSgeQFFHpeeiw5ykvhuueW5jEzrLTMXWGMBMRqs")
SHVAULT22 = Pubkey.from_string("7vmDZC25QefmsBzpCdxcNe3vKLZo18fYjFVqAdUTr1iH")
SHDEST22 = Pubkey.from_string("Ea1RHzBD6Nuh6X5Lk8GKfujd6AUXqXYZTZspk4gXBJSj")
ZEROVAULT = Pubkey.from_string("8N3GDaZ2iwN65oxVatKTLPNooAVUJTbfiVJ1ahyqwjSk")
ZEROVAULT22 = Pubkey.from_string("CtzzHDfaH7NX6Zu6w5JpRiJRTctPVE5wMhqcnohx9mig")
ZERODEST22 = Pubkey.from_string("2sZUUBGq1i6aE47ZoxCaCW89jmYm2EXLPPmNMgMDXHMS")
ORIGDEST22 = Pubkey.from_string("Dv7PMRUFDTJywhzw88zJ3tpyBmj9HqLbNq8BZwXWb7MW")
META_PDA = Pubkey.from_string("DmwqzAppxfZoXLB3CXRxMxMWTkG2DSWeMfup9JBg7Kzx")
BC_PDA = Pubkey.from_string("3MUkKMbuornHohtAtzrToSzqkj1gEEhQqYVz8sZnmQg1")
POOLV2 = Pubkey.from_string("4Jjna3h73QbgmdqwnV5NJxjCidKWB7Q26jeuj9jtFetC")
CONFIG_KEY = Pubkey.from_string("ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw")
ROLE_KEY = {"userbase": USERBASE, "userquote": USERQUOTE, "userlp": USERLP,
            "vaultbase": VAULTBASE, "vaultquote": VAULTQUOTE, "buyback": BUYBACK,
            "vb1": VAULTBASE, "vq1": VAULTQUOTE, "vb2": VB2, "vq2": VQ2,
            "vb3": VB3, "vq3": VQ3, "vb4": VB4, "vq4": VQ4,
            "vb5": VB5, "vq5": VQ5, "vb2s": VB2S, "vq2s": VQ2S,
            "vb3s": VB3S, "vq3s": VQ3S, "u3": U3, "u4": U4, "u5": U5,
            "protoata": PROTOCOL_ATA, "creatorata": CREATOR_ATA, "dest": DEST,
            "protoata3": PROTOCOL_ATA_P3, "creatorata3": CREATOR_ATA_P3, "dest3": DEST3,
            "protoata2": PROTOCOL_ATA_P2, "creatorata2": CREATOR_ATA_P2, "dest2": DEST2,
            "protoata4": PROTOCOL_ATA_P4, "creatorata4": CREATOR_ATA_P4, "dest4": DEST4,
            "protoata5": PROTOCOL_ATA_P5, "creatorata5": CREATOR_ATA_P5, "dest5": DEST5,
            "protoatas": PROTO_ATA_S, "creatoratas": CREAT_ATA_S, "dests": DEST_S,
            "bb22": BB22, "proto22": PROTO22, "creat22": CREAT22, "dest22": DEST22,
            "wdest": WDEST, "base22": BASE22, "plain": PLAIN,
            "boostata": BATA, "boostata3": BA3, "boostata5": BA5S,
            "gata": GA_ATA, "uata": UA_ATA, "uvata": UVATA,
            "newvault": NEWVAULT22, "newdest": NEWDEST22,
            "bcvault": BCVAULT22, "bcdest": BCDEST22,
            "shvault": SHVAULT22, "shdest": SHDEST22,
            "zerovault": ZEROVAULT22, "zerodest": ZERODEST22,
            "origdest": ORIGDEST22,
            "ou5": OU5, "oquote": OQUOTE, "ouata": OUA_ATA, "ouvata": OUVATA}
TOKEN_ROLES = ["userbase", "userquote", "userlp", "vb1", "vq1", "vb2", "vq2",
               "vb3", "vq3", "vb4", "vq4", "vb5", "vq5",
               "vb2s", "vq2s", "vb3s", "vq3s", "u3", "u4", "u5", "buyback",
               "protoata", "creatorata", "dest",
               "protoata3", "creatorata3", "dest3",
               "protoata2", "creatorata2", "dest2",
               "protoata4", "creatorata4", "dest4",
               "protoata5", "creatorata5", "dest5",
               "protoatas", "creatoratas", "dests",
               "bb22", "proto22", "creat22", "dest22",
               "wdest", "base22", "plain",
               "boostata", "boostata3", "boostata5",
               "gata", "uata", "uvata",
               "newvault", "newdest", "bcvault", "bcdest",
               "shvault", "shdest", "zerovault", "zerodest", "origdest",
               "ou5", "oquote", "ouata", "ouvata"]
POOL_KEYS = {"main": POOL, "pool2": POOL2, "p3": P3, "p4": P4, "p5": P5,
             "p2s": P2S, "p3s": P3S}


def fail(msg):
    raise SystemExit(f"FAIL: {msg}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tok_amount(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 72:
        return None
    return struct.unpack_from("<Q", raw, 64)[0]


def tok_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (tok_amount(a) or 0) - (tok_amount(b) or 0)


def wh_of(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) == 178:
        return struct.unpack_from("<Q", raw, 170)[0]
    if len(raw) == 182:
        return struct.unpack_from("<Q", raw, 174)[0]
    return None


def wh_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (wh_of(a) or 0) - (wh_of(b) or 0)


def mint_wh(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    return struct.unpack_from("<Q", raw, 234)[0] if len(raw) >= 242 else None


def lam_delta(rec, key):
    b = rec["before"][str(key)]
    a = rec["after"][str(key)]
    return (a["lamports"] if a else 0) - (b["lamports"] if b else 0)


def pool_state(entry):
    if entry is None:
        return None
    d = bytes.fromhex(entry["data_hex"])
    if len(d) < 287:
        return {"len": len(d)}
    return [int.from_bytes(d[245:261], "little", signed=True),
            struct.unpack_from("<Q", d, 271)[0],
            struct.unpack_from("<Q", d, 279)[0],
            struct.unpack_from("<Q", d, 203)[0]]


def vol_state(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    return {"lamports": entry["lamports"], "len": len(raw),
            "user": raw[8:40].hex()}


def uva_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 90:
        return {"len": len(raw)}
    needs, unc, cla, vol, last, hasc, earn, cbcl = struct.unpack_from('<BQQQqBQQ', raw, 40)
    return {"needs": needs, "unclaimed": unc, "claimed": cla, "volume": vol,
            "last": last, "has": hasc, "earned": earn, "cb_claimed": cbcl}


def gva_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 544:
        return {"len": len(raw)}
    start, end, seconds = struct.unpack_from('<qqq', raw, 8)
    supply0, = struct.unpack_from('<Q', raw, 64)
    sol0, = struct.unpack_from('<Q', raw, 304)
    supply29, = struct.unpack_from('<Q', raw, 296)
    sol29, = struct.unpack_from('<Q', raw, 536)
    return {"lamports": entry["lamports"], "len": len(raw),
            "start": start, "end": end, "seconds": seconds,
            "mint": raw[32:64].hex(), "supply0": supply0, "sol0": sol0,
            "supply29": supply29, "sol29": sol29}


def u64(raw, off):
    return struct.unpack_from("<Q", raw, off)[0]


def cfg_fields(entry):
    if entry is None:
        return None
    raw = bytes.fromhex(entry["data_hex"])
    if len(raw) < 949:
        return {"len": len(raw)}
    return {"admin": raw[8:40].hex(), "disable": raw[56], "lp": u64(raw, 40), "proto": u64(raw, 48),
            "recipients": [raw[57 + i * 32:57 + (i + 1) * 32].hex() for i in range(8)],
            "creator_fee": u64(raw, 313), "fee_auth": raw[321:353].hex(),
            "bps": u64(raw, 899),
            "bb_recipients": [raw[643 + i * 32:643 + (i + 1) * 32].hex() for i in range(8)],
            "mayhem": raw[417], "cashback": raw[642],
            "boost_auth": raw[907:939].hex(), "boost_enabled": raw[939]}


def ev_list(logs):
    return [base64.b64decode(l.split("Program data: ", 1)[1].strip())
            for l in logs if l.startswith("Program data: ")]


def decode_event(kind, raw):
    if kind in ("mhbuy3", "mhbuy5", "mhbuy4", "mhbuy1", "stbuy3", "omhbuy5"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "base": u64(raw, 16), "quote": u64(raw, 24)}
    if kind in ("mhsell3", "mhsell5", "mhsell4", "mhsell1", "stsell3", "omhsell5"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "base": u64(raw, 16), "quote_gross": u64(raw, 104),
                "quote": u64(raw, 112)}
    if kind in ("swp", "swc", "swp22", "swc22", "swc22c"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "recipient": raw[112:144].hex(),
                "amount": u64(raw, 176), "bucket": raw[184]}
    if kind == "uadm":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "old": raw[16:48].hex(), "new": raw[48:80].hex()}
    if kind in ("dep", "wd"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "base": u64(raw, 72), "quote": u64(raw, 80)}
    if kind in ("col", "col22", "col22c"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "timestamp": struct.unpack_from("<q", raw, 8)[0],
                "creator": raw[16:48].hex(), "fee": u64(raw, 48),
                "vault_ata": raw[56:88].hex(), "dest": raw[88:120].hex()}
    if kind in ("tclaim", "otclaim"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "mint": raw[40:72].hex(),
                "amount": u64(raw, 72), "ts": struct.unpack_from("<q", raw, 80)[0],
                "total_claimed": u64(raw, 88), "current_sol_volume": u64(raw, 96)}
    if kind in ("cclaim", "occlaim"):
        return {"disc": raw[:8].hex(), "len": len(raw),
                "user": raw[8:40].hex(), "amount": u64(raw, 40),
                "ts": struct.unpack_from("<q", raw, 48)[0],
                "total_claimed": u64(raw, 56), "total_earned": u64(raw, 64)}
    if kind in ("close", "close_other", "close_unsigned"):
        return {"disc": raw[:8].hex(), "user": raw[8:40].hex(),
                "ts": struct.unpack_from("<q", raw, 40)[0],
                "unc": u64(raw, 48), "claimed": u64(raw, 56),
                "vol": u64(raw, 64), "last": struct.unpack_from("<q", raw, 72)[0],
                "len": len(raw)}
    if kind == "init":
        return {"disc": raw[:8].hex(), "payer": raw[8:40].hex(),
                "user": raw[40:72].hex(),
                "ts": struct.unpack_from("<q", raw, 72)[0], "len": len(raw)}
    if kind in ("sync", "osync"):
        return {"disc": raw[:8].hex(), "user": raw[8:40].hex(),
                "before": u64(raw, 40), "after": u64(raw, 48),
                "ts": struct.unpack_from("<q", raw, 56)[0], "len": len(raw)}
    if kind in ("extend", "extend_unsigned", "extend_readonly"):
        return {"disc": raw[:8].hex(),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "account": raw[16:48].hex(), "user": raw[48:80].hex(),
                "old": u64(raw, 80), "new": u64(raw, 88), "len": len(raw)}
    if kind == "buy2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "qwlp": u64(raw, 104),
                "uin": u64(raw, 112)}
    if kind in ("legbuy", "legsell"):
        # Legacy BuyEvent (disc 67f4521f2cf57777, len 497) and
        # SellEvent (disc 3e2f370aa503dc2a, len 449) share the
        # multi-hop event discriminators; only disc/len are pinned.
        return {"disc": raw[:8].hex(), "len": len(raw)}
    if kind == "sell2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    if kind == "boost":
        if raw[:8].hex() != "3f451c16305cc2b9":
            return {"disc": raw[:8].hex(), "len": len(raw)}
        return {"disc": raw[:8].hex(), "len": len(raw),
                "requested": u64(raw, 144), "used": u64(raw, 152),
                "burned": u64(raw, 160),
                "vq": int.from_bytes(raw[168:184], "little", signed=True),
                "quote_after": u64(raw, 184), "base_after": u64(raw, 192),
                "remaining": u64(raw, 200)}
    if kind == "ufc":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "admin": raw[16:48].hex(), "lp": u64(raw, 48), "proto": u64(raw, 56),
                "recipients": [raw[64 + i * 32:64 + (i + 1) * 32].hex() for i in range(8)],
                "creator": u64(raw, 320), "authority": raw[328:360].hex()}
    if kind == "dis":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "ts": struct.unpack_from("<q", raw, 8)[0],
                "admin": raw[16:48].hex(),
                "bools": [raw[48 + i] for i in range(5)]}
    if kind == "set":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "creator": raw[112:144].hex()}
    if kind == "mig":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "old": raw[112:144].hex(), "new": raw[144:176].hex()}
    if kind == "buy2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "qwlp": u64(raw, 104),
                "uin": u64(raw, 112)}
    if kind == "sell2":
        return {"disc": raw[:8].hex(), "len": len(raw),
                "curve": u64(raw, 64), "lp_bps": u64(raw, 72),
                "lp_fee": u64(raw, 80), "proto_bps": u64(raw, 88),
                "proto_fee": u64(raw, 96), "quote": u64(raw, 104),
                "uout": u64(raw, 112)}
    if kind in ("boost", "boost3", "boost4", "boost5"):
        if raw[:8].hex() != "3f451c16305cc2b9":
            return {"disc": raw[:8].hex(), "len": len(raw)}
        return {"disc": raw[:8].hex(), "len": len(raw),
                "requested": u64(raw, 144), "used": u64(raw, 152),
                "burned": u64(raw, 160),
                "vq": int.from_bytes(raw[168:184], "little", signed=True),
                "quote_after": u64(raw, 184), "base_after": u64(raw, 192),
                "remaining": u64(raw, 200)}
    return None


def surface(recs):
    out = []
    for rec in recs:
        def strip(snap):
            d = dict(snap)
            if d.get(str(PAYER_KEY)) is not None:
                d[str(PAYER_KEY)] = dict(d[str(PAYER_KEY)])
                d[str(PAYER_KEY)]["lamports"] = 0
            return d
        out.append({"step": rec["step"], "error": rec["error"],
                    "events": len(rec["events"]),
                    "before": strip(rec["before"]), "after": strip(rec["after"])})
    return out


def main():
    manifest = json.loads((ROOT / "MANIFEST.json").read_text())
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        if not path.exists():
            fail(f"missing file {entry['path']}")
        if sha(path.read_bytes()) != entry["sha256"]:
            fail(f"sha mismatch {entry['path']}")
    with gzip.open(ROOT / "runtime" / "report.json.gz", "rt", encoding="utf-8") as fh:
        report = json.load(fh)
    if report["case_count"] != 81 or report["receipt_count"] != 372:
        fail(f"counts {report['case_count']} cases / {report['receipt_count']} receipts")
    if report["counts"] != {"cases": 81, "receipts": 372, "parts": 38}:
        fail(f"counts block {report['counts']}")
    if report["mismatches"] != []:
        fail(f"mismatches recorded: {report['mismatches']}")
    for name, path in IMAGE_PATHS.items():
        if sha(path.read_bytes()) != report["images"][name]:
            fail(f"image hash mismatch {name}")
    receipts = []
    for part in report["parts"]:
        path = ROOT / part["file"]
        data = path.read_bytes()
        if sha(data) != part["sha256"] or len(data) != part["bytes"]:
            fail(f"part hash/size mismatch {part['file']}")
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            chunk = [json.loads(line) for line in fh if line.strip()]
        if len(chunk) != part["count"]:
            fail(f"part count mismatch {part['file']}")
        receipts.extend(chunk)
    if len(receipts) != 372:
        fail(f"receipt total {len(receipts)}")
    by_case = {}
    for rec in receipts:
        by_case.setdefault(rec["case"], {}).setdefault(rec["image"], []).append(rec)
    divergent_labels = []
    for case in report["cases"]:
        label = case["label"]
        steps = case["steps"]
        for image in ("original", "control", "candidate"):
            expect = steps["original" if image == "original" else "rebuilt"] \
                if isinstance(steps, dict) else steps
            recs = by_case.get(label, {}).get(image)
            if recs is None or len(recs) != len(expect):
                fail(f"{label}/{image}: {0 if recs is None else len(recs)} receipts, expected {len(expect)}")
            for rec, exp in zip(recs, expect):
                tag = f"{label}/{image}/{rec['step']}"
                tx = Transaction.from_bytes(base64.b64decode(rec["transaction_base64"]))
                if not all(tx.verify_with_results()):
                    fail(f"{tag}: signature verification failed")
                if exp["error"] is None:
                    if rec["error"] is not None:
                        fail(f"{tag}: unexpected error {rec['error']}")
                else:
                    if rec["error"] is None or exp["error"] not in rec["error"]:
                        fail(f"{tag}: expected error {exp['error']}, got {rec['error']}")
                if len(rec["events"]) != exp["events"]:
                    fail(f"{tag}: events {len(rec['events'])} != {exp['events']}")
                if lam_delta(rec, PAYER_KEY) != exp["dPAYER"]:
                    fail(f"{tag}: dPAYER {lam_delta(rec, PAYER_KEY)} != {exp['dPAYER']}")
                if lam_delta(rec, OUTSIDER_KEY) != exp.get("dOUT", 0):
                    fail(f"{tag}: dOUT {lam_delta(rec, OUTSIDER_KEY)} != {exp.get('dOUT', 0)}")
                for role, want in exp.get("lam_deltas", {}).items():
                    if lam_delta(rec, ROLE_KEY[role]) != want:
                        fail(f"{tag}: lam_delta {role} {lam_delta(rec, ROLE_KEY[role])} != {want}")
                for role in TOKEN_ROLES:
                    if role in exp.get("lam_deltas", {}):
                        continue
                    if lam_delta(rec, ROLE_KEY[role]) != 0:
                        fail(f"{tag}: unexpected lam_delta {role} {lam_delta(rec, ROLE_KEY[role])}")
                if "mint_wh" in exp:
                    if mint_wh(rec["after"][str(QUOTE)]) != exp["mint_wh"]:
                        fail(f"{tag}: mint_wh {mint_wh(rec['after'][str(QUOTE)])} != {exp['mint_wh']}")
                for role, want in exp["deltas"].items():
                    if tok_delta(rec, ROLE_KEY[role]) != want:
                        fail(f"{tag}: delta {role} {tok_delta(rec, ROLE_KEY[role])} != {want}")
                for role in TOKEN_ROLES:
                    if role in exp["deltas"]:
                        continue
                    if tok_delta(rec, ROLE_KEY[role]) != 0:
                        fail(f"{tag}: unexpected delta {role} {tok_delta(rec, ROLE_KEY[role])}")
                for role, want in exp.get("withheld", {}).items():
                    if wh_delta(rec, ROLE_KEY[role]) != want:
                        fail(f"{tag}: withheld {role} {wh_delta(rec, ROLE_KEY[role])} != {want}")
                for role in TOKEN_ROLES:
                    if role in exp.get("withheld", {}):
                        continue
                    if wh_delta(rec, ROLE_KEY[role]) != 0:
                        fail(f"{tag}: unexpected withheld {role} {wh_delta(rec, ROLE_KEY[role])}")
                for pool_name, pool_key in POOL_KEYS.items():
                    if pool_state(rec["after"][str(pool_key)]) != exp["pools"][pool_name]:
                        fail(f"{tag}: pool {pool_name} {pool_state(rec['after'][str(pool_key)])} != {exp['pools'][pool_name]}")
                if "pool_creator" in exp:
                    _pc_ent = rec["after"][str(POOL)]
                    got_pc = bytes.fromhex(_pc_ent["data_hex"])[211:243].hex() if _pc_ent else None
                    if got_pc != exp["pool_creator"]:
                        fail(f"{tag}: pool_creator {got_pc} != {exp['pool_creator']}")
                if vol_state(rec["after"][str(VOLUME)]) != exp["volume"]:
                    fail(f"{tag}: volume {vol_state(rec['after'][str(VOLUME)])} != {exp['volume']}")
                if exp.get("uva") is not None:
                    got_uva = uva_fields(rec["after"][str(VOLUME)])
                    if got_uva != exp["uva"]:
                        fail(f"{tag}: uva {got_uva} != {exp['uva']}")
                if exp.get("ouva") is not None:
                    got_ouva = uva_fields(rec["after"][str(OUVA)])
                    if got_ouva != exp["ouva"]:
                        fail(f"{tag}: ouva {got_ouva} != {exp['ouva']}")
                if "gva" in exp:
                    got_gva = gva_fields(rec["after"][str(GVOL)])
                    if got_gva != exp["gva"]:
                        fail(f"{tag}: gva {got_gva} != {exp['gva']}")
                if "cfg" in exp:
                    got_cfg = cfg_fields(rec["after"][str(CONFIG_KEY)])
                    if got_cfg != exp["cfg"]:
                        fail(f"{tag}: cfg {got_cfg} != {exp['cfg']}")
                if exp.get("uva_absent"):
                    if rec["after"][str(VOLUME)] is not None:
                        fail(f"{tag}: volume should stay absent")
                for role, want in exp.get("lam_after", {}).items():
                    got = rec["after"][str(ROLE_KEY[role])]
                    if got is None or got["lamports"] != want:
                        fail(f"{tag}: lam_after {role} {None if got is None else got['lamports']} != {want}")
                if rec["after"][str(GVOL)] != rec["before"][str(GVOL)]:
                    fail(f"{tag}: global volume accumulator changed")
                if exp.get("log_fragment"):
                    if exp["log_fragment"] not in "\n".join(rec["logs"]):
                        fail(f"{tag}: log fragment missing")
                if exp.get("site_fragment"):
                    if exp["site_fragment"] not in "\n".join(rec["logs"]):
                        fail(f"{tag}: site fragment missing")
                if exp.get("rollback"):
                    for k, b in rec["before"].items():
                        if k in (str(PAYER_KEY), str(OUTSIDER_KEY)):
                            continue
                        if rec["after"][k] != b:
                            fail(f"{tag}: rollback violated for {k}")
                if exp.get("boost_event") is not None:
                    raws = ev_list(rec["logs"])
                    if len(raws) != 2:
                        fail(f"{tag}: boost events {len(raws)} != 2")
                    first = decode_event(rec["step"], raws[0])
                    if first != {"disc": "67f4521f2cf57777", "len": 512}:
                        fail(f"{tag}: boost first event {first}")
                    got = decode_event(rec["step"], raws[1])
                    if got is None:
                        fail(f"{tag}: boost event decode failed")
                    for fkey, want in exp["boost_event"].items():
                        if got.get(fkey) != want:
                            fail(f"{tag}: boost event {fkey} {got.get(fkey)} != {want}")
                if exp.get("events_list") is not None:
                    raws = ev_list(rec["logs"])
                    if len(raws) != len(exp["events_list"]):
                        fail(f"{tag}: decoded events {len(raws)} != {len(exp['events_list'])}")
                    for raw, want in zip(raws, exp["events_list"]):
                        got = decode_event(rec["step"], raw)
                        if got is None:
                            fail(f"{tag}: event decode failed")
                        for fkey, wval in want.items():
                            if got.get(fkey) != wval:
                                fail(f"{tag}: event {fkey} {got.get(fkey)} != {wval}")
                if exp.get("event") is not None:
                    raws = ev_list(rec["logs"])
                    if len(raws) != exp["events"]:
                        fail(f"{tag}: decoded events {len(raws)} != {exp['events']}")
                    for raw in raws:
                        got = decode_event(rec["step"], raw)
                        if got is None:
                            fail(f"{tag}: event decode failed")
                        for fkey, want in exp["event"].items():
                            if got.get(fkey) != want:
                                fail(f"{tag}: event {fkey} {got.get(fkey)} != {want}")
        base = surface(by_case[label]["original"])
        if surface(by_case[label]["control"]) != surface(by_case[label]["candidate"]):
            fail(f"{label}: control and candidate surfaces differ")
        computed_divergent = (surface(by_case[label]["control"]) != base
                              or surface(by_case[label]["candidate"]) != base)
        if computed_divergent:
            divergent_labels.append(label)
        if computed_divergent != case["divergent"]:
            fail(f"{label}: divergent flag {case['divergent']} != computed {computed_divergent}")
        for image in ("original", "control", "candidate"):
            sites = case["error_sites"][image]
            recs = by_case[label][image]
            if len(sites) != len(recs):
                fail(f"{label}/{image}: site count mismatch")
            for rec, site in zip(recs, sites):
                if site is not None and site not in "\n".join(rec["logs"]):
                    fail(f"{label}/{image}: recorded site line not in logs: {site}")
    print(f"PASS: 81 cases, 372 receipts, 38 parts, true 5-hop split x boost x tf boost window and burn chains, per-image expectations hold "
          f"(signatures, deltas, withheld, mint withheld, lamports, events, "
          f"error codes, rollback, UVA fields, GVA fields, pool creator bytes, "
          f"GlobalConfig fields, multi-hop/v2/legacy/sweep/collect/boost/claim events, GVOL invariance); "
          f"control == candidate everywhere; "
          f"({len(divergent_labels)} divergent cases): {divergent_labels}")


if __name__ == "__main__":
    main()
