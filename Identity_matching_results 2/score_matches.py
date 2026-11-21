"""Reproducible baseline identity comparison. Python 3 standard library only.
Usage: python3 score_matches.py [input_directory] [output_directory]
Scores are heuristic evidence scores, not probabilities or disposition decisions.
"""
import csv
import datetime as dt
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

WEIGHTS = {'name': .60, 'dob': .25, 'country': .10, 'city': .05}
MISSING = {'', 'unknown', 'n/a', 'na', 'null', 'none', 'not available', '-'}

def norm(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', value).split())

def known(value):
    return norm(value) not in MISSING and value.strip().casefold() not in MISSING

def name_similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return None
    if a == b or sorted(a.split()) == sorted(b.split()):
        return 1.0
    score = max(SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, ' '.join(sorted(a.split())), ' '.join(sorted(b.split()))).ratio())
    if set(a.split()) < set(b.split()) or set(b.split()) < set(a.split()):
        score = min(score, .85)
    return score

def dates(value):
    result = []
    for raw in value.split(';'):
        raw = raw.strip()
        if not re.fullmatch(r'\d{4}(?:-\d{2})?(?:-\d{2})?', raw):
            continue
        parts = tuple(map(int, raw.split('-')))
        try:
            dt.date(parts[0], parts[1] if len(parts)>1 else 1, parts[2] if len(parts)>2 else 1)
            result.append(parts)
        except ValueError:
            pass
    return result

def dob_comparison(a, b):
    left, right = dates(a), dates(b)
    if not left or not right:
        return None, 'unknown_or_unparseable'
    scores = []
    for x in left:
        for y in right:
            precision = min(len(x), len(y))
            scores.append({1: .70, 2: .85, 3: 1.0}[precision] if x[:precision] == y[:precision] else 0.0)
    score = max(scores)
    return score, {1.0: 'full_date_agreement', .85: 'year_month_agreement', .70: 'year_agreement', 0.0: 'date_conflict'}[score]

def contains_phrase(phrase, text):
    return (' '+norm(phrase)+' ') in (' '+norm(text)+' ')

def location(value, text):
    if not known(value) or not known(text):
        return None, 'unknown'
    if contains_phrase(value, text):
        return 1.0, 'location_mentioned'
    # Location lists are not exclusive; absence is weak negative evidence.
    return .25, 'not_found_in_available_locations'

def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)

