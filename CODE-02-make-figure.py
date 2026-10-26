"""
CODE-02-make-figure.py

Regenerates the manuscript figure from the deposited data.

Inputs : DATA-01, DATA-02, DATA-04 (all-drug benchmark) and DATA-05 (CPI-U)
Output : FIGURE-01-composition-and-subsidy.png

Panel A payments per enrollee by subsidy status in 2024 dollars; panel B payments per
unsubsidized enrollee in 2024 dollars for lipid-lowering versus all other Part D drugs
(2013 = 100); panel C each class's share of unsubsidized beneficiary payments 2013-2024.
Panels are lettered in the order the text cites them.
Run from the directory containing the deposit files.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

# Global style setup
META_GREY = "#8d9aa5"

def apply_figure_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.labelsize': 7,
        'xtick.labelsize': 6.5,
        'ytick.labelsize': 6.5,
    })

def set_frame(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def panel_letter(ax, letter):
    ax.text(0.0, 1.04, letter, transform=ax.transAxes, fontsize=13, fontweight='bold', va='bottom')

OP = pd.read_csv("DATA-01-oop-panel-2013-2024.csv")
LD = pd.read_csv("DATA-02-lis-enrollment-2013-2025.csv").sort_values("year")
e = LD[LD.year == 2024].iloc[0]

KEEP = ["PCSK9 monoclonal", "Inclisiran (siRNA)", "Bempedoic acid", "Icosapent ethyl",
        "Ezetimibe (alone)", "Statin (incl. combinations)", "Fibrate", "Niacin (Rx)"]
k = OP[(OP.year == 2024) & (OP.agent_class.isin(KEEP))].copy()
k["oop_per_nonlis_enrollee"] = k.nonlis_oop / e.no_lis
k["oop_per_lis_enrollee"] = k.lis_oop / e.lis
k["ratio_per_enrollee"] = k.oop_per_nonlis_enrollee / k.oop_per_lis_enrollee
k["annual"] = k.tot_oop_per_fill * 12
k["headroom"] = 2000 - k.annual

SHORT = {"PCSK9 monoclonal": "PCSK9 mAb", "Inclisiran (siRNA)": "Inclisiran",
         "Bempedoic acid": "Bempedoic acid", "Icosapent ethyl": "Icosapent ethyl",
         "Ezetimibe (alone)": "Ezetimibe", "Statin (incl. combinations)": "Statin",
         "Fibrate": "Fibrate", "Niacin (Rx)": "Niacin"}
NOVEL = {"PCSK9 monoclonal", "Inclisiran (siRNA)", "Bempedoic acid"}

# Build per-enrollee ratio trend
T = OP[OP.agent_class.isin(KEEP)].copy()
E = LD.set_index("year")
T = T[T.year.isin(E.index)]
T["r"] = (T.nonlis_oop / T.year.map(E.no_lis)) / (T.lis_oop / T.year.map(E.lis))
piv = T.pivot(index="year", columns="agent_class", values="r")
g = T.groupby("year").agg(n=("nonlis_oop", "sum"), l=("lis_oop", "sum"))
g["ratio"] = (g.n / E.no_lis) / (g.l / E.lis)
pk = piv["PCSK9 monoclonal"].dropna()

RED, BLU, GRY, LT = "#c0392b", "#1f4e79", META_GREY, "#dfe5ea"

apply_figure_style()
fig = plt.figure(figsize=(7.4, 6.4))
gs = fig.add_gridspec(2, 2, height_ratios=[0.96, 1.0], hspace=0.50, wspace=0.44)
axA = fig.add_subplot(gs[1, :])  # class composition, panel C
axB = fig.add_subplot(gs[0, 1])  # real-dollar index, panel B
axC = fig.add_subplot(gs[0, 0])  # per-enrollee trend by subsidy, panel A

# Panel A: each class's share of unsubsidized beneficiary payments, 2013-2024
ORDER_A = ["Statin (incl. combinations)", "Ezetimibe (alone)", "Fibrate", "Icosapent ethyl",
           "Niacin (Rx)", "PCSK9 monoclonal", "Bempedoic acid", "Inclisiran (siRNA)"]
COLOR_A = {"Statin (incl. combinations)": "#9ab4cc", "Ezetimibe (alone)": "#1f4e79",
           "Fibrate": "#5b7f9e", "Icosapent ethyl": "#dfe5ea", "Niacin (Rx)": "#8d9aa5",
           "PCSK9 monoclonal": "#c0392b", "Bempedoic acid": "#e8846f", "Inclisiran (siRNA)": "#7a1f14"}
LABEL_A = {"Statin (incl. combinations)": "#44586a", "Ezetimibe (alone)": "#1f4e79",
           "Fibrate": "#5b7f9e", "Icosapent ethyl": "#44586a", "Niacin (Rx)": "#44586a",
           "PCSK9 monoclonal": "#c0392b", "Bempedoic acid": "#c0392b", "Inclisiran (siRNA)": "#7a1f14"}
p8 = OP[OP.agent_class.isin(KEEP)]
tot_nl = p8.groupby("year").nonlis_oop.sum()
wide = (p8.pivot(index="year", columns="agent_class", values="nonlis_oop").fillna(0.0)
        .div(tot_nl, axis=0) * 100)[ORDER_A]
years_a = wide.index.values
stack = wide.values.T
axA.stackplot(years_a, stack, colors=[COLOR_A[c] for c in ORDER_A], linewidth=0.3, edgecolor="white")
cum = stack.cumsum(axis=0)
mid = cum[:, -1] - stack[:, -1] / 2.0
val = stack[:, -1]
MIN_GAP = 7.5
target = list(mid)
for i in range(1, len(target)):
    if target[i] - target[i - 1] < MIN_GAP:
        target[i] = target[i - 1] + MIN_GAP
excess = target[-1] - 100.0 + 1.5
if excess > 0:
    target = [t - excess for t in target]
    for i in range(len(target) - 2, -1, -1):
        if target[i + 1] - target[i] < MIN_GAP:
            target[i] = target[i + 1] - MIN_GAP
for i, c in enumerate(ORDER_A):
    axA.annotate(f"{SHORT[c]}  {val[i]:.1f}%", xy=(2024, mid[i]), xytext=(2024.35, target[i]),
                 textcoords="data", va="center", ha="left", fontsize=6.5, color=LABEL_A[c],
                 arrowprops=dict(arrowstyle="-", lw=0.5, color="#6b7a86", shrinkA=0, shrinkB=0, relpos=(0, 0.5)))
axA.set_xlim(2013, 2024 + 2.6)
axA.set_ylim(0, 100)
axA.set_xticks([2013, 2016, 2019, 2022, 2024])
axA.set_yticks([0, 25, 50, 75, 100])
axA.set_yticklabels(["0", "25", "50", "75", "100%"])
axA.set_ylabel("Share of out-of-pocket payments by\nenrollees without the subsidy", fontsize=7)
axA.set_xlabel("Year", fontsize=7)
axA.spines["left"].set_bounds(0, 100)
axA.spines["bottom"].set_bounds(2013, 2024)
set_frame(axA)
panel_letter(axA, "C")

# Panel B: payments per enrollee without the subsidy, 2024 dollars, lipid-lowering versus all other Part D drugs (2013 = 100)
CPI = pd.read_csv("DATA-05-cpi-u-annual-2013-2024.csv").set_index("year").cpi_u_annual_avg
DEFL = CPI.loc[2024] / CPI
ALL = pd.read_csv("DATA-04-alldrug-national-2013-2024.csv")
lip_nl = p8.groupby("year").nonlis_oop.sum()
oth_nl = ALL.groupby("year").NonLIS_Bene_Cst_Shr.sum() - lip_nl
NL = LD.set_index("year").no_lis.reindex(lip_nl.index)
lip_real = (lip_nl / NL * DEFL)
oth_real = (oth_nl / NL * DEFL)
lip_idx = 100 * lip_real / lip_real.loc[2013]
oth_idx = 100 * oth_real / oth_real.loc[2013]
axB.plot(oth_idx.index, oth_idx.values, "-o", ms=3.0, lw=2.0, color="#9ab4cc", zorder=2)
axB.plot(lip_idx.index, lip_idx.values, "-o", ms=3.0, lw=2.0, color="#1a1a1a", zorder=3)
axB.axhline(100, color="#6b7a86", lw=0.6, ls=(0, (3, 2)))
axB.annotate("All other Part D drugs", (2016.2, oth_idx.loc[2016]), xytext=(4, 6), textcoords="offset points",
             fontsize=6, color="#5b7f9e")
axB.annotate("Lipid-lowering, 8 classes", (2018, lip_idx.loc[2018]), xytext=(4, 7), textcoords="offset points",
             fontsize=6, color="#1a1a1a")
axB.annotate(f"{oth_idx.loc[2024]:.0f}", (2024, oth_idx.loc[2024]), xytext=(4, -2), textcoords="offset points",
             fontsize=6, color="#5b7f9e")
axB.annotate(f"{lip_idx.loc[2024]:.0f}", (2024, lip_idx.loc[2024]), xytext=(4, -2), textcoords="offset points",
             fontsize=6, color="#1a1a1a")
axB.set_xlim(2012.4, 2025.6)
axB.set_xticks([2013, 2017, 2021, 2024])
axB.set_ylim(0, 115)
axB.set_yticks([0, 25, 50, 75, 100])
axB.set_xlabel("Year", fontsize=7)
axB.set_ylabel("Payments per enrollee without the subsidy,\n2024 dollars (2013 = 100)", fontsize=7)
set_frame(axB)
panel_letter(axB, "B")

# Panel C: payments per enrollee by subsidy status, 2024 dollars, log scale
g["pe_nonlis"] = g.n / E.no_lis.reindex(g.index) * DEFL.reindex(g.index)
g["pe_lis"] = g.l / E.lis.reindex(g.index) * DEFL.reindex(g.index)
axC.plot(g.index, g.pe_nonlis, "-o", ms=3.2, lw=2.0, color="#1a1a1a", zorder=3)
axC.plot(g.index, g.pe_lis, "-o", ms=3.2, lw=2.0, color="#9ab4cc", zorder=2)
axC.annotate(f"Without subsidy, ${g.pe_nonlis.iloc[0]:,.2f} in 2013", (2013, g.pe_nonlis.iloc[0]), xytext=(3, 6),
             textcoords="offset points", fontsize=6, color="#1a1a1a")
axC.annotate(f"With subsidy, ${g.pe_lis.iloc[0]:,.2f} in 2013", (2013, g.pe_lis.iloc[0]), xytext=(3, 6),
             textcoords="offset points", fontsize=6, color="#5b7f9e")
for yr, col, cl in ((2024, "pe_nonlis", "#1a1a1a"), (2024, "pe_lis", "#5b7f9e")):
    axC.annotate(f"${g.loc[yr, col]:,.2f}", (yr, g.loc[yr, col]), xytext=(5, -2),
                 textcoords="offset points", fontsize=6, ha="left", va="center", color=cl)
axC.set_yscale("log")
axC.set_xlim(2012.4, 2025.4)
axC.set_xticks([2013, 2017, 2021, 2024])
axC.set_ylim(1.0, 120)
axC.set_yticks([1, 3, 10, 30, 100])
axC.yaxis.set_major_formatter(mpl.ticker.FixedFormatter(["$1", "$3", "$10", "$30", "$100"]))
axC.yaxis.set_minor_formatter(mpl.ticker.NullFormatter())
axC.set_xlabel("Year", fontsize=7)
axC.set_ylabel("Out-of-pocket dollars per enrollee,\n2024 dollars", fontsize=7)
set_frame(axC)
panel_letter(axC, "A")

fig.subplots_adjust(left=0.135, right=0.988, top=0.945, bottom=0.100)
fig.savefig("FIGURE-01-composition-and-subsidy.png", dpi=300)
