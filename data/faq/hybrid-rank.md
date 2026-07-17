# What is hybrid / AI-assisted ranking?

**Rules only** ranks recommendable talent by the deterministic weighted score.

**AI-assisted rank (hybrid)** keeps the same hard gates and the same ≥70 shortlist rule. It only reorders the recommendable pool using:

`final = 0.85 * rule_score + 0.15 * feedback_prior`

Feedback prior comes from past Hire/Hold/Pass decisions and the talent rehire rate. Eligibility never changes under hybrid mode.
