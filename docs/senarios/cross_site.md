## Scenario 2: Cross-Site Workflow Orchestration

**Researcher prompt:** "Run the GA4GH standard GATK germline variant calling pipeline on the WGS samples registered in site B's data catalog, using the compute available at site A."

**Agent workflow:**

- **Discovery:** Use the registry MCP to enumerate WES endpoints at site A and DRS/Data Connect endpoints at site B.
- **Tool resolution:** Resolve the GATK pipeline from Dockstore using TRS, obtaining a versioned, checksummed WDL descriptor.
- **Authorization:** Obtain cross-site Passport visas enabling the compute job at site A to pull input data from site B's DRS server.
- **Execution:** Submit the WDL workflow to site A's WES endpoint, with DRS URIs pointing to site B's data. Monitor and retrieve results.

![Cross-site Workflow Mermaid](cross-site.png)