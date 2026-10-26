"""Benchmark, class composition, decomposition and constant-dollar series.

Inputs : DATA-01-oop-panel-2013-2024.csv, DATA-02-lis-enrollment-2013-2025.csv,
         DATA-04-alldrug-national-2013-2024.csv, DATA-05-cpi-u-annual-2013-2024.csv
Outputs: RESULTS-05-benchmark-2013-2024.csv, RESULTS-09-established-vs-newer-2013-2024.csv, RESULTS-06-class-contribution-2013-2024.csv,
         RESULTS-07-decomposition-2013-2024.csv, RESULTS-08-constant-dollar-2013-2024.csv
Run from the directory containing the deposit files.
"""
import itertools
import numpy as np
import pandas as pd

REPORTED = ["Statin (incl. combinations)", "Ezetimibe (alone)", "Fibrate", "Icosapent ethyl",
            "Niacin (Rx)", "Bempedoic acid", "PCSK9 monoclonal", "Inclisiran (siRNA)"]
NEWER = ["PCSK9 monoclonal", "Bempedoic acid", "Inclisiran (siRNA)"]

# Comparator classes by generic name (case-insensitive substring on Gnrc_Name).
COMPARATORS = {
    "Direct oral anticoagulants": ["apixaban", "rivaroxaban", "dabigatran", "edoxaban"],
    "P2Y12 inhibitors": ["clopidogrel", "prasugrel", "ticagrelor"],
    "SGLT2 inhibitors": ["empagliflozin", "dapagliflozin", "canagliflozin", "ertugliflozin"],
    "GLP-1 receptor agonists": ["semaglutide", "liraglutide", "dulaglutide", "exenatide", "tirzepatide"],
    "Insulins": ["insulin"],
}

panel = pd.read_csv("DATA-01-oop-panel-2013-2024.csv")
enroll = pd.read_csv("DATA-02-lis-enrollment-2013-2025.csv").set_index("year")
alld = pd.read_csv("DATA-04-alldrug-national-2013-2024.csv")
cpi = pd.read_csv("DATA-05-cpi-u-annual-2013-2024.csv").set_index("year")["cpi_u_annual_avg"]


def shares(df, label):
    g = df.groupby("year").agg(nonlis_oop=("NonLIS_Bene_Cst_Shr", "sum"),
                               lis_oop=("LIS_Bene_Cst_Shr", "sum"), fills=("Tot_30day_Fills", "sum"))
    g["group"] = label
    return g.reset_index()


rows = [shares(alld, "All Part D drugs")]
for label, names in COMPARATORS.items():
    mask = alld.Gnrc_Name.str.lower().apply(lambda s: any(n in s for n in names))
    rows.append(shares(alld[mask], label))
lip = panel[panel.agent_class.isin(REPORTED)].rename(
    columns={"nonlis_oop": "NonLIS_Bene_Cst_Shr", "lis_oop": "LIS_Bene_Cst_Shr", "fills": "Tot_30day_Fills"})
rows.append(shares(lip, "Lipid-lowering, 8 reported classes"))
bench = pd.concat(rows, ignore_index=True)
alld_rows = bench[bench.group == "All Part D drugs"].set_index("year")
lip_rows = bench[bench.group == "Lipid-lowering, 8 reported classes"].set_index("year")
other = (alld_rows[["nonlis_oop", "lis_oop", "fills"]] - lip_rows[["nonlis_oop", "lis_oop", "fills"]]).reset_index()
other["group"] = "All other Part D drugs"
bench = pd.concat([bench, other], ignore_index=True)
bench["share_nonlis_pct"] = 100 * bench.nonlis_oop / (bench.nonlis_oop + bench.lis_oop)
bench["pe_nonlis"] = bench.nonlis_oop / bench.year.map(enroll.no_lis)
bench["pe_lis"] = bench.lis_oop / bench.year.map(enroll.lis)
bench["ratio"] = bench.pe_nonlis / bench.pe_lis
bench.to_csv("RESULTS-05-benchmark-2013-2024.csv", index=False)

p8 = panel[panel.agent_class.isin(REPORTED)].copy()
tot = p8.groupby("year")[["nonlis_oop", "lis_oop"]].sum()
p8["share_of_nonlis_oop_pct"] = 100 * p8.nonlis_oop / p8.year.map(tot.nonlis_oop)
p8["share_of_total_oop_pct"] = 100 * (p8.nonlis_oop + p8.lis_oop) / p8.year.map(tot.sum(axis=1))
p8["newer_class"] = p8.agent_class.isin(NEWER)
p8[["year", "agent_class", "newer_class", "fills", "nonlis_oop", "lis_oop",
    "share_of_nonlis_oop_pct", "share_of_total_oop_pct"]].to_csv(
    "RESULTS-06-class-contribution-2013-2024.csv", index=False)


