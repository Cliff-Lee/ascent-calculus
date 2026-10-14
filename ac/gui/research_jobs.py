"""Isolated small reference jobs; responsive termination and no provider access."""
from collections import OrderedDict
import multiprocessing as mp
import queue
import threading
import time
import uuid
import copy
import hashlib
import json
from ac.research_resources import source_bytes

from ac.gui.research_library_model import METHODS


def run_method(method):
    if method not in METHODS:raise ValueError('Unknown reference method')
    objects=[];failures=[];obligations=[]
    flags=['VERIFIED_TO_N','INDEPENDENT_FINITE_CHECK']
    if method=='counts':
        from ac.research_benchmarks import run_case
        evidence=[run_case('PP129-P6',n) for n in (1,2,3,4)]
        from ac.research_recursive_bijections import reference_specification
        from ac.research_math import engine_words
        objects=[{'word':list(w),'value_base':0,'label':'Ordinary source, degree 4'} for w in engine_words(reference_specification().class_spec,4)]
        passed=all(e['status']=='finite_verified' for e in evidence)
        structure={'count_rows':evidence}
    elif method=='specification':
        from ac.research_specifications import search_fibonacci_specifications
        search=search_fibonacci_specifications();survivor=search['survivors'][0]
        structure=survivor['description'];evidence=survivor['evidence'];obligations=survivor['obligations']
        passed=evidence['status']=='finite_verified'
        failures=[t['first_training_failure'] for t in search['trials'] if t['first_training_failure']][:3]
        flags.insert(0,'CONJECTURED')
        objects=[{'word':[0,1,2,2,1],'value_base':0,'label':'Source for recursive insertion'}]
    elif method=='tree':
        from ac.research_generating_trees import reference_demo
        report=reference_demo(5);left=report['sides']['left']
        structure={'transition_table':left['published_replay']['inference']['table'],
                   'recurrence_candidate':left['published_replay']['recurrence_candidate']}
        evidence={side:value['tree_audit'] for side,value in report['sides'].items()}
        passed=all(e['status']=='finite_verified' for e in evidence.values()) and left['published_replay']['counts_match']
        obligations=left['published_replay']['unproved_obligations']
        for trial in left['label_trials']:
            failure=trial.get('training_plus_holdout',trial['training'])['shortest_tested_witness']
            if failure and trial['label']==['zero_count']:
                failures.append(failure)
                objects += [{'word':list(failure[key]),'value_base':0,'label':'Refuted total-zero-count label: '+key} for key in ('word_a','word_b')]
        flags.insert(0,'CONJECTURED')
    elif method in ('transport','bijection'):
        from ac.research_conversion_audit import load_reference_graph,audit_conversion
        graph=load_reference_graph();edge='modified-to-tree' if method=='transport' else 'fibonacci-to-tiles'
        evidence=audit_conversion(graph,edge,(1,2,3,4))
        passed=evidence['status']=='finite_verified'
        if method=='transport':
            structure={'tree':graph.apply_path((edge,),(1,2,1,3)),
                       'pattern_encoding':'Classical word patterns in the in-order encoding; not tree-shape patterns'}
            objects=[{'word':[1,2,1,3],'value_base':1,'label':'Modified source for Fishburn representation'}]
        else:
            from ac.research_recursive_bijections import derivation
            structure=derivation((0,1,2,2,1))
            failures=[audit_conversion(graph,edge,(1,2,3),inverse_override=lambda _: (0,))]
            objects=[{'word':[0,0],'value_base':0,'label':'Smallest tested faulty-inverse source'},
                     {'word':[0,1,2,2,1],'value_base':0,'label':'Recursive bijection source'}]
            flags.insert(0,'CONJECTURED')
        obligations=['All-length implementation correspondence and inverse identities remain unproved.']
    else:
        from ac.research_language_benchmarks import reference_demo
        report=reference_demo()
        structure={'regular_equations':report['regular']['human_equations'],
                   'grammar_equations':report['counter_grammar']['human_equations'],
                   'counter_state_space':report['counter_grammar']['state_space']}
        evidence={'regular_rows':report['regular']['rows'],'grammar':report['counter_grammar']['audit'],
                  'ascent_bridge':report['counter_grammar']['class_bridge'],'empty_convention':report['counter_grammar']['empty_convention']}
        failures=report['negative_controls'];obligations=report['counter_grammar']['logical_obligations']
        passed=all(r['passed'] for r in report['regular']['rows']) and report['counter_grammar']['audit']['status']=='finite_verified' and all(r['counts_match'] and r['same_complete_ascent_members'] for r in report['counter_grammar']['class_bridge'])
    if not passed:flags=[flag for flag in flags if flag not in ('VERIFIED_TO_N','INDEPENDENT_FINITE_CHECK')]
    provenance={'method_source_sha256':hashlib.sha256(source_bytes('gui/research_jobs.py')).hexdigest(),
                'configuration_sha256':hashlib.sha256(json.dumps(METHODS[method],sort_keys=True).encode()).hexdigest(),
                'execution':'isolated local reference worker; no provider calls'}
    return {'provenance':provenance,'finite_validation_status':'finite_verified' if passed else 'validation_failed','method_id':method,'title':METHODS[method]['title'],'status_flags':flags,
            'tested_degrees':METHODS[method]['degrees'],'source_work':METHODS[method]['lead'],
            'evidence':evidence,'generated_structure':structure,'counterexamples':failures,
            'obligations':obligations,'inspectable_objects':objects,
            'proof_status':'not_formally_checked','universal_implementation_status':'unproved',
            'notice':'Finite independent checks do not establish an all-length proof. Source review is shown separately.'}


