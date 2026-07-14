# AWS Architecture: MVP Baseline

Status: AWS content and retrieval baseline provisioned July 14, 2026. The Knowledge Base is active, and the initial corpus is still processing. The application has not been implemented.

## Scope

- AWS account: `335010339891`
- Region: `us-west-2`
- AWS CLI profile: `summercamp`
- Access model: AWS IAM Identity Center / SSO session; no raw or long-lived access keys
- Product boundary: public, no-auth procurement guidance using public-approved sources only

Public/no-auth describes the future user experience. It does not make the S3 bucket or Bedrock resources public. A future backend will call Bedrock with an IAM role.

## Live Resources

### Source bucket

- Bucket: `csub-pa-mvp-source-335010339891-us-west-2`
- Purpose: canonical source storage for procurement documents and timestamped transcripts
- Region: `us-west-2`
- Public access: blocked
- Object ownership: bucket-owner enforced
- Default encryption: SSE-S3
- Versioning: enabled
- Lifecycle: noncurrent versions expire after 90 days; incomplete multipart uploads abort after 7 days
- Transport: bucket policy denies non-TLS requests

The Bedrock source boundary is `approved/`. The separate bucket `dxhub-camp-2026-csub-purchasing-procurement` contains project instructions and is not a retrieval source. It was not modified during this setup.

Current layout:

- `approved/documents/` - documents approved for the public/no-auth MVP
- `approved/transcripts/` - future reviewed, timestamped transcripts
- `incoming/` - future staging area; never directly indexed
- `retired/` - future superseded content; never directly indexed

Sixteen procurement documents from `customer-dataaisummercamp` were copied into `approved/documents/`. Two uploaded files represented versions of the same default-address guide; only the newer seven-page `csubuy_setting_default_address.pdf` was placed in the approved corpus.

`customer-dataaisummercamp` is now an import/staging source, not the canonical source of truth for the MVP corpus. Future approved content should be managed in `csub-pa-mvp-source-335010339891-us-west-2`.

### Retrieval

- Knowledge Base: `csub-pa-mvp-kb`
- Knowledge Base ID: `KZWZQVCCJW`
- Type: Amazon Bedrock managed Knowledge Base
- Embeddings: Bedrock service-managed
- Service role: `AmazonBedrockExecutionRoleForKnowledgeBase_csub_pa_mvp`
- Data source: `csub-pa-mvp-approved-direct` (`UEPVWR8BSS`)

The managed Knowledge Base was selected because it keeps S3 as the source of truth while Bedrock manages embeddings, vector storage, indexing, and retrieval. The account's organization policy explicitly denies S3 Vectors and prevents Bedrock service roles from listing S3 buckets. Therefore, the source is synchronized through Bedrock's supported custom connector using the authenticated `summercamp` operator session instead of a native S3 crawler. The Knowledge Base service role has no S3 permissions. A native S3 crawler should not be assumed available unless the campus organization policy changes.

## Current Verification Status

Last verified July 14, 2026:

- Knowledge Base status: `ACTIVE`
- Data source status: `AVAILABLE`
- Canonical approved corpus: 16 documents
- Ingestion status: 1 `INDEXED`, 15 `IN_PROGRESS`, 0 `FAILED`, and 0 `IGNORED`
- The indexed document is `Copy-of-Chartfield-Request-DOA-Form-2-22-22.xlsx`.
- A retrieval test for chartfield and delegation-of-authority guidance returned grounded passages from that document. The result included the canonical S3 URI in its metadata and a best relevance score of `0.833`.

The remaining documents should not be treated as queryable until Bedrock reports them as `INDEXED`. Their current asynchronous processing state has no reported failure reason.

## Ingestion Boundary

- Index only material explicitly approved for public/no-auth exposure.
- Synchronize only objects under `approved/` through the custom connector.
- Keep raw videos outside the indexed prefix.
- Convert videos into reviewed transcripts with timestamp ranges before placing them under `approved/transcripts/`.
- Treat requester, vendor, and internal-staff roles as guidance context, not authorization.
- Do not add restricted, personalized, supplier-specific, invoice-specific, or payment-specific records to this Knowledge Base.

## Source Synchronization

The custom connector does not automatically crawl S3. Until a different ingestion path is approved, source updates should follow this operating sequence:

1. Place candidate material under `incoming/`.
2. Review it for authority, currency, duplication, and public/no-auth suitability.
3. Promote approved documents or timestamped transcripts into the appropriate `approved/` prefix.
4. Submit the approved object to the custom connector using an authenticated `summercamp` session.
5. Wait for `INDEXED` status, then run a small retrieval-and-citation check before relying on the source.
6. When retiring or replacing content, update both the canonical S3 corpus and the corresponding custom-connector document state.

The owner of this approval and synchronization process is still an open governance decision. Event-driven or scheduled synchronization remains deferred.

## Deferred Until Application Work Is Authorized

- Chat/orchestration API runtime
- Frontend hosting and CDN
- Public endpoint rate limiting and abuse controls
- Application logs, analytics, and feedback storage
- Authentication for any future restricted or personalized workflows
- Automated video transcription and ingestion pipeline
- Scheduled or event-driven Knowledge Base synchronization

No AWS Budgets or Cost Anomaly Detection resources are part of this baseline.
