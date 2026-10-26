"""Recompute every value reported in the manuscript from the DATA files and CODE-03 outputs.

Exits non-zero if any reported value fails to reproduce. Prints one line per check.
"""
import sys
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

REPORTED = ["Statin (incl. combinations)", "Ezetimibe (alone)", "Fibrate", "Icosapent ethyl",
            "Niacin (Rx)", "Bempedoic acid", "PCSK9 monoclonal", "Inclisiran (siRNA)"]
ESTABLISHED = ["Statin (incl. combinations)", "Ezetimibe (alone)", "Fibrate",
               "Icosapent ethyl", "Niacin (Rx)"]
INTRODUCED = ["PCSK9 monoclonal", "Bempedoic acid", "Inclisiran (siRNA)"]
CAP = 2000.0


def r(x, places="1"):
    return float(Decimal(float(x)).quantize(Decimal(places), ROUND_HALF_UP))


def load():
    panel = pd.read_csv("DATA-01-oop-panel-2013-2024.csv")
    panel = panel[panel.agent_class.isin(REPORTED)].copy()
    enroll = pd.read_csv("DATA-02-lis-enrollment-2013-2025.csv").set_index("year")
    return panel, enroll


def per_enrollee(panel, enroll, year, classes):
    e = enroll.loc[year]
    s = panel[(panel.year == year) & (panel.agent_class.isin(classes))]
    return s.nonlis_oop.sum() / e.no_lis, s.lis_oop.sum() / e.lis


