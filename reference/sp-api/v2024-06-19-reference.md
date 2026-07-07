Overview
The Selling Partner API for Finances provides financial information relevant to a seller's business. You can obtain financial events for a given order or date range without having to wait until a statement period closes.

Version information
Version : 2024-06-19

Contact information
Contact : Selling Partner API Developer Support
Contact URL : https://sellercentral.amazon.com/gp/mws/contactus.html

License information
License : Apache License 2.0
License URL : http://www.apache.org/licenses/LICENSE-2.0

URI scheme
Host : sellingpartnerapi-na.amazon.com
Schemes : HTTPS

Consumes
application/json
Produces
application/json
Operations
listTransactions


Paths

GET /finances/2024-06-19/transactions
Operation: listTransactions

Description
Returns transactions for the given parameters. Financial events might not include orders from the last 48 hours.

Usage plan:

Rate (requests per second)	Burst
0.5	10
The x-amzn-RateLimit-Limit response header returns the usage plan rate limits that were applied to the requested operation, when available. The preceding table contains the default rate and burst values for this operation. Selling partners whose business demands require higher throughput may have higher rate and burst values than those shown here. For more information, refer to Usage Plans and Rate Limits.

Parameters
Type	Name	Description	Schema
Query	postedAfter
optional	The response includes financial events posted on or after this date. This date must be in ISO 8601 date-time format. The date-time must be more than two minutes before the time of the request.

This field is required if you do not specify a related identifier.	string (date-time)
Query	postedBefore
optional	The response includes financial events posted before (but not on) this date. This date must be in ISO 8601 date-time format.

The date-time must be later than PostedAfter and more than two minutes before the request was submitted. If PostedAfter and PostedBefore are more than 180 days apart, the response is empty.

Default: Two minutes before the time of the request.	string (date-time)
Query	marketplaceId
optional	The identifier of the marketplace from which you want to retrieve transactions. The marketplace ID is the globally unique identifier of a marketplace. To find the ID for your marketplace, refer to Marketplace IDs.	string
Query	transactionStatus
optional	The status of the transaction.

Possible values:

DEFERRED: the transaction is currently deferred.

RELEASED: the transaction is currently released.

DEFERRED_RELEASED: the transaction was deferred in the past, but is now released. The status of a deferred transaction is updated to DEFERRED_RELEASED when the transaction is released.
string
Query	relatedIdentifierName
optional	The name of the relatedIdentifier.

Possible values:

FINANCIAL_EVENT_GROUP_ID: the financial event group ID associated with the transaction.

ORDER_ID: the order ID associated with the transaction.


Note:

FINANCIAL_EVENT_GROUP_ID and ORDER_ID are the only relatedIdentifier with filtering capabilities at the moment. While other relatedIdentifier values will be included in the response when available, they cannot be used for filtering purposes.	string
Query	relatedIdentifierValue
optional	The value of the relatedIdentifier.	string
Query	nextToken
optional	The response includes nextToken when the number of results exceeds the specified pageSize value. To get the next page of results, call the operation with this token and include the same arguments as the call that produced the token. To get a complete list, call this operation until nextToken is null. Note that this operation can return empty pages.	string
Responses
HTTP Code	Description	Schema
200	Success.
Headers :
x-amzn-RateLimit-Limit (string) : Your rate limit (requests per second) for this operation.
x-amzn-RequestId (string) : Unique request reference identifier.	ListTransactionsResponse
For error status codes, descriptions and schemas, see Error responses and schemas.


Error Responses and Schemas
This table contains HTTP status codes and associated information for error responses.

HTTP Code	Description	Schema
400	Request has missing or invalid parameters and cannot be parsed.
Headers:
x-amzn-RateLimit-Limit (string):Your rate limit (requests per second) for this operation.
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
403	Indicates that access to the resource is forbidden. Possible reasons include Access Denied, Unauthorized, Expired Token, or Invalid Signature.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
404	The resource specified does not exist.
Headers:
x-amzn-RateLimit-Limit (string):Your rate limit (requests per second) for this operation.
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
413	The request size exceeded the maximum accepted size.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
415	The request payload is in an unsupported format.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
429	The frequency of requests was greater than allowed.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
500	An unexpected condition occurred that prevented the server from fulfilling the request.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList
503	Temporary overloading or maintenance of the server.
Headers:
x-amzn-RequestId (string):Unique request reference identifier.	ErrorList

Definitions

ListTransactionsResponse
The response schema for the listTransactions operation.

Name	Description	Schema
payload
optional	The payload for the listTransactions operation.	TransactionsPayload

