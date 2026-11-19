"""Реальные воспроизводимые замеры лабораторных работ."""
from pathlib import Path
import sys
import os
import json
import time
import statistics
import tracemalloc
import subprocess
import asyncio
import ast
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
import platform

ROOT=Path(__file__).resolve().parent
for n in (13,14,15):
    sys.path.insert(0,str(ROOT/f'lab{n}'/'src'))
from analytics.core import is_prime, count_primes
from analytics.parallel import chunks
from analytics.images import transform
from analytics.async_io import load,sources,aggregate
from shop.legacy import process as imperative
from shop.pipeline import process as functional
from radon.raw import analyze
from radon.complexity import cc_visit
from radon.metrics import mi_visit

def timed(fn, repeats=3):
    times=[]
    for _ in range(repeats):
        t=time.perf_counter()
        value=fn()
        times.append(time.perf_counter()-t)
    return value,statistics.median(times)

def cpu_pool(values, workers, kind, size):
    executor=ThreadPoolExecutor if kind=='thread' else ProcessPoolExecutor
    with executor(max_workers=workers) as pool:
        return sum(pool.map(count_primes,chunks(values,size)))

def findings(source):
    result=[]
    tree=ast.parse(source)
    functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    mutating={'append','extend','insert','remove','pop','clear','sort','reverse','update','setdefault','add','discard'}
    io={'print','input','open','read_text','write_text','read_bytes','write_bytes'}
    for fn in functions:
        for node in ast.walk(fn):
            kind=None
            if isinstance(node,(ast.Global,ast.Nonlocal)):
                kind='global/nonlocal'
            if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                if any(isinstance(t,(ast.Attribute,ast.Subscript)) for t in targets):
                    kind='mutation'
            if isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
                if name in io: kind='IO'
                elif name in mutating: kind='mutation'
            if kind:
                result.append({'function':fn.name,'line':node.lineno,'kind':kind})
    impure={x['function'] for x in result}
    return {'functions':len(functions),'heuristically_pure':len(functions)-len(impure),
            'mutations':sum(x['kind'] in ('mutation','global/nonlocal') for x in result),
            'findings':result}

def metrics(paths):
    result=[]
    for path in paths:
        src=path.read_text(encoding='utf-8')
        blocks=cc_visit(src)
        raw=analyze(src)
        pure=findings(src)
        result.append({'file':path.name,'sloc':raw.sloc,'mi':mi_visit(src,True),
                       'cc':[(b.name,b.lineno,b.complexity) for b in blocks], **pure})
    return result

