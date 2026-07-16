from services.research_service import ResearchService
from models.address_utils import COUNTRY_COLUMNS, POSTAL_CODE_COLUMNS, STREET_COLUMNS, first_value
from inspect import Parameter, signature


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
        use_street_matching: bool = True,
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
            values = row.to_dict()
            street = first_value(values, STREET_COLUMNS)
            zipcode = first_value(values, POSTAL_CODE_COLUMNS)
            country = first_value(values, COUNTRY_COLUMNS)
            customer_id = next((values.get(name) for name in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID")
                                if name in values), None)

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
                research = self.research_service.research
                parameters = signature(research).parameters
                supports_kwargs = any(item.kind == Parameter.VAR_KEYWORD for item in parameters.values())
                supports_address = supports_kwargs or "street" in parameters
                kwargs = {"force_refresh": force_refresh}
                if supports_address:
                    kwargs.update(
                        street=street,
                        zipcode=zipcode,
                        country=country,
                        customer_id=customer_id,
                    )
                if supports_kwargs or "use_street_matching" in parameters:
                    kwargs["use_street_matching"] = use_street_matching
                result = research(company, city, **kwargs)
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