def write(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def build(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    af, alerts = read(input_dir/'Alerts.csv')
    hf, hits = read(input_dir/'Hits.csv')
    if len({a['alert_id'] for a in alerts}) != len(alerts):
        raise ValueError('Duplicate alert_id: resolve ambiguous alerts before scoring.')
    if len({h['hit_id'] for h in hits}) != len(hits):
        raise ValueError('Duplicate hit_id: resolve before scoring.')
    lookup = {a['alert_id']: a for a in alerts}
    amap = {'screened_at':'screening_date', 'customer_name':'full_name', 'dob':'date_of_birth', 'country':'country', 'city':'city', 'account_ref':'internal_account_reference', 'login_handle':'login_handle', 'email':'email', 'hit_count':'reported_hit_count', 'hit_ids':'reported_hit_ids'}
    hmap = {'name':'full_name', 'dobs':'dates_of_birth', 'countries':'associated_countries', 'addresses':'addresses', 'match_score':'original_match_score', 'sources':'source_details'}
    ar = [{amap.get(k,k):v for k,v in a.items()} for a in alerts]
    output, features = [], []
    for h in hits:
        a = lookup.get(h['alert_id'])
        row = {hmap.get(k,k):v for k,v in h.items()}
        company = bool(a and norm(a['entity_type']) == 'company')
        eligible = {k:v for k,v in WEIGHTS.items() if not(company and k=='dob')}
        vals = {k: None for k in WEIGHTS}
        statuses = {k:'unknown' for k in WEIGHTS}
        entity_status, best_name = 'unknown', ''
        if a:
            candidates = [h['name']] + [re.sub(r'\s*\([^)]*\)', '', x).strip() for x in h['aliases'].split(';')]
            candidates = [x for x in candidates if known(x)]
            if known(a['customer_name']) and candidates:
                best_name = max(candidates, key=lambda n:name_similarity(a['customer_name'], n) or 0)
                vals['name'] = name_similarity(a['customer_name'], best_name)
                statuses['name'] = 'main_name' if best_name == h['name'] else 'alias'
            if company:
                statuses['dob'] = 'not_applicable_company'
            else:
                vals['dob'], statuses['dob'] = dob_comparison(a['dob'],h['dobs'])
            loc = '; '.join(x for x in [h['countries'], h['addresses']] if known(x))
            vals['country'], statuses['country'] = location(a['country'],loc)
            vals['city'], statuses['city'] = location(a['city'],h['addresses'])
            if known(a['entity_type']) and known(h['entity_type']):
                entity_status = 'agreement' if norm(a['entity_type']) == norm(h['entity_type']) else 'conflict'
        available = sum(w for k,w in eligible.items() if vals[k] is not None)
        coverage = available/sum(eligible.values())
        similarity = sum(w*vals[k] for k,w in eligible.items() if vals[k] is not None)/available if available else None
        score = 100*similarity*(.5+.5*coverage) if similarity is not None else None
        conflicts = []
        if entity_status == 'conflict':
            conflicts.append('entity_type_conflict')
            if score is not None:
                score = min(score,20)
        if statuses['dob'] == 'date_conflict':
            conflicts.append('date_of_birth_conflict')
        reason = [f'{k}: {statuses[k]}' for k in WEIGHTS]
        if not a:
            reason.append('alert_id_not_found')
        row.update({'best_matching_name':best_name, 'entity_type_comparison':entity_status})
        for k,v in vals.items():
            row[k+'_similarity'] = round(100*v,2) if v is not None else ''
        row.update({'evidence_coverage':round(100*coverage,2), 'available_evidence_similarity':round(100*similarity,2) if similarity is not None else '', 'conflict_flags':'; '.join(conflicts), 'match_reason':'; '.join(reason), 'score_method':'weighted_baseline_v1', 'match_score':round(score,2) if score is not None else ''})
        output.append(row)
        feat = {'alert_id':h['alert_id'], 'hit_id':h['hit_id'], 'entity_type_conflict':int(entity_status=='conflict')}
        for k,v in vals.items():
            feat[k+'_similarity'] = round(v,6) if v is not None else ''
            feat[k+'_missing'] = int(v is None)
        feat['reviewed_same_person'] = ''
        features.append(feat)
    write(output_dir/'Alerts_clean.csv', [amap.get(k,k) for k in af], ar)
    write(output_dir/'Hits_scored.csv', list(output[0]), output)
    write(output_dir/'Training_review.csv', list(features[0]), features)
    dictionary = []
    for dataset, fields, mapping in [('Alerts',af,amap),('Hits',hf,hmap)]:
        for old in fields:
            dictionary.append({'dataset':dataset, 'original_column':old, 'clean_column':mapping.get(old,old), 'role':'preserved_source_data'})
    for field in list(output[0])[len(hf):]:
        dictionary.append({'dataset':'Hits','original_column':'','clean_column':field,'role':'derived_comparison_or_score'})
    write(output_dir/'Column_mapping.csv',list(dictionary[0]),dictionary)
    summary = {'alerts':len(alerts),'hits':len(hits),'unlinked_hits':sum(h['alert_id'] not in lookup for h in hits),'company_alerts':sum(a['entity_type']=='Company' for a in alerts),'entity_type_conflicts':sum(r['entity_type_comparison']=='conflict' for r in output),'dob_conflicts':sum('date_of_birth_conflict' in r['conflict_flags'] for r in output),'unscored_hits':sum(r['match_score']=='' for r in output),'score_min':min(r['match_score'] for r in output if r['match_score']!=''),'score_max':max(r['match_score'] for r in output if r['match_score']!=''),'comparison_availability':{k:sum(r[k+'_similarity']!='' for r in output) for k in WEIGHTS}}
    (output_dir/'Validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Verify source preservation, order, score bounds, and final-column contract.
    assert len(output)==len(hits) and len(ar)==len(alerts)
    for old,new in zip(hits,output):
        assert all(new[hmap.get(k,k)]==v for k,v in old.items())
        assert new['match_score']=='' or 0<=new['match_score']<=100
    assert list(output[0])[-1]=='match_score'
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    build(Path(sys.argv[1] if len(sys.argv)>1 else 'inputs'),Path(sys.argv[2] if len(sys.argv)>2 else 'outputs'))
