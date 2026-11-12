"""Timing pilot, BASE mix only (results already public), with an early parity check. Prototype, not the final code. See RULES.md.

Run from the repo root: py -3.11 -m study.severity_mix.pilot_timing 500
"""
import sys, time, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from study.sim import charts, dgm, shipped
SEED=20261104; LAM=charts.LAMBDA
W=dgm.WEIGHT_SCHEMES; P1=dgm.PHASE1_DAYS
def fit_of(sc,w):
    return charts.true_fit(sc,w)
def params(sc,idx):
    mean=float(sc.mu0*dgm.PI0[idx].sum()); var=mean+(0 if np.isinf(sc.theta) else mean**2/sc.theta)
    return mean,float(np.sqrt(var*LAM/(2-LAM)))
ALL=np.arange(9); EI=np.arange(4,9)
def c7stat(sc,c):
    best=None
    for g in (ALL,EI):
        m,s=params(sc,g); z=(charts.ewma_paths(c[...,g].sum(axis=-1).astype(float),LAM,m)-m)/s
        best=z if best is None else np.maximum(best,z)
    return best
def limits(sc,idx):
    t={}
    for wn,which in (("squared",("M2","M4","M5","M7")),("linear",("M2","M4","M5")),("harm_only",("M4",))):
        f=fit_of(sc,W[wn]); r=np.random.default_rng(np.random.SeedSequence(SEED,spawn_key=(idx,10**9)))
        t[wn]=(f,charts.thresholds(f,W[wn],r,which,reps=1000))
    r=np.random.default_rng(np.random.SeedSequence(SEED,spawn_key=(idx,10**9+7)))
    lev=r.multinomial(dgm.draw_n(r,np.full((1000,1000),sc.mu0),sc.theta),dgm.PI0)
    mei,_=params(sc,EI)
    t["C4"]=charts.calibrate_threshold(charts.ewma_paths(lev[...,4:].sum(axis=-1).astype(float),LAM,mei))
    t["C5"]=charts.calibrate_threshold(charts.ewma_paths(lev.sum(axis=-1).astype(float),LAM,sc.mu0))
    t["C7"]=charts.calibrate_threshold(c7stat(sc,lev))
    return t
def first(a): return P1+1+int(a.argmax()) if a.any() else 0
def evaluate(sc,counts,t):
    c=counts[P1:]; n=c.sum(axis=1); ne=c[:,4:].sum(axis=1); out={}
    for wn,(f,th) in ((k,t[k]) for k in ("squared","linear","harm_only")):
        x=c@W[wn]
        for m,a in charts.alarms(th,f,x,n,ne).items():
            if m=="M7": out["M7|none"]=first(a)
            else: out[f"{m}|{wn}"]=first(a)
    mei,_=params(sc,EI)
    out["C4|none"]=first(charts.ewma_paths(ne.astype(float),LAM,mei)>t["C4"])
    out["C5|none"]=first(charts.ewma_paths(n.astype(float),LAM,sc.mu0)>t["C5"])
    out["C7|none"]=first(c7stat(sc,c)>t["C7"])
    return out
def task(a):
    sid,n,two=a
    sc=dgm.BY_ID[sid]; idx=dgm.SCENARIO_INDEX[sid]
    t0=time.perf_counter(); t=limits(sc,idx); t1=time.perf_counter()
    rows=[]
    for r in range(n):
        d,_=dgm.scenario_rngs(SEED,idx,r); counts=dgm.simulate_stream(sc,d)
        e=evaluate(sc,counts,t)
        if two: evaluate(sc,counts,t)
        x=counts@W["squared"]; st=shipped.status(x,counts.sum(axis=1),(2.0,))[2.0][P1:]
        e["M1a_out|squared"]=first(st==shipped.OUTSIDE); e["M1a_any|squared"]=first(st>=shipped.MARGINAL)
        rows+=[(sid,r,*k.split("|"),v) for k,v in e.items()]
    return rows,dict(sid=sid,n=n,two=two,pool=round(t1-t0,1),reps=round(time.perf_counter()-t1,1))
if __name__=="__main__":
    n=int(sys.argv[1])
    tasks=[("IC5",n,False),("IC5",n,True),("S2",n,False),("S2",n,True),("SEV",n,False),("SEV",n,True),("REP",n,False),("REP",n,True),("IC5",n,True),("S2",n,True)]
    t0=time.perf_counter(); rows=[];tm=[]
    with ProcessPoolExecutor(10) as ex:
        for r,m in ex.map(task,tasks):
            print(m,flush=True); tm.append(m)
            if not m["two"]: rows+=r
    print("wall",round(time.perf_counter()-t0,1))
    d=pd.DataFrame(rows,columns=["scenario","rep","method","weights","first"])
    R="study"
    bad=0;tot=0
    def chk(path,mask,label):
        global bad,tot
        o=pd.read_csv(path,usecols=["scenario","weights","rep","method","first_alarm"])
        o=o[(o.rep<n)&o.scenario.isin(["IC5","S2","SEV","REP"])]
        s=d[mask]; j=s.merge(o,on=["scenario","rep","method"] if label!="w" else ["scenario","rep","method","weights"],how="left")
        print(label,len(j),"missing",j.first_alarm.isna().sum(),"mismatch",(j["first"]!=j.first_alarm).sum())
    chk(R+r"\larger_run\output\weights_replicates.csv",d.method.isin(["M2","M4","M5"])|d.method.str.startswith("M1a"),"w")
    chk(R+r"\larger_run\output\replicates.csv",d.method=="M7","m7")
    chk(R+r"\category_test\output\replicates.csv",d.method.isin(["C4","C5"]),"c45")
    chk(R+r"\category_test\output_pairs\replicates.csv",d.method=="C7","c7")
