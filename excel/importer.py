def load_excel(filename):
    import pandas as pd
    from models.address_utils import POSTAL_CODE_COLUMNS, normalize_postal_code
    converters = {column: normalize_postal_code for column in POSTAL_CODE_COLUMNS}
    if filename.lower().endswith(".xls"):
        engine = "xlrd"
    else:
        engine = "openpyxl"
    try:
        dataframe = pd.read_excel(filename, engine=engine, converters=converters)
    except TypeError as error:
        if "converters" not in str(error):
            raise
        dataframe = pd.read_excel(filename, engine=engine)
    for column in dataframe.columns:
        if str(column).upper() in POSTAL_CODE_COLUMNS:
            dataframe[column] = dataframe[column].map(normalize_postal_code)
    if "KUNDENNAME" not in dataframe.columns:
        raise ValueError("Die Excel-Datei enthält die erforderliche Spalte KUNDENNAME nicht.")
    if dataframe.empty:
        raise ValueError("Die Excel-Datei enthält keine Datenzeilen.")
    return dataframe
