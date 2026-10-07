# Governance

*Draft, open for review by the initial committers. Nothing here is final until they have reviewed it.*

This repository belongs to the LFDT lab `composable-evidence-criteria`. It holds test cases that pair evidence records from separately maintained specifications, and the criteria for judging whether those combinations still verify.

## Roles

**Committers** can merge changes. Initial committers: giskard09, azender1, magentixai, kenneives. Write access to this repository is administered by LF Decentralized Trust. Merges follow the rules below regardless of who holds it. A new committer is added when they have maintained test cases or criteria over time and an existing committer proposes them; the addition needs no objection from the other committers within 7 days. Nobody is listed as a committer before they have accepted.

**Contributors** are anyone who opens an issue or pull request. Running the test cases and reporting a result counts as a contribution; it does not make someone a committer.

## How changes are merged

1. **Author ≠ verifier.** A new test case or criterion is merged only after a committer other than its author has rerun it from the published bytes and confirmed the declared outcome.
2. **Every test case states where it came from.** It records which spec and which revision each side targets, who produced it, and whether each published run was made by the author or by someone independent.
3. **Disputed cases are marked, not deleted.** If a public issue shows a reproducible divergence, or a conflict with the pinned spec revision, the case is marked disputed. It stays marked until the issue is resolved in public. Removing the mark requires review by a committer other than the one who wrote the case.
4. **Decisions** are made by lazy consensus among committers in public issues. If a committer objects, the change waits until the objection is resolved or withdrawn. A merge by one maintainer is never described as agreement of the group.

## What the lab does not do

- It does not issue conformance verdicts or certify any implementation.
- It does not govern or amend the specifications it tests. Each spec keeps its own repository, license and maintainers.
- No specification, implementation or commercial product gets special standing, and the lab's outputs are not used to promote one.

## Conflicts of interest

Every committer declares their ties to the specifications and products the lab tests, and recuses from decisions that would directly benefit them: choosing which spec to prioritize, or designing a test case that would favor it.

Ties declared today:
- giskard09 maintains the action-ref specification and argentum-core.
- giskard09 and azender1 have a signed Revenue Share Agreement; azender1's SafeAgent uses action-ref in production.
- kenneives maintains AgentGraph/AgentAvow.
- magentixai (Martin Sansone) leads Magentix.AI, maintains AXES, and proposed the x402 Foundation TSC evidence-record charter (tsc#4).

A committer adds a new tie to this list when it arises.

## Working with other labs

Where another LFDT lab publishes test vectors in the same area, we reuse them rather than duplicate them, crediting the source and pinning the revision. Rules 2–4, the rule that nobody is listed as a committer before accepting, and the "does not do" list above follow the operating constraints published by the Agent Authority Conformance lab, credited to that lab. Collaboration between the two labs is being discussed with its maintainer; nothing is agreed yet.

## Changing this document

Changes to this file follow the same process as any other change, and need review from at least two committers other than the author.
