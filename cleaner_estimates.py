import ast
import pandas as pd

from cleaner_jobs import convert_all_date_columns

def get_first_id(x):
    try:
        if pd.isna(x):
            return None

        if isinstance(x, list):
            return x[0].get("id") if x else None

        x = str(x).replace("null", "None")
        data = ast.literal_eval(x)

        if isinstance(data, list) and len(data) > 0:
            return data[0].get("id")

        return None

    except:
        return None
    
def clean_estimates(df):

    # =========================
    # Extract related job ID
    # =========================
    df["related_jnid"] = df["related"].apply(get_first_id)

    # =========================
    # Ensure primary key
    # =========================
    if "jnid" not in df.columns:
        df["jnid"] = df["id"].astype(str)
    else:
        df["jnid"] = df["jnid"].astype(str)

    # =========================
    # Select important columns
    # =========================
    columns_to_keep = [
        "jnid",
        "related_jnid",
        "guid",
        "number",
        "status",
        "status_name",
        "signature_status",
        "record_type_name",
        "date_created",
        "date_updated",
        "date_estimate",
        "date_signed",
        "date_status_change",
        "created_by_name",
        "sales_rep_name",
        "subtotal",
        "tax",
        "cost",
        "margin",
        "total",
        "last_synced_at"
    ]

    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]

    # =========================
    # Convert ALL date columns
    # =========================
    df = convert_all_date_columns(df)

    # =========================
    # Clean NaN
    # =========================
    df = df.replace([float("inf"), float("-inf")], None)
    df = df.astype(object).where(pd.notnull(df), "")

    # # =========================
    # # Remove duplicates
    # # =========================
    # df = df.drop_duplicates(subset=["jnid"])

    return df