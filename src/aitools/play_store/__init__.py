"""Google Play — installs + store-listing performance via the Play reporting bucket.

Google Play exports monthly statistics CSVs to a Cloud Storage bucket
(pubsite_prod_<developerId>). This module reads them with a service account:
- installs           -> stats/installs/installs_<pkg>_YYYYMM_overview.csv
- store performance  -> stats/store_performance/store_performance_<pkg>_YYYYMM_country.csv
  (store listing visitors = Play's equivalent of "app-page views").

Reports are monthly files of daily rows, UTF-16 encoded, with a ~2-3 day lag.
"""

__all__ = ["auth", "reports"]
