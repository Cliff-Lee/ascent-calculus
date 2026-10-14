"""Independent finite audits for typed conversions; failure witnesses retained."""
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from ac.core.word import ChainWord
from ac.research_benchmarks import compare_members, check_transport, word_statistics
from ac.research_math import engine_words, integer
from ac.research_math_oracle import reference_words
from ac.research_benchmark_oracles import fishburn_trees
from ac.research_fishburn import tree_statistics, max_tree
from ac.research_recursive_bijections import tile_levels, independent_tiles, reference_specification, derivation
from ac.research_conversion_graph import ConversionGraph

ROOT=Path(__file__).resolve().parents[1]
GRAPH_SHA256='327852932bf57ad9bfac9a2456eb0f8a2ebf0803d81d718687f5cb630c2da36c'


def load_reference_graph():
    from ac.research_evidence import load_review
    raw=(ROOT/'docs/research/pp07/graph_v1.json').read_text()
    graph=ConversionGraph.from_json(raw)
    if sha256(graph.to_json().encode()).hexdigest()!=GRAPH_SHA256:
        raise ValueError('Reference conversion binding changed; explicit re-audit required')
    reviews=[load_review(ROOT/'docs/research'/folder/'source_reviews_v1.json') for folder in ('pp03','pp04')]
    by_hash={r.fingerprint:r for r in reviews}
    for edge in graph.edges:
        if edge.review_sha256 not in by_hash:
            raise ValueError('Conversion source snapshot changed')
        cites={c.id for c in by_hash[edge.review_sha256].entities('Citation')}
        if not set(edge.citation_ids)<=cites:
            raise ValueError('Dangling conversion citation')
    return graph


def statistics(endpoint,obj):
    if endpoint.kind=='word':
        return {**word_statistics(obj),'length':len(obj),
                'distinct_count':len(set(obj)),'repeat_count':len(obj)-len(set(obj))}
    if endpoint.kind=='tile_word':
        return {'size':sum(obj),'tile_count':len(obj),'two_count':obj.count(2)}
    return {**tree_statistics(obj),'node_count':endpoint.degree(obj)}


def independent_tree_contains(tree,pattern):
    """Read labels through an independent iterative in-order traversal.

    Pattern semantics are pairwise comparisons, not the engine pattern compiler.
    This is word-pattern containment in the in-order encoding, not shape avoidance.
    """
    labels=[];stack=[];current=tree
    while current is not None or stack:
        while current is not None:
            stack.append(current);current=current[0]
        current=stack.pop();labels.append(current[1]);current=current[2]
    for selected in combinations(labels,len(pattern.values)):
        if all((selected[i]<selected[j])==(pattern.values[i]<pattern.values[j]) and
               (selected[i]==selected[j])==(pattern.values[i]==pattern.values[j])
               for i in range(len(selected)) for j in range(len(selected))):
            return True
    return False


def endpoint_members(endpoint,degree):
    if endpoint.kind=='word':
        a=list(engine_words(endpoint.word_class,degree)); b=list(reference_words(endpoint.word_class,degree))
    elif endpoint.kind=='tile_word':
        a=tile_levels(degree)[degree]; b=list(independent_tiles(degree))
    else:
        # Trees are enumerated independently, not inferred from image counts.
        from ac.research_math import ClassPresentation
        mod=ClassPresentation('modified',1,(),(),0,'C-PP04-047')
        a=[max_tree(w) for w in engine_words(mod,degree)]; b=list(fishburn_trees(degree))
    return a,b


