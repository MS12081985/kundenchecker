import pandas as pd

def load_excel(filename):
    if filename.lower().endswith(".xls"):
        return pd.read_excel(filename, engine="xlrd")
    return pd.read_excel(filename)