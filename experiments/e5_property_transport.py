from ac import (
    R,
    Modified,
    Avoid,
    Cayley,
    SameSet,
    Last,
    ScopeLast,
    RawDescTop,
    transport_predicate,
    pushforward,
    check_lift_restriction_law,
    check_capacity_shift_law,
    compare_classes,
)
from ac.generate.universes import chain_words, modified_via_hat, cayley_words

print("E5 PROPERTY TRANSPORT")
print("=====================")

rev_mod = transport_predicate(Modified(), R())
expected_rev_mod = Cayley() & SameSet(Last(), ScopeLast() | RawDescTop())
print("Reversed modified theory:")
print("  Last = {n} union RawDescTop")
print("  exact through Cayley n<=6:", all(
    rev_mod.holds(x) == expected_rev_mod.holds(x)
    for n in range(1, 7) for x in cayley_words(n)
))

source = Modified() & Avoid("2122")
transported = transport_predicate(source, R())
semantic = pushforward(R(), source)
print("Reverse transports Av(2122) to Av(2212) while changing the structure theory:")
print("  symbolic == semantic through Cayley n<=6:", all(
    transported.holds(x) == semantic.holds(x)
    for n in range(1, 7) for x in cayley_words(n)
))

print("\nLift laws:")
print("  ambient restriction law, all words height=4 n<=5:",
      check_lift_restriction_law(universe=chain_words, through=5, height=4) is None)
for r in (2, 3, 4, 5):
    ok = check_capacity_shift_law(r, universe=chain_words, through=5, height=4) is None
    print(f"  1^{r} capacity-shift law, all words height=4 n<=5: {ok}")

print("\nModified Av(2122) vs Av(2212):")
comp = compare_classes(
    Avoid("2122"), Avoid("2212"),
    universe=modified_via_hat,
    through=9,
    statistics=(
        "height", "ascents", "multiplicity_partition",
        "height+partition", "ascents+partition",
        "first_positions", "last_positions",
    ),
)
for row in comp.rows:
    flags = ", ".join(f"{k}={'=' if v else '!='}" for k, v in row.profile_equal)
    mark = "different members" if row.first_membership_difference else "same members"
    print(f"  n={row.n}: {row.left_count} / {row.right_count}; {mark}; {flags}")

first = comp.first_class_difference()
if first:
    print("  first class difference n=", first.n, " witness=", first.first_membership_difference, sep="")
for stat in ("height", "ascents", "multiplicity_partition", "height+partition", "ascents+partition", "first_positions", "last_positions"):
    row = comp.first_profile_mismatch(stat)
    print(f"  first {stat} profile mismatch:", None if row is None else row.n)
