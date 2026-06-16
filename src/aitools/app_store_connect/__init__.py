"""App Store Connect — downloads + product page views via the Analytics Reports API.

Apple exposes app downloads and store-listing engagement (impressions, product
page views) through the asynchronous Analytics Reports API: you create a report
request once, Apple generates report instances/segments (gzipped CSV), and you
download them. This module wraps that flow behind simple commands.
"""

__all__ = ["auth", "reports"]
