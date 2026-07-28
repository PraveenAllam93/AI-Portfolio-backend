/**
 * Lambda: Portfolio Generator (Node.js)
 *
 * Generates a static HTML portfolio from parsed resume data stored in DynamoDB.
 * Uses the shared TypeScript templates (bundled at deploy time from the frontend repo)
 * so the published output is pixel-identical to the editor preview.
 *
 * Security:
 *   - publishMode=true strips EDITOR_SCRIPT and all contenteditable/data-path attrs
 *   - All user data is HTML-escaped inside normalize() before template rendering
 *     (URLs additionally pass _safeUrl, which only allows http/https)
 *   - No CSP is injected: templates ship their own inline animation scripts
 *     (scroll reveals, nav toggles) that a script-src 'none' policy would break.
 */

import {
	DynamoDBClient,
	GetItemCommand,
	PutItemCommand,
	UpdateItemCommand,
} from '@aws-sdk/client-dynamodb';
import { marshall, unmarshall } from '@aws-sdk/util-dynamodb';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { CloudFrontClient, CreateInvalidationCommand } from '@aws-sdk/client-cloudfront';
import { renderPortfolio } from './templates/index';

const dynamodb = new DynamoDBClient({});
const s3 = new S3Client({});
const cf = new CloudFrontClient({});

const PORTFOLIO_BUCKET = process.env.PORTFOLIO_BUCKET!;
const DYNAMODB_TABLE = process.env.DYNAMODB_TABLE!;
const CLOUDFRONT_DISTRIBUTION_ID = process.env.CLOUDFRONT_DISTRIBUTION_ID ?? '';

/**
 * Reserve this portfolio's permanent public number, and make it the user's
 * main portfolio if they do not have one yet.
 *
 * The number is allocated once and never reassigned — see the "Portfolio
 * numbers" note in src/lambdas/auth/username_utils.py, which is the authority
 * for this record layout. Deleting a portfolio leaves a gap on purpose:
 * renumbering would repoint links that have already been shared.
 *
 * Allocation happens here, at publish, rather than at portfolio creation, for
 * two reasons: only published portfolios are reachable by URL, and a guest's
 * portfolio is re-published under the REAL user during the claim flow, so
 * allocating here draws the number from the correct user's counter instead of
 * carrying a guest number that could collide.
 *
 * Returns null on failure — publishing must not fail because numbering did.
 */
async function ensurePortfolioNumber(
	userId: string,
	uploadId: string,
	existing: number | undefined,
	correlationId: string
): Promise<number | null> {
	if (existing) return existing;

	try {
		// ADD is atomic and returns the post-increment value, so simultaneous
		// publishes cannot be handed the same number.
		const bumped = await dynamodb.send(
			new UpdateItemCommand({
				TableName: DYNAMODB_TABLE,
				Key: marshall({ PK: `USER#${userId}`, SK: 'COUNTER#PORTFOLIO' }),
				UpdateExpression: 'ADD #seq :one',
				ExpressionAttributeNames: { '#seq': 'seq' },
				ExpressionAttributeValues: marshall({ ':one': 1 }),
				ReturnValues: 'UPDATED_NEW',
			})
		);
		const number = Number(unmarshall(bumped.Attributes ?? {}).seq);
		if (!number) return null;

		// number -> uploadId pointer, resolved by the edge gate.
		await dynamodb.send(
			new PutItemCommand({
				TableName: DYNAMODB_TABLE,
				Item: marshall({
					PK: `USER#${userId}`,
					SK: `PNUM#${number}`,
					uploadId,
					portfolioNumber: number,
					createdAt: new Date().toISOString(),
				}),
			})
		);

		await dynamodb.send(
			new UpdateItemCommand({
				TableName: DYNAMODB_TABLE,
				Key: marshall({ PK: `USER#${userId}`, SK: `PORTFOLIO#${uploadId}` }),
				UpdateExpression: 'SET portfolioNumber = :n',
				ExpressionAttributeValues: marshall({ ':n': number }),
			})
		);

		// First portfolio published becomes the main one, served at the bare
		// /u/{username}. Conditional so it never steals the slot from a later
		// portfolio the user has explicitly chosen.
		await dynamodb
			.send(
				new PutItemCommand({
					TableName: DYNAMODB_TABLE,
					Item: marshall({
						PK: `USER#${userId}`,
						SK: 'PNUM#main',
						uploadId,
						portfolioNumber: number,
						createdAt: new Date().toISOString(),
					}),
					ConditionExpression: 'attribute_not_exists(PK)',
				})
			)
			.catch(() => {
				/* already set — the user has a main portfolio, leave it alone */
			});

		log('INFO', 'Portfolio number allocated', { correlationId, userId, uploadId, number });
		return number;
	} catch (err) {
		log('ERROR', 'Portfolio number allocation failed (non-fatal)', {
			correlationId,
			userId,
			uploadId,
			error: String(err),
		});
		return null;
	}
}

