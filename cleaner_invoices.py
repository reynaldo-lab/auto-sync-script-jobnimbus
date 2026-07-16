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


def clean_invoices(df):

    # =========================
    # Extract related job ID
    # =========================
    if "related" in df.columns:
        df["related_jnid"] = df["related"].apply(get_first_id)
    else:
        df["related_jnid"] = None

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
        "number",
        "status",
        "status_name",
        "record_type_name",
        "date_created",
        "date_updated",
        "date_status_change",
        "date_sent",
        "date_due",
        "date_paid",
        "created_by_name",
        "sales_rep",
        "subtotal",
        "tax",
        "total",
        "amount_paid",
        "balance",
        "parent_approved_estimate_total",
        "parent_approved_invoice_total",
        "parent_approved_invoice_due",
        "last_synced_at"
    ]

    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]

    # =========================
    # Convert dates (your shared utility)
    # =========================
    df = convert_all_date_columns(df)

    # =========================
    # Clean numeric fields (important for KPIs)
    # =========================
    numeric_cols = [
        "subtotal",
        "tax",
        "total",
        "amount_paid",
        "balance",
        "parent_approved_estimate_total",
        "parent_approved_invoice_total",
        "parent_approved_invoice_due"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # Payment status (VERY useful later)
    # =========================
    if "balance" in df.columns and "total" in df.columns:
        def get_payment_status(row):
            if pd.isna(row["balance"]):
                return "unknown"
            elif row["balance"] == 0:
                return "paid"
            elif row["balance"] < row["total"]:
                return "partial"
            else:
                return "unpaid"

        df["payment_status"] = df.apply(get_payment_status, axis=1)

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