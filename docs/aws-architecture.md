# AWS Architecture: MVP Baseline

Status: AWS content and retrieval baseline provisioned July 14, 2026. The replacement `CSUBuyP2P` corpus is text-searchable, all video transcripts are indexed, and the application has not been implemented.

## Scope

- AWS account: `335010339891`
- Region: `us-west-2`
- AWS CLI profile: `summercamp`
- Access model: AWS IAM Identity Center / SSO session; no raw or long-lived access keys
- Product direction: public, no-auth procurement guidance

Public/no-auth describes the future user experience. It does not make the S3 bucket or Bedrock resources public. The current Knowledge Base contains mixed-scope material, including internal/admin guidance, so it must not be exposed directly to a public application without enforced filtering or corpus separation. A future backend will call Bedrock with an IAM role.

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

- `approved/documents/` - 63 PDF/DOCX sources, preserving the `CSUBuyP2P` folder hierarchy
- `approved/transcripts/` - 17 timestamped VTT transcripts used for video retrieval
- `media/videos/` - 17 original MP4 sources; stored but not indexed directly
- `transcription-output/raw/` - Amazon Transcribe job outputs retained for traceability
- `incoming/` - future staging area; never directly indexed
- `retired/` - future superseded content; never directly indexed

The canonical corpus was replaced with all 80 real source files in the local `CSUBuyP2P` collection: 63 documents and 17 videos. The macOS `.DS_Store` artifact was excluded. The local collection is ignored by Git and is not part of the repository.

The earlier 16-document corpus imported from `customer-dataaisummercamp` was deleted. Future source changes should be managed in `csub-pa-mvp-source-335010339891-us-west-2`.

### Retrieval

- Knowledge Base: `csub-pa-mvp-kb`
- Knowledge Base ID: `KZWZQVCCJW`
- Type: Amazon Bedrock managed Knowledge Base
- Embeddings: Bedrock service-managed
- Service role: `AmazonBedrockExecutionRoleForKnowledgeBase_csub_pa_mvp`
- Data source: `csub-pa-mvp-approved-direct` (`UEPVWR8BSS`)

The managed Knowledge Base was selected because it keeps S3 as the source of truth while Bedrock manages embeddings, vector storage, indexing, and retrieval. The account's organization policy explicitly denies S3 Vectors and prevents Bedrock service roles from listing S3 buckets. Therefore, the source is synchronized through Bedrock's supported custom connector using the authenticated `summercamp` operator session instead of a native S3 crawler. A native S3 crawler should not be assumed available unless the campus organization policy changes.

The Bedrock role has a single inline permission: `s3:GetObject` for `approved/documents/*` and `approved/transcripts/*` in the canonical source bucket. It has no bucket-list permission, no access to `media/videos/`, and no access to the DXHub instruction bucket.

## Current Verification Status

Last verified July 14, 2026:

- Knowledge Base status: `ACTIVE`
- Data source status: `AVAILABLE`
- Canonical source corpus: 63 documents and 17 original videos
- Video processing: 17 Amazon Transcribe jobs `COMPLETED`, 0 failed
- Retrieval representations: 63 documents plus 17 timestamped VTT transcripts
- Document state: all 63 report `TEXT_INDEXED` when checked directly and are text-searchable
- Transcript state: all 17 report `INDEXED`
- Retrieval tests returned the sensitive-PII guide, the internal supplier FAQ, and timestamped payment-terms video guidance with their replacement-corpus paths and S3 metadata.

The aggregate list API currently summarizes the 63 documents as `IN_PROGRESS` while optional image extraction continues, but direct status checks report `TEXT_INDEXED` and retrieval is working. Sixteen identifiers from the deleted corpus appear as `NOT_FOUND` deletion tombstones. For example, `approved/documents/VPAT_2.5_Nov2023.pdf` is intentionally absent from both S3 and the replacement collection; its `NOT_FOUND` row is not a failed new upload.

## Content And Access Boundary

- The current Knowledge Base includes every real file from `CSUBuyP2P` by explicit project direction.
- This includes supplier material labeled internal, campus-admin guidance, and the sensitive-PII access guide.
- Internal/admin/PII-related sources are tagged with `access_scope=internal` metadata where identified.
- The custom connector has ACL enforcement disabled. Metadata tags do not prevent retrieval by themselves.
- Before a public/no-auth application launches, enforce metadata filtering or separate internal sources into a restricted Knowledge Base.
- Synchronize only objects under `approved/` through the custom connector.
- Keep raw videos under `media/videos/`, outside the indexed prefixes.
- Convert videos into timestamped VTT transcripts before placing them under `approved/transcripts/`.
- Treat requester, vendor, and internal-staff roles as guidance context, not authorization.
- Do not add personalized supplier, invoice, payment, requester, or transaction records to this Knowledge Base.

## Source Synchronization

The custom connector does not automatically crawl S3. Until a different ingestion path is approved, source updates should follow this operating sequence:

1. Place candidate material under `incoming/`.
2. Review it for authority, currency, duplication, access scope, and intended audience.
3. Promote approved documents into `approved/documents/`; store original videos under `media/videos/` and promote their timestamped VTT output into `approved/transcripts/`.
4. Submit the approved document or transcript to the custom connector using an authenticated `summercamp` session. The Bedrock role reads only the approved object.
5. Confirm `TEXT_INDEXED` or `INDEXED` status, then run a small retrieval-and-citation check before relying on the source.
6. When retiring or replacing content, update both the canonical S3 corpus and the corresponding custom-connector document state.

The owner of this approval and synchronization process is still an open governance decision. Event-driven or scheduled synchronization remains deferred.

## Deferred Until Application Work Is Authorized

- Chat/orchestration API runtime
- Frontend hosting and CDN
- Public endpoint rate limiting and abuse controls
- Application logs, analytics, and feedback storage
- Authentication for any future restricted or personalized workflows
- Enforced separation or filtering of internal content before public launch
- Automated video transcription and ingestion pipeline; the current 17-video batch was operator-run
- Scheduled or event-driven Knowledge Base synchronization

No AWS Budgets or Cost Anomaly Detection resources are part of this baseline.
