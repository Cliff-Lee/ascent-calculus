"""Brute-force finite oracle; no engine predicate/generator/matcher imports."""
from itertools import product,combinations


def reference_words(spec,length):
    if type(length) is not int or not 0<=length<=6:raise ValueError('Oracle length budget is 0..6')
    if spec.family not in ('ordinary','modified','revised'):raise ValueError('Unsupported oracle family')
    base=spec.value_base
    def contains(word,pattern):
        for selected in combinations(range(length),len(pattern.values)):
            if any(selected[i]!=selected[i-1]+1 for i in pattern.adjacent_positions):continue
            values=tuple(word[i] for i in selected)
            # Compare every pair directly: no standardization/compiler shared.
            if all((values[i]==values[j])==(pattern.values[i]==pattern.values[j]) and
                   (values[i]<values[j])==(pattern.values[i]<pattern.values[j])
                   for i in range(len(values)) for j in range(len(values))):return True
        return False
    for word in product(range(base,base+length),repeat=length):
        if spec.family=='ordinary':
            member=bool(word) and word[0]==base
            for i in range(1,length):
                asc=sum(word[j]<word[j+1] for j in range(i-1))
                member=member and word[i]<=base+1+asc
        else:
            first=set();seen=set()
            for i,v in enumerate(word):
                if v not in seen:first.add(i);seen.add(v)
            levels=set(range(base,max(word,default=base-1)+1))
            roles=({0} if word else set())
            for i in range(length-1):
                if word[i]<word[i+1]:roles.add(i+1 if spec.family=='modified' else i)
            member=seen==levels and first==roles
        if member and not any(contains(word,p) for p in spec.avoid) and all(contains(word,p) for p in spec.contain):yield word
