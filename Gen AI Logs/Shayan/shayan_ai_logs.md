# Generative AI Chat Log

**Name:** Shayan Ashish Chakaborty

---

## 1. Home Page UI Design

**Prompt:**

"What are the key UI/UX principles I should consider when designing a landing page for a Dublin Bikes web app that displays real-time station data?"

**AI Response Summary:**

The AI recommended prioritising clarity and immediate data visibility, suggesting a map-centric layout as the primary interface with station data surfaced through interactive elements. It also advised keeping the landing experience focused rather than loading all information at once.

**How I Used It:**

I adopted the map-first approach but restructured the page layout based on what made sense for our specific workflow. Rather than displaying all data on a single page, I split station and weather information into separate views, keeping the home page focused on real-time availability. This reduced visual overload and gave users a clearer entry point into the app.

---

## 2. Home Page Flask Debugging

**Prompt:**

"My Flask app is throwing a 500 error when trying to render the home page — what are the most common reasons this happens and how do I systematically debug it?"

**AI Response Summary:**

The AI outlined common causes including missing template variables, broken route logic, and unhandled exceptions in backend functions. It suggested checking the Flask debug logs and isolating each route to narrow down the source of the error.

**How I Used It:**

I used this as a checklist when diagnosing my own 500 errors. The suggestion to check for missing template context variables was directly useful — I identified that a variable expected by the template was not being passed correctly from the route function. I also enabled Flask's debug mode during development to surface more detailed error traces.

---

## 3. Responsive Layout

**Prompt:**

"I have a home page that loads station data but the layout feels cluttered on smaller screens. What are some approaches to structuring a responsive UI with HTML and CSS?"

**AI Response Summary:**

The AI suggested using CSS flexbox and grid for responsive layouts, along with media queries to adjust element sizing and spacing at different breakpoints. It also recommended simplifying content density on smaller viewports.

**How I Used It:**

I applied flexbox to reorganise the layout and added media queries to adjust the spacing and sizing of key components on smaller screens. I did not implement a full responsive framework; instead, I focused on the most critical breakpoints relevant to the app's expected usage.

---

## 4. Dynamic Data Display

**Prompt:**

"What is the best way to display dynamic data on a webpage that updates without requiring a full page reload?"

**AI Response Summary:**

The AI explained using the Fetch API with async/await to retrieve data from a backend endpoint and update the DOM directly, avoiding full page reloads. It also mentioned using intervals for periodic refresh.

**How I Used It:**

I implemented periodic data fetching using setInterval combined with async fetch calls to the Flask backend. Station availability data is updated on the map without reloading the page, improving the real-time feel of the interface. I adjusted the refresh interval based on what felt reasonable for the data update frequency.

---

## 5. Weather Page UI

**Prompt:**

"I'm building a weather page for my Dublin Bikes app. What weather metrics are most relevant to bike-sharing users and how should I think about presenting them visually?"

**AI Response Summary:**

The AI suggested prioritising temperature, precipitation, wind speed, and general conditions as the most relevant metrics for bike users. It recommended separating a concise summary view from a more detailed breakdown.

**How I Used It:**

I structured the weather page with a high-level summary at the top and more detailed metrics below. I also introduced a navigation bar element showing current temperature and a weather icon across all pages, so users always have basic weather context regardless of which page they are on.

---

## 6. Weather API Rendering Issues

**Prompt:**

"I'm fetching weather data from an external API in Flask and passing it to my frontend, but the data sometimes doesn't render correctly. What should I check to debug this?"

**AI Response Summary:**

The AI recommended checking that API response fields match what the frontend expects, verifying that the data is being correctly serialised before being passed to the template, and adding error handling for cases where fields are missing or null.

**How I Used It:**

I traced the issue to inconsistent field names between the API response and what the frontend was referencing. I standardised the field names in the Flask route before passing the data to the template, and added fallback values for fields that were occasionally absent in the API response.

---

## 7. Cross-Browser CSS Inconsistencies

**Prompt:**

"My weather page UI looks inconsistent across different browsers. What are the common CSS issues that cause this and how do I approach fixing them?"

