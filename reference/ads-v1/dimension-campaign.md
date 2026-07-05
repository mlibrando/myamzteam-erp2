# Dimension: Campaign (Level of detail)

> Source: official Amazon Ads advanced tools center (advertising.amazon.com/API/docs). Copied verbatim for offline/repo use.

The Campaign dimension contains 15 fields, listed below:

Campaign ID (Primary Key)
Reporting Field ID: campaign.id
Data Type: STRING
Description: The unique ID associated with the campaign.
Required fields: N/A
Complementary fields: N/A
Version 3 Reporting Name (DSP): orderId
Version 3 Reporting Name (Sponsored Ads): campaignId
Campaign name
Reporting Field ID: campaign.name
Data Type: STRING
Description: The name of the campaign used to organize ad groups, apply a budget, and various other settings.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): order
Version 3 Reporting Name (Sponsored Ads): campaignName
Campaign OMS proposal ID
Reporting Field ID: campaign.omsId
Data Type: STRING
Description: The unique ID associated with the campaign imported from Amazon's order management system (OMS).
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): proposalId
Version 3 Reporting Name (Sponsored Ads): N/A
Global Campaign ID
Reporting Field ID: campaign.globalCampaignId
Data Type: STRING
Description: The global campaign ID associated with the campaign.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): N/A
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign currency code
Reporting Field ID: campaign.currencyCode
Data Type: STRING
Description: The three-letter currency code like USD, EUR, GBP, etc.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): orderCurrency
Version 3 Reporting Name (Sponsored Ads): campaignBudgetCurrencyCode
Campaign budget amount
Reporting Field ID: campaign.budgetAmount
Data Type: LONG
Description: The total budget allocated for the campaign.
Required fields: budgetCurrency.value 📎, campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): orderBudget
Version 3 Reporting Name (Sponsored Ads): campaignBudget
Campaign budget type
Reporting Field ID: campaign.budgetType
Data Type: STRING
Description: The way spending is structured for a campaign like "daily" indicating the spending limit per day or "total" indicating the entire campaign duration.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): NA
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign delivery status
Reporting Field ID: campaign.deliveryStatus
Data Type: STRING
Description: The status of the campaign like delivering, inactive, ended, etc.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): N/A
Version 3 Reporting Name (Sponsored Ads): campaignStatus
Campaign start date
Reporting Field ID: campaign.startDate
Data Type: DATE_TIME
Description: The date when the campaign is scheduled to start running and serving ads.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): orderStartDate
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign end date
Reporting Field ID: campaign.endDate
Data Type: DATE_TIME
Description: The date when the campaign is scheduled to stop running and serving ads.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): orderEndDate
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign bid strategy
Reporting Field ID: campaign.bidStrategy
Data Type: STRING
Description: The bid strategy for the campaign like front loaded or evenly spread.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): N/A
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign rule amount
Reporting Field ID: campaign.ruleAmount
Data Type: LONG
Description: The modified campaign budget based on a rule.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): N/A
Version 3 Reporting Name (Sponsored Ads): campaignRuleBasedBudgetAmount
Campaign cost type
Reporting Field ID: campaign.costType
Data Type: STRING
Description: The way you pay for your ads like CPC and CPM.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): N/A
Version 3 Reporting Name (Sponsored Ads): costType
Campaign PO number
Reporting Field ID: campaign.purchaseOrderNumber
Data Type: STRING
Description: The ID assigned to a campaign for tracking purposes. Campaign PO number or external ID is optional.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): PO Number
Version 3 Reporting Name (Sponsored Ads): N/A
Campaign country
Reporting Field ID: campaign.country
Data Type: STRING
Description: The country in which the campaign is delivering.
Required fields: campaign.id 📎
Complementary fields: N/A
Version 3 Reporting Name (DSP): country
Version 3 Reporting Name (Sponsored Ads): N/A