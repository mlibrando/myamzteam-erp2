# Amazon Ads API (ads-v1) — Reporting Overview

> Source: official Amazon Ads advanced tools center (advertising.amazon.com/API/docs). Copied verbatim for offline/repo use.

Overview
The new Amazon Ads reporting API is an ad-hoc programmatic interface to access Amazon Ads performance data. Part of the Amazon Ads v1, the new reporting API follows the common model. Compared to the V3 API, the new reporting API offers the following features:

Multi-dimensional Reporting: Report types are no longer available or required as they were in the V3 API. Customers can now combine dimensions that were previously only available in separate reports (e.g., Geo x Technology). This improved data flexibility allows customers to combine dimensions to get customized insights for business needs.
Cross-Ad Product Reporting: Create reports that span different ad products and campaign types, providing a consolidated view of overall advertising performance that remains consistent as ad products evolve.
Cross-Account Reporting: For customers managing multiple ad accounts, generate a single report that spans across all the accounts you have access to and generate a unified performance view.
Additionally, this release reflects a major update to Amazon Ads reporting in response to customer feedback, with updated standardization of metric names, definitions, and entity terminology across all ad products, simplifying cross-program reporting and unifying measurement for a more consistent customer experience.

 Note
While underlying measurement logic remains unchanged, the alignment of metrics across products may affect backward compatibility. DSP integrations should be reviewed carefully, as several metrics now use broader standardized definitions (for example, metric.detailPageViews and metric.purchases now include both promoted and halo conversions) and may return higher totals than in Version 3.
What has changed in the new Reporting API
Standardized terminology for core entities
Terminology for key system objects is now consistent across DSP and Sponsored Ads.

DSP (V3 API)	Sponsored Ads (V3 API)	New Reporting API
Order	Campaign	Campaign
Ad line / Line item	Ad group	Ad group
Creative	Ad	Ad
Click-throughs	Clicks	Clicks
Reporting on traffic date
All conversion metrics are now reported on "traffic date," meaning conversions are reported on the date of the ad interaction rather than the date the conversion occurred. Previously, DSP reported conversions on the conversion date.

Example: If a shopper clicked an ad on Oct 1 and purchased on Oct 3, the purchase conversion is now reported on Oct 1 (i.e. date of ad interaction). Previously, the purchase conversion would have been reported on Oct 3 (i.e. date of conversion).

This update aligns DSP with Sponsored Ads, following industry best practices and improving the interpretability of rate metrics such as ROAS and Purchase rate, ensuring they represent outcomes relative to the traffic that generated them. You may observe higher conversion volumes earlier in campaign flight as DSP now reports conversions on the traffic date. Metric categorization Metrics are now clearly categorized as Traffic, Engagement, and Conversion metrics to improve discoverability and consistency across ad products:

Traffic metrics measure ad delivery (e.g., metric.impressions, metric.viewableImpressions, metric.clicks, metric.totalCost).
Engagement metrics measure shopper interaction or interest in the ad itself (e.g., metric.videoFirstQuartile, metric.videoCompletions).
Conversion metrics measure attributed outcomes for supported conversion types (e.g., metric.purchases, metric.detailPageViews, metric.addToCart, metric.offAmazonLeads, etc.).
This categorization is reflected throughout the metrics library.

Updated naming conventions for conversion metrics
Conversion metrics now follow a unified structure. A base metric (e.g., metric.detailPageViews, metric.addToList, metric.purchases) represents all conversions of that type.

Qualified metrics include additional context for product relevance or traffic source:

metric.detailPageViews — All detail-page-view conversions
metric.detailPageViewsPromoted — Detail-page-view conversions for promoted products only
metric.detailPageViewsFromClicksPromoted — Detail-page-view conversions for promoted products, attributed to an ad click
metric.detailPageViewsFromViewsHalo — Detail-page-view conversions for products in the halo of the campaign (see next section), attributed to an ad view
metric.newToBrandDetailPageViewsFromClicksPromoted — Detail-page-view conversions for promoted products by shoppers who are new to the brand, attributed to an ad click
 Note
These naming changes do not affect measurement logic. Campaigns that do not measure view-through attribution (e.g., Sponsored Products or Sponsored Brands CPC) will continue to report 0 for conversions from views.
Promoted and halo qualifiers
All conversion metrics now include Promoted and Halo qualified versions, distinguishing conversions for explicitly promoted products from those for highly relevant ("Halo") products defined by the expansion rules of each campaign. Additionally, terms such as "Brand Halo" and "Other SKU" are now standardized as "Halo".

Removal of "Total" prefix in DSP metrics
The "Total" prefix previously used in DSP metrics has been deprecated. Base metrics (e.g., metric.purchases, metric.detailPageViews) now include all conversions—both promoted and halo.

DSP (V3 API)	New Reporting API	Definition
totalPurchases	metric.purchases	Includes all attributed purchases
purchases	metric.purchasesPromoted	Includes attributed purchases of directly promoted products
purchasesBrandHalo	metric.purchasesHalo	Includes attributed purchases of highly relevant (non-promoted) products
 Important
For DSP integrations, some metrics now represent broader definitions and may return different values from before. To report attribution for promoted products only, use metrics with the Promoted qualifier (e.g., instead of metric.purchases, metric.roas, and metric.newToBrandPurchases use metric.purchasesPromoted, metric.roasPromoted, and metric.newToBrandPurchasesPromoted).
Removal of interval suffixes (1d, 7d, 14d, 30d)
Conversion metrics no longer include a look-back interval in their names. The base metric (e.g., metric.purchases, metric.sales, metric.unitsSold, metric.roas) always reflects the correct look-back for the campaign type.

Sponsored Products: Base metrics automatically align with campaign defaults—7-day look-back for sellers and 14-day look-back for vendors—consistent with the advertising console and downloadable reports. For example, metric.roas now corresponds to roas7d (sellers) or roas14d (vendors).
Other campaign types: The standard look-back is 14 days, except for DSP campaigns using flexible look-back windows, where metrics reflect the advertiser-selected click and view windows.
Consistent labeling for off-Amazon conversions
All off-Amazon conversion metrics now include the prefix offAmazon (e.g., metric.offAmazonLeads, metric.offAmazonCheckouts). Previously, this qualifier appeared only when necessary to distinguish off-Amazon conversions from on-Amazon conversion types.

Simplified metric syntax and terminology
Some terms have been replaced with clearer, more intuitive names:

effectiveCostPerAddToList → metric.costPerAddToList
effectiveRatePerMille (eRPM) → metric.returnPerThousandImpressions
Less common acronyms have been expanded for readability (e.g., eCPATL → metric.costPerAddToList).

 Tip
When utilizing the new Reporting API, be sure to: (a) update metric mappings to reflect Version 1 names and definitions, (b) review DSP integrations in particular, as some metrics now represent broader or standardized definitions and may return different values than before, (c) validate that your reporting logic aligns with traffic-date attribution and the standardized look-back configuration
