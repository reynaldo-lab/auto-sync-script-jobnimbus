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


def clean_tasks(df):

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
        "title",
        "date_start",
        "date_end",
        "date_created",
        "date_updated",
        "is_active",              # task name
        "is_completed",
        "hide_from_calendarview",
        "hide_from_tasklist",
        "is_archived",
        "created_by_name",
        "last_synced_at",

    ]

    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]

    # =========================
    # Convert dates
    # =========================
    df = convert_all_date_columns(df)

    # =========================
    # Task completion flag (🔥 useful KPI)
    # =========================
    if "date_completed" in df.columns:
        df["is_completed"] = df["date_completed"].apply(lambda x: 1 if pd.notnull(x) else 0)

    # =========================
    # Overdue flag (🔥 very useful)
    # =========================
    if "date_due" in df.columns and "date_completed" in df.columns:
        df["is_overdue"] = df.apply(
            lambda row: 1 if pd.notnull(row["date_due"]) and pd.isnull(row["date_completed"]) and row["date_due"] < pd.Timestamp.now()
            else 0,
            axis=1
        )

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