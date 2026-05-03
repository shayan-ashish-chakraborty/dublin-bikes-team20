Generative AI Log

1. UI Layout Design

Prompt:

“Design a responsive UI for a bike sharing web app. It needs a full-screen map, a sidebar for station details, a weather dashboard, and predictive charts for bike availability.”

AI Response Summary:

The AI suggested a map-centric layout where the map acts as the primary interface, complemented by sidebar overlays for station details. It also proposed using a tab-based system to separate weather and prediction information in order to reduce visual clutter.

How I Used It:

I adopted the core idea of a map-first layout but chose not to implement the tab-based interface. Instead, I redesigned the system into separate pages to better support user workflows. A stations page focuses on real-time station availability and navigation, while a separate weather page presents detailed weather information and trends. To maintain global awareness of weather conditions, I introduced a navigation bar element displaying current temperature and an icon across all pages. This approach reduced interface complexity while ensuring that key information remained accessible without interrupting the main user task.

2. Information Hierarchy & Visual Weight

Prompt:

“What data points should be most prominent in a bike app to ensure high usability?”

AI Response Summary:

The AI recommended structuring information into a hierarchy where real-time availability is prioritised, followed by location relevance, and then contextual data such as weather or trends.

How I Used It:

I applied this hierarchy by making bike and stand availability the most visually prominent elements, displayed directly on markers and within popup windows. Secondary information such as station names and additional metadata was included but visually de-emphasised. Prediction data was treated as tertiary information and presented only when the user interacts with a station. I deliberately avoided implementing features such as distance-based ranking, as they were not part of the current system, ensuring that all claims align with the actual implementation.

3. Map Usability Improvements

Prompt:

“What are common UX pitfalls in Google Maps API integrations?”

AI Response Summary:

The AI identified issues such as marker overcrowding, overly complex popups, and poor readability.

How I Used It:

To address these issues, I simplified the visual design of markers by using colour coding (green, orange, and red) to represent availability levels. I also limited the content of popups to essential information, ensuring that users can quickly understand station status without being overwhelmed. Advanced features such as clustering were not implemented; instead, I focused on maintaining clarity through minimal design and controlled interaction.

4. Flask Structure

Prompt:

“How to structure a Flask app with multiple APIs?”

AI Response Summary:

The AI recommended separating functionality into modular endpoints and maintaining clear boundaries between different data services.

How I Used It:

I implemented a structured backend with clearly defined endpoints, including /api/stations, /api/weather, and /api/stations/predict. Each endpoint is responsible for a specific type of data, ensuring consistency and simplifying frontend integration. Rather than implementing a full blueprint system, I focused on maintaining logical separation within the existing structure.

5. Error Handling for APIs

Prompt:

“How to handle external API failures?”

AI Response Summary:

The AI suggested using exception handling, timeouts, and fallback values to prevent application crashes.

How I Used It:

I incorporated error handling primarily on the frontend using .catch() and fallback values when data is unavailable. This ensures that the application remains stable even when external APIs fail, avoiding situations where the UI breaks due to missing data.
6. Marker Generation

Prompt:

“How to generate markers from JSON data?”

AI Response Summary:

The AI suggested iterating through JSON data and dynamically creating markers using the Google Maps API.

How I Used It:

I implemented dynamic marker generation by looping through station data and creating markers programmatically. This allows the map to reflect real-time station data and ensures scalability as the number of stations increases.

7. Marker Interaction

Prompt:

“How to show station details on click?”

AI Response Summary:

The AI recommended attaching event listeners to markers and displaying information through popups.

How I Used It:

I implemented click events that open an InfoWindow containing station details such as available bikes and stands. This allows users to access detailed information without leaving the map context.

8. Performance Optimisation

Prompt:

“How to optimize many markers?”

AI Response Summary:

The AI suggested reducing unnecessary re-rendering and avoiding duplicate objects.

How I Used It:

I ensured that markers are cleared before being re-rendered, preventing duplication and reducing performance issues when refreshing data.

9. Popup Design

Prompt:

“How to design a clean InfoWindow?”

AI Response Summary:

The AI suggested using structured HTML with minimal content and clear hierarchy.

How I Used It:

I designed the popup to display only key information such as station name, available bikes, and available stands, with optional prediction charts. This maintains clarity while still providing additional insights when needed.

10. Weather Display

Prompt:

“How to display weather data clearly?”

AI Response Summary:

The AI recommended separating summary information from detailed data.

How I Used It:

I implemented a dual-level display where the navigation bar shows a concise summary (temperature and icon), while the weather page provides more detailed information. I used a simplified icon system instead of implementing a full mapping of weather codes, which reduced complexity while maintaining clarity.

11. Prediction Integration and Performance Optimisation

Prompt:

“How to fetch, display, and optimize machine learning prediction data?”

AI Response Summary:

The AI suggested retrieving prediction data using the Fetch API, dynamically rendering it in charts, and reducing unnecessary API calls through caching and controlled request triggers.

How I Used It:

