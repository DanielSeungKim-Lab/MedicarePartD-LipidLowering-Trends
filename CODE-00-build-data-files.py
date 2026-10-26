"""CODE-00-build-data-files.py

Builds DATA-01, DATA-02 and DATA-03 from the CMS public use files.

Run only to regenerate the inputs from source. The DATA files shipped with this
deposit are the snapshot the manuscript analyses; CMS revises posted files, so a
later run can legitimately differ from them. When a shipped copy is present this
script compares against it and reports any difference.

  python CODE-00-build-data-files.py            # write, then compare if present
  python CODE-00-build-data-files.py --check    # compare only, write nothing

Exits non-zero if a rebuilt file differs from a shipped copy.
Requires network access to data.cms.gov.
"""
import json, sys, urllib.request
import pandas as pd

CATALOG = "https://data.cms.gov/data.json"
API = "https://data.cms.gov/data-api/v1/dataset/{}/data?{}&size=5000&offset={}"
ENROLLMENT_ID = "d7fabe1e-d19b-4333-9eff-e80e0643f2fd"
PAGE = 5000

# Explicit generic-name to class map. Built by enumerating every distinct
# Gnrc_Name in the national rows that names a lipid-lowering molecule, then
# adjudicating each one. Pattern matching is unsafe here: "Imipenem/Cilastatin",
# "Nystatin" and "Pentostatin" all contain the substring "statin", the brand
# "Sandostatin" contains it too, and "Insulin Aspart (Niacinamide)" contains
# "niacin". Fixed-dose combinations go to the class of the agent that defines
# the regimen: statin-containing combinations to statins, bempedoic
# acid/ezetimibe to bempedoic acid.
STATIN = "Statin (incl. combinations)"
CLASS_MAP = {
    "Atorvastatin Calcium": STATIN, "Simvastatin": STATIN,
    "Rosuvastatin Calcium": STATIN, "Pravastatin Sodium": STATIN,
    "Lovastatin": STATIN, "Fluvastatin Sodium": STATIN,
    "Pitavastatin Calcium": STATIN, "Pitavastatin Magnesium": STATIN,
    "Amlodipine/Atorvastatin": STATIN,
    "Ezetimibe/Atorvastatin Calcium": STATIN,
    "Ezetimibe/Rosuvastatin Calcium": STATIN,
    "Ezetimibe/Simvastatin": STATIN,
    "Niacin/Lovastatin": STATIN, "Niacin/Simvastatin": STATIN,
    "Sitagliptin/Simvastatin": STATIN,
    "Alirocumab": "PCSK9 monoclonal", "Evolocumab": "PCSK9 monoclonal",
    "Inclisiran Sodium": "Inclisiran (siRNA)",
    "Bempedoic Acid": "Bempedoic acid", "Bempedoic Acid/Ezetimibe": "Bempedoic acid",
    "Icosapent Ethyl": "Icosapent ethyl",
    "Niacin": "Niacin (Rx)",
    "Ezetimibe": "Ezetimibe (alone)",
    "Fenofibrate": "Fibrate", "Fenofibrate Nanocrystallized": "Fibrate",
    "Fenofibrate,micronized": "Fibrate", "Fenofibric Acid": "Fibrate",
    "Fenofibric Acid (Choline)": "Fibrate", "Gemfibrozil": "Fibrate",
    "Cholestyramine": "Bile acid sequestrant",
    "Cholestyramine (With Sugar)": "Bile acid sequestrant",
    "Cholestyramine/Aspartame": "Bile acid sequestrant",
    "Colesevelam Hcl": "Bile acid sequestrant",
    "Colestipol Hcl": "Bile acid sequestrant",
    "Omega-3 Acid Ethyl Esters": "Prescription omega-3 (other)",
    "Evinacumab-Dgnb": "Other orphan (ANGPTL3/MTP/ASO)",
    "Lomitapide Mesylate": "Other orphan (ANGPTL3/MTP/ASO)",
    "Mipomersen Sodium": "Other orphan (ANGPTL3/MTP/ASO)",
}

