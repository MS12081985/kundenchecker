import pandas as pd


class CustomerService:
    def __init__(self):
        self.df = pd.DataFrame()

    def set_dataframe(self, dataframe):
        self.df = dataframe.copy()

    def get_all(self):
        return self.df

    def search(self, text):
        if self.df.empty:
            return self.df

        if not text.strip():
            return self.df

        text = text.lower()

        mask = self.df.astype(str).apply(
            lambda col: col.str.lower().str.contains(text, na=False)
        ).any(axis=1)

        return self.df[mask]