/** The owner's public handle, used to build viewer-facing invalidation paths. */
async function getUsername(userId: string): Promise<string | null> {
	try {
		const res = await dynamodb.send(
			new GetItemCommand({
				TableName: DYNAMODB_TABLE,
				Key: marshall({ PK: `USER#${userId}`, SK: 'PROFILE' }),
				ProjectionExpression: 'username',
			})
		);
		if (!res.Item) return null;
		return (unmarshall(res.Item).username as string) ?? null;
	} catch {
		return null;
	}
}

const DEFAULT_SECTION_ORDER = [
	'experience',
	'projects',
	'skills',
	'education',
	'certifications',
	'achievements',
	'awards',
	'campaigns',
	'financial_modeling',
	'investment_portfolios',
	'design_philosophy',
	'software_proficiency',
	'custom_sections',
];

// ---------------------------------------------------------------------------
// Structured logger — outputs JSON, captured by CloudWatch Logs
// ---------------------------------------------------------------------------

function log(level: string, message: string, extra: Record<string, unknown> = {}): void {
	console.log(JSON.stringify({ level, function: 'portfolio_generator', message, ...extra }));
}

// ---------------------------------------------------------------------------
// Lambda handler
// ---------------------------------------------------------------------------

interface LambdaContext {
	awsRequestId: string;
}

interface LambdaEvent {
	userId?: string;
	uploadId?: string;
	target?: string;
	// Set on the INITIAL guest draft build (from ai_processing). Tells the
	// generator to finalize the upload record to DRAFT_READY / portfolio DRAFT
	// after rendering the draft — as opposed to an edit rebuild (patch_portfolio)
	// which writes the draft silently and must not touch the upload status.
	finalizeUpload?: boolean;
	Records?: Array<{
		eventName?: string;
		dynamodb?: {
			Keys?: { PK?: { S?: string } };
		};
	}>;
}

