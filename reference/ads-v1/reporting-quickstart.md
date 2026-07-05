# Amazon Ads API (ads-v1) — Reporting Quickstart

> Source: official Amazon Ads advanced tools center (advertising.amazon.com/API/docs). Copied verbatim for offline/repo use.

Quickstart guide
 Note
The below content assumes you already have a working developer account. For more details on how to set that up, see the Amazon Ads API onboarding overview as well as how to make your first API call.
Creating your first report
In Version 3 Reporting, you worked within report types. Each report type had a set of supported metrics, dimensions, and ad programs. So, you could generate a dspGeo report to get aggregated metrics per postal code, or you could generate a dspInventory report to get aggregated metrics per supply source. However, you did not have a way to combine all of that into one report. With the new reporting API, that is now possible.

Your focus now is on fields. Fields can be either metric fields (e.g. metric.impressions) or dimension fields (e.g. campaign.id). When you create a report, you simply have to specify which fields you want to include in the report, and the aggregation will occur on all of your specified dimensions:

POST /adsApi/v1/create/reports
curl -X POST https://advertising-api.amazon.com/adsApi/v1/create/reports \
  -H "Amazon-Advertising-API-ClientId: {YOUR_CLIENT_ID}" \
  -H "Authorization: {YOUR_ACCESS_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "accessRequestedAccounts": [
    {
      "advertiserAccountId": "{YOUR_ACCOUNT_ID}"
    }
  ],
  "reports": [
    {
      "format": "CSV",
      "periods": [
        {
          "datePeriod": {
            "startDate": "2025-10-28",
            "endDate": "2025-11-04"
          }
        }
      ],
      "query": {
        "fields": [
          "date.value",
          "campaign.id",
          "campaign.name",
          "postalCode.value",
          "supplySource.name",
          "metric.impressions"
        ]
      }
    }
  ]
}'

In the above example, the included dimensions are date, campaign, postalCode, and supplySource. The generated report will aggregate the desired metrics (e.g. metric.impressions) for each combination of your selected dimensions in a GROUP BY fashion.

For example, the report above represents an eight day period of time (A=8). Say there were two active campaigns during that period (B=2). Each campaign was flighted in 10 postal codes (C=10), on 20 supply sources (D=20). The number of rows in the report would be A * B * C * D = 3200, and each row would include the metric totals for the dimension combination.

When you submit your request, we will provide you with a report ID, along with other metadata, in the response:

{
  "error": null,
  "success": [
    {
      "index": 0,
      "report": {
        "creationDateTime": "2025-11-05T00:00:38.285Z",
        "format": "CSV",
        "lastUpdatedDateTime": "2025-11-05T00:00:38.285Z",
        "periods": [
          {
            "datePeriod": {
              "startDate": "2025-10-28",
              "endDate": "2025-11-04"
            }
          }
        ],
        "query": {
          "fields": [
            "date.value",
            "campaign.id",
            "campaign.name",
            "postalCode.value",
            "supplySource.name",
            "metric.impressions"
          ]
        },
        "reportId": "{YOUR_REPORT_ID}",
        "status": "PENDING"
      }
    }
  ]
}

Retrieving your report
When you first create your report, the status will be PENDING, and the generation will occur asynchronously. It will transition through different statuses as the generation executes:

Status	Meaning	Terminal
PENDING	The report is pending, check back later.	-
PROCESSING	The report is processing, check back later.	-
COMPLETED	The report generation completed, see the completedReportParts for download information.	Yes
FAILED	The report generation failed, see the failureCode and failureReason for more information.	Yes


You can check the status of your report at any time by retrieving the report. The recommended frequency is once per minute:

POST /adsApi/v1/retrieve/reports
curl -X POST https://advertising-api.amazon.com/adsApi/v1/retrieve/reports \
  -H "Amazon-Advertising-API-ClientId: {YOUR_CLIENT_ID}" \
  -H "Authorization: {YOUR_ACCESS_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "reportIds": [
    "{YOUR_REPORT_ID}"
  ]
}'

The response will include the current status. Eventually, the report will transition to a terminal status — either COMPLETED or FAILED. In the event of a report generation failure, the response includes information about the failure. See Handling errors for a full explanation of this flow.

When the report completes successfully, the response includes information about how to retrieve the report in the completedReportParts:

{
  "error": null,
  "success": [
    {
      "index": 0,
      "report": {
        "completedDateTime": "2025-11-05T00:12:50.443Z",
        "completedReportParts": [
          {
            "sizeInBytes": 1024000,
            "url": "{PRESIGNED_S3_URL}",
            "urlExpirationDateTime": "2025-11-05T00:12:50.443Z"
          }
        ],
        "creationDateTime": "2025-11-05T00:00:38.285Z",
        "format": "CSV",
        "lastUpdatedDateTime": "2025-11-05T00:00:38.285Z",
        "periods": [
          {
            "datePeriod": {
              "startDate": "2025-10-28",
              "endDate": "2025-11-04"
            }
          }
        ],
        "query": {
          "fields": [
            "dateRange.value",
            "metric.addToList",
            "budgetCurrency.value",
            "campaign.bidStrategy",
            "campaign.budgetAmount",
            "campaign.budgetType",
            "campaign.id",
            "campaign.name",
            "campaign.deliveryStatus",
            "metric.impressions"
          ]
        },
        "reportId": "{YOUR_REPORT_ID}",
        "status": "COMPLETED"
      }
    }
  ]
}

Each report part will include a pre-signed S3 URL, and you can then download the report using your mechanism of choice. For example, with curl:

curl -L "{PRESIGNED_S3_URL}" -o desired_filename.csv
