#!/usr/bin/env python3
"""Replay the offline comparison using only histories, receipts and checkers."""
from collections import Counter
import hashlib
import gzip
import json
from pathlib import Path
import time
from analyze_continuation import verify_source_receipts, expected_rows
from src.model import key
from src.checker import Checker
from src.continuation_checker import ContinuationChecker
from src.corpus import build
from src.real_history import build_real_history
from recount_incremental import check_source_work

ROOT = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False)


def strict_json(data):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    return json.loads(data,object_pairs_hook=pairs)


def replay_report(stem, directory=None, *, trace_path=None, select=None):
    """Replay the exact complete report/trace pair; never trust an old PASS."""
    if not __debug__:
        raise ValueError('Replay assertions require Python without -O')
    directory=Path(directory) if directory is not None else ROOT/'results'
    report_bytes=(directory/f'{stem}.json').read_bytes()
    trace_bytes=Path(trace_path or directory/f'{stem}-trace.json.gz').read_bytes()
    report=strict_json(report_bytes)
    packet=strict_json(gzip.decompress(trace_bytes))
    if not packet['trials']:raise ValueError('empty comparison trace')
    if canonical(report)!=canonical(packet['report']):
        raise ValueError('report/trace content binding')
    if canonical(report['trials'])!=canonical([t['summary'] for t in packet['trials']]):
        raise ValueError('report/trial summary binding')
    indices=[i for i,t in enumerate(report['trials']) if select is None or select(t)]
    if not indices:raise ValueError('empty replay selection')
    fixture=build_real_history(ROOT,build(ROOT))
    counts=dict(verify({'trials':[packet['trials'][i] for i in indices]},fixture['payloads']))
    receipt={'result':'PASS','counts':counts,
             'input_trials':len(packet['trials']),'replayed_trial_indices':indices,
             'report_sha256':hashlib.sha256(report_bytes).hexdigest(),
             'trace_sha256':hashlib.sha256(trace_bytes).hexdigest(),
             'scope':'Complete report/trace content bound; fresh source/checker/oracle/phase-cost/refill/source-work replay of listed trial indices. Unselected trials and CPU/coordinator counters are not independently recounted.'}
    return report,receipt


def verify(packet, payloads):
    checked = Counter()
    for trial in packet['trials']:
        check_source_work(trial, payloads)
        checked['source_work_censuses'] += 1
        source, evidence, states, rank_cache = verify_source_receipts(trial, payloads)
        checked.update(source)
        oracle = Checker(payloads)
        checker = ContinuationChecker(payloads)
        owners = [[0, 1], [2, 3], [4, 5]]
        queries = {q['id']: q for q in trial['queries']}
        acquisition = len(queries)*3
        for ident in range(1, acquisition+1):
            entry = evidence[ident]
            query = entry['request']['query']
            checker.install_prefix(query, entry, owners, 0, entry['request']['length'])
        score_cache={}
        def exact_at(cut,query):
            # Reuse the independently reconstructed source states/ranks, not
            # producer results. Cache keys include shard, cut and full plan.
            rows=[]
            for shard in range(3):
                rows.extend(expected_rows(rank_cache,score_cache,states,oracle,shard,cut[shard],query['plan'])[:query['k']])
            return sorted(rows,key=key)[:query['k']]
        last = {q['id']: exact_at([0,0,0],q) for q in queries.values()}
        accepted = set()
        changes = 0
        for record in trial['records']:
            sequence = record['sequence']
            cut = record['result']['cut']
            if sequence not in accepted:
                for shard in range(3):
                    lo, hi = checker.frontiers[shard], cut[shard]
                    if lo == hi:
                        continue
                    matches = [e for e in evidence.values() if e['reply'].get('kind') == 'events'
                               and e['reply']['shard'] == shard and e['reply']['hi'] == hi
                               and e['reply']['lo'] == lo]
                    if len(matches) != 1:
                        raise AssertionError('unique feed receipt')
                    checker.accept_events(matches[0], owners, 0)
                accepted.add(sequence)
            query = queries[record['query']]
            result = record['result']
            checker.check_result(result, query, cut, 0, owners, evidence, result['repairs'])
            exact = exact_at(cut,query)
            oracle.check_rows(record['oracle'])
            changed = exact != last[query['id']]
            if record['oracle'] != exact or record['changed'] != changed:
                raise AssertionError('recorded oracle')
            if result['rows'] != exact or result['status'] != 'complete':
                raise AssertionError('policy correctness')
            changes += int(changed)
            last[query['id']] = exact
            checked['results'] += 1
        costs = Counter()
        returned_rows = Counter()
        messages = Counter()
        for ident, entry in evidence.items():
            phase = ('acquisition' if ident <= acquisition else
                     'feed' if entry['request']['op'] == 'events' else 'refill')
            # Independent canonical encoder, same declared wire format.
            for value in (entry['request'], entry['reply']):
                costs[phase] += len((json.dumps(value, sort_keys=True,
                    separators=(',', ':'))+'\n').encode())
                messages[phase] += 1
            returned_rows[phase] += len(entry['reply'].get('rows', []))
        summary = trial['summary']
        from result_metrics import integer
        for field in ('total_source_bytes','oracle_changes','refill_shards'):
            integer(summary[field],field)
        if type(summary['calls']) is not int or summary['calls'] != len(trial['records']):
            raise AssertionError('strict call denominator')
        for phase, recorded in summary['source_costs'].items():
            for field in ('bytes','messages','returned_rows'):
                integer(recorded.get(field,0),phase+'/'+field)
            if costs[phase] != recorded.get('bytes', 0) or messages[phase] != recorded.get('messages', 0):
                raise AssertionError('phase payload accounting')
            if returned_rows[phase] != recorded.get('returned_rows', 0):
                raise AssertionError('source row accounting')
        if sum(costs.values()) != summary['total_source_bytes'] or changes != summary['oracle_changes']:
            raise AssertionError('summary aggregation')
        refills = sum(len(r['result']['repairs']) for r in trial['records'])
        if refills != summary['refill_shards']:
            raise AssertionError('refill aggregation')
        checked['trials'] += 1
    return checked


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', action='store_true')
    parser.add_argument('--trace', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    stem = 'incremental-generated' if args.generated else 'incremental-comparison'
    trace = args.trace or ROOT/f'results/{stem}-trace.json.gz'
    _,result = replay_report(stem,trace.parent,trace_path=trace)
    result['wall_seconds']=time.monotonic()-started
    output = args.output or trace.parent/f'{stem}-replay-current.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