TransactionsPayload
The payload for the listTransactions operation.

Name	Description	Schema
nextToken
optional	The response includes nextToken when the number of results exceeds the specified pageSize value. To get the next page of results, call the operation with this token and include the same arguments as the call that produced the token. To get a complete list, call this operation until nextToken is null. Note that this operation can return empty pages.	string
transactions
optional	A list of transactions within the specified time period.	Transactions

Transactions
A list of transactions within the specified time period.

Type : < Transaction > array


Transaction
All the information related to a transaction.

Name	Description	Schema
sellingPartnerMetadata
optional	Metadata that describes the seller.	SellingPartnerMetadata
relatedIdentifiers
optional	Identifiers related to the transaction, such as order and shipment IDs.	RelatedIdentifiers
transactionType
optional	The type of transaction.

Possible value: Shipment	string
transactionId
optional	The unique identifier of the transaction.	string
transactionStatus
optional	The status of the transaction.

Possible values:

DEFERRED: the transaction is currently deferred.

RELEASED: the transaction is currently released.

DEFERRED_RELEASED: the transaction was deferred in the past, but is now released. The status of a deferred transaction is updated to DEFERRED_RELEASED when the transaction is released.
string
description
optional	Describes the reasons for the transaction.

Example: 'Order Payment', 'Refund Order'	string
postedDate
optional	The date and time when the transaction was posted.	Date
totalAmount
optional	The total amount of money in the transaction.	Currency
marketplaceDetails
optional	Information about the marketplace where the transaction occurred.	MarketplaceDetails
items
optional	Additional information about the items in the transaction.	Items
contexts
optional	Additional Information about the transaction.	Contexts
breakdowns
optional	A list of breakdowns that detail how the total amount is calculated for the transaction.	< Breakdown > array

BigDecimal
A signed decimal number.

Type : number


Currency
A currency type and amount.

Name	Description	Schema
currencyCode
optional	The three-digit currency code in ISO 4217 format.	string
currencyAmount
optional	The monetary value.	BigDecimal

SellingPartnerMetadata
Metadata that describes the seller.

Name	Description	Schema
sellingPartnerId
optional	A unique seller identifier.	string
accountType
optional	The type of account in the transaction.	string
marketplaceId
optional	The identifier of the marketplace where the transaction occurred. The marketplace ID is the globally unique identifier of a marketplace. To find the ID for your marketplace, refer to Marketplace IDs.	string

RelatedIdentifier
Related business identifier of the transaction.

Name	Description	Schema
relatedIdentifierName
optional	An enumerated set of related business identifier names.	enum (RelatedIdentifierName)
relatedIdentifierValue
optional	Corresponding value of RelatedIdentifierName.	string

RelatedIdentifiers
Related business identifiers of the transaction.

Type : < RelatedIdentifier > array


Date
A date in ISO 8601 date-time format.

Type : string (date-time)


MarketplaceDetails
Information about the marketplace where the transaction occurred.

Name	Description	Schema
marketplaceId
optional	The identifier of the marketplace where the transaction occurred. The marketplace ID is the globally unique identifier of a marketplace. To find the ID for your marketplace, refer to Marketplace IDs.	string
marketplaceName
optional	The name of the marketplace where the transaction occurred. For example: Amazon.com,Amazon.in	string

Items
A list of items in the transaction.

Type : < Item > array


Item
Additional information about the items in a transaction.

Name	Description	Schema
description
optional	A description of the items in a transaction.	string
relatedIdentifiers
optional	Related business identifiers of the item.	ItemRelatedIdentifiers
totalAmount
optional	The total monetary amount of the item.	Currency
breakdowns
optional	A list of breakdowns that detail how the total amount is calculated for the transaction.	< Breakdown > array
contexts
optional	Additional Information about the item.	Contexts

ItemRelatedIdentifier
Related business identifiers of the item.

Name	Description	Schema
itemRelatedIdentifierName
optional	Enumerated set of related item identifier names for the item.	enum (ItemRelatedIdentifierName)
itemRelatedIdentifierValue
optional	Corresponding value to ItemRelatedIdentifierName.	string

ItemRelatedIdentifiers
Related business identifiers of the item in the transaction.

Type : < ItemRelatedIdentifier > array


Breakdown
Details about the movement of money in the financial transaction. Breakdowns are further categorized into breakdown types, breakdown amounts, and further breakdowns.

Name	Description	Schema
breakdownType
optional	The type of charge.	string
breakdownAmount
optional	The monetary amount of the charge.	Currency
breakdowns
optional	A list of breakdowns that detail how the total amount is calculated for the transaction.	< Breakdown > array

