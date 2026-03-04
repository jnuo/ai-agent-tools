"""GA4 reporting via Google Analytics Data API."""

from .auth import get_ga4_credentials


def run_report(
    property_id: str,
    dimensions: list[str],
    metrics: list[str],
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 10000,
) -> dict:
    """Run a GA4 report.

    Args:
        property_id: GA4 property ID (e.g., '506362940')
        dimensions: List of dimension names (e.g., ['date', 'sessionSource'])
        metrics: List of metric names (e.g., ['sessions', 'activeUsers'])
        start_date: Start date ('YYYY-MM-DD' or relative like '90daysAgo')
        end_date: End date ('YYYY-MM-DD' or relative like 'yesterday')
        limit: Max rows to return

    Returns:
        dict with 'rows' key containing list of dicts with 'dimension_values' and 'metric_values',
        plus 'row_count', 'dimensions', and 'metrics' metadata
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )

    creds = get_ga4_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        limit=limit,
    )

    response = client.run_report(request)

    rows = []
    for row in response.rows:
        rows.append({
            "dimension_values": [dv.value for dv in row.dimension_values],
            "metric_values": [mv.value for mv in row.metric_values],
        })

    return {
        "rows": rows,
        "row_count": response.row_count,
        "dimensions": dimensions,
        "metrics": metrics,
    }
