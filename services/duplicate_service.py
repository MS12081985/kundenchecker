import pandas as pd
from rapidfuzz import fuzz


class DuplicateService:
    """
    Erkennt exakte und ähnliche Dubletten.
    """

    def __init__(self, dataframe: pd.DataFrame):

        if dataframe is None:
            dataframe = pd.DataFrame()

        self.df = dataframe.copy()

    def find_exact_duplicates(self) -> pd.DataFrame:
        """
        Exakte Dubletten anhand von Firmenname + Ort.
        """

        if self.df.empty:
            return pd.DataFrame()

        if "KUNDENNAME" not in self.df.columns:
            return pd.DataFrame()

        columns = ["KUNDENNAME"]

        if "CITY" in self.df.columns:
            columns.append("CITY")

        duplicates = self.df[
            self.df.duplicated(
                subset=columns,
                keep=False
            )
        ].copy()

        duplicates = duplicates.sort_values(
            by=columns
        )

        return duplicates.reset_index(drop=True)

    def find_similar_duplicates(
        self,
        threshold: int = 90
    ) -> pd.DataFrame:
        """
        Erkennt ähnliche Firmennamen.
        """

        if self.df.empty:
            return pd.DataFrame()

        if "KUNDENNAME" not in self.df.columns:
            return pd.DataFrame()

        matches = []

        names = (
            self.df["KUNDENNAME"]
            .fillna("")
            .astype(str)
            .tolist()
        )

        for i in range(len(names)):

            for j in range(i + 1, len(names)):

                score = fuzz.ratio(
                    names[i],
                    names[j]
                )

                if score >= threshold:

                    row1 = self.df.iloc[i].copy()
                    row2 = self.df.iloc[j].copy()

                    row1["MATCH"] = score
                    row2["MATCH"] = score

                    matches.append(row1)
                    matches.append(row2)

        if not matches:
            return pd.DataFrame()

        return pd.DataFrame(matches).reset_index(drop=True)

    def statistics(self):

        return {

            "rows": len(self.df),

            "exact_duplicates": len(
                self.find_exact_duplicates()
            ),

            "similar_duplicates": len(
                self.find_similar_duplicates()
            )

        }