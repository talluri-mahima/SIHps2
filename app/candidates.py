"""Conservative field candidates from varied English labels. No LLM decisions."""
import re
from decimal import Decimal

ALIASES = {
    'BUILDING': ['building', 'building name', 'block', 'block name'],
    'CLAIMED_FLOORS': ['claimed floors', 'instructional floors', 'classroom floors'],
    'COVERED_FLOORS': ['covered floors', 'floors covered', 'permitted floors', 'approved floors', 'occupancy scope'],
    'FDR_NUMBER': ['fdr number', 'fdr no', 'fixed deposit number', 'fixed deposit no', 'deposit receipt no', 'fd no'],
    'HOLDER': ['holder', 'account holder', 'depositor', 'name of depositor', 'depositor name'],
    'BANK': ['bank', 'bank name', 'issuing bank'],
    'PRINCIPAL_INR': ['principal inr', 'principal amount', 'deposit amount', 'principal'],
    'LIEN_INR': ['lien inr', 'lien amount', 'amount under lien', 'pledged amount'],
    'UNRESTRICTED_CLAIM_INR': ['unrestricted claim inr', 'unrestricted funding', 'unrestricted funds', 'unencumbered funds'],
    'VALID_UNTIL': ['valid until', 'valid upto', 'valid up to', 'expiry date', 'expires on', 'date of expiry'],
}


def canonical_label(label):
    return re.sub(r'[^a-z0-9]+', ' ', label.lower()).strip()


LABELS = {canonical_label(alias): key for key, aliases in ALIASES.items() for alias in [key, *aliases]}


def candidate_value(key, raw):
    value = raw.strip()
    if key.endswith('_INR'):
        match = re.fullmatch(r'(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)\s*(crores?|cr\.?|lakhs?|lacs?)?(?:\s*(?:INR|rupees))?', value, re.I)
        if not match:
            raise ValueError('Ambiguous amount')
        amount = Decimal(match[1].replace(',', ''))
        unit = (match[2] or '').lower()
        amount *= 10000000 if unit.startswith(('cr', 'crore')) else 100000 if unit.startswith(('lac', 'lakh')) else 1
        return str(amount)
    if key.endswith('FLOORS'):
        mapping = {'ground': 'G', 'ground floor': 'G', 'first': '1', 'first floor': '1',
                   'second': '2', 'second floor': '2', 'third': '3', 'third floor': '3',
                   'fourth': '4', 'fourth floor': '4'}
        parts = re.split(r'\s*(?:,|;|\band\b|&)\s*', value, flags=re.I)
        return ', '.join(mapping.get(p.lower().strip(), p.strip()) for p in parts)
    if key == 'VALID_UNTIL':
        # Ambiguous numeric dates never guessed. ISO or explicit English month.
        from datetime import datetime
        for fmt in ('%Y-%m-%d', '%d %B %Y', '%d %b %Y'):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError('Ambiguous date')
    return value


def labelled_candidate(text):
    match = re.fullmatch(r'(.{2,60}?)\s*[:=]\s*(.{1,200})', text.strip())
    if not match:
        return None
    key = LABELS.get(canonical_label(match[1]))
    if not key:
        return None
    return key, match[2], candidate_value(key, match[2])


def classify(lines):
    text = ' '.join(lines).lower()
    markers = {'OCCUPANCY': ['occupancy certificate', 'completion certificate'],
               'FIRE_CERTIFICATE': ['fire safety', 'fire certificate', 'fire service licence', 'fire & rescue service licence', 'fire and rescue services licence'],
               'FDR_ADVICE': ['fixed deposit receipt', 'fixed deposit advice', 'fdr advice'],
               'DPR': ['detailed project report', 'dpr'], 'ROOM_SCHEDULE': ['room schedule', 'classroom schedule'],
               'PRIOR_EOA': ['extension of approval', 'eoa report'], 'LIEN_EVIDENCE': ['lien advice', 'pledge advice']}
    return [{'kind': kind, 'basis': 'KEYWORD_HEURISTIC_NOT_CALIBRATED', 'matches': [p for p in phrases if p in text]}
            for kind, phrases in markers.items() if any(p in text for p in phrases)]
