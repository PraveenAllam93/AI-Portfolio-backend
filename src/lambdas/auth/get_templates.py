"""
Lambda: Get Template Catalog
GET /templates — public, no authentication required.

Returns the list of available portfolio templates with metadata for
the frontend template picker. No AWS calls — pure in-memory response.
"""

import json
import os

ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Template catalog — keep ids in sync with VALID_TEMPLATE_IDS in:
#   upload/handler.py, auth/patch_portfolio.py, portfolio/handler.py
TEMPLATES = [
    {
        'id': 'modern',
        'name': 'Modern',
        'description': (
            'Clean blue gradient hero with professional typography '
            'and smooth hover transitions.'
        ),
        'accentColor': '#2563eb',
        'heroBg': 'linear-gradient(135deg, #2563eb, #1d4ed8)',
        'bodyBg': '#ffffff',
        'isPremium': False,
        'previewPath': 'templates/modern/preview.html',
    },
    {
        'id': 'minimal',
        'name': 'Minimal',
        'description': (
            'Ultra-clean monochrome layout. '
            'No gradients — just sharp typography and whitespace.'
        ),
        'accentColor': '#111827',
        'heroBg': '#ffffff',
        'bodyBg': '#ffffff',
        'isPremium': False,
        'previewPath': 'templates/minimal/preview.html',
    },
    {
        'id': 'bold',
        'name': 'Bold',
        'description': (
            'Dark slate background with high-contrast orange accents. '
            'Maximum visual impact.'
        ),
        'accentColor': '#f97316',
        'heroBg': 'linear-gradient(135deg, #0f172a, #1e293b)',
        'bodyBg': '#0f172a',
        'isPremium': False,
        'previewPath': 'templates/bold/preview.html',
    },
    {
        'id': 'creative',
        'name': 'Creative',
        'description': (
            'Two-column sidebar layout in teal. '
            'Skills and contact left, experience right.'
        ),
        'accentColor': '#0d9488',
        'heroBg': '#0d9488',
        'bodyBg': '#f8fafc',
        'isPremium': False,
        'previewPath': 'templates/creative/preview.html',
    },
    {
        'id': 'executive',
        'name': 'Executive',
        'description': (
            'Refined dark-green hero with gold accents and a '
            'timeline experience layout. Formal and premium.'
        ),
        'accentColor': '#b45309',
        'heroBg': 'linear-gradient(140deg, #14532d, #166534)',
        'bodyBg': '#fafaf9',
        'isPremium': True,
        'previewPath': 'templates/executive/preview.html',
    },
    {
        'id': 'nebula',
        'name': 'Nebula',
        'description': (
            'Cyberpunk dark-space with neon purple + cyan dual accents. '
            'Animated grid, drifting glow orbs, glassmorphism cards, '
            'gradient hero text, and "Hello I\'m" intro style.'
        ),
        'accentColor': '#a855f7',
        'heroBg': 'linear-gradient(135deg, #07070f, #1a0a2e)',
        'bodyBg': '#07070f',
        'isPremium': True,
        'previewPath': 'templates/nebula/preview.html',
    },
    {
        'id': 'aurora',
        'name': 'Aurora',
        'description': (
            'Aurora borealis animated gradient cycling teal to violet. '
            'Full glassmorphism with backdrop-filter blur on all cards. '
            'Syne 800w headings with emerald gradient text.'
        ),
        'accentColor': '#4ade80',
        'heroBg': (
            'linear-gradient(-45deg, #0d1b2a, #0a4a4a, #1a0a3e)'
        ),
        'bodyBg': '#0f172a',
        'isPremium': True,
        'previewPath': 'templates/aurora/preview.html',
    },
    {
        'id': 'luxury',
        'name': 'Luxury',
        'description': (
            'Ultra-premium editorial on deep midnight navy. '
            'Cormorant Garamond serif with gold shimmer sweep, '
            '"Hello, I am" italic intro, gold timeline experience, '
            'and animated gold underlines on headings.'
        ),
        'accentColor': '#c9a84c',
        'heroBg': '#060c18',
        'bodyBg': '#060c18',
        'isPremium': True,
        'previewPath': 'templates/luxury/preview.html',
    },
]


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type',
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'public, max-age=3600',
        },
        'body': json.dumps({'templates': TEMPLATES}),
    }
