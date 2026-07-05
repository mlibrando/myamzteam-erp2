# Amazon Ads API — Regional Hosts & Header Parameters

> Source: official Amazon Ads advanced tools center (endpoints / getting started). Provided by the developer; saved for repo use.

## Endpoints by region

| URL | Region | Marketplaces |
| --- | --- | --- |
| `https://advertising-api.amazon.com` | North America (NA) | United States (US), Canada (CA), Mexico (MX), Brazil (BR) |
| `https://advertising-api-eu.amazon.com` | Europe (EU) | United Kingdom (GB), France (FR), Italy (IT), Spain (ES), Germany (DE), Netherlands (NL), United Arab Emirates (AE), Poland (PL), Turkey (TR), Egypt (EG), Saudi Arabia (SA), Sweden (SE), Belgium (BE), India (IN) |
| `https://advertising-api-fe.amazon.com` | Far East (FE) | Japan (JP), Australia (AU), Singapore (SG) |

> Note: the developer's original paste of the EU host included a trailing `/dub2zaz` fragment that appears to be a copy artifact; the canonical EU host is `https://advertising-api-eu.amazon.com`. Confirm on first call.

## Header parameters

| Header | Description | Example |
| --- | --- | --- |
| `Amazon-Advertising-API-ClientId` * | The identifier of a client associated with an Amazon Developer account. | `amzn1.application-oa2-client.abcdef123456ghijkkl7890` |
| `Amazon-Advertising-API-Scope` * | The identifier of a profile associated with the advertiser account. Use `GET /v2/profiles` to list profiles for the access token; choose the `profileId` from the response. | `123123123123123` |
| `Authorization` * | Login with Amazon token in the form `Bearer {{token}}`. | `Bearer Atza|IwEBIIR1q...` |
| `Accept` | `application/json` | `application/json` |
| `Content-Type` | `application/json` | `application/json` |

\* required

## Example endpoint — Query Publishers

`POST /adsApi/v1/query/publishers` — retrieve a list of available publishers. POST with no request body; call with the required headers.

cURL:

```
curl -X POST \
  https://advertising-api.amazon.com/adsApi/v1/query/publishers \
  -H 'Amazon-Advertising-API-ClientId: amzn1.application-oa2-client.abcdef123456ghijkkl7890' \
  -H 'Amazon-Advertising-API-Scope: 123123123123123' \
  -H 'Authorization: Atza|...' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json'
```

Response:

```json
{
  "publishers": [
    { "name": "publisherName", "rootDomain": "exampleDomainName" }
  ]
}
```

> IMPORTANT (auth-model note for this build): this `query/*` endpoint uses the profile-scope
> header (`Amazon-Advertising-API-Scope`), whereas the reporting reference for
> `POST /adsApi/v1/create/reports` showed the header `Amazon-Ads-ClientId` with accounts in the
> request body (`accessRequestedAccounts`) and no scope. Amazon's own docs are inconsistent on
> the ClientId header name. Resolve empirically with a two-request probe (see the Claude Code
> prompt, Phase 0) before committing to one.