def decompose(base_year, end_year, rule="end"):
    """Symmetric Shapley decomposition of pooled beneficiary payments into
    total fills (F), class mix (m_c) and within-class payment per fill (p_c).
    See the imputation note below for classes absent in the base year."""
    sub = p8[p8.year.isin([base_year, end_year])]
    w = sub.pivot(index="agent_class", columns="year", values="fills").fillna(0.0)
    tot_oop = (sub.assign(oop=sub.nonlis_oop + sub.lis_oop)
               .pivot(index="agent_class", columns="year", values="oop").fillna(0.0))
    F = w.sum()
    m = w / F
    p = (tot_oop / w).replace([np.inf, np.nan], 0.0)
    # Classes with no base-year fills need a base-year price. Primary rule ("end"):
    # use the class's end-year price, so its entry is attributed entirely to class
    # mix and none to within-class price change. Sensitivity rule ("base_average"):
    # use the base-year average payment per fill across classes present.
    base_avg = float(tot_oop[base_year].sum() / w[base_year].sum())
    for c in p.index:
        if w.loc[c, base_year] == 0:
            p.loc[c, base_year] = p.loc[c, end_year] if rule == "end" else base_avg

    def value(fy, my, py):
        return float((F[fy] * m[my] * p[py]).sum())

    factors = ["F", "m", "p"]
    contrib = {f: 0.0 for f in factors}
    for order in itertools.permutations(factors):
        state = {f: base_year for f in factors}
        prev = value(state["F"], state["m"], state["p"])
        for f in order:
            state[f] = end_year
            cur = value(state["F"], state["m"], state["p"])
            contrib[f] += (cur - prev) / 6.0
            prev = cur
    total = value(end_year, end_year, end_year) - value(base_year, base_year, base_year)
    return pd.DataFrame({"period": f"{base_year}-{end_year}", "imputation_new_class_base_price": rule,
                         "factor": ["total_fills", "class_mix", "payment_per_fill_within_class"],
                         "contribution_usd": [contrib["F"], contrib["m"], contrib["p"]],
                         "total_change_usd": total})


dec = pd.concat([decompose(b, e, r) for r in ("end", "base_average")
                 for b, e in ((2013, 2024), (2013, 2023), (2023, 2024))], ignore_index=True)
dec.to_csv("RESULTS-07-decomposition-2013-2024.csv", index=False)

# Established-versus-newer identity (the manuscript's reported decomposition)
p8["oop"] = p8.nonlis_oop + p8.lis_oop
est = p8[~p8.newer_class].groupby("year").oop.sum()
newc = p8[p8.newer_class].groupby("year").oop.sum()
ident = pd.DataFrame({"quantity": ["established_change_2013_2024_usd", "newer_classes_2024_usd", "total_change_2013_2024_usd"],
                      "value": [est.loc[2024] - est.loc[2013], newc.loc[2024], p8.groupby("year").oop.sum().loc[2024] - p8.groupby("year").oop.sum().loc[2013]]})
ident.to_csv("RESULTS-09-established-vs-newer-2013-2024.csv", index=False)

defl = cpi.loc[2024] / cpi
cdoll = bench[bench.group.isin(["All Part D drugs", "All other Part D drugs", "Lipid-lowering, 8 reported classes"])].copy()
cdoll["deflator_to_2024"] = cdoll.year.map(defl)
cdoll["pe_nonlis_2024usd"] = cdoll.pe_nonlis * cdoll.deflator_to_2024
cdoll["pe_lis_2024usd"] = cdoll.pe_lis * cdoll.deflator_to_2024
cdoll.to_csv("RESULTS-08-constant-dollar-2013-2024.csv", index=False)

b24 = bench[bench.year == 2024].set_index("group")
print(f"all-drug unsubsidized share 2024: {b24.loc['All Part D drugs','share_nonlis_pct']:.1f}%")
print(f"all-other-drug unsubsidized share 2024: {b24.loc['All other Part D drugs','share_nonlis_pct']:.1f}%")
print(f"lipid 8-class share 2024: {b24.loc['Lipid-lowering, 8 reported classes','share_nonlis_pct']:.1f}%")
comp = b24.drop(["All Part D drugs", "All other Part D drugs", "Lipid-lowering, 8 reported classes"]).share_nonlis_pct
print(f"comparator range 2024: {comp.min():.1f}% to {comp.max():.1f}%")
l = cdoll[cdoll.group.str.startswith("Lipid")].set_index("year")
a = cdoll[cdoll.group == "All other Part D drugs"].set_index("year")
print(f"real decline 2013-2024, lipid unsubsidized: {100*(1-l.loc[2024,'pe_nonlis_2024usd']/l.loc[2013,'pe_nonlis_2024usd']):.1f}%")
print(f"real decline 2013-2024, all other drugs unsubsidized: {100*(1-a.loc[2024,'pe_nonlis_2024usd']/a.loc[2013,'pe_nonlis_2024usd']):.1f}%")
print(dec[(dec.period == "2013-2024") & (dec.imputation_new_class_base_price == "end")].round(0).to_string(index=False))
