# Reference caveats recorded before the final model run

Codex inspected the frozen supporting passages while the development batch ran. The labels
remain unchanged; George's independent verification is pending. These are source-relative
observations, not a new gold set or an attempt to improve measured final scores.

| Case | Caveat to keep visible during review |
| --- | --- |
| final-bridge-01 | The source names ambassador roles as well as Chief of Protocol. The question says only “what government position”; the single reference is narrower than the wording. |
| final-bridge-03 | Greenwich Village is a neighborhood in New York City. A correct city-only answer can miss the full frozen phrase. |
| final-bridge-05 | The Aladin passage itself names his former consultancy role; requiring the generic management-consulting definition as a second cited source is conservative. |
| final-bridge-06 | The venue has 4,000 total capacity and 3,677 seated. The question says “seat,” favoring 3,677, but the distinction should be reviewed. |
| final-bridge-07 | The native dataset labels this bridge, although the wording compares two birth dates. Keep its frozen category for the stated counts. |
| final-bridge-12 | The question says “country”; the source gives Brown County, Kansas and its 2010 population of 9,984. Do not infer that this is a national population or a current census count. |
| final-comparison-04 | “Used for real estate” is ambiguous. Random House Tower contains publisher headquarters/apartments; 888 7th Avenue contains Vornado Realty Trust headquarters. The reference “no” relies on a narrower interpretation than ordinary real-estate usage. |
| final-comparison-06 | The prepared Childers passage says British, not English, and gives no birthplace. England is not entailed merely by British nationality. The single reference also includes the DSC suffix, so a name-only prediction may fail the literal expected-fact check. |
| final-comparison-07 | “Multi-instrumentalist” versus a four-person band's listed roles does not specify instrument counts or a consistent counting convention for vocals/guitars. A numerical ratio is not fully established by the selected passages. |

These caveats should inform qualitative review, with raw label scores retained. A future revised
benchmark needs a versioned label change and a fresh held-out set; do not tune the final system
or silently amend labels after observing its answers.