I integrated prediction data via the /api/stations/predict endpoint and visualised it using charts within the UI. To improve performance, I introduced simple caching and ensured that prediction requests are only triggered when necessary (e.g., when a user selects a station rather than during every map refresh). This reduced redundant machine learning requests, lowered backend load, and improved overall application responsiveness.

12. Async UI Updates

Prompt:

“How to update the UI after fetch?”

AI Response Summary:

The AI explained updating the DOM after data has been retrieved.

How I Used It:

I used asynchronous logic (await) to ensure that data is loaded before updating the UI, preventing rendering issues caused by incomplete data.

13. Loading States

Prompt:

“How to handle loading states?”

AI Response Summary:

The AI suggested using placeholders and loading indicators.

How I Used It:

I implemented simple loading messages and ensured that undefined data is not rendered, improving user experience during data fetching.

14. API Field Consistency

Prompt:

“How to fix mismatched API fields?”

AI Response Summary:

The AI suggested standardising naming conventions.

How I Used It:

I ensured consistent field names such as available_bikes and available_stands, reducing frontend parsing complexity.

15. Frontend Error Handling

Prompt:

“How to handle fetch errors?”

AI Response Summary:

The AI recommended using .catch() for graceful error handling.

How I Used It:

I implemented fallback UI behaviour to ensure the application remains functional even when data requests fail.

16. Edge Case Handling

Prompt:

“How to represent empty stations?”

AI Response Summary:

The AI suggested using clear visual indicators.

How I Used It:

I used red markers to indicate stations with very low or no availability, allowing users to quickly identify unavailable stations.

Throughout this project, Generative AI was used as a development support tool across multiple stages, including UI/UX design, backend architecture, frontend implementation, and debugging. Its primary role was to assist in idea generation, clarify technical concepts, and provide guidance when addressing development challenges.

In the early stages, AI was used to explore UI/UX design approaches. For example, when prompted to design a responsive interface for a bike-sharing web application, the AI proposed a map-centric layout with sidebar overlays and a tab-based system for weather and predictive data. While the map-first approach was adopted, the tab-based interface was not implemented. Instead, the system was redesigned into separate pages, one focused on station data and navigation, and another dedicated to weather information. To maintain accessibility of key data, a global navigation bar displaying temperature and a weather icon was introduced. This decision reduced visual complexity and aligned better with user workflows. AI also contributed to defining information hierarchy. It suggested prioritising real-time availability.  This structure was applied by making bike and stand availability the most visually prominent elements on the map and within popups. Secondary information, such as station names, was included but visually de-emphasised. Prediction data was treated as tertiary information and displayed only upon user interaction. In terms of map usability, AI highlighted marker overcrowding. Therefore, the design uses simple colored dots (green, orange, red) to represent bikes available at the current station.

For backend development, AI provided guidance on structuring a Flask application. It recommended modular endpoints with clear separation of concerns. This led to the implementation of distinct API routes, including /api/stations, /api/weather, and /api/stations/predict, each responsible for a specific dataset. AI also suggested strategies for handling external API failures, such as exception handling and fallback values. These were primarily implemented on the frontend using .catch() to ensure the application remained stable even when data was unavailable.

On the frontend, Generative AI supported the implementation of core interactive map features, particularly in the areas of dynamic marker generation, user interaction handling, and performance optimisation. Station markers were generated dynamically by iterating over JSON data retrieved from the backend API. Each data object contained key attributes such as geographic coordinates, station name, and availability metrics (e.g., available bikes and stands). By looping through this dataset, markers were programmatically instantiated and placed on the map using the Google Maps API. This approach ensured that the interface could scale efficiently with real-time data updates, as new or updated station information could be rendered without requiring manual changes to the codebase. To enable user interaction, event listeners were attached to each marker. Specifically, click events were used to trigger the display of an InfoWindow associated with the selected station. These InfoWindows presented essential station details—such as current bike and stand availability—within the map interface itself. This interaction pattern allowed users to access relevant information without navigating away from the map, thereby preserving spatial context and improving overall usability. In terms of performance optimization, to improve performance and reduce unnecessary load, previously generated prediction data was cached to avoid redundant machine learning requests.

During frontend development, many merge conflicts occurred on GitHub because each team member was responsible for a different feature. Generative AI was used to assist in resolving these conflicts by helping interpret Git conflict markers and analyse how independently developed features could be correctly combined. It provided guidance on integrating code without breaking existing functionality, particularly when different features introduced dependencies, overlapping variables, or conflicting structures within the same file. AI also helped identify issues such as inconsistent naming or integration errors after merging. This support improved the efficiency of resolving conflicts, while all final decisions were manually reviewed to ensure the merged code remained stable and aligned with the overall system design.

Overall, AI-generated solutions are not always directly usable and must be critically evaluated. In many cases, I had to modify the suggested approaches to fit the existing project structure, ensure compatibility with components developed by teammates, and handle real-world constraints such as incomplete data or performance limitations. Through this process, I improved my ability to analyse problems, adapt solutions, and build a more robust and user-focused application. Generative AI significantly improved my efficiency and supported my learning throughout the project, but it functioned as a support tool rather than a replacement for independent thinking. The final system reflects my own understanding, decisions, and implementation, with AI acting as a guide rather than the source of the final solution.


