import os
import requests
import pandas as pd
import numpy as np
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from cleaner_contacts import clean_contacts
from cleaner_jobs import clean_jobs, convert_all_date_columns

# ======================
# CONFIG (FROM ENV)
# ======================
API_KEY = os.getenv("JOBNIMBUS_API_KEY")

if not API_KEY:
    raise ValueError("Missing API key")

API_KEY = API_KEY.strip()

headers = {
    "Authorization": f"Bearer {API_KEY}",   # 🔥 MUST BE BEARER
    "Content-Type": "application/json"
}

GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
SHEET_TAB_NAME = os.getenv("SHEET_TAB_NAME", "raw")

# Load credentials JSON from environment variable

GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

BASE_URL = "https://app.jobnimbus.com/api1"
#endpoint = "/contacts"

# ======================
# JOBNIMBUS FETCH
# ======================

def get_all_data(endpoint):
    all_data = []
    start = 0
    page_size = 1000
    MAX_RECORDS = 10000  # API limit

    while True:
        url = f"{BASE_URL}{endpoint}?from={start}&size={page_size}"
        response = requests.get(url, headers=headers)

        # =========================
        # Handle API errors safely
        # =========================
        if response.status_code != 200:
            print(f"❌ Error at offset {start}:", response.text)
            break

        try:
            data = response.json()
        except Exception:
            print("❌ Failed to parse JSON:", response.text)
            break

        results = data.get("results", [])

        # =========================
        # Stop if no more data
        # =========================
        if not isinstance(results, list) or not results:
            print("✅ No more data.")
            break

        all_data.extend(results)
        print(f"{endpoint}: Fetched {len(all_data)} records")

        start += page_size

        # =========================
        # 🔥 STOP at 10k limit
        # =========================
        if start >= MAX_RECORDS:
            print(f"⚠️ Reached API limit ({MAX_RECORDS}). Stopping.")
            break

    return all_data


# ======================
# GOOGLE SHEETS CONNECT
# ======================
def connect_sheets(worksheet_name):
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(os.getenv("GSHEET_ID"))

    try:
        sheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="50")

    return sheet

