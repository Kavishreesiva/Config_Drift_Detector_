# Prompts Used During Development

## 1. Config Drift Analysis Prompt
Used to analyze differences between intended and actual config files.

**Prompt:**
"You are a config drift analyzer. Given the following differences between intended and actual configuration files, explain what each change means and rate the severity as Cosmetic, Functional, or Breaking."

## 2. Risk Score Prompt
Used to calculate overall risk score.

**Prompt:**
"Based on the configuration differences provided, calculate a risk score from 0-100 and explain the reasoning."

## 3. Summary Report Prompt
Used to generate a summary report.

**Prompt:**
"Summarize the configuration drift analysis in a clear, concise report suitable for a DevOps team."

## What AI Got Wrong
- Sometimes misclassified minor changes as Breaking severity
- Occasionally gave generic explanations instead of specific ones

## Best Prompts
- Being specific about severity levels (Cosmetic/Functional/Breaking) gave better results
- Adding context about the file type improved AI explanations
