# AM-Next N4 — Structural fingerprints and invariant analysis

N4 adds a direct structural feature calculator in
`ac/discovery/fingerprints.py`. It independently derives new positions,
ascent-top and ascent-bottom positions, their overlaps, adjacent edge
directions, run lengths, multiplicities, fibre gaps, and first-to-last spans
from a word’s value tuple. It does not rely on `ChainWord`’s cached role sets.

## Object fingerprints

`structural_fingerprint(word)` returns:

- the exact values and degree;
- named, JSON-ready structural features;
- a one-based position trace showing whether each entry is `new`, `asctop`,
  and/or `ascbot`;
- current ordinary, modified, and revised classification;
- a SHA-256 digest of the structural features, degree, height, and semantics
  version.

The digest intentionally identifies the structural signature, so distinct
words may share it when their selected structure is the same. Keep the values
alongside the digest when identifying a specific word.

## Class profiles

`class_structural_profile(class_spec, degree, features=..., joint_features=...)`
enumerates a selected class and records the exact distribution of each feature.
It also keeps an example word for every feature value, so a mismatch can be
read as a concrete role-level witness. Optional joint profiles compare two or
three features together; these catch dependencies that separate one-feature
histograms cannot see.

`compare_structural_profiles` ranks the strongest finite profile differences
by changed multiplicity mass and number of changed values. The worker handler
`analyze-structural-profiles` computes these reports one degree at a time and
commits each degree as a checkpoint. It accepts any exact two-class N1
`SearchSpec` and supports degree offsets.

The default profile-value budget is 200,000 distinct values across selected
features and joint profiles. A researcher can raise it to 2,000,000 or select
fewer features. Exceeding the budget fails the degree without returning a
partial profile as though it were complete.

## Reading the result

For example, modified `111`-avoiders at degree 1 and revised `111`-avoiders at
degree 3 both contain one object. Their count match does not preserve several
natural feature profiles: the source has one new position and one ascent top;
the target word `212` has two new positions and two ascent tops. The analysis
shows these distribution differences and the example words. That rules out a
map preserving those exact features on the tested classes, but it does not
rule out an arbitrary bijection and it does not identify the block map.

When profiles match, the report says only that the statistic is equidistributed
on the tested finite sets. It does not produce an objectwise pairing. A map
could fail to preserve the profile, and equal profiles alone do not prove a
bijective map exists.

## Validation and limits

Tests compare new/top/bottom positions against the independent literal
definitions for every positive word of degrees 1 through 4. They check the
position-role view, ordinary-class distributions, joint profiles, finite
counterexamples, the profile budget, and execution through the persistent
worker.

N4 improves candidate interpretation and identifies which statistics a
transformation could preserve. It does not itself search the candidate space
for maps or derive proof arguments; generated operations begin in N5.
