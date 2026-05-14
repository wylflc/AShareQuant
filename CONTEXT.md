# AShareQuant

AShareQuant models listed-company research for mainland China, Hong Kong, and U.S. equity markets. This context keeps stable domain language separate from changing implementation plans and task-specific requirements.

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

**U.S. Security**:
A security listed on a U.S. exchange and represented by its listing exchange, symbol, share class or security type, and provider identifiers.
_Avoid_: U.S. company when referring only to the listed instrument.

**Universe**:
The full set of listed securities eligible for a given analysis run.
_Avoid_: all stocks when eligibility rules are part of the meaning.

**Universe Snapshot**:
A timestamped capture of securities returned by a named data provider for a universe construction run, with source provenance retained for auditability.
_Avoid_: current stock list when provider and retrieval time matter.

**Watchlist**:
The set of listed companies retained for ongoing attention after business-quality screening.
_Avoid_: buy list, target list.

**Moat Screening**:
Assessment of durable business advantages and resistance to competitive displacement.
_Avoid_: valuation screen, cheap-stock screen.

**Screening Evidence**:
Reliable source-backed information used to support a **Moat Screening** decision.
_Avoid_: unsourced notes, model guesses.

**Full-Coverage Screening Run**:
A screening run that attempts to score every eligible listed company in a universe with the same rubric, rather than only companies that were manually selected first.
_Avoid_: candidate sampling, partial watchlist when the run claims universe coverage.

**Dimensional Score**:
A 0-100 score for one explicit screening dimension, such as business moat, technology barrier, market position, business quality, operating quality, industry outlook, or governance and risk quality.
_Avoid_: unweighted impression, single blended note.

**Cyclicality Profile**:
A screening label that identifies whether a listed company's industry is mainly stable, structurally growing, macro-credit cyclical, commodity cyclical, property/rate cyclical, capex cyclical, or demand/policy cyclical.
_Avoid_: treating all growth industries or all current profit leaders as equally durable.

**Compounding Profile**:
A screening label that identifies whether a listed company has a plausible path to compound value through brand, data, innovation, regulated assets, installed base, balance-sheet discipline, or scale/process advantages.
_Avoid_: assuming high current revenue or a large addressable market automatically means compound growth.

**Capital Replicability Test**:
A way to evaluate competitive strength by asking whether a well-funded new entrant could quickly build the same capability, enter the industry, and overtake the listed company mainly through capital spending.
_Avoid_: assuming a business is strong only because it is large or profitable today.

**Insufficient Disclosure**:
A narrow screening status for a listed company that is too newly listed to have enough periodic reports and also lacks authoritative public business descriptions from filings, regulators, credible media, or research institutions.
_Avoid_: not yet researched, missing evidence row.

**Moat Score**:
A rough 0-100 quality score from **Moat Screening** based on source-backed evidence of business barriers, technical barriers, market position, cash flow quality, and margin quality.
_Avoid_: valuation score, buy score.

**Watchlist Candidate**:
A listed company or security that passes the current **Moat Screening** threshold and is worth later **Valuation Assessment**.
_Avoid_: buy candidate, undervalued stock.

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
- A **Universe Snapshot** records the **Securities** available from a provider at retrieval time and can be used as input to later screening.
- **Screening Evidence** supports a **Moat Score**; a high enough **Moat Score** can produce a **Watchlist Candidate**.
- A **Full-Coverage Screening Run** must produce **Dimensional Scores** for every eligible **Listed Company**, except the narrow **Insufficient Disclosure** case.
- A **Dimensional Score** should apply the **Capital Replicability Test** where relevant so the score reflects durable competitive strength rather than current size alone.
- **Cyclicality Profile** and **Compounding Profile** explain how the industry outlook contributes to **Moat Screening** without turning it into a valuation or market-momentum signal.
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
- "Evidence insufficient" is narrow. It does not mean a company has not yet been reviewed; it means the company lacks enough public disclosure and authoritative external description to support a fair score.