def audit_conversion(graph,edge_id,degrees,*,forward_override=None,inverse_override=None):
    if type(graph) is not ConversionGraph or type(degrees) is not tuple or not degrees:
        raise ValueError('Typed graph and nonempty degree tuple required')
    if edge_id not in {e.id for e in graph.edges}:
        raise ValueError('Unknown conversion edge')
    edge=next(e for e in graph.edges if e.id==edge_id)
    source=next(n for n in graph.endpoints if n.id==edge.domain)
    target=next(n for n in graph.endpoints if n.id==edge.codomain)
    if any(type(n) is not int for n in degrees) or tuple(sorted(set(degrees)))!=degrees:
        raise ValueError('Unique increasing exact degrees required')
    for n in degrees:integer(n,source.minimum_degree,source.maximum_degree)
    forward=forward_override or (lambda obj:graph.apply_path((edge.id,),obj))
    inverse=inverse_override or (lambda obj:graph.apply_path((edge.inverse_edge,),obj))
    source_stat=lambda obj:tuple(statistics(source,obj)[a] for a,_ in edge.statistic_links)
    target_stat=lambda obj:tuple(statistics(target,obj)[b] for _,b in edge.statistic_links)
    rows=[];first=None
    for n in degrees:
        source_members,source_oracle=endpoint_members(source,n)
        target_members,target_oracle=endpoint_members(target,n)
        a=compare_members(source_members,source_oracle);b=compare_members(target_members,target_oracle)
        transport=check_transport(source_oracle,target_oracle,forward,inverse,source_stat,target_stat)
        patterns=[]
        for correspondence in edge.pattern_correspondences:
            mismatch=None
            for word in sorted(source_oracle):
                try:
                    actual=correspondence.source_pattern.compile().contains(ChainWord(word))
                    transported=independent_tree_contains(forward(word),correspondence.target_pattern)
                    if actual!=transported:
                        mismatch={'source':word,'source_contains':actual,'target_contains':transported};break
                except (ValueError,TypeError,IndexError) as exc:
                    mismatch={'source':word,'error':str(exc)};break
            patterns.append({'pattern':correspondence.source_pattern.values,'encoding':correspondence.target_encoding,
                             'passed':mismatch is None,'first_failure':mismatch})
        failures=transport['failures']
        checks={'source_membership':all(source.holds(w) and source.degree(w)==n for w in source_oracle),
                'target_membership':all(target.holds(w) and target.degree(w)==n for w in target_oracle) and 'target_membership' not in failures and 'construction_error' not in failures,
                'injectivity':'collision' not in failures and 'duplicate_generation' not in failures and 'construction_error' not in failures,
                'surjectivity':'surjectivity' not in failures,
                'left_composition':'left_inverse' not in failures and 'construction_error' not in failures,
                'right_composition':'right_inverse' not in failures and 'inverse_error' not in failures,
                'statistics':'statistic' not in failures and 'construction_error' not in failures,
                'patterns':all(p['passed'] for p in patterns)}
        disagreement=not a['same_complete_members'] or not b['same_complete_members']
        passed=not disagreement and all(checks.values()) and transport['passed']
        row={'degree':n,'source_count':len(source_oracle),'target_count':len(target_oracle),
             'source_backend_agreement':a,'target_backend_agreement':b,
             'target_oracle_independence':'word-engine images versus independent structural tree generator' if target.kind=='fishburn_tree' else 'independent object generator',
             'checks':checks,'transport':transport,'pattern_tests':patterns,'passed':passed}
        if not passed and first is None:first=row
        rows.append(row)
    backend_failure=any(not r['source_backend_agreement']['same_complete_members'] or not r['target_backend_agreement']['same_complete_members'] for r in rows)
    return {'schema_version':1,'edge_id':edge.id,'degrees':list(degrees),'rows':rows,
            'status':'validation_disagreement' if backend_failure else 'refuted' if first else 'finite_verified',
            'first_tested_failure':first,'proof_status':'unproved','citation_ids':list(edge.citation_ids),
            'graph_sha256':sha256(graph.to_json().encode()).hexdigest(),
            'source_review_sha256':edge.review_sha256,
            'overrides_applied':forward_override is not None or inverse_override is not None}


def reference_demo():
    graph=load_reference_graph()
    degrees=tuple(range(1,7))
    reports=[audit_conversion(graph,key,degrees) for key in ('modified-to-tree','fibonacci-to-tiles')]
    from dataclasses import replace
    edge=next(e for e in graph.edges if e.id=='fibonacci-to-tiles')
    false_stat=replace(edge,statistic_links=(('distinct_count','size'),))
    stat_graph=replace(graph,edges=tuple(false_stat if e.id==edge.id else e for e in graph.edges))
    negative_controls=[
        {'construction':'inverse returns the base word (0,) for every tile word',
         'audit':audit_conversion(graph,'fibonacci-to-tiles',(1,2,3),inverse_override=lambda _: (0,))},
        {'construction':'forward returns only size-one tiles, losing repeated-value data',
         'audit':audit_conversion(graph,'fibonacci-to-tiles',(1,2,3),forward_override=lambda w: (1,)*len(w))},
        {'construction':'unchanged bijection with false statistic link distinct_count = total tile size',
         'audit':audit_conversion(stat_graph,'fibonacci-to-tiles',(1,2,3))}]
    return {'schema_version':1,'graph':json.loads(graph.to_json()),'audits':reports,
            'negative_controls':negative_controls,
            'worked_recursive_derivation':derivation((0,1,2,2,1)),
            'parallel_source_specification':json.loads(reference_specification().to_json()),
            'parallel_target_specification':{'family':'ordered_one_two_tilings','degree':'sum of tile sizes',
                'atoms':[[1],[2],[1,1]],'rules':[{'append':1,'minimum_parent_size':2},{'append':2,'minimum_parent_size':1}]},
            'unproved_obligations':['Source recursive decomposition at every length','Parallel constructors form disjoint and exhaustive branches',
                                    'Recursive maps are inverse at every degree','Statistic preservation at every degree',
                                    'Formal definitions match the inspected external transport theorem'],
            'proof_status':'unproved','implementation_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