**AI Response Summary:**

The AI identified common culprits including browser default stylesheets, inconsistent handling of flexbox properties, and font rendering differences. It suggested using a CSS reset and testing with browser developer tools.

**How I Used It:**

I applied a basic CSS reset to remove default browser styling and adjusted a few flexbox properties that were behaving differently across browsers. I used Chrome and Firefox developer tools to identify the specific elements causing visual inconsistencies.

---

## 8. Machine Learning Model Selection

**Prompt:**

"What is the general process for training a machine learning model to predict bike availability using historical data? What factors should I consider before choosing a model type?"

**AI Response Summary:**

The AI outlined a general pipeline from data collection and cleaning through feature selection, model training, and evaluation. It suggested considering the nature of the target variable and the size and structure of the dataset before selecting a model type.

**How I Used It:**

I used this as a framework to structure my approach before writing any code. After reviewing the dataset, I decided on a regression model given that the target variable was a continuous count of available bikes. This helped me narrow down which models to explore and how to evaluate them.

---

## 9. Feature Engineering

**Prompt:**

"I have a Dublin Bikes dataset with timestamps, station data, and weather conditions. How should I think about feature engineering before training a prediction model?"

**AI Response Summary:**

The AI recommended extracting time-based features such as hour of day and day of week, encoding weather conditions numerically, and normalising continuous variables before training.

**How I Used It:**

I extracted hour and day-of-week features from the timestamps, which turned out to be among the most predictive variables. I encoded weather condition categories numerically and normalised the remaining continuous features before training. I did not implement holiday detection at this stage as the data did not clearly label public holidays.

---

## 10. Model Accuracy Investigation

**Prompt:**

"I trained a model but the accuracy seems low. What are the typical reasons a regression model underperforms on time-series transport data and how do I investigate?"

**AI Response Summary:**

The AI suggested checking for data leakage, insufficient feature representation, and whether the model was underfitting. It recommended plotting residuals and reviewing feature importance scores to diagnose the issue.

**How I Used It:**

I used feature importance scores to identify which variables were contributing most to predictions and found that some features were adding noise rather than signal. Removing them and re-training the model improved performance. I also reviewed whether the train/test split was introducing leakage by ensuring it respected chronological order.

---

## 11. Serving ML Model via Flask

**Prompt:**

"I want to serve my trained machine learning model through a Flask backend so the frontend can request predictions. What are the main architectural considerations for doing this?"

**AI Response Summary:**

The AI recommended loading the model once at application startup rather than on each request, using a dedicated endpoint for predictions, and validating input data before passing it to the model.

**How I Used It:**

I implemented a /api/stations/predict endpoint that loads the saved model at startup and accepts input parameters from the frontend. I added basic input validation to catch missing or malformed fields before they reach the model, which prevented several silent failures during testing.

---

## 12. ML Endpoint Output Discrepancy

**Prompt:**

"My Flask ML endpoint is returning unexpected values compared to what I see during local model testing. How do I trace where the discrepancy is coming from?"

**AI Response Summary:**

The AI suggested checking whether the input data passed to the endpoint matches the preprocessing steps used during training, and verifying that the same scaler or encoder used during training is being applied at inference time.

**How I Used It:**

The issue was that I had saved the model but not the scaler used during preprocessing. The endpoint was applying different normalisation, causing prediction values to differ from what I expected. I saved the scaler alongside the model and loaded both at startup, which resolved the discrepancy.

---

## 13. Gemini API Request Flow

**Prompt:**

"I'm implementing a chatbot in my Flask web app using the Gemini API. Can you explain how the request and response flow works end-to-end?"

**AI Response Summary:**

The AI explained that a user message is sent from the frontend to a Flask route, which formats the message and forwards it to the Gemini API. The response is then extracted from the API reply and returned to the frontend for display.

**How I Used It:**

I used this as a reference when building the initial chatbot implementation. The explanation helped me understand where to handle errors in the flow — specifically that failures could occur at the network layer, the API response parsing stage, or the frontend rendering stage — and I added handling at each point.

