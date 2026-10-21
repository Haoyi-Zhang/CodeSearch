"""Finite regressions for metric admission, replay binding and mandatory plot build."""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import validate_release as release
import generate_incremental_tables as tables
import replay_incremental as replay
from compare_incremental import trial
from src.model import features

ART = Path(__file__).resolve().parents[1]
PAPER = ART.parent/'paper'

def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

@contextmanager
def altered_summary(field, value):
    original=release.load_json
    changed=deepcopy(original(ART/'results/continuation-summary.json'))
    changed['policies']['continuation'][field]=value
    def load(path):
        return changed if path.name=='continuation-summary.json' else original(path)
    with patch.object(release,'load_json',side_effect=load):
        yield changed

class MetricAdmission(unittest.TestCase):
    def test_trace_totals_cannot_replace_raw_phase_query_costs(self):
        from result_metrics import load_trace,trace_metrics
        trace=load_trace(ART/'results/continuation-traces/continuation-fresh-seed2-capacity5.json.gz')
        trace['policy_totals']['continuation']['bytes']+=1
        with self.assertRaisesRegex(ValueError,'metric mismatch'):
            trace_metrics(trace)

    def test_real_history_costs_are_reconstructed_too(self):
        from result_metrics import load_trace,trace_metrics
        trace=load_trace(ART/'results/real-history-trace.json.gz')
        trace['policy_costs']['continuation']['messages']+=1
        with self.assertRaisesRegex(ValueError,'metric mismatch'):
            trace_metrics(trace,('continuation','overlay','cut-cache','unsafe-stale'),real=True)

    def test_total_cannot_disagree_with_retained_records(self):
        with altered_summary('total_source_bytes',6141025):
            with self.assertRaisesRegex((AssertionError,ValueError),'metric|total|bytes'):
                release.validate_results(False,False)

    def test_messages_denominator_and_mean_are_strict(self):
        for field,value in [('total_source_messages',8441),('queries',4537),
                            ('total_source_bytes',True),('queries',4536.0)]:
            with self.subTest(field=field,value=value),altered_summary(field,value):
                with self.assertRaises((AssertionError,ValueError)):
                    release.validate_results(False,False)

    def test_export_rejects_before_writing_any_consumer(self):
        if not PAPER.is_dir():self.skipTest('optional sibling manuscript absent')
        assets=module('p016_assets_regression',PAPER/'generate_assets.py')
        raw=json.loads((ART/'results/continuation-summary.json').read_text())
        raw['policies']['continuation']['total_source_bytes']=6141025
        original=assets.read
        with patch.object(assets,'read',side_effect=lambda n:raw if n=='continuation-summary.json' else original(n)):
            with patch.object(assets,'write_macros',side_effect=RuntimeError('export started')):
                with self.assertRaisesRegex((AssertionError,ValueError),'metric|total|bytes'):
                    assets.main()

class IncrementalBinding(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        sources={'x':'def f(x):\n    return x\n','xy':'def f(x,y):\n    return x+y\n'}
        self.payloads={b:{'source':text,'features':list(features(text))} for b,text in sources.items()}
        fixture={'payloads':self.payloads,'initial':[{'a':'xy','b':'x'}, {}, {}],
          'history':[[{'shard':0,'seq':1,'changes':[['a',None]]}],[],[]],
          'schedule':[[1,0,0]]}
        query={'id':'q','plan':[['name:x','name:y']],'k':1}
        self.trial=await trial(fixture,[query],'continuation',1,0)
        self.temp=tempfile.TemporaryDirectory(prefix='p016-binding-')
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)

    def write(self, tamper_report=False, tamper_semantics=False):
        item=deepcopy(self.trial)
        report={'trials':[deepcopy(item['summary'])]}
        if tamper_semantics:
            item['records'][0]['oracle']=[]
        packet={'report':deepcopy(report),'trials':[item]}
        if tamper_report:report['trials'][0]['refill_shards']+=7
        (self.directory/'probe.json').write_text(json.dumps(report))
        with gzip.open(self.directory/'probe-trace.json.gz','wt') as stream:json.dump(packet,stream)
        (self.directory/'probe-replay.json').write_text(json.dumps({'result':'PASS','counts':{'trials':1,'results':item['summary']['calls']}}))
        return report,packet

    def read(self):
        with patch.object(replay,'build',return_value={}),patch.object(replay,'build_real_history',return_value={'payloads':self.payloads}):
            return tables.read('probe',self.directory)

    async def test_stale_pass_does_not_admit_changed_report(self):
        self.write(tamper_report=True)
        with self.assertRaises((AssertionError,ValueError)):self.read()

    async def test_matching_counts_do_not_replace_semantic_replay(self):
        self.write(tamper_semantics=True)
        with self.assertRaises((AssertionError,ValueError)):self.read()

    async def test_valid_pair_replays_without_editing_historical_receipt(self):
        report,_=self.write()
        old=(self.directory/'probe-replay.json').read_bytes()
        with patch.object(replay,'verify',wraps=replay.verify) as verified:
            self.assertEqual(report['trials'],self.read())
            self.assertEqual(1,verified.call_count)
        self.assertEqual(old,(self.directory/'probe-replay.json').read_bytes())

class MandatoryPlotBuild(unittest.TestCase):
    def setUp(self):
        if not PAPER.is_dir():self.skipTest('optional sibling manuscript absent')
        self.build=module('p016_build_regression',PAPER/'build.py')
        self.temp=tempfile.TemporaryDirectory(prefix='p016-build-')
        self.addCleanup(self.temp.cleanup)
        self.build.REPORT=Path(self.temp.name)/'report.json'

    def test_plot_consumer_is_mandatory_before_tex(self):
        calls=[]
        with patch.object(self.build.shutil,'which',return_value='tool'),patch.object(self.build,'command',side_effect=lambda x:calls.append(x) or ''),patch.object(self.build,'verify',return_value={'status':'PASS'}):
            self.build.main_run()
        names=[str(c[1]) for c in calls]
        self.assertIn('figures/draw_evaluation.py',names)
        self.assertLess(names.index('figures/draw_evaluation.py'),next(i for i,c in enumerate(calls) if c[0]=='pdflatex'))

    def test_renderer_failure_is_nonzero_not_cached_success(self):
        def command(args):
            if 'figures/draw_evaluation.py' in args:raise RuntimeError('renderer dependency/data failed')
            return ''
        with patch.object(self.build.shutil,'which',return_value='tool'),patch.object(self.build,'command',side_effect=command),patch.object(self.build,'verify',return_value={'status':'PASS'}):
            with self.assertRaisesRegex(RuntimeError,'renderer dependency/data failed'):
                self.build.main_run()
        self.assertEqual('FAIL',json.loads(self.build.REPORT.read_text())['status'])

if __name__=='__main__':unittest.main()
