"""Customer export selection and file writing without UI dependencies."""

from __future__ import annotations

from pathlib import Path
import math

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill


EXPORT_SCOPES = {
    "visible": None,
    "complete": {"vollständig"},
    "active": {"aktiv"},
    "contactable": {"vollständig", "aktiv"},
    "inactive": {"nicht aktiv"},
    "not_found": {"nicht gefunden"},
    "selected": None,
    "all_loaded": None,
}
STANDARD_COLUMNS = (
    "KUNDENNAME", "CITY", "PLZ", "POSTLEITZAHL", "STRASSE", "STREET",
    "LAND", "COUNTRY", "TELEFON", "EMAIL", "WEBSITE", "STATUS",
)
CRM_COLUMNS = (
    "ANSPRECHPARTNER", "POSITION", "DIREKTTELEFON", "DIREKTE_EMAIL",
    "KUNDENSTATUS", "PRIORITÄT", "TAGS", "NOTIZEN", "LETZTER_KONTAKT",
    "NÄCHSTE_WIEDERVORLAGE",
)


def normalize_status(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip().casefold()


class CustomerExportService:
    @staticmethod
    def select(dataframe, scope="visible", selected_keys=None):
        frame = dataframe.copy() if dataframe is not None else pd.DataFrame()
        if frame.empty:
            return frame
        if scope not in EXPORT_SCOPES:
            raise ValueError("Unbekannter Exportumfang")
        if scope == "selected":
            keys = {(str(name), str(city)) for name, city in (selected_keys or set())}
            if not keys:
                return frame.iloc[0:0].copy()
            mask = frame.apply(lambda row: (str(row.get("KUNDENNAME", "")), str(row.get("CITY", ""))) in keys, axis=1)
            return frame.loc[mask].reset_index(drop=True)
        statuses = EXPORT_SCOPES[scope]
        if statuses is not None:
            if "STATUS" not in frame.columns:
                return frame.iloc[0:0].copy()
            mask = frame["STATUS"].map(normalize_status).isin(statuses)
            return frame.loc[mask].reset_index(drop=True)
        return frame.reset_index(drop=True)

    @staticmethod
    def columns(dataframe, *, include_crm=True, include_technical=False):
        if include_technical:
            return dataframe.copy()
        allowed = list(STANDARD_COLUMNS) + (list(CRM_COLUMNS) if include_crm else [])
        return dataframe.loc[:, [column for column in allowed if column in dataframe.columns]].copy()

    @staticmethod
    def target_path(filename, export_format):
        path = Path(filename)
        expected = ".csv" if export_format == "csv" else ".xlsx"
        if path.suffix and path.suffix.lower() != expected:
            raise ValueError(f"Das gewählte Format benötigt die Dateiendung {expected}.")
        return path if path.suffix else path.with_suffix(expected)

    def write(self, dataframe, filename, export_format):
        path = self.target_path(filename, export_format)
        if path.suffix.lower() not in {".xlsx", ".csv"}:
            raise ValueError("Bitte wählen Sie eine .xlsx- oder .csv-Datei.")
        if path.suffix.lower() == ".csv":
            dataframe.to_csv(path, index=False, encoding="utf-8-sig")
            return path
        dataframe.to_excel(path, index=False, engine="openpyxl")
        workbook = load_workbook(path); sheet = workbook.active
        fill = PatternFill("solid", fgColor="2F5597")
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF"); cell.fill = fill
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            width = min(60, max(10, max(len(str(cell.value or "")) for cell in column) + 2))
            sheet.column_dimensions[column[0].column_letter].width = width
        workbook.save(path)
        return path