---

## 14. Gemini Rate Limit Debugging

**Prompt:**

"My Gemini API integration stops returning responses after a few messages — what are the likely causes and how do I investigate whether it's a rate limit, quota, or implementation issue?"

**AI Response Summary:**

The AI suggested checking the API response status codes and error messages for rate limit indicators, reviewing the free-tier quota limits in the API documentation, and adding logging to capture the raw API response when failures occur.

**How I Used It:**

I added logging to the Flask route to capture the full API response when an error occurred. The logs confirmed that the free-tier quota was being exhausted. After researching alternatives, I decided to switch to the Grok API, which offered more generous free-tier limits for our use case.

---

## 15. Migrating from Gemini to Grok

**Prompt:**

"I'm switching my chatbot backend from Gemini to Grok due to free-tier limitations. What differences should I be aware of in how the two APIs handle requests and responses?"

**AI Response Summary:**

The AI highlighted differences in request format, authentication headers, and response structure between the two APIs. It recommended abstracting the API call into a helper function to make future provider changes easier.

**How I Used It:**

I refactored the chatbot route to isolate the API call logic, which made the migration straightforward. The main changes involved updating the request format and parsing the response from a different JSON structure. The abstraction also made it easier to test the integration independently of the rest of the Flask app.

---

## 16. Chatbot Frontend Errors

**Prompt:**

"My chatbot sometimes returns an error on the frontend even though the Flask route appears to be working. What are common points of failure between an API call and the final UI response?"

**AI Response Summary:**

The AI identified potential failure points including incorrect JSON parsing on the frontend, missing or misnamed response fields, and unhandled promise rejections in the fetch logic.

**How I Used It:**

I reviewed the frontend fetch logic and found that the code was not handling cases where the response field was absent or had a different name than expected. I added a fallback message to display when the response could not be parsed, which prevented the UI from breaking silently.

---

## 17. README Structure

**Prompt:**

"What should a good README for a student software engineering project include, and how do I structure it so it clearly documents setup, features, and architecture?"

**AI Response Summary:**

The AI suggested sections covering project overview, setup instructions, environment variables, feature descriptions, architecture, and known limitations. It recommended keeping setup instructions step-by-step and testing them from a clean environment.

**How I Used It:**

I used this structure as a template when writing the README. I focused on making the setup instructions as clear as possible, since team members with different environments needed to be able to run the project. I did not include an architecture diagram but described the component structure in prose.

---

## 18. Documenting the ML Component

**Prompt:**

"I want to document the machine learning component of my project in the README. How should I explain the model, dataset, and prediction logic to someone unfamiliar with the project?"

**AI Response Summary:**

The AI recommended explaining the purpose of the model, the data it was trained on, the features used, how predictions are requested, and any known limitations or assumptions.

**How I Used It:**

I structured the ML section of the README around these points, briefly describing the dataset source, the features used during training, and how the prediction endpoint works. I also noted the limitations of the model, particularly that it was trained on historical data and may not reflect unusual demand patterns.

---

## 19. Team Branching Strategy

**Prompt:**

"I'm working on a team project and want to understand the best branching strategy for a group of developers — what are the common approaches and what are the tradeoffs?"

**AI Response Summary:**

The AI described common strategies including feature branching, Git Flow, and trunk-based development. It noted that for smaller teams, a feature branch model where each developer works on a named branch and merges into main via pull request is usually the most practical.

**How I Used It:**

I recommended the feature branch approach to the team, where each person works on a branch named after their feature. This gave each team member an isolated working environment and made it easier to review and merge changes without disrupting others' work.

---

## 20. Branch Syncing

**Prompt:**

"I created a new branch for my feature but my teammate's changes aren't showing up in it — how does branch syncing work in Git and what steps should I take?"

**AI Response Summary:**

The AI explained that branches do not automatically receive changes from other branches and that syncing requires either merging or rebasing from the target branch. It outlined the steps to pull the latest changes from main and merge them into a feature branch.

**How I Used It:**

