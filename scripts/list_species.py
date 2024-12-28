# /// script
# dependencies = [
#   "polars",
# ]
# ///

import polars as pl

# csv_file = "inputs/intake-form.csv"
csv_file = "inputs/previous_years_reports/DNR-2020.csv"

df = pl.read_csv(csv_file)

# Print all the unique values for the Species column
species = df["Species"].unique().to_list()
# species.sort()

for s in species:
    print(s)
