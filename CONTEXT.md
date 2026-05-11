# AShareQuant

AShareQuant models listed-company research for mainland China and Hong Kong equity markets. This context keeps stable domain language separate from changing implementation plans and task-specific requirements.

## Language

**Listed Company**:
The business entity being researched, which may correspond to one or more tradable securities.
_Avoid_: stock, ticker, security when referring to the business entity.

**Security**:
A tradable instrument identified by exchange, symbol, share class, and market-specific identifiers.
_Avoid_: company when referring to the listed instrument.

**A-Share Security**:
A security listed on a mainland China exchange and traded under that market's rules.
_Avoid_: China stock when the exchange and share class matter.

**Hong Kong Security**:
A security listed on the Hong Kong market and traded under that market's rules.
_Avoid_: HK company when referring only to the instrument.

**Universe**:
The full set of listed securities eligible for a given analysis run.
_Avoid_: all stocks when eligibility rules are part of the meaning.

**Watchlist**:
The set of listed companies retained for ongoing attention after business-quality screening.
_Avoid_: buy list, target list.

**Moat Screening**:
Assessment of durable business advantages and resistance to competitive displacement.
_Avoid_: valuation screen, cheap-stock screen.

**Valuation Assessment**:
Assessment of whether a security's current price is attractive relative to fundamentals or intrinsic value.
_Avoid_: moat screening.

**Market Data**:
Daily trading records such as open, high, low, close, volume, turnover, and trading status.
_Avoid_: financial data.

**Corporate Action**:
An issuer event that affects ownership, cash flows, or historical price comparability, such as dividends, splits, bonus shares, or rights issues.
_Avoid_: price data.

**Financial Report Data**:
Reported financial statements, key metrics, narrative disclosures, and their reporting periods.
_Avoid_: market data.

**Disclosure Timeline**:
Expected, preliminary, forecast, and official announcement dates for financial reporting events.
_Avoid_: report date when the specific event type matters.

## Relationships

- A **Listed Company** can have one or more **Securities**.
- A **Universe** contains **Securities**, but a **Watchlist** contains **Listed Companies**.
- **Moat Screening** determines whether a **Listed Company** deserves attention; **Valuation Assessment** determines whether a **Security** may be attractively priced.
- **Market Data** belongs to a **Security** and trading date.
- **Corporate Actions** belong to a **Security** or **Listed Company** and affect how **Market Data** should be interpreted.
- **Financial Report Data** belongs to a **Listed Company** and reporting period, with dates captured in the **Disclosure Timeline**.

## Example Dialogue

> **Dev:** "If a company passes moat screening, should it be marked as a buy?"
> **Domain expert:** "No. It enters the Watchlist. Buying requires a separate Valuation Assessment on the relevant Security."

## Flagged Ambiguities

- "Company" and "stock" are easy to conflate. Use **Listed Company** for the business entity and **Security** for the exchange-traded instrument.
- "Worth attention" is resolved as **Watchlist** inclusion based on **Moat Screening**, not as a purchase recommendation.
