import unittest
from pathlib import Path

from app.matcher import extract_skills, missing_keywords, normalize, score_resume, text_similarity

FIXTURES = Path(__file__).parent / "fixtures"
JOB = (FIXTURES / "job_java_backend.txt").read_text()
RESUME = """Entry-level Java developer who builds REST APIs with Spring Boot and MySQL and writes
unit tests with JUnit. Comfortable with Git, OOP and data structures. Projects: Library Portal,
a Spring Boot and MySQL application serving 500 users with JWT login and 85% test coverage."""


class ExtractSkillsTest(unittest.TestCase):
    def test_finds_skills_by_alias(self):
        skills = extract_skills("Built APIs in SpringBoot with Postgres and node.js")
        self.assertIn("Spring Boot", skills)
        self.assertIn("PostgreSQL", skills)
        self.assertIn("Node.js", skills)

    def test_respects_symbols_and_word_boundaries(self):
        skills = extract_skills("Wrote C++ and C# code, used .NET; my github is public")
        self.assertIn("C++", skills)
        self.assertIn("C#", skills)
        self.assertIn(".NET", skills)
        self.assertIn("GitHub", skills)
        self.assertNotIn("Git", skills, "'git' inside 'github' must not count as Git")

    def test_ignores_ambiguous_everyday_words(self):
        skills = extract_skills("Take some rest in spring and express your ideas")
        self.assertEqual(skills, {})

    def test_returns_category(self):
        self.assertEqual(extract_skills("JUnit")["JUnit"], "Testing & QA")


class SimilarityTest(unittest.TestCase):
    def test_identical_text_is_fully_similar(self):
        self.assertAlmostEqual(text_similarity(JOB, JOB), 1.0, places=5)

    def test_unrelated_text_is_not_similar(self):
        self.assertLess(text_similarity("baking bread with flour and yeast", JOB), 0.05)

    def test_related_text_scores_higher_than_unrelated(self):
        self.assertGreater(text_similarity(RESUME, JOB), text_similarity("I enjoy gardening and painting", JOB))


class MissingKeywordsTest(unittest.TestCase):
    def test_reports_job_terms_absent_from_resume(self):
        terms = missing_keywords("I write Java code", "You will join code reviews and code reviews matter", set())
        self.assertIn("code reviews", terms)

    def test_skips_generic_words_and_terms_already_in_resume(self):
        terms = missing_keywords("I like code reviews", "Strong experience required. Code reviews.", set())
        self.assertNotIn("strong", terms)
        self.assertNotIn("code reviews", terms)


class ScoreTest(unittest.TestCase):
    def test_score_is_within_bounds_and_explained(self):
        r = score_resume(RESUME, JOB)
        self.assertTrue(0 <= r.score <= 100)
        self.assertIn(r.verdict, {"Strong match", "Good match with gaps", "Weak match"})
        self.assertIn("Java", r.matched_skills)
        self.assertIn("Docker", r.missing_skills)
        self.assertTrue(r.suggestions)

    def test_better_resume_scores_higher(self):
        weak = score_resume("I am a graphic designer skilled in Photoshop and illustration. " * 5, JOB)
        strong = score_resume(RESUME, JOB)
        self.assertGreater(strong.score, weak.score)
        self.assertEqual(weak.verdict, "Weak match")

    def test_job_without_known_skills_uses_similarity_only(self):
        r = score_resume(RESUME, "We need someone friendly and punctual to greet visitors at the front desk every morning.")
        self.assertIsNone(r.skill_coverage)

    def test_normalize_collapses_whitespace_and_dashes(self):
        self.assertEqual(normalize("A–B   C\n"), "a-b c")


if __name__ == "__main__":
    unittest.main()
