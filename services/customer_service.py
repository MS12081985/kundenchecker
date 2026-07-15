import pandas as pd


class CustomerService:
    """
    Verwaltet die geladenen Kundendaten und stellt
    Suchfunktionen zur Verfügung.
    """

    def __init__(self):

        self.df = pd.DataFrame()

    def set_dataframe(
        self,
        dataframe: pd.DataFrame
    ):

        if dataframe is None:
            self.df = pd.DataFrame()
            return

        self.df = dataframe.copy()

    def get_dataframe(self):

        return self.df

    def is_empty(self):

        return self.df.empty

    def row_count(self):

        return len(self.df)

    def search(
        self,
        text: str
    ) -> pd.DataFrame:

        if self.df.empty:
            return self.df

        text = text.strip()

        if not text:
            return self.df

        text = text.lower()

        mask = self.df.astype(str).apply(

            lambda column:

                column
                .str.lower()
                .str.contains(
                    text,
                    na=False
                )

        ).any(axis=1)

        return self.df.loc[mask].reset_index(drop=True)

    def get_row(
        self,
        row: int
    ):

        if self.df.empty:
            return None

        if row < 0:
            return None

        if row >= len(self.df):
            return None

        return self.df.iloc[row]

    def get_company(
        self,
        row: int
    ) -> str:

        record = self.get_row(row)

        if record is None:
            return ""

        return str(
            record.get(
                "KUNDENNAME",
                ""
            )
        )

    def get_city(
        self,
        row: int
    ) -> str:

        record = self.get_row(row)

        if record is None:
            return ""

        return str(
            record.get(
                "CITY",
                ""
            )
        )