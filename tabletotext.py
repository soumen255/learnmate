import os
import argparse
import pandas as pd
from groq import Groq

# ------------------------------------------------------------
# 1. Initialize Groq client (API key from env or direct input)
# ------------------------------------------------------------
def get_groq_client(api_key=None):
    if api_key is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            # Fallback to hardcoded (not recommended for production)
            api_key = "GROQ_API_KEY"
    return Groq(api_key=api_key)

# ------------------------------------------------------------
# 2. Convert DataFrame to narrative text
# ------------------------------------------------------------
def table_to_text(data: pd.DataFrame, tone: str = "professional", client=None) -> str:
    """
    Send a DataFrame to Groq and return a descriptive summary.
    """
    if client is None:
        client = get_groq_client()
    
    # Convert to markdown for clarity
    markdown_table = data.to_markdown(index=False)
    
    prompt = f"""
You are a senior data analyst. Transform the following table into a {tone} narrative summary.

Requirements:
- Highlight the key trends, patterns, or anomalies.
- Identify the highest and lowest values for numeric columns (if any).
- Provide a brief concluding insight or recommendation.

Table:
{markdown_table}

Summary:
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You convert tabular data into clear, insightful text."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error calling Groq API: {e}"

# ------------------------------------------------------------
# 3. Synthetic data generators (different table types)
# ------------------------------------------------------------
def generate_sales_data(rows=8):
    """Generate random sales records."""
    import numpy as np
    products = ["Laptop", "Mouse", "Keyboard", "Monitor", "Headset"]
    regions = ["North", "South", "East", "West"]
    np.random.seed(42)  # reproducible
    data = {
        "Product": np.random.choice(products, rows),
        "Region": np.random.choice(regions, rows),
        "Units_Sold": np.random.randint(10, 500, rows),
        "Price_USD": np.random.choice([250, 30, 80, 200, 60], rows),
        "Date": pd.date_range("2025-01-01", periods=rows, freq="D")
    }
    df = pd.DataFrame(data)
    df["Revenue"] = df["Units_Sold"] * df["Price_USD"]
    return df

def generate_hr_data(rows=6):
    """Generate employee performance data."""
    import numpy as np
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    depts = ["Engineering", "Sales", "HR", "Marketing"]
    np.random.seed(42)
    data = {
        "Employee": np.random.choice(names, rows, replace=False),
        "Department": np.random.choice(depts, rows),
        "Salary_K": np.random.randint(50, 150, rows),
        "Performance_Score": np.random.uniform(2.5, 5.0, rows).round(1),
        "Projects_Completed": np.random.randint(1, 12, rows)
    }
    return pd.DataFrame(data)

def generate_inventory_data(rows=7):
    """Generate inventory stock data."""
    import numpy as np
    items = ["Widget A", "Widget B", "Gadget C", "Gadget D", "Tool E"]
    np.random.seed(42)
    data = {
        "Item": np.random.choice(items, rows),
        "Stock_Level": np.random.randint(0, 500, rows),
        "Reorder_Threshold": np.random.randint(20, 100, rows),
        "Lead_Time_Days": np.random.randint(1, 14, rows),
        "Unit_Cost_USD": np.random.choice([5, 12, 25, 8, 45], rows)
    }
    return pd.DataFrame(data)

# ------------------------------------------------------------
# 4. Manual data entry helper
# ------------------------------------------------------------
def manual_data_entry():
    """Let user enter a small table row by row."""
    print("\n--- Manual Table Entry ---")
    print("Enter column names separated by commas (e.g., Name, Age, City):")
    cols = input("Columns: ").strip().split(",")
    cols = [c.strip() for c in cols]
    
    rows = []
    print("Enter data rows (values separated by commas). Type 'done' when finished.")
    while True:
        row_input = input(f"Row {len(rows)+1}: ")
        if row_input.lower() == "done":
            break
        values = [v.strip() for v in row_input.split(",")]
        if len(values) != len(cols):
            print(f"Expected {len(cols)} values, got {len(values)}. Try again.")
            continue
        rows.append(values)
    
    if not rows:
        print("No data entered. Using empty DataFrame.")
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

# ------------------------------------------------------------
# 5. Main CLI
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Convert tabular data to narrative text using Groq LLM.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", help="Path to CSV or Excel file")
    input_group.add_argument("--generate", choices=["sales", "hr", "inventory"], help="Generate synthetic data of given type")
    input_group.add_argument("--manual", action="store_true", help="Enter table manually")
    parser.add_argument("--rows", type=int, default=6, help="Number of rows for generated data (default 6)")
    parser.add_argument("--tone", default="professional", help="Tone of the narrative (e.g., professional, concise, casual)")
    parser.add_argument("--api-key", help="Groq API key (optional, falls back to env GROQ_API_KEY or hardcoded)")
    args = parser.parse_args()
    
    # Load data based on user choice
    if args.file:
        file_path = args.file
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        print(f"Loaded table from {file_path}: {df.shape[0]} rows, {df.shape[1]} columns")
    
    elif args.generate:
        if args.generate == "sales":
            df = generate_sales_data(args.rows)
        elif args.generate == "hr":
            df = generate_hr_data(args.rows)
        elif args.generate == "inventory":
            df = generate_inventory_data(args.rows)
        print(f"Generated {args.generate} data with {args.rows} rows:")
    
    elif args.manual:
        df = manual_data_entry()
        print(f"Manual table created: {df.shape[0]} rows, {df.shape[1]} columns")
    
    else:
        print("No input specified. Use --help for options.")
        return
    
    # Show the table
    print("\n--- Input Table ---")
    print(df.to_string(index=False))
    print("\n--- Generating Narrative ---")
    
    # Create Groq client
    client = get_groq_client(api_key=args.api_key)
    
    # Get narrative
    narrative = table_to_text(df, tone=args.tone, client=client)
    print("\n--- AI Narrative ---")
    print(narrative)

if __name__ == "__main__":
    main()l