def main():
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from analytics import frames
    from schedule.libraries import builtin_pipeline, toolz_pipeline
    output={'machine':{'python':platform.python_version(),'platform':platform.platform(),
                       'cpu_count':os.cpu_count(),'processor':platform.processor(),
                       'repeats':3,'statistic':'median','process_startup_included':True}}
    values=tuple(1_000_000_001+2*i for i in range(3500))
    expected,seq=timed(lambda:count_primes(values))
    cpu=[]
    for kind in ('thread','process'):
        for workers in (1,2,4,8):
            value,seconds=timed(partial(cpu_pool,values,workers,kind,256))
            assert value==expected
            cpu.append({'kind':kind,'workers':workers,'seconds':seconds,'speedup':seq/seconds})
    tuning=[]
    for size in (1,64,256,1024):
        value,seconds=timed(partial(cpu_pool,values,4,'process',size))
        assert value==expected
        tuning.append({'size':size,'seconds':seconds})
    measured=[r for r in cpu if r['kind']=='process']
    def error(p):
        return sum((1/((1-p)+p/r['workers'])-r['speedup'])**2 for r in measured)
    p=min((i/10000 for i in range(10001)),key=error)
    try:
        with ProcessPoolExecutor(max_workers=1) as pool:
            list(pool.map(lambda x:is_prime(x),values[:1]))
    except Exception as exc:
        pickle_error=type(exc).__name__+': '+str(exc)
    with ProcessPoolExecutor(max_workers=1) as pool:
        assert list(pool.map(partial(is_prime),values[:3])) == list(map(is_prime,values[:3]))
    async_rows=[]
    for concurrent in (False,True):
        t=time.perf_counter(); result=asyncio.run(load(sources(),concurrent)); dt=time.perf_counter()-t
        async_rows.append({'concurrent':concurrent,'seconds':dt,'aggregate':aggregate(result)})
    assert async_rows[0]['aggregate']==async_rows[1]['aggregate']
    df=pd.DataFrame({'branch':[' A ','b','c','a']*5000,'qty':[1,2,-1,3]*5000,
                     'price':[100,200,50,300]*5000})
    original=df.copy(deep=True)
    result,df_seq=timed(lambda:frames.pipeline(df))
    other,df_par=timed(lambda:frames.parallel(df,4))
    pd.testing.assert_frame_equal(result,other)
    pd.testing.assert_frame_equal(df,original)
    image=tuple(tuple((i*17+j*31)%256 for j in range(180)) for i in range(180))
    images=[]
    for mode in ('blur','edges'):
        reference=None
        for workers in (1,2,4,8):
            value,dt=timed(lambda:transform(image,mode,workers))
            if reference is None: reference=value
            assert value==reference
            images.append({'mode':mode,'workers':workers,'seconds':dt,'checksum':sum(map(sum,value))})
    output['lab13']={'cpu_rows':len(values),'prime_count':expected,'sequential':seq,'cpu':cpu,
                     'tuning':tuning,'p':p,'fit_error':error(p),'pickle_error':pickle_error,
                     'async':async_rows,'frame_rows':len(df),'frame_seq':df_seq,'frame_parallel':df_par,
                     'frame_result':result.to_dict(orient='records'),'images':images}
    fig,ax=plt.subplots(figsize=(7,3.8))
    for kind,label in [('thread','Потоки'),('process','Процессы')]:
        rows=[r for r in cpu if r['kind']==kind]
        ax.plot([r['workers'] for r in rows],[r['speedup'] for r in rows],'o-',label=label)
    ns=[1,2,4,8]
    ax.plot(ns,[1/((1-p)+p/n) for n in ns],'--',label=f'Амдал p={p:.4f}')
    ax.set(xlabel='Рабочие',ylabel='Ускорение Tпосл / Tпул',xticks=ns)
    ax.legend(); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(ROOT/'lab13'/'speedup.png',dpi=160); plt.close(fig)
    values14=tuple(range(-1000,2000))
    a,ta=timed(lambda:builtin_pipeline(values14),100)
    b,tb=timed(lambda:toolz_pipeline(values14),100)
    assert a==b
    output['lab14']={'builtin_seconds':ta,'toolz_seconds':tb,'values':len(values14),
                     'counterexamples':{'median':[0,1],'chunks':{'xs':[0],'n':1},'rle':'0'}}
    perf=[]
    for size in (10,1000,20000):
        events=[{'op':'add','sku':str(i%50),'price':1000,'qty':1} for i in range(size)]
        assert imperative(events)==functional(events)
        for name,fn in [('imperative',imperative),('functional',functional)]:
            value,dt=timed(partial(fn,events))
            tracemalloc.start()
            fn(events)
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            perf.append({'size':size,'version':name,'seconds':dt,'peak_bytes':peak})
    package=ROOT/'lab15/src/shop'
    before=metrics([package/'legacy.py'])
    after=metrics([package/name for name in ('model.py','core.py','discounts.py','pricing.py','pipeline.py','shell.py')])
    output['lab15']={'before':before,'after':after,'performance':perf}
    for metric,ylabel in [('seconds','Время, с'),('peak_bytes','Пиковая память, байт')]:
        fig,ax=plt.subplots(figsize=(7,3.8))
        for version,label in [('imperative','Императивная'),('functional','Функциональная')]:
            rows=[r for r in perf if r['version']==version]
            ax.plot([r['size'] for r in rows],[r[metric] for r in rows],'o-',label=label)
        ax.set(xscale='log',yscale='log',xlabel='Количество действий',ylabel=ylabel)
        ax.legend();ax.grid(alpha=.2);fig.tight_layout()
        fig.savefig(ROOT/'lab15'/f'{metric}.png',dpi=160);plt.close(fig)
    (ROOT/'measurements.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
