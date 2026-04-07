# Project Context Collection Guide

Collect project context before evaluation to ensure rules and conventions are respected.
Check the following sources **in order**, collecting only items that exist.

## 1. Project Rules

| Source | Collect |
|---|---|
| `CLAUDE.md` (project root) | Project-wide rules, conventions |
| `.claude/rules/*.md` | Detailed rule files |
| `eslint.config.*`, `.eslintrc.*` | Lint rules |
| `tsconfig.json` | TypeScript config (strict, paths, etc.) |

## 2. Project Structure & Dependencies

From `package.json`, identify key dependencies:

| Item | Examples |
|---|---|
| Framework | React / React Native / Next.js |
| State management | Redux Toolkit, Zustand, Recoil, Jotai |
| Styling | styled-components, Tailwind, CSS Modules |
| Testing | Jest, Vitest, Testing Library |

## 3. Directory Structure

`ls src/` or `ls app/` to identify architecture pattern:
- feature-based / layer-based / hybrid
