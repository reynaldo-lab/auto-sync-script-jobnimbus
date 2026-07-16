import pandas as pd

def convert_all_date_columns(df):
    import pandas as pd

    date_cols = [col for col in df.columns if "date" in col.lower()]

    for col in date_cols:
        df[col] = df[col].apply(
            lambda x: pd.to_datetime(x, unit="ms", errors="coerce")
            if pd.notnull(x) and isinstance(x, (int, float)) and x > 1e12
            else pd.to_datetime(x, unit="s", errors="coerce")
        )

        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


import pandas as pd

def convert_all_date_columns(df):
    date_cols = [col for col in df.columns if "date" in col.lower()]

    for col in date_cols:
        df[col] = df[col].apply(
            lambda x: pd.to_datetime(x, unit="ms", errors="coerce")
            if pd.notnull(x) and isinstance(x, (int, float)) and x > 1e12
            else pd.to_datetime(x, unit="s", errors="coerce")
        )
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


def clean_jobs(df):

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
        "jnid","contact_id","job_number","name",
        "status","status_name","record_type_name",
        "address_line1","city","state_text","zip",
        "sales_rep_name","created_by_name",
        "contract_amount","approved_estimate_total","invoice_total","last_synced_at"
    ]

    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols + [col for col in df.columns if "date" in col.lower()]]

    # =========================
    # Convert ALL date columns
    # =========================
    df = convert_all_date_columns(df)

    # =========================
    # Clean NaN (CRITICAL)
    # =========================
    df = df.replace([float("inf"), float("-inf")], None)
    df = df.astype(object).where(pd.notnull(df), "")

    # =========================
    # Remove duplicates
    # =========================
    df = df.drop_duplicates(subset=["jnid"])

    return df
