# Copilot Instructions

<!-- This file provides context to GitHub Copilot when working in this repository. -->
<!-- Update it as the project evolves to keep Copilot sessions effective. -->

## Build & Test

<!-- Add build, test, and lint commands as they are introduced. Example: -->
<!-- ```sh -->
<!-- npm install        # install dependencies -->
<!-- npm run build      # build the project -->
<!-- npm test           # run all tests -->
<!-- npm test -- --grep "pattern"  # run a single test by name -->
<!-- npm run lint       # lint the codebase -->
<!-- ``` -->

## Architecture

<!-- Describe the high-level structure once the project takes shape. Example: -->
<!-- - `src/api/` — REST API layer (Express routes and middleware) -->
<!-- - `src/core/` — Business logic, independent of transport layer -->
<!-- - `src/db/` — Database access via repository pattern -->
<!-- Entry point: `src/index.ts` -->

## Conventions

<!-- Document project-specific patterns that aren't obvious from a single file. Example: -->
<!-- - All async functions return `Result<T, AppError>` instead of throwing -->
<!-- - Environment config is loaded once in `src/config.ts` and injected via context -->
<!-- - Database migrations live in `migrations/` and are run with `npm run migrate` -->