Contexts
A list of additional information about the item.

Type : < Context > array


Context
Additional Information about the item.

Polymorphism : Composition

Name	Description	Schema
contextType
required	-	string
storeName
optional	The store name associated with the transaction.	enum (StoreName)
orderType
optional	The transaction's order type.	string
channel
optional	Channel details of related transaction.	string
asin
optional	The Amazon Standard Identification Number (ASIN) of the item.	string
sku
optional	The Stock Keeping Unit (SKU) of the item.	string
quantityShipped
optional	The quantity of the item shipped.	integer (int32)
fulfillmentNetwork
optional	The fulfillment network of the item.	string
paymentType
optional	The type of payment.	string
paymentMethod
optional	The method of payment.	string
paymentReference
optional	The reference number of the payment.	string
paymentDate
optional	The date of the payment.	Date
deferralReason
optional	The deferral policy applied to the transaction.

Examples: B2B (invoiced orders), DD7 (delivery date policy)	string
maturityDate
optional	The release date of the transaction.	Date
startTime
optional	The start time of the transaction.	Date
endTime
optional	The end time of the transaction.	Date

ProductContext
Additional information related to the product.

Name	Description	Schema
asin
optional	The Amazon Standard Identification Number (ASIN) of the item.	string
sku
optional	The Stock Keeping Unit (SKU) of the item.	string
quantityShipped
optional	The quantity of the item shipped.	integer (int32)
fulfillmentNetwork
optional	The fulfillment network of the item.	string

AmazonPayContext
Additional information related to Amazon Pay.

Name	Description	Schema
storeName
optional	The name of the store that is related to the transaction.	string
orderType
optional	The transaction's order type.	string
channel
optional	Channel details of related transaction.	string

PaymentsContext
Additional information related to payments-related transactions.

Name	Description	Schema
paymentType
optional	The type of payment.	string
paymentMethod
optional	The method of payment.	string
paymentReference
optional	The reference number of the payment.	string
paymentDate
optional	The date of the payment.	Date

DeferredContext
Additional information related to deferred transactions.

Name	Description	Schema
deferralReason
optional	The deferral policy applied to the transaction.

Examples: B2B (invoiced orders), DD7 (delivery date policy)	string
maturityDate
optional	The release date of the transaction.	Date

BusinessContext
Information about the line of business associated with a transaction.

Name	Description	Schema
storeName
optional	The store name associated with the transaction.	enum (StoreName)

TimeRangeContext
Additional information that is related to the time range of the transaction.

Name	Description	Schema
startTime
optional	The start time of the transaction.	Date
endTime
optional	The end time of the transaction.	Date

ErrorList
A list of error responses returned when a request is unsuccessful.

Name	Description	Schema
errors
required	The error responses that are returned when the request is unsuccessful.	< Error > array

Error
An error response returned when the request is unsuccessful.

Name	Description	Schema
code
required	An error code that identifies the type of error that occurred.	string
message
required	A message that describes the error condition.	string
details
optional	Additional details that can help the caller understand or fix the issue.	string

StoreName
The store name associated with the transaction.

Type : enum

Value	Description
AMAZON_HAUL	-

RelatedIdentifierName
An enumerated set of related business identifier names.

Type : enum

Value	Description
ORDER_ID	The OrderId that is associated with the transaction.
SHIPMENT_ID	The ShipmentId that is associated with the transaction.
FINANCIAL_EVENT_GROUP_ID	The identifier that is associated with the transaction's financial event group.
REFUND_ID	The RefundId that is associated with the transaction.
INVOICE_ID	The InvoiceId that is associated with the transaction.
DISBURSEMENT_ID	The disbursement ID for Amazon's bank transfer.
TRANSFER_ID	The TransferId associated with the transaction.
DEFERRED_TRANSACTION_ID	The transaction ID for the related deferred transaction
RELEASE_TRANSACTION_ID	The transaction ID for the related released transaction
SETTLEMENT_ID	The identifier that is associated with the transaction's settlement group.

ItemRelatedIdentifierName
Enumerated set of related item identifier names for the item.

Type : enum

Value	Description
ORDER_ADJUSTMENT_ITEM_ID	An Amazon-defined order adjustment identifier defined for refunds, guarantee claims, and chargeback events.
COUPON_ID	An identifier for a coupon that is applied to a transaction.
REMOVAL_SHIPMENT_ITEM_ID	An identifier for an item in a removal shipment.
TRANSACTION_ID	The transaction ID of the item.
