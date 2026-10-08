# AI prompts

Every prompt is versioned as name_vN (for example job_analysis_v1). The version is stored with
every result, so you can always tell which prompt produced a stored score.

Rules
- Never edit a published version. Add a new one (job_analysis_v2), switch the call site to it,
  and keep the old text for reference.
- Prompts live in backend/app/ai/prompts/ and are registered in prompts/__init__.py.
- Placeholders use $name and are filled by Prompt.render. A missing value raises an error.
- Only verified facts go into a prompt. Contact details never do.

## job_analysis_v1
Purpose: judge how well one job fits the verified career profile.

Inputs: verified candidate facts (confirmed skills, usable bullets, projects, education,
certifications, years of experience), plus the job title, company, location, workplace, stated
minimum years, detected required and preferred technologies, and the job description (cut at
7000 characters).

The AI returns (schema JobAnalysisAI in backend/app/jobs/analysis.py):
- technical_match, seniority_match, domain_match: integers 0 to 100
- confirmed_matches and partial_matches: each cites an evidence_ref (a skill, project, or employer
  that exists in the career profile)
- gaps, uncertain_requirements, risks, summary

Computed by rules, not by the AI: experience, location, authorization, role relevance, and the
overall score (weights in backend/app/jobs/scoring.py).

Checks on every answer: valid JSON, matches the schema, every evidence_ref exists in the career
profile, and the technical score is within 35 points of a keyword check when three or more
required technologies were detected. A failed check is retried with the reason, then falls back to
the next provider, then the job is marked needs_review.
