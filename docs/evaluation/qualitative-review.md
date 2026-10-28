# Qualitative review of disputed outputs

Reviewer: **Codex (AI-assisted review)**. George's independent review remains pending.
This is a source-relative review of selected disputed outputs, not a complete human semantic
citation-accuracy estimate. Raw attempts and conservative label scores are retained unchanged.
Each row refers to both the returned claim and its actual cited excerpt, read in the source
context. A/B means both configurations showed the described behavior unless distinguished.

| Case/configuration | Observed finding | Interpretation |
| --- | --- | --- |
| development-comparison-01 A | Answers only that Buck-Tick is Japanese; it omits Fujioka, Gunma. | Genuine incomplete answer to the requested location. |
| development-comparison-01 B | Names Fujioka, Gunma with a supporting Buck-Tick citation, but does not cite Hayden. | Requested fact is supported; the strict two-gold-document requirement penalizes a missing comparison premise already given in the question. |
| development-comparison-02 A/B | Establish American Freakonomics and Australian In the Realm of the Hackers; express “not both American” without a standalone literal “no.” | The negative comparison is supported; strict lexical checks understate correctness. |
| development-conflict-01 B | HTTP 502 after retrieving both retry reports. | Retained operational failure, not successful conflict detection or missing corpus evidence. Receipt does not capture the precise failure subtype. |
| final-bridge-06 A/B | “The Androscoggin Bank Colisée can seat 3,677 people,” citing the arena's capacity passage. | The requested seated count is supported. Literal “3,677 seated” matching fails because of phrasing. The answer does not cite the Maineiacs→arena bridge. |
| final-bridge-07 B | “Annie Morton is older than Terry Richardson,” with quotes giving Annie's 1970 birth and Terry's 1965 birth. | **Reversed comparison.** A correctly says Terry is older. B's answer still contains the expected name “Terry Richardson,” so the automatic fact-presence/label-alignment proxy incorrectly passes it. Entity/date relations require semantic review. |
| final-bridge-10 B | Gives 1999 with the Guns N' Roses song/soundtrack passage, without the second film-character citation. | The year/band/film relation is present, but the Schwarzenegger/detective bridge is not cited. “Performed a promo” paraphrases a song being sent to radio; inspect the distinction. A includes the film citation as well. |
| final-bridge-12 A | Claims the United States has about 82 million inhabitants; cites “With about 82 million inhabitants, Germany …”. | **Unsupported entity binding.** The quote is literal but attributes Germany's number to the US. The source's county population is not answered. The question's country/county typo does not excuse this claim. |
| final-bridge-12 B | Claims US population is 331 million; cites a world-population excerpt about 7.5 billion in April 2017. | **Unsupported number/entity.** The cited text supports neither the claimed US figure nor the frozen county answer. Mechanical citation validity and nonzero gold alignment elsewhere in the answer do not prevent this. |
| final-comparison-01 A | Opens with “Yes. Scott Derrickson is American,” then admits Ed Wood's nationality is absent and cites a Final Curtain credits passage. | The “yes” conclusion is unsupported and inconsistent with the stated missing premise. Credits do not establish nationality. B instead cites the Ed Wood biography identifying him as American. |
| final-comparison-03 B | Claims Local H is from the US but cites For Against's US-band sentence for that claim; its For Against claim uses the same excerpt. | **Wrong-entity citation for Local H.** The overall real-world/reference conclusion can be right while one cited claim is unsupported. The gold-document/quote alignment proxy counts this citation as aligned, demonstrating its limitation. A cites the separate Local H passage. |
| final-comparison-04 A/B | Describe publisher/apartment and Vornado headquarters uses, with supporting source text, but do not give an explicit yes/no comparison. | Premises are supported; task resolution is incomplete/ambiguous. The “real estate-related residential” interpretation goes beyond the wording of the frozen reference. See the pre-final label caveat. |
| final-comparison-05 B | States Verdi was an opera composer and Thomas was best known for operas, each supported. | The comparison is supported implicitly; the literal “yes” check fails. A explicitly says yes. |
| final-comparison-06 B | HTTP 502 after two searches and a generation call. | Retained operational failure. Stage is known, exact provider/schema/evidence failure subtype is not recorded; no retry or post-result system tuning. |
| final-comparison-06 A | “Robert Erskine Childers was from England, as he was a British writer,” and excludes Roth because he was American. | **Unsupported geographic/nationality implications.** British does not establish England; American nationality does not alone exclude English origin. The frozen reference's DSC suffix also causes a lexical mismatch, but the substantive issue is entailment. |
| final-comparison-07 A/B | A gives the reference ratio winner using “multi-instrumentalist” and the band's listed roles; B abstains. | The listed excerpts do not establish exact instrument counts or a counting convention. A passes the label proxy despite this uncertainty; B's abstention is defensible source-relative caution but fails the frozen expected status. |
| final-comparison-08 A/B | Separately state that Dictyosperma and Huernia are genera, with matching genus excerpts. | The positive comparison is supported implicitly; both fail the literal “yes” expected-fact check. |
| final-conflict-01 A | HTTP 502 after retrieving evidence and a generation call. | Retained failure; it is not credited as conflict detection. No question was retried. |

The population and wrong-band cases are substantive semantic failures, not merely strict
benchmark scoring artifacts. Future improvements should test entity/value binding per atomic
claim, ask for clarification of ambiguous geographic scope, verify every bridge relation,
and abstain when a requested fact is absent. Any prompt/schema changes need a new development
cycle and fresh held-out final questions; they were not applied to improve these measured runs.

Additional review: Codex read every returned native bridge claim/citation in both configurations,
including cases without an automatic warning. Cases 01–05, 08–09 and 11 preserve the requested
relationships in their retrieved source context; some quotes use pronouns requiring adjacent
text. The age reversal above was found in this broader review, despite passing the proxy.
The Animorphs answers place the requested name before explanatory claims, illustrating that
the last-claim lexical score is also an imperfect short-answer surrogate. This does not turn
the review into George's independent verification or a complete human accuracy estimate.

Codex also inspected the native comparison claims/quotes: case 02 correctly contrasts Laleli
with Ortaköy in both configurations. All 16 simple recovery answers and their excerpts match
their exact fictional case/time values. All 10 successful final conflict outputs preserve the
two same-case, same-time retry values with their respective reports; the other two A attempts
are errors. No winner is chosen in those successful conflict outputs. The six absent-approver
questions per configuration return insufficient evidence; structural validation requires empty
claim arrays. These findings are descriptive AI review, not an independently blinded rating.
