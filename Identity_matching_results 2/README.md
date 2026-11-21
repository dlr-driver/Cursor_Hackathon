# Alert–hit identity matching baseline

## Files

- Alerts_clean.csv: 440 alerts, original row order and every source value retained, with clearer headings.
- Hits_scored.csv: 819 hits, original row order and every source value retained; derived comparisons and final match_score appended.
- Column_mapping.csv: original-to-clean headings, plus derived column inventory.
- Training_review.csv: per-pair model features and an empty reviewed_same_person column for future human labels (1=same person, 0=different person, blank=unreviewed/uncertain). It is not a trained model.
- Validation_summary.json: counts and data-quality findings.
- score_matches.py: rerunnable, standard-library Python implementation. Run `python3 score_matches.py INPUT_DIRECTORY OUTPUT_DIRECTORY`; the input directory must contain Alerts.csv and Hits.csv.

## Meaning of the score

match_score is an experimental 0–100 evidence score, **not an estimated probability**, validated confidence level, or automatic clearance/escalation recommendation. Higher means stronger support under the stated rules. No labelled same-person outcomes were supplied; logistic regression has therefore not been fitted. The existing source match_score (90–100 in this dataset) is preserved as original_match_score and excluded from the computation. It is not treated as truth.

Weights: name 0.60, date of birth 0.25, country 0.10, city 0.05. For company alerts, DOB is excluded and the remaining weights normalise to 0.75. Company records' source DOB values are retained without interpreting them as incorporation dates. Entity type is a compatibility check, not positive evidence: agreement alone never increases the score; a person/company conflict caps the result at 20.

Let W be the total eligible weight, A the total weight of usable comparisons, and S the weighted mean of available similarities. evidence_coverage = 100*A/W; available_evidence_similarity = 100*S. Final score = 100*S*(0.5+0.5*A/W), subject to the entity conflict cap. All coefficients and the cap are explicit starting assumptions, not learned parameters. A perfect person-name-only comparison scores 80 with 60% evidence coverage; a perfect company-name-only comparison scores 90 with 80% coverage. Missing evidence lowers support through the coverage factor, without asserting a contradiction. Low final scores can reflect either missing evidence or conflicting evidence; inspect the separate similarity, coverage and conflict columns.

Scores are independent per pair, do not sum to 100 per alert, and do not select a unique winner. Multiple reports may concern the same person. Hits are not deduplicated or merged.

## Comparisons

- Names: Unicode case normalisation, accent removal, punctuation removal, whitespace normalisation and token-order comparison; best match across primary name and semicolon-delimited aliases after removing parenthetical alias annotations. Exact names or equal sorted token lists score 100. Otherwise use the better of character-sequence similarity and sorted-token sequence similarity. Strict token subsets are capped at 85. There is no transliteration, nickname model or learned name-frequency weighting. Common names remain a limitation.
- DOB: parse valid ISO year, year-month or full date, including semicolon-delimited alternatives. Best compatible comparison scores 70 (year), 85 (year and month), or 100 (full date). A contradiction in the shared precision scores 0 and flags date_of_birth_conflict. Partial dates never become fabricated full dates. Multiple alternatives can increase chance agreement and should be reviewed.
- Country: customer's country searched as a complete normalised phrase in hit associated_countries and addresses. A mention scores 100; absence in populated location evidence scores 25 because locations may be incomplete or historical. These fields need not mean residence, so agreement is contextual support only. Nationality and citizenship are retained but not substituted for residence.
- City: customer's city searched as a complete phrase in hit addresses. Same 100/25 rule. Country and city evidence can be correlated; weights are deliberately small, but remain heuristic. Country aliases, abbreviations and city translations are not resolved in this baseline.
- Entity type: exact normalised comparison. One conflict was found.

Derived name_similarity, dob_similarity, country_similarity and city_similarity are 0–100; blanks mean unavailable. best_matching_name records the selected hit name/alias. match_reason explains which comparisons were available. conflict_flags records explicit DOB/entity contradictions. score_method identifies the baseline version. Training_review.csv stores similarities on the 0–1 scale with missing flags.

## Missing data and exclusions

Blank and common unknown placeholders stay unchanged in source columns. Missing comparison scores remain blank, rather than zero. Missing DOBs are not guessed from names or articles. City/country absence in a populated text field is weak negative evidence, distinct from a wholly unavailable comparison. Fixed eligible weights expose evidence missing on either side.

The bank's internal account reference is not comparable to hit passport, sanctions, tax or national identifiers. Login handles and email have no corresponding dedicated hit fields. Gender, birth place, nationality, citizenship and other hit attributes lack directly comparable alert fields. All remain available in the cleaned files where originally supplied but do not affect the score. News categories, allegations, relationships, notes, source URLs and the existing screening score are preserved for context and excluded from identity scoring. Source URLs were not opened and allegations were not verified.

## Validation and next step

Verified: unique alert IDs, unique hit IDs, all 819 hits link to one of 440 alerts, every source hit value retained, original ordering retained, scores within 0–100, match_score is the final hits column. DOB comparison is available for 99 pairs; country for 225; city for 150; names for all 819. There are 32 DOB conflicts and one entity-type conflict. These are mechanical checks, not evidence of predictive accuracy.

For logistic regression, manually label representative pairs including ambiguous names, sparse records, company records, conflicting dates and examples across the score range. Avoid selecting only obvious cases. Train on comparison features and missing flags, never IDs or allegations. Keep company DOB absence distinct from unknown person DOB. Split by customer identity, not rows; where identities are unavailable, use alert_id and also keep shared hit identities/near duplicates together to reduce leakage. Retain a separate validation/test set, measure precision/recall and calibration, and choose review thresholds based on measured error costs. Until labels exist, no accuracy, probability calibration or production threshold has been established.
