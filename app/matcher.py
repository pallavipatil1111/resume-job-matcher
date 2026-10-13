"""Score how well a resume matches a job description.

The score combines two signals so it can be explained to the user:

* skill coverage (60%) - which skills named in the job description also appear in the resume,
  matched against a curated list of ~100 skills and their common spellings (data/skills.json)
* text similarity (40%) - cosine similarity of the two texts as term-frequency vectors (words and word pairs)

It also reports the job's most frequent important terms that the resume never mentions.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

SKILLS_FILE = Path(__file__).parent / "data" / "skills.json"

SKILL_WEIGHT = 0.6
SIMILARITY_WEIGHT = 0.4
# Cosine similarity between a resume and a job post rarely goes above ~0.35
# (they are different kinds of documents), so 0.35 counts as "fully similar".
SIMILARITY_CEILING = 0.35

# Words that are frequent in job posts but say nothing about the job itself
GENERIC_TERMS = set(ENGLISH_STOP_WORDS) | {
    "ability", "able", "candidate", "candidates", "company", "experience", "experienced", "good",
    "job", "join", "knowledge", "looking", "plus", "preferred", "required", "requirements", "role",
    "responsibilities", "skills", "strong", "team", "teams", "understanding", "work", "working",
    "year", "years", "including", "etc", "using", "use", "new", "help", "opportunity", "excellent",
    "related", "degree", "bachelor", "field", "familiarity", "proficiency", "proficient", "hands",
    "level", "minimum", "must", "nice", "apply", "location", "salary", "lpa", "per", "annum",
    "fresher", "freshers", "graduate", "graduates", "b.tech", "btech", "b.e", "will", "day", "days",
    "basic", "associate", "clean", "contribute", "participate", "write", "writing", "engineer", "engineers",
    "engineering", "software", "application", "applications", "exposure", "maintainable", "programming",
    "language", "languages", "senior", "junior", "member", "members", "environment", "best", "practices",
    "hiring", "hire", "developer", "developers", "fundamentals", "build", "building", "design", "designing",
}


@dataclass
class MatchResult:
    score: int
    verdict: str
    similarity: float
    skill_coverage: float | None
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    extra_skills: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def normalize(text: str) -> str:
    text = text.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


@lru_cache(maxsize=1)
def _skill_patterns() -> list[tuple[str, str, re.Pattern]]:
    """(canonical name, category, compiled regex) for every alias in skills.json."""
    data = json.loads(SKILLS_FILE.read_text(encoding="utf-8"))
    patterns = []
    for category, skills in data.items():
        for name, aliases in skills.items():
            for alias in aliases:
                # word boundaries that also respect symbols like c++, c#, .net, node.js
                rx = re.compile(r"(?<![\w+#.])" + re.escape(alias) + r"(?![\w+#])")
                patterns.append((name, category, rx))
    return patterns


@lru_cache(maxsize=1)
def _all_aliases() -> set[str]:
    words = set()
    for name, _category, rx in _skill_patterns():
        words.add(name.lower())
    data = json.loads(SKILLS_FILE.read_text(encoding="utf-8"))
    for skills in data.values():
        for aliases in skills.values():
            for alias in aliases:
                words.update(alias.split())
    return words


def extract_skills(text: str) -> dict[str, str]:
    """Return {skill name: category} for every known skill mentioned in the text."""
    text = normalize(text)
    found = {}
    for name, category, rx in _skill_patterns():
        if name not in found and rx.search(text):
            found[name] = category
    return found


def text_similarity(resume: str, job: str) -> float:
    # Plain term frequencies: with only two documents, IDF would down-weight exactly the
    # words they share, which is the opposite of what we want to measure.
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, use_idf=False)
    matrix = vec.fit_transform([normalize(resume), normalize(job)])
    return float(cosine_similarity(matrix[0], matrix[1])[0, 0])


def missing_keywords(resume: str, job: str, skills_in_job: set[str], limit: int = 8) -> list[str]:
    """Most frequent meaningful terms in the job description that never appear in the resume."""
    job_n, resume_n = normalize(job), normalize(resume)
    vec = CountVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)\b[a-z][a-z0-9+#.-]{2,}\b")
    counts = vec.fit_transform([job_n]).toarray()[0]
    terms = sorted(zip(vec.get_feature_names_out(), counts), key=lambda t: (-t[1], t[0]))
    skill_words = {s.lower() for s in skills_in_job} | _all_aliases()
    out = []
    for term, _count in terms:
        words = term.split()
        if any(w in GENERIC_TERMS or w in skill_words for w in words):
            continue
        if term in resume_n:
            continue
        if any(term in kept or kept in term for kept in out):
            continue
        out.append(term)
        if len(out) == limit:
            break
    return out


def _verdict(score: int) -> str:
    if score >= 75:
        return "Strong match"
    if score >= 50:
        return "Good match with gaps"
    return "Weak match"


def _suggestions(result: MatchResult, resume: str, job_skills: dict[str, str]) -> list[str]:
    tips = []
    for skill in result.missing_skills[:3]:
        tips.append(
            f"The job asks for {skill}. If you have used it, add it to your skills and show it in a project bullet."
        )
    if result.similarity < 0.15:
        tips.append("Your resume uses different wording from the job post. Describe your work with the job's own terms where they are true for you.")
    numbers = re.findall(r"\d+(?:\.\d+)?\s*(?:%|x|k|\+|users|ms|seconds|hours|lpa)", normalize(resume))
    if len(numbers) < 3:
        tips.append("Add numbers to your bullets (users, records, response time, test coverage) so impact is easy to see.")
    words = len(resume.split())
    if words < 200:
        tips.append("Your resume text is short. Add a line or two of detail to each project.")
    elif words > 900:
        tips.append("Your resume is long for a fresher role. Aim for one page.")
    if not tips:
        tips.append("Good alignment. Tailor your summary to name this role and company before you apply.")
    return tips[:5]


def score_resume(resume_text: str, job_text: str) -> MatchResult:
    job_skills = extract_skills(job_text)
    resume_skills = extract_skills(resume_text)

    matched = sorted(s for s in job_skills if s in resume_skills)
    missing = sorted(s for s in job_skills if s not in resume_skills)
    extra = sorted(s for s in resume_skills if s not in job_skills)

    similarity = text_similarity(resume_text, job_text)
    sim_scaled = min(1.0, similarity / SIMILARITY_CEILING)

    if job_skills:
        coverage = len(matched) / len(job_skills)
        raw = SKILL_WEIGHT * coverage + SIMILARITY_WEIGHT * sim_scaled
    else:
        coverage = None
        raw = sim_scaled
    score = round(100 * raw)

    result = MatchResult(
        score=score,
        verdict=_verdict(score),
        similarity=round(similarity, 3),
        skill_coverage=None if coverage is None else round(coverage, 3),
        matched_skills=matched,
        missing_skills=missing,
        extra_skills=extra,
        missing_keywords=missing_keywords(resume_text, job_text, set(job_skills)),
    )
    result.suggestions = _suggestions(result, resume_text, job_skills)
    return result