# ======================
# CLEAN DATA
# ======================
def clean_dataframe(df):
    df = df.replace([np.inf, -np.inf], "").fillna("")

    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
        )

    # ✅ ADD THIS LINE (applies to ALL datasets)
    df["last_synced_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    return df


# ======================
# SYNC SHEET
# ======================
def sync_sheet(df, sheet):
    existing_data = sheet.get_all_records()

    # FIRST RUN
    if not existing_data:
        sheet.update([df.columns.values.tolist()])
        sheet.append_rows(df.values.tolist())
        print("✅ Initial load complete")
        return

    existing_df = pd.DataFrame(existing_data)

    # Ensure types match
    df["jnid"] = df["jnid"].astype(str)
    existing_df["jnid"] = existing_df["jnid"].astype(str)

    # Create lookup for fast matching
    existing_lookup = {
        row["jnid"]: (idx, row)
        for idx, row in existing_df.iterrows()
    }

    updates = []
    new_rows = []

    for _, new_row in df.iterrows():
        jnid = new_row["jnid"]

        if jnid in existing_lookup:
            sheet_index, old_row = existing_lookup[jnid]

            # 👇 CHECK IF status_name CHANGED
            if str(old_row.get("status_name", "")) != str(new_row.get("status_name", "")):
                updates.append((sheet_index + 2, new_row))  # +2 for header + 1-index
        else:
            new_rows.append(new_row)

    print(f"🆕 New rows: {len(new_rows)}")
    print(f"🔄 Updates needed: {len(updates)}")

    # ======================
    # APPLY UPDATES
    # ======================
    for row_num, row_data in updates:
        sheet.update(
            f"A{row_num}",
            [row_data.values.tolist()]
        )

    # ======================
    # APPEND NEW
    # ======================
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        sheet.append_rows(new_df.values.tolist())

    print("✅ Sync complete")
    

def upload_new_only(df, sheet):

    existing_values = sheet.get_all_values()

    # ============================
    # 🔥 FIX: Detect truly empty OR broken sheet
    # ============================
    is_empty_sheet = (
        not existing_values or
        not any(any(cell.strip() for cell in row) for row in existing_values)
    )

    if is_empty_sheet:
        print("🆕 Initializing sheet with headers...")
        sheet.clear()
        sheet.append_row(df.columns.tolist())
        existing_df = pd.DataFrame()

    else:
        headers = existing_values[0]

        # 🔥 Stronger validation
        invalid_headers = (
            "" in headers or
            len(headers) != len(set(headers)) or
            all(h.strip() == "" for h in headers)
        )

        if invalid_headers:
            print("⚠️ Fixing broken headers...")
            sheet.clear()
            sheet.append_row(df.columns.tolist())
            existing_df = pd.DataFrame()
        else:
            existing_df = pd.DataFrame(existing_values[1:], columns=headers)

    # ============================
    # Ensure jnid exists in df
    # ============================
    if "jnid" not in df.columns:
        raise ValueError("❌ 'jnid' column missing in DataFrame")

    # ============================
    # Filter new rows
    # ============================
    if not existing_df.empty and "jnid" in existing_df.columns:
        new_rows = df[~df["jnid"].isin(existing_df["jnid"])]
    else:
        new_rows = df

    # ============================
    # Clean NaN / Inf
    # ============================
    new_rows = new_rows.replace([float("inf"), float("-inf")], None)
    new_rows = new_rows.astype(object).where(pd.notnull(new_rows), "")

    # ============================
    # Upload
    # ============================
    if not new_rows.empty:
        sheet.append_rows(new_rows.values.tolist())
        print(f"✅ Uploaded {len(new_rows)} new rows")
    else:
        print("✅ No new rows to upload")

# ======================
# MAIN
# ======================
def main():
    print("🚀 Starting JobNimbus sync...")

    # ======================
    # CONTACTS
    # ======================
    contacts = get_all_data("/contacts")

    if contacts:
        df_contacts = pd.json_normalize(contacts)
        #data cleaning 1
        df_contacts = clean_dataframe(df_contacts)
        #data cleaning 2
        df_contacts = clean_contacts(df_contacts)
        sheet_contacts = connect_sheets("contacts")
        upload_new_only(df_contacts, sheet_contacts)

    # ======================
    # JOBS
    # ======================
    jobs = get_all_data("/jobs")

    if jobs:
        df_jobs = pd.json_normalize(jobs)
        df_jobs = clean_dataframe(df_jobs)
        df_jobs = clean_jobs(df_jobs)   
        sheet_jobs = connect_sheets("jobs")  # 🔥 NEW TAB
        upload_new_only(df_jobs, sheet_jobs)

    print("✅ Done.")
    
    
    # ======================
    # estimates
    # ======================
    estimates = get_all_data("/estimates")

    if estimates:
        df_estimates = pd.json_normalize(estimates)
        df_estimates = clean_dataframe(df_estimates)
        df_estimates = convert_all_date_columns(df_estimates)

        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_estimates.columns:
            df_estimates["jnid"] = df_estimates["id"].astype(str)
        else:
            df_estimates["jnid"] = df_estimates["jnid"].astype(str)

        sheet_estimates = connect_sheets("estimates")  # new tab
        upload_new_only(df_estimates, sheet_estimates)
        
    
    # ======================
    # budgets
    # ======================
    budgets = get_all_data("/budgets")

    if budgets:
        df_budgets = pd.json_normalize(budgets)
        df_budgets = clean_dataframe(df_budgets)
        df_budgets = convert_all_date_columns(df_budgets)

        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_budgets.columns:
            df_budgets["jnid"] = df_budgets["id"].astype(str)
        else:
            df_budgets["jnid"] = df_budgets["jnid"].astype(str)

        sheet_budgets = connect_sheets("budgets")  # new tab
        upload_new_only(df_budgets, sheet_budgets)
        
    # ======================
    # tasks
    # ======================
    tasks = get_all_data("/tasks")

    if tasks:
        df_tasks = pd.json_normalize(tasks)
        df_tasks = clean_dataframe(df_tasks)
        df_tasks = convert_all_date_columns(df_tasks)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_tasks.columns:
            df_tasks["jnid"] = df_tasks["id"].astype(str)
        else:
            df_tasks["jnid"] = df_tasks["jnid"].astype(str)

        sheet_tasks = connect_sheets("tasks")  # new tab
        upload_new_only(df_tasks, sheet_tasks)

    # ======================
    # Products
    # ======================
    products = get_all_data("/v2/products")

    if products:
        df_products = pd.json_normalize(products)
        df_products = clean_dataframe(df_products)
        df_products = convert_all_date_columns(df_products)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_products.columns:
            df_products["jnid"] = df_products["id"].astype(str)
        else:
            df_products["jnid"] = df_products["jnid"].astype(str)

        sheet_products = connect_sheets("products")  # new tab
        upload_new_only(df_products, sheet_products)
    
    # ======================
    # Invoices
    # ======================
    invoices = get_all_data("/v2/invoices")

    if invoices:
        df_invoices = pd.json_normalize(invoices)
        df_invoices = clean_dataframe(df_invoices)
        df_invoices = convert_all_date_columns(df_invoices)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_invoices.columns:
            df_invoices["jnid"] = df_invoices["id"].astype(str)
        else:
            df_invoices["jnid"] = df_invoices["jnid"].astype(str)

        sheet_invoices = connect_sheets("invoices")  # new tab
        upload_new_only(df_invoices, sheet_invoices)
        
    # ======================
    # Payments
    # ======================
    payments = get_all_data("/payments")

    if payments:
        df_payments = pd.json_normalize(payments)
        df_payments = clean_dataframe(df_payments)
        df_payments = convert_all_date_columns(df_payments)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_payments.columns:
            df_payments["jnid"] = df_payments["id"].astype(str)
        else:
            df_payments["jnid"] = df_payments["jnid"].astype(str)

        sheet_payments = connect_sheets("payments")  # new tab
        upload_new_only(df_payments, sheet_payments)
    
    # ======================
    # Materials order
    # ======================
    materialsorder = get_all_data("/v2/materialorders")

    if materialsorder:
        df_materialsorder = pd.json_normalize(materialsorder)
        df_materialsorder = clean_dataframe(df_materialsorder)
        df_materialsorder = convert_all_date_columns(df_materialsorder)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_materialsorder.columns:
            df_materialsorder["jnid"] = df_materialsorder["id"].astype(str)
        else:
            df_materialsorder["jnid"] = df_materialsorder["jnid"].astype(str)

        sheet_materialsorder = connect_sheets("materialsorder")  # new tab
        upload_new_only(df_materialsorder, sheet_materialsorder)
        
    # ======================
    # Work order
    # ======================
    workorder = get_all_data("/v2/workorders")

    if workorder:
        df_workorder = pd.json_normalize(workorder)
        df_workorder = clean_dataframe(df_workorder)
        df_workorder = convert_all_date_columns(df_workorder)
        # 🔥 IMPORTANT: ensure unique ID
        if "jnid" not in df_workorder.columns:
            df_workorder["jnid"] = df_workorder["id"].astype(str)
        else:
            df_workorder["jnid"] = df_workorder["jnid"].astype(str)

        sheet_workorder = connect_sheets("workorders")  # new tab
        upload_new_only(df_workorder, sheet_workorder)
        

if __name__ == "__main__":
    main()