# **Refactoring Instructions: From CreditFlow AI to CreditGraph AI**

**Objective:** Update all references to the project name to reflect the new brand identity “CreditGraph AI.”

### **Tasks for the Agent:**

1. **Global Search and Replace:**  
   * Search for all occurrences of CreditFlow AI and replace them with CreditGraph AI.  
   * Search for all occurrences of CreditFlow (without the AI) and evaluate whether they should be changed to CreditGraph.  
   * *Note:* Keep file paths as they are for now to avoid breaking imports, unless explicitly requested to rename folders.  
2. **Documentation Update:**  
   * **README.md:** Change the main title and system descriptions.  
   * **docs/planning/prd.md:** Update the product name, vision, and any mentions in the glossary. Ensure the “Architecture” section mentions why the name “Graph” is now central.  
3. **Agent Identity (Prompts):**  
   * Review the files in app/agents/*/prompt.py (or wherever the system prompt definitions reside).  
   * Update the **Underwriter** prompt (app/agents/underwriter/node.py or similar) so that the model identifies itself as the “Brain of CreditGraph AI.”  
   * Adjust the output narrative in the **IRS Engine** agent to mention that the analysis was generated using the CreditGraph AI intelligence graph.  
4. **API and Metadata:**  
   * **app/api/models.py:** If there are descriptions in the Pydantic schemas that mention the old name, update them.  
   * **main.py:** Update the application title in the FastAPI instance: FastAPI(title=“CreditGraph AI API”, ...).  
5. **Consistency Check:**  
   * Ensure that the term **IRS (Internal Risk Score)** is retained, as it is the core metric of the graph.  
   * Verify that comments in files such as app/core/graph.py now reflect “CreditGraph Orchestration.”

**Final Instruction for Chat:** “Idequel wants to rename the project. Perform a comprehensive refactoring following these points. Prioritize consistency in AI prompts so that the models ‘know’ they are now part of CreditGraph AI.”