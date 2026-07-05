# Amazon Ads API (ads-v1) — Reporting Helpful Concepts

> Source: official Amazon Ads advanced tools center (advertising.amazon.com/API/docs). Copied verbatim for offline/repo use.

Dimensions
Dimensions determine the aggregation level of your report data. They define how your data is grouped in each row of your report, allowing you to analyze performance at different levels of granularity. For example, common dimensions include:

campaign : Groups data by campaign
adGroup : Groups data by ad group
ad : Groups data by individual ad
placement : Groups data by placement
advertisedProduct : Groups data by the product that was featured in the ad
convertedProduct : Groups data by the product that was attributed
When you request a report with a specific dimension, each row will represent a unique value for that dimension, with all metrics aggregated accordingly.

For a complete list of dimensions, see our dimension library.

Time dimensions
In the new reporting API, time is treated as another dimension. Previously, you provided a timeUnit to control the temporal aggregation of the report. For instance, you would pass DAILY as the time unit if you wanted the report to group data based on the date. Now, if you want to group data based on the date, you need to include date.value as one of your requested fields. That will result in the report being aggregated on the date dimension. The mapping below explains the connection between the two APIs:

New Reporting API Field	Version 3 Reporting Time Unit
date.value	DAILY
day.value	N/A – new feature
week.value	WEEKLY
month.value	MONTHLY
year.value	N/A – new feature
hour.value	HOURLY
See the dimension library to learn more about the possible time dimensions.

Dimension fields
Every dimension has one or more associated fields. One of those fields is denoted as the primary key, and the value of that field uniquely identifies the dimension. For example, the primary key for campaign is campaign.id, and every campaign has a unique ID. Some dimensions also have additional attribute fields that provide additional context and detail for that dimension.

For example, the campaign dimension includes the following fields (and more):

campaign.id (Primary Key) : The unique identifier for the campaign
campaign.name : The display name of the campaign
campaign.budgetAmount : The budget allocated to the campaign
campaign.bidStrategy : The bidding strategy applied
campaign.startDate : When the campaign started
campaign.endDate : When the campaign is scheduled to end
 Note
If you want to include a dimension attribute in a report (e.g. campaign.name), you must also include the primary key (e.g. campaign.id).
Including dimension attributes in your report allows you to enrich your data with relevant metadata without changing the aggregation level. You can see all available attributes for each dimension in our dimension library.

Metric fields
Metrics are the quantifiable performance measurements in your report. They represent the numerical data you want to analyze, such as impressions, clicks, spend, and conversions. Metrics are aggregated and grouped according to the dimensions you request. For example, common metrics include:

metric.impressions : The number of times the ad was displayed.
metric.clicks : The number of times the ad was clicked.
metric.addToCart : The number of times a shopper added a product to their cart, attributed to an ad interaction.
metrics.sales : The sales from purchases attributed to an ad interaction.
Each metric is calculated based on the dimensional grain of your report, providing insights into performance at your chosen level of detail. For complete definitions and calculation methods for all available metrics, see our metrics library.

Compatibility and requirements
While the system is designed for flexibility and comprehensive reporting, not all dimensions and metrics can be used together. Some metrics are only meaningful at specific levels of detail based on how the underlying data is collected and aggregated.

For example:

The convertedProduct dimension is incompatible with the audienceSegment dimension
The audienceSegment dimension is incompatible with the supplySource dimension
The metric.userReach metric is incompatible with the postalCode dimension
Additionally, some fields cannot be used unless you also include another field.

For example:

The campaign.name field requires the campaign.id field
The metric.sales field requires the budgetCurrency.value field
The metric.convertedSales field requires the convertedCurrency.value field
When building your reports, it is important to verify that (a) your requested fields are compatible with one another and (b) required fields are included. You can check the compatibility and requirements for every field in our dimension library and metrics library.

If you attempt to create a report that misses one of those scenarios, you will be provided an error response with a detail message. The most common scenario you might encounter is incompatible fields. When that occurs, the error message will include additional information about what went wrong:

400004: field {FIELD_1} cannot be used along with fields: {FIELD_2}


In this scenario, you need to remove one of the conflicting fields to continue. Similarly, if you include a field without its required field, the error message will include an explanation:

400006: field {FIELD_1} cannot be used without also including fields: {FIELD_2}

Refer to our errors documentation for more information about the types of errors that might occur and how to handle them.

Accounts
The new reporting API is the first multi-account API available from Amazon Ads. Previously, when you generated a report, you could only utilize a single account. For most use-cases, identity operated at a specific marketplace account level and was passed to the API in the form of a profile via the Amazon-Advertising-API-Scope HTTP header. In the new reporting API, up to 5 accounts at the same time within the accessRequestedAccounts configuration. Additionally, the requested accounts can be a mixture of ADSP regional accounts, global accounts and manager accounts. As a result, a single report can now span hundreds of individual marketplace accounts, greatly expanding your ability to retrieve data while also reducing the number of API requests you have to manage.

Account Type	Key to Use
ADSP Regional Account	advertiserAccountId
Global Account	advertiserAccountId
Manager Account	managerAccountId
 Tip
If you want to understand how different accounts work, please refer to the Amazon Ads Well-Architected Framework.
Empty and null values
When a field has no value for a given row, the representation depends on the output format of your report.


CSV format
Fields without a value are represented as empty strings. In the CSV file, this appears as an empty cell between delimiters:
"campaign.id","campaign.name","metric.impressions"
"campaign_001","","1000"

In this example, campaign.name has no value and is represented as an empty quoted string ("").

JSON format
Fields without a value are represented as null in the JSON output:

{
  "campaign.id": "campaign_001",
  "campaign.name": null,
  "metric.impressions": 1000
}

Why a field might have no value
There are several reasons a field may appear empty or null in your report. Some possible reasons are:

Some dimensions (the whole dimension, not a specific attribute alone) and metrics are not applicable to the specific ad type or campaign type in that row. For example, a metric that only applies to video ads will have no value for display ad rows.
Some dimension attributes are nullable by nature. For example, an optional campaign setting that was never configured.
Data is not yet available due to processing timelines. Some metrics may take longer to finalize than others.
Access restrictions prevent the value from being included for your account.
A missing value does not imply zero. If a numeric metric has a measured value of zero, it will be explicitly reported as 0, not as an empty string or null.

Recommendations for handling empty values
When parsing report data, we recommend:

For CSV: treat empty strings as the absence of a value
For JSON: treat null values as the absence of a value