# Names that match a lipid molecule as a substring but are not lipid-lowering
# agents. Listed so that an unrecognized name raises instead of being dropped.
NOT_LIPID = {
    "Imipenem/Cilastatin Sodium", "Imipenem/Cilastatin/Relebactam", "Pentostatin",
    "Nystatin", "Nystatin/Emollient Combo No.54", "Nystatin/Hydrocortisone/Diphen",
    "Nystatin/Tcn/Hc/Diphenhydramin", "Nystatin/Triamcin",
    "Nystatin/Triamcinolone Acet", "Octreotide Acetate",
    "Octreotide Acetate,mi-Spheres", "Insulin Aspart (Niacinamide)",
    "M-Tetrahyrofolate/Niacin/Cu/Zn", "Omega-3s/Dha/Epa/Fish Oil",
    "Phospserin/Omega-3/Dha/Epa", "Pnv Cmb 52/Iron/Fa/Omega-3/Dha",
    "Pnv No10/Iron Fum&p/Fa/Omega-3", "Pnv W-Ca No.37/Iron/Fa/Omega-3",
    "Pnv2/Iron B-G Suc-P/Fa/Omega-3",
}

# Working label grouping classes by cost per fill. Carried in DATA-01 for
# convenience; no reported value uses it.
TIER = {
    "PCSK9 monoclonal": "high", "Inclisiran (siRNA)": "high",
    "Bempedoic acid": "high", "Other orphan (ANGPTL3/MTP/ASO)": "high",
    "Icosapent ethyl": "mid", "Bile acid sequestrant": "mid",
    "Prescription omega-3 (other)": "mid",
    "Niacin (Rx)": "low", "Ezetimibe (alone)": "low",
    "Fibrate": "low", "Statin (incl. combinations)": "low",
}

MOLECULE = ("statin|ezetimibe|alirocumab|evolocumab|inclisiran|bempedoic|icosapent|"
            "niacin|fibrate|fibric|gemfibrozil|clofibrate|cholestyramine|colesevelam|"
            "colestipol|omega-3|evinacumab|lomitapide|mipomersen")


def fetch(dataset_id, query):
    """All rows of one dataset matching a filter query, paged."""
    rows, offset = [], 0
    while True:
        url = API.format(dataset_id, query, offset)
        with urllib.request.urlopen(url, timeout=300) as response:
            page = json.loads(response.read().decode())
        if not page:
            break
        rows += page
        offset += PAGE
    return pd.DataFrame(rows)


def geography_dataset_ids():
    """Map year to dataset id for the Part D Prescribers by Geography and Drug files."""
    with urllib.request.urlopen(CATALOG, timeout=120) as response:
        catalog = json.loads(response.read().decode())
    import re
    ids = {}
    for entry in catalog.get("dataset", []):
        title = entry.get("title", "")
        if "Part D Prescribers - by Geography and Drug" not in title:
            continue
        year = re.search(r":\s*(\d{4})-\d\d-\d\d", title)
        uid = re.search(r"dataset/([0-9a-f-]{36})", entry.get("identifier", ""))
        if year and uid:
            ids[int(year.group(1))] = uid.group(1)
    if len(ids) != 12:
        sys.exit(f"expected 12 annual vintages in the CMS catalog, found {len(ids)}")
    return ids


def classify(frame):
    """Attach agent_class, raising if any candidate name is unadjudicated."""
    name = frame["Gnrc_Name"].str.strip()
    candidate = (name.str.contains(MOLECULE, case=False, na=False, regex=True) |
                 frame["Brnd_Name"].str.contains(MOLECULE, case=False, na=False, regex=True))
    unknown = set(name[candidate]) - set(CLASS_MAP) - NOT_LIPID
    if unknown:
        sys.exit("unadjudicated drug names, add them to CLASS_MAP or NOT_LIPID: "
                 + "; ".join(sorted(unknown)))
    frame = frame.copy()
    frame["agent_class"] = name.map(CLASS_MAP)
    return frame[frame["agent_class"].notna()]


