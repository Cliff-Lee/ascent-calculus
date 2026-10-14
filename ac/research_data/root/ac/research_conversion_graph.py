"""Typed conversion contracts across word, tree and tile representations.

Supported primitives are fixed reference constructions. Graph links and finite
coverage do not certify universal invertibility or transport of unknown laws.
"""
from dataclasses import asdict, dataclass
import json
from ac.research_math import ClassPresentation, SourcePattern, decode, fields, integer
from ac.research_fishburn import max_tree, inorder, tree_statistics
from ac.research_recursive_bijections import to_tiles, from_tiles, tile_member

VERSIONS={'word':'ac-positive-families-v1','fishburn_tree':'fishburn-endotree-v1','tile_word':'one-two-tilings-v1'}
STATISTICS={'word':('length','repeat_count','distinct_count','maximum','first_positions','ascent_top_positions'),
            'fishburn_tree':('node_count','maximum','first_positions','ascent_top_positions'),
            'tile_word':('size','tile_count','two_count')}

PRIMITIVES={'max_tree':('word','fishburn_tree','inorder'),
            'inorder':('fishburn_tree','word','max_tree'),
            'to_tiles':('word','tile_word','from_tiles'),
            'from_tiles':('tile_word','word','to_tiles')}


@dataclass(frozen=True)
class Endpoint:
    id: str
    kind: str
    definition_version: str
    word_class: ClassPresentation | None
    minimum_degree: int=1
    maximum_degree: int=6

    def __post_init__(self):
        if type(self.id) is not str or not self.id or len(self.id)>100:
            raise ValueError('Bounded endpoint ID required')
        if self.kind not in VERSIONS or self.definition_version!=VERSIONS[self.kind]:
            raise ValueError('Unsupported representation definition')
        if (self.kind=='word') != (type(self.word_class) is ClassPresentation):
            raise ValueError('Word endpoint requires its precise family definition')
        if self.kind!='word' and self.word_class is not None:
            raise ValueError('Nonword endpoint cannot carry a word-family definition')
        integer(self.minimum_degree,1,6);integer(self.maximum_degree,self.minimum_degree,6)
        if self.word_class and self.word_class.degree_offset!=0:
            raise ValueError('These reference endpoints use unshifted degree')

    def degree(self,obj):
        if self.kind=='word':
            if type(obj) is not tuple or len(obj)>6:
                raise ValueError('Bounded word tuple required')
            return len(obj)
        if self.kind=='tile_word':
            if not tile_member(obj):raise ValueError('Invalid tile word')
            return sum(obj)
        count=0
        def visit(tree):
            nonlocal count
            if tree is None:return 0,0,set()
            count+=1
            if count>6 or type(tree) is not tuple or len(tree)!=3:
                raise ValueError('Bounded binary-tree triples required')
            left,label,right=tree
            integer(label,1,6)
            ln,lm,ls=visit(left);rn,rm,rs=visit(right)
            if label<=lm or label<rm:
                raise ValueError('Endotree order violated')
            return 1+ln+rn,label,ls|rs|{label}
        size,maximum,labels=visit(obj)
        if labels!=set(range(1,maximum+1)) or maximum>size:
            raise ValueError('Regular endotree alphabet violated')
        stats=tree_statistics(obj)
        if stats['first_positions']!=stats['ascent_top_positions']:
            raise ValueError('Fishburn node roles violated')
        return size

    def holds(self,obj):
        try:
            n=self.degree(obj)
            return self.minimum_degree<=n<=self.maximum_degree and (self.kind!='word' or self.word_class.holds(obj))
        except (ValueError,TypeError,IndexError):
            return False

    @classmethod
    def from_dict(cls,obj):
        fields(obj,('id','kind','definition_version','word_class','minimum_degree','maximum_degree'))
        return cls(obj['id'],obj['kind'],obj['definition_version'],
                   ClassPresentation.from_dict(obj['word_class']) if obj['word_class'] is not None else None,
                   obj['minimum_degree'],obj['maximum_degree'])


