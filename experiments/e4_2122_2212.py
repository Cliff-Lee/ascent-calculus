"""E4 calibration: compare modified 2122- and 2212-avoidance classes."""
from ac import Pattern, BUILTIN_STATS, compare_profile
from ac.generate.universes import modified_via_hat

p = Pattern("2122").compile()
q = Pattern("2212").compile()

for n in range(1, 10):
    left = []
    right = []
    total = 0
    for x in modified_via_hat(n):
        total += 1
        if p.avoids(x):
            left.append(x)
        if q.avoids(x):
            right.append(x)
    print(f"n={n}: M={total}, Av2122={len(left)}, Av2212={len(right)}")
    if n >= 6:
        for name, stat in BUILTIN_STATS.items():
            result = compare_profile(left, right, stat, name=name)
            print(f"    {name:24s} {'=' if result.equal else '!='}")
