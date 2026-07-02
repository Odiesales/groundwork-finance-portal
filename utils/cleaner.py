import pandas as pd
import re

def clean_ar_data(df):

    df = df.copy()

    # Rule 1: Reporting Customer
    def reporting_customer(row):

        parent = str(row["Parent Customer/Project: Company Name"]).strip()

        if parent and parent.lower() != "nan":
            return parent

        customer = str(row["Customer"])

        # Remove CP/CW/CX account numbers
        customer = re.sub(r"^(CP|CW|CX)\d+\s*", "", customer)

        return customer

    df["Reporting Customer"] = df.apply(reporting_customer, axis=1)

    # Rule 2: Channel Cleanup
    mapping = {
        "Foodservice Direct": "Foodservice",
        "Foodservice Distributor": "Foodservice",
        "Grocery Direct": "Grocery",
        "Grocery Distributor": "Grocery",
    }

    if "Sales Channel: Name" in df.columns:
        df["Channel Clean"] = (
            df["Sales Channel: Name"]
            .replace(mapping)
            .fillna(df["Sales Channel: Name"])
        )

    return df