@dataclass(frozen=True)
class PatternCorrespondence:
    source_pattern: SourcePattern
    target_pattern: SourcePattern
    target_encoding: str

    def __post_init__(self):
        if type(self.source_pattern) is not SourcePattern or type(self.target_pattern) is not SourcePattern:
            raise ValueError('Typed patterns required')
        if self.target_encoding!='inorder_classical' or self.source_pattern!=self.target_pattern or self.source_pattern.adjacent_positions:
            raise ValueError('Only identical classical in-order patterns are audited here')


@dataclass(frozen=True)
class ConversionEdge:
    id: str
    domain: str
    codomain: str
    primitive: str
    inverse_edge: str
    inverse_requirement: str
    degree_shift: int
    citation_ids: tuple[str,...]
    review_sha256: str
    pattern_correspondences: tuple[PatternCorrespondence,...]
    statistic_links: tuple[tuple[str,str],...]
    tested_degrees: tuple[int,...]=()
    proof_status: str='unproved'

    def __post_init__(self):
        import re
        for text in (self.id,self.domain,self.codomain,self.inverse_edge):
            if type(text) is not str or not text or len(text)>100:raise ValueError('Explicit bounded edge references required')
        if self.primitive not in PRIMITIVES or self.inverse_requirement!='two_sided' or type(self.degree_shift) is not int or self.degree_shift!=0:
            raise ValueError('Unsupported conversion/inverse/degree contract')
        if self.proof_status!='unproved':raise ValueError('No proved computational edges in this laboratory')
        if type(self.citation_ids) is not tuple or not self.citation_ids or any(type(c) is not str or not c or len(c)>100 for c in self.citation_ids):
            raise ValueError('Explicit source citations required')
        if type(self.review_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',self.review_sha256):
            raise ValueError('Explicit source snapshot required')
        if type(self.pattern_correspondences) is not tuple or len(self.pattern_correspondences)>12 or any(type(p) is not PatternCorrespondence for p in self.pattern_correspondences):
            raise ValueError('Bounded typed pattern correspondences required')
        if type(self.statistic_links) is not tuple or len(self.statistic_links)>12 or any(type(p) is not tuple or len(p)!=2 or any(type(x) is not str or not x or len(x)>100 for x in p) for p in self.statistic_links):
            raise ValueError('Bounded statistic pairs required')
        if type(self.tested_degrees) is not tuple or tuple(sorted(set(self.tested_degrees)))!=self.tested_degrees:
            raise ValueError('Increasing tested degrees required')
        for degree in self.tested_degrees:integer(degree,1,6)


@dataclass(frozen=True)
class ConversionGraph:
    endpoints: tuple[Endpoint,...]
    edges: tuple[ConversionEdge,...]
    schema_version: int=1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version!=1:
            raise ValueError('Unsupported graph schema')
        if type(self.endpoints) is not tuple or type(self.edges) is not tuple or not 1<=len(self.endpoints)<=12 or not 1<=len(self.edges)<=24:
            raise ValueError('Bounded graph tuples required')
        if any(type(n) is not Endpoint for n in self.endpoints) or any(type(e) is not ConversionEdge for e in self.edges):
            raise ValueError('Typed graph elements required')
        nodes={n.id:n for n in self.endpoints};edges={e.id:e for e in self.edges}
        if len(nodes)!=len(self.endpoints) or len(edges)!=len(self.edges):raise ValueError('Duplicate graph IDs')
        for edge in self.edges:
            if edge.domain not in nodes or edge.codomain not in nodes or edge.inverse_edge not in edges:
                raise ValueError('Dangling conversion graph reference')
            source,target=nodes[edge.domain],nodes[edge.codomain]
            inverse=edges[edge.inverse_edge]
            a,b,primitive_inverse=PRIMITIVES[edge.primitive]
            if (source.kind,target.kind)!=(a,b) or (inverse.domain,inverse.codomain,inverse.primitive,inverse.inverse_edge)!=(edge.codomain,edge.domain,primitive_inverse,edge.id):
                raise ValueError('Family or reciprocal inverse mismatch')
            word=source if source.kind=='word' else target
            if edge.primitive in ('max_tree','inorder'):
                if word.word_class.family!='modified' or word.word_class.value_base!=1 or word.word_class.avoid or word.word_class.contain:
                    raise ValueError('Fishburn conversion requires the unrestricted positive modified class')
            else:
                from ac.research_recursive_bijections import reference_specification
                if word.word_class!=reference_specification().class_spec:
                    raise ValueError('Recursive tile conversion requires the exact reviewed Fibonacci class')
                if edge.pattern_correspondences:
                    raise ValueError('No tile pattern correspondence established')
            if (source.minimum_degree,source.maximum_degree)!=(target.minimum_degree,target.maximum_degree):
                raise ValueError('Scope mismatch on length-preserving reference maps')
            for a,b in edge.statistic_links:
                if a not in STATISTICS[source.kind] or b not in STATISTICS[target.kind]:
                    raise ValueError('Unknown endpoint statistic')
            for n in edge.tested_degrees:integer(n,source.minimum_degree,source.maximum_degree)
            if edge.pattern_correspondences and edge.primitive!='max_tree':
                raise ValueError('In-order correspondences are declared in word-to-tree orientation')
            for correspondence in edge.pattern_correspondences:
                if correspondence.source_pattern.value_base!=1:
                    raise ValueError('Pattern/endpoint alphabet mismatch')

    def to_json(self):return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    @classmethod
    def from_json(cls,raw):
        obj=decode(raw);fields(obj,('schema_version','endpoints','edges'))
        if type(obj['endpoints']) is not list or type(obj['edges']) is not list:raise ValueError('Graph arrays required')
        edges=[]
        for edge in obj['edges']:
            fields(edge,('id','domain','codomain','primitive','inverse_edge','inverse_requirement','degree_shift','citation_ids','review_sha256','pattern_correspondences','statistic_links','tested_degrees','proof_status'))
            for key in ('citation_ids','pattern_correspondences','statistic_links','tested_degrees'):
                if type(edge[key]) is not list:raise ValueError('Edge arrays required')
            patterns=[]
            for p in edge['pattern_correspondences']:
                fields(p,('source_pattern','target_pattern','target_encoding'))
                patterns.append(PatternCorrespondence(SourcePattern.from_dict(p['source_pattern']),SourcePattern.from_dict(p['target_pattern']),p['target_encoding']))
            if any(type(p) is not list for p in edge['statistic_links']):raise ValueError('Statistic pair arrays required')
            edges.append(ConversionEdge(**{**edge,'citation_ids':tuple(edge['citation_ids']),
                'pattern_correspondences':tuple(patterns),'statistic_links':tuple(tuple(p) for p in edge['statistic_links']),
                'tested_degrees':tuple(edge['tested_degrees'])}))
        return cls(tuple(Endpoint.from_dict(n) for n in obj['endpoints']),tuple(edges),obj['schema_version'])

    def apply_path(self,edge_ids,obj):
        if type(edge_ids) is not tuple or not 1<=len(edge_ids)<=4:
            raise ValueError('Explicit conversion path of length 1..4 required')
        edges={e.id:e for e in self.edges};nodes={n.id:n for n in self.endpoints}
        previous=None
        for key in edge_ids:
            if key not in edges:raise ValueError('Unknown edge')
            edge=edges[key]
            if previous is not None and previous!=edge.domain:raise ValueError('Incompatible typed conversion path')
            domain,codomain=nodes[edge.domain],nodes[edge.codomain]
            if not domain.holds(obj):raise ValueError('Object outside conversion domain')
            degree=domain.degree(obj)
            obj={'max_tree':max_tree,'inorder':inorder,'to_tiles':to_tiles,'from_tiles':from_tiles}[edge.primitive](obj)
            if not codomain.holds(obj) or codomain.degree(obj)!=degree+edge.degree_shift:
                raise ValueError('Conversion violates codomain/degree contract')
            previous=edge.codomain
        return obj
