# Concept-Based Question Selection Flow

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER SUBMITS ANSWER                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MASTERY AGENT (Evaluation)                    │
│  - Analyzes SQL correctness                                      │
│  - Identifies weak_concepts: ["JOIN syntax", "WHERE clause"]     │
│  - Identifies missing_concepts: ["INNER JOIN", "GROUP BY"]       │
│  - Scores concept_understanding: {"JOIN syntax": 0.4}            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  STUDENT PROFILE AGENT                           │
│  1. Saves evaluation with weak concepts                          │
│  2. Tracks weak_concepts in dictionary:                          │
│     {                                                            │
│       "JOIN syntax": {occurrences: 3, severity: "high"},         │
│       "WHERE clause": {occurrences: 2, severity: "medium"}       │
│     }                                                            │
│  3. Tracks concept_gaps: ["INNER JOIN", "GROUP BY"]             │
│  4. Calculates priority_concepts (top 3 weak + top 3 gaps)      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                QUESTION PICKER AGENT                             │
│                                                                  │
│  Step 1: Extract Priority Concepts                              │
│  ┌────────────────────────────────────────────────────┐         │
│  │ priority_concepts = [                              │         │
│  │   "JOIN syntax",     ← from weak_concepts (3x)     │         │
│  │   "WHERE clause",    ← from weak_concepts (2x)     │         │
│  │   "INNER JOIN"       ← from concept_gaps           │         │
│  │ ]                                                  │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  Step 2: Select Cluster by Concept Coverage                     │
│  ┌────────────────────────────────────────────────────┐         │
│  │ For each cluster:                                  │         │
│  │   skills = ["JOIN operations", "WHERE filters"]    │         │
│  │   coverage_score = count matching priority concepts│         │
│  │                                                    │         │
│  │ Cluster A: skills=["JOIN", "ON clause"]           │         │
│  │   → coverage=2 (matches "JOIN syntax", "INNER JOIN")         │
│  │                                                    │         │
│  │ Cluster B: skills=["SELECT", "GROUP BY"]          │         │
│  │   → coverage=0 (no matches)                       │         │
│  │                                                    │         │
│  │ ✓ Select Cluster A (highest coverage)             │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  Step 3: Select Problem by Concept Richness                     │
│  ┌────────────────────────────────────────────────────┐         │
│  │ For each problem in Cluster A:                     │         │
│  │                                                    │         │
│  │ Problem 1:                                         │         │
│  │   summary: "Tests INNER JOIN with ON clause..."   │         │
│  │   weak_coverage = 2 (JOIN syntax, INNER JOIN)     │         │
│  │   skill_coverage = 2 (cluster skills)             │         │
│  │   score = 2*3 + 2*1 = 8                          │         │
│  │                                                    │         │
│  │ Problem 2:                                         │         │
│  │   summary: "Simple JOIN example..."               │         │
│  │   weak_coverage = 1 (JOIN syntax)                 │         │
│  │   skill_coverage = 1                              │         │
│  │   score = 1*3 + 1*1 = 4                          │         │
│  │                                                    │         │
│  │ ✓ Select Problem 1 (highest score = 8)            │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  CONCEPT-WISE PROGRESSION (not difficulty-wise)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISPLAY QUESTION                              │
│                                                                  │
│  🎯 This question targets your weak areas:                      │
│     JOIN syntax, INNER JOIN                                      │
│                                                                  │
│  📝 Question: [Selected concept-rich problem]                   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Decision Points

### 1. Concept Coverage Scoring
```python
coverage_score = sum(
    1 for concept in priority_concepts 
    if any(
        concept.lower() in skill.lower() or 
        skill.lower() in concept.lower() 
        for skill in cluster_skills
    )
)
```

**Example:**
- Priority: `["JOIN syntax", "INNER JOIN", "WHERE clause"]`
- Cluster skills: `["JOIN operations", "ON clause usage"]`
- Matches: "JOIN syntax" ↔ "JOIN operations", "INNER JOIN" ↔ "JOIN operations"
- Coverage score: **2**

### 2. Problem Richness Scoring
```python
total_score = (weak_concept_coverage × 3) + cluster_skill_coverage
```

**Example:**
- Problem covers 2 weak concepts: 2 × 3 = 6
- Problem covers 3 cluster skills: 3 × 1 = 3
- Total score: **9**

### 3. Fallback Logic
```
IF priority_concepts exist AND coverage > 0:
    → Use concept-based selection
ELSE:
    → Fallback to mastery-based selection (original logic)
```

## Comparison: Old vs New

### OLD (Difficulty-Based)
```
Mastery 0.3 → Difficulty 1-2 (Easy)
Mastery 0.5 → Difficulty 2-3 (Medium)
Mastery 0.7 → Difficulty 3-4 (Hard)
Mastery 0.9 → Difficulty 4-5 (Very Hard)
```
**Problem:** Student might master easy JOINs but never see WHERE clause concepts

### NEW (Concept-Based)
```
Weak: ["JOIN syntax"] → Find questions covering JOIN syntax
                         (regardless of difficulty)
                         
Weak: ["WHERE clause"] → Find questions covering WHERE clause
                          (regardless of difficulty)
```
**Benefit:** Student practices exact concepts they struggle with

## Real-World Example

### Session Timeline

**Question 1:** INNER JOIN basics
- **Answer:** `SELECT * FROM a, b WHERE a.id = b.id` (old-style JOIN)
- **Evaluation:** 
  - weak_concepts: `["modern JOIN syntax"]`
  - missing_concepts: `["INNER JOIN keyword"]`

**Question 2:** System response
- **Priority:** `["modern JOIN syntax", "INNER JOIN keyword"]`
- **Selected Cluster:** "INNER JOIN with explicit syntax" (coverage=2)
- **Selected Problem:** Comprehensive INNER JOIN with ON clause
- **NOT selected:** Easy subquery (coverage=0) even if student has low mastery

**Question 3:** Student improves
- **Answer:** Correct INNER JOIN usage
- **Evaluation:** 
  - weak_concepts: `["multi-table joins"]`
- **Next question:** Focuses on multi-table scenarios

## Performance Metrics

### Tracking Effectiveness

The system tracks:
1. **Weak Concept Occurrences:** How many times each concept appears as weak
2. **Concept Gap Coverage:** Which missing concepts are being addressed
3. **Mastery Improvement:** Score changes for specific concepts over time

### Success Indicators

✅ **Good:**
- Weak concepts decrease in occurrences over time
- Concept gaps get filled (removed from list)
- Overall mastery increases

❌ **Needs Attention:**
- Same weak concept appears 5+ times
- Concept gaps persist across 10+ questions
- Mastery plateaus

## Integration Points

### Data Flow Between Components

```
EvaluatorAgent.evaluate()
    ↓ (weak_concepts, missing_concepts)
StudentProfileAgent._track_weak_concepts()
    ↓ (weak_concepts dict, concept_gaps list)
StudentProfileAgent.get_weak_topics()
    ↓ (priority_concepts)
QuestionPickerAgent._extract_priority_concepts()
    ↓ (priority_concepts list)
QuestionPickerAgent._select_cluster_by_concept_coverage()
    ↓ (best cluster)
QuestionPickerAgent._select_problem_by_concept_richness()
    ↓ (best problem)
App.py displays question with targeting info
```

## Summary

**Core Innovation:** Questions are selected based on **what concepts the student struggles with**, not based on an arbitrary difficulty progression. This ensures every question is relevant and addresses actual learning gaps.

**Result:** More efficient, personalized learning that adapts to individual weaknesses in real-time.