def build_drug_panels():
    """DATA-01 and the drug side of DATA-03, from the twelve annual vintages."""
    numeric = ["Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes", "Tot_Clms",
               "Tot_Prscrbrs", "LIS_Bene_Cst_Shr", "NonLIS_Bene_Cst_Shr"]
    frames = []
    for year, dataset_id in sorted(geography_dataset_ids().items()):
        raw = fetch(dataset_id, "filter[Prscrbr_Geo_Lvl]=National")
        lipid = classify(raw)
        for column in numeric:
            lipid[column] = pd.to_numeric(lipid[column].replace("", pd.NA), errors="coerce")
        lipid["year"] = year
        frames.append(lipid)
        print(f"  {year}: {len(raw):>5} national rows, {len(lipid):>4} lipid-lowering")
    rows = pd.concat(frames, ignore_index=True)

    grouped = (rows.groupby(["year", "agent_class"], as_index=False)
               .agg(fills=("Tot_30day_Fills", "sum"), benes=("Tot_Benes", "sum"),
                    spend=("Tot_Drug_Cst", "sum"), claims=("Tot_Clms", "sum"),
                    prescribers=("Tot_Prscrbrs", "sum"),
                    lis_oop=("LIS_Bene_Cst_Shr", "sum"),
                    nonlis_oop=("NonLIS_Bene_Cst_Shr", "sum"))
               .sort_values(["agent_class", "year"], ignore_index=True))

    panel = grouped[["year", "agent_class", "fills", "benes", "spend",
                     "lis_oop", "nonlis_oop"]].copy()
    panel.insert(2, "tier", panel["agent_class"].map(TIER))
    total_oop = panel["lis_oop"] + panel["nonlis_oop"]
    # Both convenience columns are stored to 4 decimals in the shipped snapshot.
    panel["tot_oop_per_fill"] = (total_oop / panel["fills"]).round(4)
    panel["pct_oop_borne_by_nonLIS"] = (100 * panel["nonlis_oop"] / total_oop).round(4)
    return panel, grouped


def build_enrollment():
    """DATA-02 from the National rows, and the state-sum denominator DATA-03 uses.

    DATA-02 takes the National row. DATA-03 sums the state rows, which excludes a
    small residual CMS does not assign to a state, so the two differ by tens of
    beneficiaries. No reported value uses the DATA-03 denominator.
    """
    columns = ["YEAR", "PRSCRPTN_DRUG_TOT_BENES",
               "PRSCRPTN_DRUG_DEEMED_ELIGIBLE_FULL_LIS_BENES",
               "PRSCRPTN_DRUG_FULL_LIS_BENES", "PRSCRPTN_DRUG_PARTIAL_LIS_BENES",
               "PRSCRPTN_DRUG_NO_LIS_BENES"]

    national = fetch(ENROLLMENT_ID, "filter[BENE_GEO_LVL]=National&filter[MONTH]=Year")
    for column in columns:
        national[column] = pd.to_numeric(national[column], errors="coerce")
    enrollment = pd.DataFrame({
        "year": national["YEAR"].astype(int),
        "total": national["PRSCRPTN_DRUG_TOT_BENES"],
        "lis": (national["PRSCRPTN_DRUG_DEEMED_ELIGIBLE_FULL_LIS_BENES"]
                + national["PRSCRPTN_DRUG_FULL_LIS_BENES"]
                + national["PRSCRPTN_DRUG_PARTIAL_LIS_BENES"]),
        "no_lis": national["PRSCRPTN_DRUG_NO_LIS_BENES"],
    }).sort_values("year", ignore_index=True)
    enrollment["pct_no_lis"] = 100 * enrollment["no_lis"] / enrollment["total"]
    enrollment["pct_lis"] = 100 * enrollment["lis"] / enrollment["total"]

    state = fetch(ENROLLMENT_ID, "filter[BENE_GEO_LVL]=State&filter[MONTH]=Year")
    state["YEAR"] = pd.to_numeric(state["YEAR"])
    state["PRSCRPTN_DRUG_TOT_BENES"] = pd.to_numeric(
        state["PRSCRPTN_DRUG_TOT_BENES"], errors="coerce")
    state_sum = (state.groupby("YEAR")["PRSCRPTN_DRUG_TOT_BENES"].sum()
                 .rename("partd_enrollees").reset_index().rename(columns={"YEAR": "year"}))
    return enrollment, state_sum


