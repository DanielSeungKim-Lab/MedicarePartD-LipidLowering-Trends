TRENDS IN LIPID-LOWERING DRUG PAYMENTS BY MEDICARE PART D LOW-INCOME SUBSIDY STATUS, 2013 TO 2024
Replication deposit

WHAT THIS IS
Data and code to reproduce every number reported in the manuscript,
its Table and its Figure. Results tables and the figure image are not
shipped; the code regenerates them.

RUN ORDER
  python CODE-00-build-data-files.py     (optional; needs data.cms.gov)
  python CODE-03-benchmark-and-decomposition.py
  python CODE-01-reproduce-results.py
  python CODE-02-make-figure.py

CODE-00 rebuilds DATA-01 to DATA-03 from the CMS public use files and compares
the result against the shipped copies, exiting non-zero on any difference. Run
it only to regenerate the inputs from source: the shipped DATA files are the
snapshot the manuscript analyses, and CMS revises posted files, so a later run
can legitimately differ. Pass --check to compare without overwriting.

CODE-03 computes the all-drug and comparator benchmarks, each class's share of
beneficiary payments by year, the change in pooled payments split into the 5 established classes and the 3
newer classes (RESULTS-09, the figure the manuscript reports), a symmetric Shapley
decomposition shown as a sensitivity analysis under two conventions for the
newer classes' undefined 2013 price (RESULTS-07), and the CPI-U constant-dollar
series, writing RESULTS-05 to RESULTS-09. The benchmark 'All other Part D
drugs' excludes the 8 studied classes. CODE-01 then recomputes every reported value from the
DATA files and those outputs and exits non-zero on any mismatch. It runs 46
checks with 0 failures.

CODE-02 writes FIGURE-01-composition-and-subsidy.png: payments per enrollee by
subsidy status in 2024 dollars on a logarithmic scale (A), payments per
unsubsidized enrollee in 2024 dollars for lipid-lowering versus all other Part D
drugs, indexed to 2013 (B), and each class's share of unsubsidized beneficiary
payments 2013 to 2024 (C). Panels are lettered in the order the text cites them.

FILES
  DATA-01-oop-panel-2013-2024.csv    class-by-year panel: 30-day fills,
                                     beneficiaries, gross spending, and
                                     beneficiary cost sharing split by
                                     low-income subsidy status
  DATA-02-lis-enrollment-2013-2025.csv  annual national Part D enrollment by
                                     subsidy status
  DATA-03-national-series-2013-2024.csv  national totals by year, all classes
  DATA-04-alldrug-national-2013-2024.csv  every national drug row, all Part D
                                     drugs, 2013 to 2024 (benchmark input)
  DATA-05-cpi-u-annual-2013-2024.csv  CPI-U annual averages, BLS series
                                     CUUR0000SA0, for constant dollars
  DATA-06-partb-inclisiran-2022-2024.csv  inclisiran (HCPCS J1306) in the CMS
                                     Part B Spending by Drug file, fee-for-
                                     service only, beside Part D totals
  CODE-00-build-data-files.py        rebuilds the DATA files from CMS
  CODE-01-reproduce-results.py       recomputes and checks reported values
  CODE-02-make-figure.py             draws the figure
  CODE-03-benchmark-and-decomposition.py  benchmarks, composition,
                                     decomposition, constant dollars
  DOC-01-README.txt                  this file
  DOC-02-data-dictionary.txt         column definitions

SCOPE
The manuscript reports 8 lipid-lowering drug classes. DATA-01 carries 11; the
3 additional classes (bile acid sequestrants, prescription omega-3 products
other than icosapent ethyl, and an ANGPTL3/MTP/antisense group) are present but
not reported, and every aggregate in CODE-01 filters to the reported 8.

STRUCTURAL LIMIT OF THE DATA
The public use files report beneficiary cost sharing separately for subsidized
and unsubsidized enrollees, but report fills, claims and beneficiary counts only
as totals. Out-of-pocket cost per fill or per year of therapy therefore cannot
be calculated for either group, which is why the manuscript reports spending per
enrollee by subsidy status instead.

REQUIREMENTS
Python 3.13 with pandas, numpy and matplotlib. CODE-00 additionally needs
network access to data.cms.gov.
