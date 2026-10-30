import collections
import json
import math
import re
from pathlib import Path

LEGACY_KK = str.maketrans('ќґѕєјўїЌҐЅЄЈЎЇ', 'қғңәөұүҚҒҢӘӨҰҮ')

def normalize(text):
    return str(text).translate(LEGACY_KK).lower().replace('ё', 'е')

def tokens(text):
    return re.findall(r'[\w]+', normalize(text), re.UNICODE)

class RuleIndex:
    """BM25 over individually addressable rule points; IDs include section context."""
    def __init__(self, path):
        self.points = []
        source = json.loads(Path(path).read_text(encoding='utf-8'))
        for section in source['rules']:
            for point in section.get('points', []):
                self.points.append({
                    'id': f"{section['id']}:{point['ref']}",
                    'ref': point['ref'], 'section': section['category'],
                    'text': point['text'], 'section_id': section['id'],
                })
            if not section.get('points') and section.get('text'):
                self.points.append({'id':f"{section['id']}:section",'ref':section['category'],
                    'section':section['category'],'text':section['text'],'section_id':section['id'],
                    'citation_type':'section'})
        self.tf = [collections.Counter(tokens(p['text'])) for p in self.points]
        self.df = collections.Counter(t for counts in self.tf for t in counts)
        self.avg = sum(sum(c.values()) for c in self.tf) / max(1, len(self.tf))

    def search(self, query, refs=(), limit=4):
        words = set(tokens(query))
        ranked = []
        for p, counts in zip(self.points, self.tf):
            length = sum(counts.values())
            score = sum(math.log(1 + (len(self.points)-self.df[w]+.5)/(self.df[w]+.5)) *
                        counts[w]*2.5/(counts[w]+1.5*(.25+.75*length/self.avg))
                        for w in words if counts[w])
            # Taxonomy references are hints. Qualified IDs disambiguate repeated refs.
            if p['ref'] in refs:
                score += 4
            if score > 0:
                ranked.append((score, p))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]['id']))
        return [dict(p, score=round(score, 3)) for score, p in ranked[:limit]]