def main():
    panel, enroll = load()
    y24 = panel[panel.year == 2024].set_index("agent_class")
    e24 = enroll.loc[2024]
    annual = y24.tot_oop_per_fill * 12
    ratio24 = (y24.nonlis_oop / e24.no_lis) / (y24.lis_oop / e24.lis)
    share24 = y24.nonlis_oop / (y24.nonlis_oop + y24.lis_oop) * 100
    pk = panel[panel.agent_class == "PCSK9 monoclonal"].set_index("year")

    checks = []

    def ck(label, reported, computed, places="1"):
        checks.append((label, reported, r(computed, places), r(computed, places) == reported))

    # Results, paragraph 1
    ck("Total 30-day fills, 2024 (millions)", 374, panel[panel.year == 2024].fills.sum() / 1e6, "1")
    ck("Gross spending, 2024 ($ billions)", 5.4, panel[panel.year == 2024].spend.sum() / 1e9, "0.1")
    for cls, dollars in [("PCSK9 monoclonal", 61.40), ("Inclisiran (siRNA)", 49.85), ("Bempedoic acid", 47.34),
                         ("Statin (incl. combinations)", 1.08)]:
        ck(f"Pooled payment per 30-day fill, {cls} ($)", dollars, y24.loc[cls, "tot_oop_per_fill"], "0.01")
    pb = pd.read_csv("DATA-06-partb-inclisiran-2022-2024.csv").set_index("year")
    ck("Inclisiran Part B (FFS) spending, 2024 ($ millions)", 296, pb.loc[2024, "partb_total_spending"] / 1e6, "1")
    ck("Inclisiran Part B (FFS) to Part D spending ratio, 2024", 21, pb.loc[2024, "partb_total_spending"] / y24.loc["Inclisiran (siRNA)", "spend"], "1")

    # Results, paragraph 2
    ck("Unsubsidized enrollees, 2024 (millions)", 39.9, e24.no_lis / 1e6, "0.1")
    ck("All Part D enrollees, 2024 (millions)", 54.4, e24.total / 1e6, "0.1")
    ck("Unsubsidized share of enrollment (%)", 73.4, e24.no_lis / e24.total * 100, "0.1")
    ck("Unsubsidized share of beneficiary payments (%)", 97.0,
       y24.nonlis_oop.sum() / (y24.nonlis_oop.sum() + y24.lis_oop.sum()) * 100, "0.1")
    ck("Lowest class-specific payment share (%)", 95.5, share24.min(), "0.1")
    ck("Highest class-specific payment share (%)", 98.9, share24.max(), "0.1")
    ck("Spending per enrollee ratio, PCSK9 mAb", 31.2, ratio24["PCSK9 monoclonal"], "0.1")
    ck("Median spending per enrollee ratio across 8 classes", 14.7, ratio24.median(), "0.1")

    # Absolute trajectories, Figure C
    a13, b13 = per_enrollee(panel, enroll, 2013, REPORTED)
    a24, b24 = per_enrollee(panel, enroll, 2024, REPORTED)
    ck("Spending per unsubsidized enrollee, 2013 ($)", 49.59, a13, "0.01")
    ck("Spending per subsidized enrollee, 2013 ($)", 6.02, b13, "0.01")
    ck("Spending per unsubsidized enrollee, 2024 ($)", 19.30, a24, "0.01")
    ck("Spending per subsidized enrollee, 2024 ($)", 1.65, b24, "0.01")

    # Fixed-class sensitivity
    a24e, b24e = per_enrollee(panel, enroll, 2024, ESTABLISHED)
    ck("Spending per unsubsidized enrollee, 5 established classes, 2024 ($)", 12.46, a24e, "0.01")
    ck("Spending per subsidized enrollee, 5 established classes, 2024 ($)", 1.43, b24e, "0.01")

    # PCSK9 per-fill decline
    peak_year = int(pk.tot_oop_per_fill.idxmax())
    ck("PCSK9 mAb per-fill payment peak year", 2016, peak_year, "1")
    ck("PCSK9 mAb per-fill payment at peak ($)", 153.78, pk.loc[peak_year, "tot_oop_per_fill"], "0.01")
    ck("PCSK9 mAb per-fill payment, 2024 ($)", 61.40, pk.loc[2024, "tot_oop_per_fill"], "0.01")
    ck("PCSK9 mAb per-fill decline (%)", 60.1,
       (pk.loc[peak_year, "tot_oop_per_fill"] - pk.loc[2024, "tot_oop_per_fill"])
       / pk.loc[peak_year, "tot_oop_per_fill"] * 100, "0.1")

    # Discussion, concentration by class vintage
    ck("Lowest class-specific spending per enrollee ratio", 7.6, ratio24.min(), "0.1")
    ck("Highest class-specific spending per enrollee ratio", 31.2, ratio24.max(), "0.1")
    ck("Classes introduced since 2015, share of 2024 fills (%)", 1.2,
       y24.loc[INTRODUCED].fills.sum() / y24.fills.sum() * 100, "0.1")
    ck("Classes introduced since 2015, share of 2024 gross spending (%)", 45.3,
       y24.loc[INTRODUCED].spend.sum() / y24.spend.sum() * 100, "0.1")
    ck("Unsubsidized payment share, classes introduced since 2015 (%)", 98.8,
       y24.loc[INTRODUCED].nonlis_oop.sum()
       / (y24.loc[INTRODUCED].nonlis_oop.sum() + y24.loc[INTRODUCED].lis_oop.sum()) * 100, "0.1")
    ck("Unsubsidized payment share, 5 established classes (%)", 96.0,
       y24.loc[ESTABLISHED].nonlis_oop.sum()
       / (y24.loc[ESTABLISHED].nonlis_oop.sum() + y24.loc[ESTABLISHED].lis_oop.sum()) * 100, "0.1")

    # Table denominators quoted in the legend
    ck("Unsubsidized enrollment denominator", 39917452, e24.no_lis, "1")
    ck("Subsidized enrollment denominator", 14457747, e24.lis, "1")

    # Structural claim: every class exceeds parity in every year
    cy = panel.merge(enroll[["no_lis", "lis"]], left_on="year", right_index=True)
    cy = cy[cy.lis_oop > 0]
    cy["ratio"] = (cy.nonlis_oop / cy.no_lis) / (cy.lis_oop / cy.lis)
    ck("Class-years with ratio above parity", len(cy), (cy.ratio > 1).sum(), "1")


    # Benchmark, composition, decomposition and constant dollars (written by CODE-03)
    import os
    if os.path.exists("RESULTS-05-benchmark-2013-2024.csv"):
        bench = pd.read_csv("RESULTS-05-benchmark-2013-2024.csv")
        b24 = bench[bench.year == 2024].set_index("group")
        ck("All-other-drug unsubsidized payment share, 2024 (%)", 96.5, b24.loc["All other Part D drugs", "share_nonlis_pct"], "0.1")
        comp = b24.drop(["All Part D drugs", "All other Part D drugs", "Lipid-lowering, 8 reported classes"]).share_nonlis_pct
        ck("Lowest comparator payment share, 2024 (%)", 94.7, comp.min(), "0.1")
        ck("Highest comparator payment share, 2024 (%)", 98.4, comp.max(), "0.1")
        cc = pd.read_csv("RESULTS-06-class-contribution-2013-2024.csv")
        c24 = cc[cc.year == 2024].set_index("agent_class")
        ck("PCSK9 mAb share of unsubsidized lipid payments, 2024 (%)", 33.1, c24.loc["PCSK9 monoclonal", "share_of_nonlis_oop_pct"], "0.1")
        ck("PCSK9 mAb share of unsubsidized lipid payments, 2015, below 0.1%", True, bool(cc[(cc.year == 2015) & (cc.agent_class == "PCSK9 monoclonal")].share_of_nonlis_oop_pct.iloc[0] < 0.1), "1")
        ck("PCSK9 mAb share of newer-class pooled payments, 2024 (%)", 93.4, 100 * (c24.loc["PCSK9 monoclonal", "nonlis_oop"] + c24.loc["PCSK9 monoclonal", "lis_oop"]) / (c24[c24.newer_class].nonlis_oop.sum() + c24[c24.newer_class].lis_oop.sum()), "0.1")
        ck("Newer 3 classes share of total beneficiary payments, 2024 (%)", 34.8, c24[c24.newer_class].share_of_total_oop_pct.sum(), "0.1")
        ident = pd.read_csv("RESULTS-09-established-vs-newer-2013-2024.csv").set_index("quantity").value / 1e6
        ck("Pooled payments, 5 established classes, change 2013-2024 ($ millions)", -753, ident["established_change_2013_2024_usd"], "1")
        ck("Pooled payments, 3 newer classes, 2024 ($ millions)", 276, ident["newer_classes_2024_usd"], "1")
        cd = pd.read_csv("RESULTS-08-constant-dollar-2013-2024.csv")
        l = cd[cd.group.str.startswith("Lipid")].set_index("year"); a = cd[cd.group == "All other Part D drugs"].set_index("year")
        ck("Real decline in unsubsidized lipid payments per enrollee, 2013-2024 (%)", 71.1, 100 * (1 - l.loc[2024, "pe_nonlis_2024usd"] / l.loc[2013, "pe_nonlis_2024usd"]), "0.1")
        ck("Real decline in unsubsidized all-other-drug payments per enrollee, 2013-2024 (%)", 33.6, 100 * (1 - a.loc[2024, "pe_nonlis_2024usd"] / a.loc[2013, "pe_nonlis_2024usd"]), "0.1")
    else:
        print("note: run CODE-03 first to check the benchmark and decomposition values")

    width = max(len(c[0]) for c in checks)
    failures = 0
    for label, reported, computed, ok in checks:
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  {label:<{width}}  reported={reported}  computed={computed}")
    print(f"\n{len(checks)} checks, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