def build_national_series(grouped, state_sum):
    """DATA-03: utilization context by class and year."""
    series = grouped.merge(state_sum, on="year", how="left")
    out = pd.DataFrame({
        "year": series["year"], "agent_class": series["agent_class"],
        "beneficiaries": series["benes"], "fills_30day": series["fills"],
        "claims": series["claims"], "gross_spending_usd": series["spend"],
        "gross_cost_per_30day_fill_usd": series["spend"] / series["fills"],
        "partd_enrollees": series["partd_enrollees"],
        "users_per_1000_enrollees": 1000 * series["benes"] / series["partd_enrollees"],
        "prescribers": series["claims"] * 0,
    })
    out["prescribers"] = series["prescribers"]
    return out.sort_values(["agent_class", "year"], ignore_index=True)


def compare(name, rebuilt):
    """Compare a rebuilt frame against a shipped copy, if one is present."""
    try:
        shipped = pd.read_csv(name)
    except FileNotFoundError:
        print(f"  {name}: no shipped copy to compare")
        return True
    if list(shipped.columns) != list(rebuilt.columns):
        print(f"  {name}: COLUMNS DIFFER\n    shipped {list(shipped.columns)}"
              f"\n    rebuilt {list(rebuilt.columns)}")
        return False
    if len(shipped) != len(rebuilt):
        print(f"  {name}: ROW COUNT DIFFERS, shipped {len(shipped)}, rebuilt {len(rebuilt)}")
        return False
    worst, ok = 0.0, True
    for column in shipped.columns:
        left, right = shipped[column], rebuilt[column].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
            gap = (left - right).abs().max()
            worst = max(worst, 0.0 if pd.isna(gap) else float(gap))
            if not pd.isna(gap) and gap > 1e-6:
                print(f"  {name}: {column} differs by up to {gap:g}")
                ok = False
        elif not left.astype(str).equals(right.astype(str)):
            print(f"  {name}: {column} differs")
            ok = False
    if ok:
        print(f"  {name}: matches shipped copy ({len(rebuilt)} rows, "
              f"largest numeric difference {worst:g})")
    return ok


def main():
    check_only = "--check" in sys.argv
    print("Part D Prescribers by Geography and Drug, national rows:")
    panel, grouped = build_drug_panels()
    print("Medicare Monthly Enrollment:")
    enrollment, state_sum = build_enrollment()
    print(f"  {len(enrollment)} years national, {len(state_sum)} years state-summed")
    series = build_national_series(grouped, state_sum)

    outputs = [("DATA-01-oop-panel-2013-2024.csv", panel),
               ("DATA-02-lis-enrollment-2013-2025.csv", enrollment),
               ("DATA-03-national-series-2013-2024.csv", series)]

    print("comparison against shipped copies:")
    agree = all(compare(name, frame) for name, frame in outputs)

    if not check_only:
        for name, frame in outputs:
            frame.to_csv(name, index=False)
        print("wrote DATA-01, DATA-02, DATA-03")

    if not agree:
        sys.exit("rebuilt files differ from the shipped snapshot; CMS may have "
                 "revised a posted file since it was extracted")
    print("all three files reproduce the shipped snapshot")


if __name__ == "__main__":
    main()
