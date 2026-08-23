# Assumptions

| # | What was unclear | What I assumed | Why |
|---|---|---|---|
| 1 | The SEC name lookup contains multiple Tudor-related entities, and an exact-name match did not produce the required 2026 filings. | I used CIK 923093 for Tudor Investment Corp. | Its SEC submission history contains the in-scope 13F filings for both required quarters. The supplied CIK pointed to an unrelated filer, while the initial exact-name candidate did not produce the expected filings. |
| 2 | The roster name `The Baupost Group LLC` differs from the official lookup spelling `BAUPOST GROUP LLC/MA`. | I retained the supplied CIK 1061768 and marked it `given`. | The legal suffix variation is a name-format difference, while the CIK resolves to the intended manager and its required filings. |
| 3 | Some XML files contain `<otherManager>0</otherManager>`, while others omit the element. | I preserved `0` when explicitly filed and used null when the element was absent. | `other_manager` is described as a reference “as filed”; preserving an explicit source value avoids silently rewriting the filing. |
| 4 | “Distinct issuers” could be defined using issuer names or security identifiers. | I count normalized filed issuer names within the filing. | The schema describes `name_of_issuer` as the issuer field, while one issuer may have multiple security classes and CUSIPs. |
| 5 | “Added shares” and “grew or shrank” could include options or principal amounts. | I compare direct `SH` positions and exclude rows with `put_call` populated. | Option quantities and principal amounts are not directly comparable to ordinary share ownership. |
| 6 | A manager may report several rows matching the same requested issuer. | For cross-manager issuer-position questions, I sum matching reported values by manager. | Duplicate rows may be legitimate and must not be removed; summing preserves every reported entry while producing a manager-level comparison. |
| 7 | “Largest position” for one manager could mean an aggregated issuer or one reported position row. | I return the largest individual information-table row by reported value. | The holdings table’s grain is one reported position, so this follows the dataset’s defined grain without collapsing rows. |
| 8 | A notice filer has no direct information table. | A `13F-NT` receives a filing row, no holdings rows, and direct-holdings questions are answered “No” with the notice accession as evidence. | This distinguishes “filed a notice with no direct holdings table” from “did not file anything.” |
| 9 | Issuer names are free text and inconsistent across managers. | The agent uses case-insensitive normalized substring matching for short issuer terms such as Apple, Nvidia, Microsoft, and Tesla. | This handles common legal suffix and punctuation differences without introducing an external security-master dependency. |
| 10 | No amendments occur within the selected periods and cutoff. | Amendment fields are parsed generically rather than hard-coded, but are false/null for this dataset. | This preserves general 13F behavior while accurately representing the in-scope filings. |

## Questions you sent us

I did not email the DSRS team with specification questions. I documented the decisions
above and continued working.