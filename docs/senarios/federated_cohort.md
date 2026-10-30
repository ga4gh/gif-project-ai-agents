## Scenario 1: Federated Cohort Query and Variant Analysis

**Researcher prompt:** "I want to find datasets that include African-ancestry participants with type 2 diabetes phenotypes and run a variant quality filtering pipeline on those samples."

**Agent workflow:**

- **Discovery:** Query the GA4GH registry MCP server to identify Beacon and/or Data Connect endpoints at participating sites. Submit phenotype queries to discover cohorts matching the researcher's criteria.
- **Authorization:** Retrieve GA4GH Passport visas scoped to the identified datasets. Pass visas to DRS servers to resolve dataset access URLs.
- **Workflow selection:** Query Dockstore (TRS) to identify a suitable variant QC workflow available as a WES-submittable descriptor.
- **Execution:** Submit the WES workflow run to a participating compute site, referencing input data via DRS URIs. Monitor run status.
- **Results:** Return outputs (DRS-registered result files) and a run summary to the researcher.

![Federated Cohort Mermaid](federated_cohort.png)