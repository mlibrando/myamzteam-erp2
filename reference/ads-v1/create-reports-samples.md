# Amazon Ads API (ads-v1) — Reporting & Query Samples

> Source: official Amazon Ads advanced tools center reference (create/reports, QueryCampaign). Request/response samples provided by the developer; saved for repo use.

## `POST /adsApi/v1/create/reports` — Create a report

- **Header:** `Amazon-Ads-ClientId` (required) — *note the reference shows this name; other Ads docs use `Amazon-Advertising-API-ClientId`. Resolve via the Phase 0 probe.*
- **Auth:** OAuth2 bearer.
- **Permissions (one of):** `ManagerAccount_Dev`, `advertiser_campaign_edit`, `nemo_report_view`, `MasterAccount_Viewer`, `MA_ReadOnly`, `advertiser_campaign_view`, `reports_edit`, `MasterAccount_Manager`, `nemo_report_edit`, `view_performance_dashboard`.
- **Body:** `accessRequestedAccounts` (array of `advertiserAccountId` or `managerAccountId` objects, `[1..2000]`) + `reports` (exactly 1 `ReportCreate`).
- **Response:** `207` multi-status, with `success[]` and `error[]` arrays indexed per account.

### Request sample

```json
{
  "accessRequestedAccounts": [
    { "advertiserAccountId": "string" }
  ],
  "reports": [
    {
      "currencyOfView": "AED",
      "format": "CSV",
      "periods": [
        { "datePeriod": { "endDate": "2019-08-24", "startDate": "2019-08-24" } }
      ],
      "query": {
        "fields": [ "string" ],
        "filter": { "and": { "filters": [ null ] } }
      }
    }
  ]
}
```

### Response sample

```json
{
  "error": [
    { "errors": [ { "code": "ACCESS_DENIED_FOR_MANAGER_ACCOUNT", "fieldLocation": "string", "message": "string" } ], "index": 0 }
  ],
  "success": [
    {
      "index": 0,
      "report": {
        "completedDateTime": "2019-08-24T14:15:22Z",
        "completedReportParts": [
          { "sizeInBytes": 9223372036854776000, "url": "string", "urlExpirationDateTime": "2019-08-24T14:15:22Z" }
        ],
        "creationDateTime": "2019-08-24T14:15:22Z",
        "currencyOfView": "AED",
        "failureCode": "string",
        "failureReason": "string",
        "format": "CSV",
        "lastUpdatedDateTime": "2019-08-24T14:15:22Z",
        "periods": [ { "datePeriod": { "endDate": "2019-08-24", "startDate": "2019-08-24" } } ],
        "query": { "fields": [ "string" ], "filter": { "and": { "filters": [ null ] } } },
        "reportId": "string",
        "status": "COMPLETED"
      }
    }
  ]
}
```

### Spend query for this build (US ad-spend feed)

`query.fields` (all verified compatible against the dimension docs):

- `date.value` — daily grain
- `adProduct.value` — splits `SPONSORED_PRODUCTS` / `SPONSORED_BRANDS` / `SPONSORED_DISPLAY` / `SPONSORED_TELEVISION` (/ `AMAZON_DSP`)
- `campaign.id` + `campaign.name`
- `campaign.country` — marketplace discriminator (filter to US)
- `budgetCurrency.value` — native currency
- `metric.totalCost` — **the advertising spend**

Poll with `POST /adsApi/v1/retrieve/reports` (`reportIds`), then download `completedReportParts[].url`.
Combine Sponsored Brands + Sponsored Brands Video into one `SPONSORED_BRANDS` line (no separate "video" adProduct).

---

## `POST /adsApi/v1/query/campaigns` — Query campaign (reference, not a spend source)

Returns campaign **configuration and configured budgets**, not spend. Useful only as optional
enrichment (mapping `campaignId → adProduct / name / state / portfolio`).

- Auth: OAuth2, scope `advertising::campaign_management`. Auth URL `https://www.amazon.com/ap/oa`; Token URL `https://api.amazon.com/auth/o2/token`.
- **AdProduct enum:** `SPONSORED_PRODUCTS`, `SPONSORED_BRANDS`, `SPONSORED_DISPLAY`, `SPONSORED_TELEVISION`, `AMAZON_DSP`.
- Filters: `adProductFilter`, `campaignIdFilter` (`[1..1000]`), `goalFilter` (AWARENESS/CONSIDERATION/CONVERSIONS), `marketplaceScopeFilter` (GLOBAL/SINGLE_MARKETPLACE), `nameFilter` (BROAD_MATCH/EXACT_MATCH), `portfolioIdFilter`, `stateFilter` (ENABLED/PAUSED/ARCHIVED), `maxResults` `[1..5000]`, `nextToken`.

### Request sample

```json
{
  "adProductFilter": { "include": [ "AMAZON_DSP" ] },
  "campaignIdFilter": { "include": [ "string" ] },
  "goalFilter": { "include": [ "AWARENESS" ] },
  "marketplaceScopeFilter": { "include": [ "GLOBAL" ] },
  "maxResults": 1,
  "nameFilter": { "include": [ "string" ], "queryTermMatchType": "BROAD_MATCH" },
  "nextToken": "string",
  "portfolioIdFilter": { "include": [ "string" ] },
  "stateFilter": { "include": [ "ARCHIVED" ] }
}
```
