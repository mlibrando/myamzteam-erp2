# Amazon Ads API — Retrieve a profile ID (`GET /v2/profiles`)

> Source: official Amazon Ads advanced tools center (Getting Started → Step 3: Retrieve profiles). Provided by the developer; saved for repo use.

There are two essential authorization credentials for calling the Amazon Ads API:

- The **client ID** of a Login with Amazon (LwA) client application approved for API access.
- An **access token** representing permission for that client to access resources on behalf of an Amazon user account that manages Amazon Ads accounts.

In addition, **nearly all requests require a profile ID** representing the advertising account of the user in a specific marketplace.

## Access the Profiles resource

To retrieve a list of available profiles, make a `GET` request to the `/v2/profiles` endpoint **in a region where the user account manages advertising accounts**.

Example (North America host):

```
https://advertising-api.amazon.com/v2/profiles
```

Two required headers:

- `Amazon-Advertising-API-ClientId`: The client identifier of the LwA client application.
- `Authorization`: The string `Bearer` prepended to the access token.

cURL:

```
curl \
  -H "Amazon-Advertising-API-ClientId: amzn1.application-oa2-client.bb48851ca..." \
  -H "Authorization: Bearer Atza|IQEBLjAsAhRmHjNgHpi0U-Dme37rR6CuUpSR..." \
  https://advertising-api.amazon.com/v2/profiles
```

## Profiles response

The response includes a list of profiles associated with the user account in the region of the API host. Example (one account, MX marketplace):

```json
[
  {
    "profileId": 888888888,
    "countryCode": "MX",
    "currencyCode": "MXN",
    "timezone": "America/Los_Angeles",
    "accountInfo": {
      "marketplaceStringId": "A1AM78C64UM0Y8",
      "id": "ENTITY2Ihjasdjkeru",
      "type": "vendor",
      "name": "Name of the Account",
      "validPaymentMethod": false
    }
  }
]
```

Notes:

- **Multiple profiles:** each profile represents an advertising account in a different marketplace. Use `countryCode` to determine the marketplace.
- **Empty array `[]`:** authorization succeeded but the account has no View/Edit permissions for advertising accounts in that region.
- **DSP:** `/v2/profiles` does **not** return ADSP advertiser accounts. Use the Query Advertiser Accounts API for those (and `GET /managerAccounts` for manager-account-linked accounts).
- **Manager account:** if the authorizing user is a manager account, the response includes all accounts in the region with Editor access; use `GET /managerAccounts` for Viewer-only.

## Pass the profile ID in subsequent requests

Aside from `/v2/profiles`, requests can access resources for **only one profile**, selected via the `Amazon-Advertising-API-Scope` header. Three required headers for most calls:

- `Amazon-Advertising-API-ClientId`: Your client ID.
- `Authorization`: `Bearer` + access token.
- `Amazon-Advertising-API-Scope`: The profile ID for an advertising account in a specific marketplace.

**Access tokens expire after 60 minutes.** A request with an expired token returns Unauthorized; refresh as needed.
