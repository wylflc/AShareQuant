# 1. Require Analyst Peer-Group Decisions For Final Watchlists

## 1.1 Status

Accepted.

## 1.2 Context

The project uses full-universe scoring and triage to avoid missing listed companies, but the final watchlist is meant to reflect durable business-quality judgment rather than a mechanical score cutoff.

An automated completion pass was tried for remaining A-share peer groups. It created broad watch/reject decisions from numeric thresholds and group caps. That approach was rejected because it did not follow the intended peer-group method: each company must still be considered within its comparable industry group, with a reasoned judgment about moat, technical or business barriers, market position, operating quality, and whether a better-funded entrant or stronger peer could realistically displace it.

## 1.3 Decision

Final `*_peer_group_decisions.csv` files must be based on analyst peer-group review, not threshold-only automation.

Scripts may be used for mechanical work:

1. building review queues;
2. joining accepted decision files into watchlists;
3. validating coverage and CSV shape;
4. preparing evidence tables for analyst review.

Scripts must not decide final watch/reject outcomes from numeric thresholds alone.

## 1.4 Implications

1. A company can be rejected even with a high baseline score when stronger same-step or same-industry peers fully cover the investment attention slot.
2. A company can be retained despite weak current profits when the evidence supports scarce capability, high technical difficulty, durable resource ownership, customer validation, or a hard-to-replicate operating system.
3. Low-barrier industries can contribute zero watchlist companies, but the reason should be stated as an industry and company-level judgment rather than hidden inside an automated cutoff.
4. Remaining A-share groups should be processed in batches without repeatedly asking the reviewer for decisions, but the output should still contain company-by-company reasoning.
5. Baseline full-coverage scores remain useful triage evidence; they are not final decision authority.
