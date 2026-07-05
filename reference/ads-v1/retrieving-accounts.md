# Retrieving Accounts (adsAccounts)

> Source: official Amazon Ads advanced tools center (advertising.amazon.com/API/docs). Copied verbatim for offline/repo use.

You can now get sponsored ads accounts globally through a single API call, including their status, countries, profiles, and other metadata. You can call with a single ads account ID to get its properties, or omit the ads account ID to get all advertising accounts for the user account associated with the access token.

View the technical specifications for account management in the Amazon Ads API.

Accounts and regions
Accounts are now global in nature and can contain multiple countries. An advertiser registered for 3 countries will usually have 1 ads account ID and 3 country-specific profile IDs, though some advertisers may have separate ads accounts per country. Note that profiles are still needed to call most Amazon Ads APIs for campaign management, and the profile ID can now be retrieved globally through this endpoint.

Account status
The endpoints described below return a status for each account. Account statuses include:

CREATED
the account is ready and available for use.
PARTIALLY CREATED
the registration is still in progress. Some but not all countries are available for use. Poll again after 3-5 seconds.
PENDING
the registration is still in progress. No countries are available yet. Poll again after 3-5 seconds.
DISABLED
the registration failed because the advertiser is ineligible for a variety of reasons. Try again with new business or selling partner details.
Operations
 Note
These operations currently only return sponsored ads accounts, and do not include Amazon DSP or other account types.
Get an account
Call to get a single account given its ID.

URL: GET /adsAccounts/{accountId}

Example: GET /adsAccounts/amzn1.ads-account.g.87rerlyohs3b1cmj2rem03xmd

Sample Response
{
    "adsAccount": {
        "adsAccountId": "amzn1.ads-account.g.87rerlyohs3b1cmj2rem03xmd",
        "accountName": "My Ads Account Name",
        "status": "CREATED",
        "countryCodes": [
            "UK",
            "US"
        ],
        "alternateIds": [{
                "profileId": 123123,
                "countryCode": "US"
            },
            {
                "entityId": "ENTITY215J8KS99D",
                "countryCode": "US"
            },
            {
                "profileId": 456456,
                "countryCode": "UK"
            },
            {
                "entityId": "ENTITY99H739IY0R",
                "countryCode": "UK"
            }
        ]
    }
}

Get all accounts by user
This endpoint retrieves all ads accounts for the user account associated with the access token. Integrators may use this endpoint to populate navigational elements or perform multi-account actions.

URL: POST /adsAccounts/list

Sample Response

[
    {
        "adsAccount": {
            "adsAccountId": "amzn1.ads-account.g.87rerlyohs3b1cmj2rem03xmd",
            "accountName": "Ads Account 1",
            "status": "CREATED",
            "countryCodes": [
                "UK",
                "US"
            ],
            "alternateIds": [{
                    "profileId": 123123,
                    "countryCode": "US"
                },
                {
                    "entityId": "ENTITY215J8KS99D",
                    "countryCode": "US"
                },
                {
                    "profileId": 456456,
                    "countryCode": "UK"
                },
                {
                    "entityId": "ENTITY99H739IY0R",
                    "countryCode": "UK"
                }
            ]
        }
    },
    {
        "adsAccount": {
            "adsAccountId": "amzn1.ads-account.g.dj398djdbnwyw4045nnf22jd",
            "accountName": "Ads Account 2",
            "status": "CREATED",
            "countryCodes": [
                "US"
            ],
            "alternateIds": [{
                    "profileId": 123123,
                    "countryCode": "US"
                },
                {
                    "entityId": "ENTITY215J8KS99D",
                    "countryCode": "US"
                }
            ]
        }
    }
]

Next steps
For many requests to the Amazon Ads API, for example a request to create a Sponsored Display campaign, you must include the profileId, rather than the ads account ID. With the profile ID you can call APIs for campaign creation, campaign management, reporting, and more.

Learn more about profiles in the Amazon Ads API.