I followed the steps to pull the latest main and merge it into my feature branch. This resolved the issue and I made it a habit to sync with main regularly throughout development to reduce the size of eventual merge conflicts.

---

## 21. Resolving Merge Conflicts

**Prompt:**

"I'm trying to merge my feature branch into main but Git is reporting merge conflicts. What is the correct process to understand and resolve them without losing changes?"

**AI Response Summary:**

The AI explained how conflict markers work in Git and recommended opening the conflicting files, reviewing both versions, and manually deciding which changes to keep. It also suggested communicating with the teammate whose changes are involved before resolving.

**How I Used It:**

I used the explanation of conflict markers to understand what Git was flagging in each file. In most cases, conflicts involved different teammates editing the same HTML or CSS file, and I resolved them by combining both sets of changes rather than choosing one over the other. Communication with teammates was essential to avoid accidentally discarding work.

---

## 22. Undoing an Accidental Commit to Main

**Prompt:**

"I accidentally committed directly to the main branch instead of my feature branch — what are the safest ways to undo or move that commit?"

**AI Response Summary:**

The AI described using git revert to create a new commit that undoes the change, which is safer than rewriting history. It also explained the process of cherry-picking the commit onto the correct branch if the work still needs to be kept.

**How I Used It:**

I used git revert to undo the accidental commit on main, which preserved the history without force-pushing. I then cherry-picked the commit onto my feature branch so the work was not lost. This approach avoided disrupting other team members who had already pulled from main.

---

## 23. Cleaning Up a Pull Request

**Prompt:**

"My pull request is showing a large number of unintended file changes that I didn't work on. What could cause this and how do I clean up the PR before requesting a review?"

**AI Response Summary:**

The AI identified that this is often caused by the feature branch being out of date with main, resulting in a large diff that includes changes already merged by others. It recommended merging main into the feature branch to bring it up to date before opening the PR.

**How I Used It:**

I merged the latest main into my feature branch before opening the PR, which removed the unintended changes from the diff. The resulting PR was much smaller and easier for teammates to review.

---

## 24. Debugging After a Merge

**Prompt:**

"After merging a teammate's branch, my local version of the app stopped working. How do I identify whether the issue is a merge conflict that wasn't caught or a missing dependency?"

**AI Response Summary:**

The AI suggested checking the terminal output for import errors or missing modules, reviewing the merged files for conflict markers that were accidentally left in, and comparing the requirements file before and after the merge.

**How I Used It:**

I checked the Flask startup output and found an import error pointing to a module added by my teammate that was not in my local environment. Installing the missing dependency resolved the issue. I also checked for leftover conflict markers in the merged files as a precaution.

---

## 25. Merge vs Rebase

**Prompt:**

"What is the difference between git merge and git rebase, and in a team project context, when is it appropriate to use each?"

**AI Response Summary:**

The AI explained that merge preserves the full history of both branches while rebase rewrites history to produce a linear sequence of commits. It recommended using merge for integrating completed feature branches into main, and using rebase cautiously and only on local branches not yet shared with others.

**How I Used It:**

I used merge for all integrations into main to keep the history traceable and avoid the risks associated with rewriting shared history. I applied this consistently across the project so that teammates could follow the history of changes without confusion.

---

Throughout this project, Generative AI was used as a support tool across frontend development, backend architecture, machine learning, chatbot integration, and version control. Its primary role was to clarify concepts, suggest approaches, and assist with debugging when I encountered issues I had not seen before.

AI-generated responses were not adopted directly. In most cases, the suggestions required adaptation to fit the specific structure of the project, the constraints of the free-tier APIs being used, and the decisions made collaboratively by the team. For example, the chatbot implementation required switching from Gemini to Grok mid-development due to quota limitations — a constraint not reflected in generic AI guidance — and the ML pipeline required careful attention to preprocessing consistency between training and inference, which involved diagnosing issues the AI had not anticipated.

Working through these gaps improved my ability to critically evaluate suggestions, identify where generic advice does not apply to a specific context, and make informed decisions independently. Generative AI improved my development efficiency and helped me learn faster, but all final implementations, decisions, and code remain my own.