import pandas as pd
import ast
from cleaner_jobs import convert_all_date_columns


def get_first_id(x):
    try:
        if pd.isna(x):
            return None

        # If already list
        if isinstance(x, list):
            return x[0].get("id") if x else None

        # If string → convert
        x = str(x).replace("null", "None")
        data = ast.literal_eval(x)

        if isinstance(data, list) and len(data) > 0:
            return data[0].get("id")

        return None

    except:
        return None

def clean_material_orders(df):

    # =========================
    # Extract related ID
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
        "number",
        "status",
        "status_name",
        "date_created",
        "date_updated",
        "date_status_change",
        "date_materialorder",
        "total_line_item_cost",
        "total_line_item_price",
        "guid",
        "supplier.status",
        "supplier.delivery_time",
        "address.city",
        "address.state_text",
        "address.zip",
        "created_by_name",
        "sales_rep",
        "last_synced_at"
    ]

    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]

    # =========================
    # Convert dates
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