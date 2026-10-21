"""Reconstruct paper-facing counts from retained records, not summary means."""
from collections import Counter
import gzip
import json
import math
from pathlib import Path

POLICIES=('continuation','overlay','cut-cache','mirror','unsafe-stale')
COUNTS=('exact','claimed_complete','false_complete','unsound_rows','returned_rows')

def integer(value, where):
    if type(value) is not int or value < 0:
        raise ValueError('metric nonnegative integer required: '+where)
    return value

def equal(actual, expected, where):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError('metric mismatch: '+where)

def mean(actual, total, n, where):
    if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,total/n,rel_tol=1e-12,abs_tol=1e-9):
        raise ValueError('metric mean/total/denominator mismatch: '+where)

def load_trace(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        return json.load(stream)

def trace_metrics(trace, policies=POLICIES, real=False):
    """Sum raw per-query costs plus charged acquisition and shared feed phases."""
    n=len(trace['records'])
    if not n:raise ValueError('metric empty trace')
    counts={p:Counter() for p in policies}
    costs={p:Counter(bytes=0,messages=0) for p in policies}
    def add(policy, record):
        for k in ('bytes','messages'):
            costs[policy][k]+=integer(record[k],policy+'/'+k)
    for record in trace['records']:
        if set(record['observations']) != set(policies):
            raise ValueError('metric policy inventory')
        for policy in policies:
            obs=record['observations'][policy]
            add(policy,obs['metrics'])
            for k in COUNTS:
                value=obs['metrics'][k]
                if k in ('exact','claimed_complete','false_complete') and type(value) is bool:
                    value=int(value)
                counts[policy][k]+=integer(value,policy+'/'+k)
            equal(integer(obs['metrics']['returned_rows'],'returned_rows'),len(obs['response']['rows']),'returned rows')
    setup=Counter();feed=Counter(bytes=0,messages=0)
    if real:
        add('continuation',trace['setup']['cost'])
        for row in trace['timeline']:
            for k in ('bytes','messages'):feed[k]+=integer(row['feed'][k],'feed/'+k)
        recorded=trace['policy_costs']
    else:
        for row in trace['setup']:
            if row['kind'] not in ('continuation-acquisition','mirror-snapshot'):
                raise ValueError('metric setup kind')
            policy='continuation' if row['kind']=='continuation-acquisition' else 'mirror'
            add(policy,row['cost'])
            setup[row['kind']]+=integer(row['cost']['bytes'],'setup bytes')
        for row in trace['timeline']:
            for k in ('bytes','messages'):feed[k]+=integer(row['feed_cost'][k],'feed/'+k)
        add('mirror',feed)
        recorded=trace['policy_totals']
    add('continuation',feed)
    for policy in policies:
        for k in ('bytes','messages'):
            equal(integer(recorded[policy][k],policy+'/'+k),costs[policy][k],'trace '+policy+'/'+k)
    return n,counts,costs,setup,feed

def check_summary(summary, n, counts, costs):
    if not n:raise ValueError('metric empty denominator')
    if set(summary['policies'])!=set(costs):raise ValueError('metric policy inventory')
    for policy,total in costs.items():
        row=summary['policies'][policy]
        equal(integer(row['queries'],policy+'/queries'),n,policy+'/queries')
        for k in COUNTS:equal(integer(row[k],policy+'/'+k),counts[policy][k],policy+'/'+k)
        equal(integer(row['partial_or_unjustified'],'partial'),n-counts[policy]['claimed_complete'],'partial')
        for metric,field in [('bytes','source_bytes'),('messages','source_messages')]:
            equal(integer(row['total_'+field],policy+'/total_'+field),total[metric],policy+'/total_'+field)
            mean(row['mean_'+field],total[metric],n,policy+'/mean_'+field)

def validate_primary(root, summary):
    from analyze_continuation import CASES, SEEDS
    root=Path(root);n=0;counts={p:Counter() for p in POLICIES};costs={p:Counter() for p in POLICIES}
    setup=Counter();feed=0;cases=[]
    equal(summary['cases'],list(CASES),'cases')
    equal(summary['seeds'],list(SEEDS),'seeds')
    for case in CASES:
        for seed in SEEDS:
            trace=load_trace(root/f'results/continuation-traces/continuation-{case}-seed{seed}-capacity5.json.gz')
            equal(trace['case'],case,'trace case');equal(trace['seed'],seed,'trace seed')
            q,c,t,a,f=trace_metrics(trace)
            n+=q;setup.update(a);feed+=f['bytes']
            row={'case':case,'seed':seed,'queries':q,
                 'repair_queries':sum(bool(r['observations']['continuation']['response'].get('repairs')) for r in trace['records']),
                 'repair_shards':sum(len(r['observations']['continuation']['response'].get('repairs',{})) for r in trace['records'])}
            for p in POLICIES:
                counts[p].update(c[p]);costs[p].update(t[p])
                row[p+'_exact']=c[p]['exact'];row[p+'_complete']=c[p]['claimed_complete']
                row[p+'_false_complete']=c[p]['false_complete'];row[p+'_unsound_rows']=c[p]['unsound_rows']
                row[p+'_mean_bytes']=t[p]['bytes']/q;row[p+'_mean_messages']=t[p]['messages']/q
            for p in ('continuation','cut-cache','mirror'):
                row[p+'_state_bytes']=integer(trace['peak_logical_state_bytes'][p],p+'/state')
            cases.append(row)
    equal(integer(summary['primary_queries'],'primary_queries'),n,'primary_queries')
    equal(integer(summary['primary_traces'],'primary_traces'),len(cases),'primary_traces')
    check_summary(summary,n,counts,costs)
    equal(summary['setup_source_bytes'],dict(setup),'setup_source_bytes')
    for k,v in setup.items():equal(integer(summary['setup_source_bytes'][k],k),v,k)
    equal(integer(summary['shared_feed_source_bytes'],'feed'),feed,'feed')
    for name,key in [('queries','repair_queries'),('shards','repair_shards')]:
        equal(integer(summary['continuation_repairs'][name],'repairs'),sum(r[key] for r in cases),'repairs/'+name)
    for p in ('continuation','cut-cache','mirror'):
        equal(integer(summary['policies'][p]['max_logical_state_bytes'],p+'/state'),
              max(r[p+'_state_bytes'] for r in cases),p+'/state')
    for baseline,field in [('overlay','communication_reduction_vs_overlay_percent'),
                            ('cut-cache','communication_reduction_vs_cut_cache_percent')]:
        mean(summary[field],100*(1-costs['continuation']['bytes']/costs[baseline]['bytes']),1,field)
    return cases

def validate_real(root, summary):
    policies=('continuation','overlay','cut-cache','unsafe-stale')
    trace=load_trace(Path(root)/'results/real-history-trace.json.gz')
    n,counts,costs,_,_=trace_metrics(trace,policies,real=True)
    check_summary(summary,n,counts,costs)
    equal(integer(summary['queries_per_policy'],'queries_per_policy'),n,'queries_per_policy')
    for baseline,field in [('overlay','communication_reduction_vs_overlay_percent'),
                            ('cut-cache','communication_reduction_vs_cut_cache_percent')]:
        mean(summary[field],100*(1-costs['continuation']['bytes']/costs[baseline]['bytes']),1,field)
    return n


def tradeoff_rows(summary):
    rows=[]
    for policy,label in [('continuation','Continuation'),('overlay','Overlay'),('cut-cache','Cut-cache'),('mirror','Mirror')]:
        row=summary['policies'][policy]
        rows.append({'policy':label,'bytes':f"{row['mean_source_bytes']:.4f}",
                     'state':f"{row['max_logical_state_bytes']/1024:.4f}" if policy!='overlay' else '0.001'})
    return rows
