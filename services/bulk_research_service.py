from services.research_service import ResearchService


class BulkResearchService:
    """
    Führt eine Recherche über mehrere Firmen durch.
    Kann mit oder ohne GUI verwendet werden.
    """

    def __init__(self):
        self.research_service = ResearchService()
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def reset(self):
        self.cancelled = False

    def research_dataframe(
        self,
        dataframe,
        progress_callback=None,
        force_refresh: bool = False,
        error_callback=None,
    ):
        """
        Führt die Recherche für alle Firmen im DataFrame aus.

        progress_callback(
            current,
            total,
            company,
            result
        )
        """

        self.reset()

        results = []

        total = len(dataframe)

        for current, (_, row) in enumerate(
            dataframe.iterrows(),
            start=1
        ):

            if self.cancelled:
                break

            company = str(
                row.get("KUNDENNAME", "")
            ).strip()

            city = str(
                row.get("CITY", "")
            ).strip()

            if progress_callback:

                progress_callback(
                    current,
                    total,
                    company,
                    type(
                        "Progress",
                        (),
                        {"status": "Suche Website..."}
                    )()
                )

            try:
                result = self.research_service.research(
                    company,
                    city,
                    force_refresh=force_refresh,
                )
            except Exception as exc:
                if error_callback:
                    error_callback(current, total, company, city, str(exc))
                    continue
                raise

            results.append(result)

            if progress_callback:

                progress_callback(
                    current,
                    total,
                    company,
                    result
                )

            if self.cancelled:
                break

        return results
