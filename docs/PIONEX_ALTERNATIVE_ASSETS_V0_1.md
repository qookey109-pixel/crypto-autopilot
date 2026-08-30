# Pionex Alternative Assets V0.1

## Outcome

This is a separate, Pionex-native perpetual-market catalog for non-Crypto Core
assets. It does not add these instruments to Crypto Core 100 and does not infer
that a token grants ownership, voting rights or the same protections as a
traditional security.

The checked-in registry contains **125 point-in-time candidates**:

- 90 tokenized US/international-equity or stock-linked candidates;
- 31 ETF, ETN or fund-linked candidates;
- 4 direct metal-reference perpetual candidates.

Candidate means “explicitly named in the maintained official-listing registry.”
It is not proof that the contract is still trading. A market enters the selected
catalog only when its exact symbol is also returned by Pionex public
`PERP + TRADING` metadata at execution time. Unknown `X`-suffix symbols remain
`REVIEW_REQUIRED_NOT_SELECTED`; an `X` suffix alone is never a classifier.

## Candidate registry

### Equity and stock-linked tokens — 90

`AAPLX`, `AAOIX`, `AAX`, `ALBX`, `AMDX`, `AMZNX`, `ANETX`, `APPX`,
`ASMLX`, `ASTSX`, `AVGOX`, `BEX`, `BMNRX`, `CARX`, `CCJX`, `COHRX`,
`COINX`, `COPXX`, `COSTX`, `CRCLX`, `CRWDX`, `CRWVX`, `DIAX`, `ENPHX`,
`ETNX`, `FLNCX`, `FNX`, `GLWX`, `GOOGLX`, `HIMSX`, `HOODLX`, `HOODX`,
`HWMX`, `INTCX`, `IRENX`, `ITAX`, `JBSX`, `KEYSX`, `KLACX`, `LACX`,
`LITEX`, `LLYX`, `LMTX`, `LRCXX`, `METAX`, `MPX`, `MRVLX`, `MSFTX`,
`MSTRX`, `MUFGX`, `MUX`, `NBISX`, `NEEX`, `NETX`, `NFLXX`, `NKEX`,
`NOCX`, `NOKX`, `NVDAX`, `OKLOX`, `ONDSX`, `ORCLX`, `PAYPX`, `PLTRX`,
`QCOMX`, `RGTIX`, `RKLBX`, `RTXX`, `SATSX`, `SKHX`, `SMSN`, `SMRX`,
`SNDKX`, `SNPSX`, `STM`, `STXX`, `SWMRX`, `TELX`, `TERX`, `TSEMX`,
`TSLAX`, `TXNX`, `UAMYX`, `UNHX`, `USARX`, `VRTX`, `VSTX`, `WDCX`,
`XMEX`, `XYZX`.

Recognizable examples include Apple (`AAPLX`), NVIDIA (`NVDAX`), Tesla
(`TSLAX`), Amazon (`AMZNX`), Alphabet (`GOOGLX`), Meta (`METAX`),
Microsoft (`MSFTX`), Strategy/MicroStrategy (`MSTRX`), Coinbase (`COINX`),
Circle (`CRCLX`), AMD (`AMDX`) and Palantir (`PLTRX`).

### ETF, ETN and fund-linked tokens — 31

`BNOX`, `CPERX`, `DBAX`, `DRAMX`, `DXYZX`, `EWJX`, `EWYX`, `GSGX`,
`IGVX`, `IWMX`, `MOOX`, `NASAX`, `PALLX`, `PPLTX`, `QQQX`, `SLVX`,
`SMHX`, `SOXLX`, `SOXXX`, `SPCX`, `SPYX`, `TQQQX`, `UNGX`, `URAX`,
`USOX`, `VGKX`, `VNQX`, `VTIX`, `VXXX`, `XLEX`, `XOVRX`.

Recognizable examples include S&P 500 (`SPYX`), Nasdaq-100 (`QQQX`),
Russell 2000 (`IWMX`), leveraged Nasdaq (`TQQQX`), leveraged semiconductor
(`SOXLX`), Japan (`EWJX`), South Korea (`EWYX`), Europe (`VGKX`), uranium
(`URAX`), energy (`XLEX`) and broad commodities (`GSGX`).

### Direct metals and other non-crypto references — 4

- `XAU` — gold;
- `XAG` — silver;
- `XPT` — platinum;
- `XPD` — palladium.

Commodity funds such as `CPERX`, `PALLX`, `PPLTX`, `SLVX`, `USOX`, `UNGX`
and `GSGX` stay in the ETF/fund class rather than being mislabeled as direct
metal or commodity contracts.

## Schedule

Workflow: `.github/workflows/pionex-alternative-assets-catalog-v0-1.yml`.

| Run | UTC | Asia/Taipei | Purpose |
| --- | --- | --- | --- |
| Initial | 2026-09-04 02:53 | 2026-09-04 10:53 | first live Pionex registry intersection after the V0.10 window |
| Review 1 | 2026-09-06 03:53 | 2026-09-06 11:53 | weekly listing/delisting refresh |
| Review 2 | 2026-09-13 03:53 | 2026-09-13 11:53 | weekly listing/delisting refresh |
| Review 3 | 2026-09-20 03:53 | 2026-09-20 11:53 | weekly listing/delisting refresh |
| Review 4 | 2026-09-27 03:53 | 2026-09-27 11:53 | final bounded V0.1 refresh |

The V0.1 catalog authority expires before provider or R2 access at
`2026-10-01T00:00:00Z`. A later ongoing cadence requires another reviewed
version rather than silently running forever.

Each run performs a fresh whole-bucket 8 GB FREE-ONLY headroom check before the
Pionex metadata request and again before R2 writes. It stores an immutable
catalog plus manifest and updates the small latest pointer last. Generated data
is R2-only; the runner report is disposable.

## What is not active yet

This version reads symbol metadata only. It does **not** call Pionex K-line,
funding, trade or order-book endpoints and does not access the replacement
holdout. The proposed `15M / 60M / 4H` Pionex-native historical dataset remains
waiting for completed V0.11 production evaluation and a separate holdout/candle
authority. There is no automatic training, model promotion, demo order, private
API, trade plan, real-money order or live-trading authority.

## Official references

- Pionex Tokenized Stocks Introduction:
  `https://support.pionex.com/hc/en-us/articles/49341792225817-Tokenized-Stocks-Introduction`
- Pionex xStocks guide and point-in-time examples:
  `https://www.pionex.com/blog/xstocks/`
- Pionex New Listings index:
  `https://support.pionex.com/hc/en-us/sections/360004940414-New-listings`
- Pionex XAU perpetual listing:
  `https://support.pionex.com/hc/en-us/articles/57038861340953-Pionex-has-listed-XAUUSDT-Gold-1-100x-Leverage-Margined-Perpetual-Futures`
