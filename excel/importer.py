def load_excel(filename):
    import pandas as pd
    if filename.lower().endswith(".xls"):
        return pd.read_excel(filename, engine="xlrd")
    dataframe = pd.read_excel(filename)
    if "KUNDENNAME" not in dataframe.columns:
        raise ValueError("Die Excel-Datei enthält die erforderliche Spalte KUNDENNAME nicht.")
    return dataframe