export async function lambdaHandler(event: LambdaEvent, context: LambdaContext): Promise<unknown> {
	const correlationId = context?.awsRequestId ?? 'local';
	let userId: string | undefined;
	let uploadId: string | undefined;

	try {
		userId = event.userId;
		uploadId = event.uploadId;

		if (!userId && event.Records?.length) {
			const record = event.Records[0];
			if (record.eventName === 'INSERT' || record.eventName === 'MODIFY') {
				const pkValue = record.dynamodb?.Keys?.PK?.S ?? '';
				userId = pkValue.replace('USER#', '');
			}
		}

		if (!userId) {
			return { statusCode: 400, body: 'Missing userId' };
		}

		log('INFO', 'Portfolio generation started', { correlationId, userId, uploadId });

		// Fetch portfolio data from DynamoDB
		if (!uploadId) {
			log('ERROR', 'Missing uploadId', { correlationId, userId });
			return { statusCode: 400, body: 'Missing uploadId' };
		}

		const getResult = await dynamodb.send(
			new GetItemCommand({
				TableName: DYNAMODB_TABLE,
				Key: marshall({ PK: `USER#${userId}`, SK: `PORTFOLIO#${uploadId}` }),
			})
		);

		if (!getResult.Item) {
			log('ERROR', 'Portfolio data not found', { correlationId, userId, uploadId });
			// Update UPLOAD record to FAILED so the frontend stops polling immediately
			// instead of waiting for the 5-minute stale detection threshold.
			if (uploadId) {
				try {
					await dynamodb.send(
						new UpdateItemCommand({
							TableName: DYNAMODB_TABLE,
							Key: marshall({ PK: `USER#${userId}`, SK: `UPLOAD#${uploadId}` }),
							UpdateExpression: 'SET #status = :status, #updatedAt = :updatedAt',
							ExpressionAttributeNames: { '#status': 'status', '#updatedAt': 'updatedAt' },
							ExpressionAttributeValues: marshall({
								':status': 'FAILED',
								':updatedAt': new Date().toISOString(),
							}),
						})
					);
				} catch (dbErr) {
					log('ERROR', 'Failed to mark upload as FAILED after portfolio not found', {
						correlationId,
						userId,
						uploadId,
						error: String(dbErr),
					});
				}
			}
			return { statusCode: 404, body: 'Portfolio data not found' };
		}

		const item = unmarshall(getResult.Item) as Record<string, unknown>;

		const parsedData = (item.parsedData ?? {}) as Record<string, unknown>;
		const portfolioContent = (item.portfolioContent ?? {}) as Record<string, unknown>;
		const category = (item.category as string | undefined) ?? 'software_engineer';
		const templateId = (item.templateId as string | undefined) ?? 'neon';
		const rawSectionOrder =
			(item.sectionOrder as string[] | undefined) ?? DEFAULT_SECTION_ORDER;
		// Always include custom_sections if parsedData has any — handles users whose
		// stored sectionOrder predates the custom_sections feature.
		const customSectionsData = parsedData.custom_sections as unknown[];
		const sectionOrder =
			Array.isArray(customSectionsData) && customSectionsData.length > 0 && !rawSectionOrder.includes('custom_sections')
				? [...rawSectionOrder, 'custom_sections']
				: rawSectionOrder;
		const hiddenSections = (item.hiddenSections as string[] | undefined) ?? [];
		const templateOverrides = (item.templateOverrides as Record<string, number> | undefined) ?? {};
		const fieldVisibility = (item.fieldVisibility as Record<string, boolean> | undefined) ?? {};
		const target = event.target ?? 'publish';
		// Increment version counter for each new publish so versions never overwrite each other.
		// Draft target always uses the fixed /draft path and does not bump the counter.
		const prevVersion = (item.version as number | undefined) ?? 0;
		const version = target === 'draft' ? prevVersion : prevVersion + 1;

		// Render HTML using the shared frontend templates (publishMode=true)
		const portfolioHtml = renderPortfolio(
			templateId,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			parsedData as any,
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			portfolioContent as any,
			category,
			sectionOrder,
			hiddenSections,
			templateOverrides,
			fieldVisibility,
			true // publishMode — strips editor JS + editable attrs, injects CSP
		);

		const basePath = target === 'draft' ? `${userId}/${uploadId}/draft` : `${userId}/${uploadId}/v${version}`;

		// Drafts must never be cached — the owner edits and re-renders constantly,
		// and a stale preview looks like a lost edit.
		//
		// Published pages ARE cached at the edge: `s-maxage` lets CloudFront serve
		// them without touching S3 or running the access-gate Lambda on every hit,
		// while `max-age=0` keeps browsers revalidating so a republish shows up
		// immediately for someone who already has the page open.
		//
		// Publishing issues an invalidation (below), so updates are normally
		// instant. The 5-minute ceiling is deliberately short as a BACKSTOP: the
		// share URL is now stable, so several actions (publish, activate version,
		// toggle live, change main portfolio) all have to invalidate it. If any
		// one of them is ever missed, content self-heals in minutes rather than
		// being wrong until the TTL expires.
		const cacheControl =
			target === 'draft'
				? 'no-cache, max-age=0, s-maxage=0, must-revalidate'
				: 'public, max-age=0, s-maxage=300, must-revalidate';

		await s3.send(
			new PutObjectCommand({
				Bucket: PORTFOLIO_BUCKET,
				Key: `${basePath}/index.html`,
				Body: Buffer.from(portfolioHtml, 'utf-8'),
				ContentType: 'text/html',
				CacheControl: cacheControl,
			})
		);

		const now = new Date().toISOString();

		if (target !== 'draft') {
			const versionId = `v${version}`;

			// Public identity of this portfolio: its permanent number and the
			// owner's handle. Both are needed to invalidate the viewer-facing URLs
			// below, and the number is what /u/{username}/{n} resolves through.
			const portfolioNumber = await ensurePortfolioNumber(
				userId,
				uploadId,
				item.portfolioNumber as number | undefined,
				correlationId
			);
			const username = await getUsername(userId);

			// Write an immutable version snapshot — used by list/activate/delete APIs
			await dynamodb.send(
				new UpdateItemCommand({
					TableName: DYNAMODB_TABLE,
					Key: marshall({ PK: `USER#${userId}`, SK: `PORTFOLIO#${uploadId}#VERSION#${versionId}` }),
					UpdateExpression:
						'SET #version = :version, portfolioPath = :path, templateId = :template, createdAt = :createdAt',
					ExpressionAttributeNames: { '#version': 'version' },
					ExpressionAttributeValues: marshall({
						':version': version,
						':path': basePath,
						':template': templateId,
						':createdAt': now,
					}),
				})
			);

			await dynamodb.send(
				new UpdateItemCommand({
					TableName: DYNAMODB_TABLE,
					Key: marshall({ PK: `USER#${userId}`, SK: `PORTFOLIO#${uploadId}` }),
					UpdateExpression:
						'SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt, lastPublishedAt = :updatedAt, #version = :version, activeVersion = :activeVersion',
					ExpressionAttributeNames: { '#status': 'status', '#version': 'version' },
					ExpressionAttributeValues: marshall({
						':status': 'PUBLISHED',
						':path': basePath,
						':updatedAt': now,
						':version': version,
						':activeVersion': versionId,
					}),
				})
			);

			if (uploadId) {
				await dynamodb.send(
					new UpdateItemCommand({
						TableName: DYNAMODB_TABLE,
						Key: marshall({ PK: `USER#${userId}`, SK: `UPLOAD#${uploadId}` }),
						UpdateExpression:
							'SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt',
						ExpressionAttributeNames: { '#status': 'status' },
						ExpressionAttributeValues: marshall({
							':status': 'COMPLETE',
							':path': basePath,
							':updatedAt': now,
						}),
					})
				);
			}

			// Drafts are written with Cache-Control: no-cache and rebuilt on every
			// edit save — invalidating CloudFront for each of those burns paid
			// invalidation paths for no benefit. Only invalidate on publish.
			if (CLOUDFRONT_DISTRIBUTION_ID && target !== 'draft') {
				try {
					// CloudFront keys its cache on the URI the VIEWER requested, not
					// the one the access gate rewrites to. Invalidating only the
					// origin path (/{userId}/{uploadId}/*) therefore never matches a
					// shared link, which is addressed as /u/{username}/... — that was
					// silently leaving published changes stale at the edge.
					const paths = [`/${userId}/${uploadId}/*`];
					if (username) {
						if (portfolioNumber) {
							paths.push(`/u/${username}/${portfolioNumber}`);
							paths.push(`/u/${username}/${portfolioNumber}/*`);
						}
						// The bare handle serves the main portfolio; refresh it too in
						// case this publish is the main one.
						paths.push(`/u/${username}`);
						paths.push(`/u/${username}/${uploadId}/*`);
					}

					await cf.send(
						new CreateInvalidationCommand({
							DistributionId: CLOUDFRONT_DISTRIBUTION_ID,
							InvalidationBatch: {
								Paths: { Quantity: paths.length, Items: paths },
								CallerReference: correlationId,
							},
						})
					);
					log('INFO', 'CloudFront cache invalidated', {
						correlationId,
						userId,
						paths,
					});
				} catch (cfErr) {
					// Non-fatal: portfolio is already written to S3.
					// Cache will expire naturally; log for visibility.
					log('ERROR', 'CloudFront invalidation failed (non-fatal)', {
						correlationId,
						userId,
						error: String(cfErr),
					});
				}
			}
		} else if (event.finalizeUpload && uploadId) {
			// Initial guest draft build: the draft HTML is written but nothing is
			// published. Mark the upload DRAFT_READY (terminal for the guest wizard
			// — the frontend treats it like COMPLETE and opens the editor) and the
			// portfolio DRAFT (isLive stays false, set by ai_processing). Edit
			// rebuilds from patch_portfolio do NOT set finalizeUpload, so they
			// leave these statuses untouched.
			await dynamodb.send(
				new UpdateItemCommand({
					TableName: DYNAMODB_TABLE,
					Key: marshall({ PK: `USER#${userId}`, SK: `PORTFOLIO#${uploadId}` }),
					UpdateExpression: 'SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt',
					ExpressionAttributeNames: { '#status': 'status' },
					ExpressionAttributeValues: marshall({
						':status': 'DRAFT',
						':path': basePath,
						':updatedAt': now,
					}),
				})
			);

			await dynamodb.send(
				new UpdateItemCommand({
					TableName: DYNAMODB_TABLE,
					Key: marshall({ PK: `USER#${userId}`, SK: `UPLOAD#${uploadId}` }),
					UpdateExpression: 'SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt',
					ExpressionAttributeNames: { '#status': 'status' },
					ExpressionAttributeValues: marshall({
						':status': 'DRAFT_READY',
						':path': basePath,
						':updatedAt': now,
					}),
				})
			);
		}

		log('INFO', 'Portfolio generated', {
			correlationId,
			userId,
			uploadId,
			portfolioPath: basePath,
			target,
			finalizeUpload: Boolean(event.finalizeUpload),
		});

		return {
			statusCode: 200,
			body: JSON.stringify({ path: basePath, status: target === 'draft' ? (event.finalizeUpload ? 'DRAFT_READY' : 'DRAFT') : 'PUBLISHED' }),
		};
	} catch (err) {
		log('ERROR', 'Portfolio generation error', {
			correlationId,
			userId,
			uploadId,
			error: String(err),
		});

		// Mark the upload as FAILED so the frontend stops polling.
		if (userId && uploadId) {
			try {
				await dynamodb.send(
					new UpdateItemCommand({
						TableName: DYNAMODB_TABLE,
						Key: marshall({ PK: `USER#${userId}`, SK: `UPLOAD#${uploadId}` }),
						UpdateExpression: 'SET #status = :status, #updatedAt = :updatedAt',
						ExpressionAttributeNames: {
							'#status': 'status',
							'#updatedAt': 'updatedAt',
						},
						ExpressionAttributeValues: marshall({
							':status': 'FAILED',
							':updatedAt': new Date().toISOString(),
						}),
					})
				);
			} catch (dbErr) {
				log('ERROR', 'Failed to mark upload as FAILED', {
					correlationId,
					userId,
					uploadId,
					error: String(dbErr),
				});
			}
		}
		throw err;
	}
}
