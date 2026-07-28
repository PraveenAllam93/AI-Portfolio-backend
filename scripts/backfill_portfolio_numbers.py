#!/usr/bin/env python3
"""
Backfill permanent portfolio numbers for portfolios created before numbering
existed.

Assigns numbers in createdAt order so the sequence matches the order the user
actually made them, then points the bare /u/{username} at the oldest one as the
default "main" portfolio.

Safe to re-run: portfolios that already have a portfolioNumber are skipped, the
counter is only advanced for portfolios that genuinely need one, and PNUM#main
is only written when the user has none.

Usage:
    AWS_PROFILE=aifolio-praveen python3 scripts/backfill_portfolio_numbers.py [--apply]

Without --apply it prints what it would do and changes nothing.
"""

import argparse
import os
import sys
from collections import defaultdict

import boto3

TABLE = os.environ.get('DYNAMODB_TABLE', 'ai-portfolio-dev-main-table')
REGION = os.environ.get('AWS_REGION', 'ap-south-1')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='actually write changes')
    args = parser.parse_args()

    table = boto3.resource('dynamodb', region_name=REGION).Table(TABLE)

    # Collect every portfolio record. A scan is acceptable here: this is a
    # one-off migration, not a request path.
    portfolios = defaultdict(list)
    kwargs = {}
    while True:
        page = table.scan(**kwargs)
        for item in page.get('Items', []):
            pk, sk = item.get('PK', ''), item.get('SK', '')
            if not pk.startswith('USER#') or not sk.startswith('PORTFOLIO#'):
                continue
            if '#VERSION#' in sk:
                continue
            portfolios[pk[len('USER#'):]].append(item)
        if 'LastEvaluatedKey' not in page:
            break
        kwargs['ExclusiveStartKey'] = page['LastEvaluatedKey']

    if not portfolios:
        print('No portfolios found.')
        return 0

    total_assigned = 0

    for user_id, items in portfolios.items():
        items.sort(key=lambda i: i.get('createdAt') or '')

        needing = [i for i in items if i.get('portfolioNumber') is None]
        existing_main = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PNUM#main'}
        ).get('Item')

        print(f'\nUSER#{user_id}')
        print(f'  portfolios: {len(items)}  needing a number: {len(needing)}'
              f'  main set: {bool(existing_main)}')

        for item in needing:
            upload_id = item.get('uploadId') or item['SK'][len('PORTFOLIO#'):]

            if not args.apply:
                print(f'  would assign a number to {upload_id} '
                      f'(created {item.get("createdAt", "?")})')
                total_assigned += 1
                continue

            result = table.update_item(
                Key={'PK': f'USER#{user_id}', 'SK': 'COUNTER#PORTFOLIO'},
                UpdateExpression='ADD #seq :one',
                ExpressionAttributeNames={'#seq': 'seq'},
                ExpressionAttributeValues={':one': 1},
                ReturnValues='UPDATED_NEW',
            )
            number = int(result['Attributes']['seq'])

            table.put_item(Item={
                'PK': f'USER#{user_id}',
                'SK': f'PNUM#{number}',
                'uploadId': upload_id,
                'portfolioNumber': number,
                'createdAt': item.get('createdAt', ''),
            })
            table.update_item(
                Key={'PK': f'USER#{user_id}', 'SK': item['SK']},
                UpdateExpression='SET portfolioNumber = :n',
                ExpressionAttributeValues={':n': number},
            )
            print(f'  assigned #{number} -> {upload_id}')
            total_assigned += 1

        # Default the main portfolio to the oldest one that has a number.
        if not existing_main and items:
            first = items[0]
            first_upload = first.get('uploadId') or first['SK'][len('PORTFOLIO#'):]
            if args.apply:
                refreshed = table.get_item(
                    Key={'PK': f'USER#{user_id}', 'SK': first['SK']}
                ).get('Item') or {}
                number = refreshed.get('portfolioNumber')
                if number is not None:
                    table.put_item(Item={
                        'PK': f'USER#{user_id}',
                        'SK': 'PNUM#main',
                        'uploadId': first_upload,
                        'portfolioNumber': int(number),
                        'createdAt': first.get('createdAt', ''),
                    })
                    print(f'  main -> #{int(number)} ({first_upload})')
            else:
                print(f'  would set main -> {first_upload}')

    print(f'\n{"Assigned" if args.apply else "Would assign"} {total_assigned} number(s).')
    if not args.apply:
        print('Re-run with --apply to write.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
