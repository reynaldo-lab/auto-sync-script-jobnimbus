import pandas as pd

def convert_unix_smart(df, columns):
    import pandas as pd

    for col in columns:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: pd.to_datetime(x, unit="ms", errors="coerce")
                if pd.notnull(x) and isinstance(x, (int, float)) and x > 1e12
                else pd.to_datetime(x, unit="s", errors="coerce")
            )

            # ✅ Convert to string format (VERY IMPORTANT for Sheets)
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df

def clean_contacts(df):
    import pandas as pd

    # Ensure jnid
    if "jnid" not in df.columns:
        df["jnid"] = df["id"].astype(str)
    else:
        df["jnid"] = df["jnid"].astype(str)

    # Select columns
    columns_to_keep = [
        "jnid","display_name","first_name","last_name","company",
        "email","mobile_phone","home_phone","work_phone",
        "address_line1","address_line2","city","state_text","zip","country_name",
        "status","status_name","record_type","record_type_name",
        "is_active","is_lead","is_closed","customer",
        "source_name","tags","sales_rep_name","created_by_name",
        "date_created","date_updated","date_status_change","last_synced_at"
    ]

    columns_existing = [col for col in columns_to_keep if col in df.columns]
    df = df[columns_existing]

    # ============================
    # ✅ ADD THIS PART HERE
    # ============================
    date_columns = ["date_created", "date_updated", "date_status_change"]
    df = convert_unix_smart(df, date_columns)

    # ============================
    # Continue cleaning
    # ============================
    df = df.replace([float("inf"), float("-inf")], None)
    df = df.astype(object).where(pd.notnull(df), "")

    df = df.drop_duplicates(subset=["jnid"])

    return df