def _worker(method,outbox):
    try:outbox.put(('completed',run_method(method)))
    except Exception as exc:outbox.put(('failed',{'detail':f'{type(exc).__name__}: {exc}'}))


class ReferenceJobs:
    """One active spawned worker, bounded history, no mutable mathematical state."""
    def __init__(self):
        self.context=mp.get_context('spawn');self.jobs=OrderedDict();self.lock=threading.Lock()

    def start(self,method):
        if method not in METHODS:raise ValueError('Unknown reference method')
        with self.lock:
            for key in tuple(self.jobs):self._poll(key)
            if any(j['status']=='running' for j in self.jobs.values()):raise ValueError('Cancel or finish the current reference run first')
            while len(self.jobs)>=8:
                _,old=self.jobs.popitem(last=False);old['queue'].close()
            key=uuid.uuid4().hex;outbox=self.context.Queue()
            process=self.context.Process(target=_worker,args=(method,outbox),daemon=True)
            process.start()
            self.jobs[key]={'status':'running','method_id':method,'process':process,'queue':outbox,'started':time.monotonic(),'result':None}
            return key

    def _poll(self,key):
        job=self.jobs[key]
        if job['status']=='running':
            try:
                status,result=job['queue'].get_nowait();job.update(status=status,result=result)
                job['process'].join(timeout=.05)
            except queue.Empty:
                if not job['process'].is_alive():
                    job.update(status='failed',result={'detail':'Reference worker exited without a result.'})
                elif time.monotonic()-job['started']>30:
                    job['process'].terminate();job['process'].join(timeout=1)
                    job.update(status='failed',result={'detail':'Reference run exceeded its 30-second budget.'})
        return {'id':key,'method_id':job['method_id'],'status':job['status'],'result':job['result']}

    def poll(self,key):
        with self.lock:
            if key not in self.jobs:raise ValueError('Unknown reference job')
            return copy.deepcopy(self._poll(key))

    def cancel(self,key):
        with self.lock:
            if key not in self.jobs:raise ValueError('Unknown reference job')
            job=self.jobs[key]
            if job['status']=='running':
                job['process'].terminate();job['process'].join(timeout=1)
                if job['process'].is_alive():job['process'].kill();job['process'].join(timeout=1)
                job.update(status='cancelled',result=None)
            return {'id':key,'status':job['status']}

    def close(self):
        for key in tuple(self.jobs):self.cancel(key)


_JOBS=None
_INIT_LOCK=threading.Lock()

def jobs():
    global _JOBS
    with _INIT_LOCK:
        if _JOBS is None:_JOBS=ReferenceJobs()
        return _JOBS
