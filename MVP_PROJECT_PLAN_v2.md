# AI Speech Assessment - MVP Project Plan

**Document Version:** 2.0
**Date:** July 31, 2025

## 1. Project Vision

To build a scalable, AI-powered speech assessment platform for Indian schools that provides personalized, curriculum-aligned feedback to students. The MVP will deliver a robust dual-mode experience and the foundational infrastructure for tracking student progress.

---

## 2. Core User Stories

* **As a Student, I want to...**
    * Choose between practicing a set sentence or speaking freely on a topic.
    * Receive detailed, personalized feedback on my speech that is easy to understand.
    * See specific examples of my errors and how to correct them.
    * Listen to a better version of what I said to learn from it.
    * Log in to my account and see my past results to track my improvement.

* **As a Teacher, I want to...**
    * Provide my students with a tool that aligns with my monthly curriculum goals.
    * Log in to a portal to set the learning objectives for my class (e.g., focus on past tense verbs).
    * View the progress of individual students in my class over time.

---

## 3. MVP Feature Set

### Backend (Python/FastAPI)
-   [ ] **Database & User Authentication:** PostgreSQL setup, User model (Student/Teacher), Signup/Login APIs.
-   [ ] **Dual-Mode API Endpoint (`/api/analyze`):**
    -   [ ] Handle `mode=pronunciation`.
    -   [ ] Handle `mode=impromptu`.
-   [ ] **"Intelligent Tutor" AI Coach:**
    -   [ ] Implement the advanced "Senior English Tutor" LLM prompt.
    -   [ ] Logic to fetch and inject teacher-defined curriculum goals into the prompt.
    -   [ ] The prompt will request a full list of grammar errors.
    -   [ ] The prompt will request a "stepping stone" rewritten sample.
-   [ ] **Data Persistence & Retrieval Endpoints.**
-   [ ] **Text-to-Speech Endpoints:**
    -   [ ] `/api/synthesize` for single words (with Indian Accent voice).
    -   [ ] `/api/synthesize-paragraph` for the rewritten sample.

### Frontend (React)
-   [ ] **User Authentication:** Login and Signup pages.
-   [ ] **Mode Selection Screen.**
-   [ ] **Pronunciation Practice UI:**
    -   [ ] Editable reference text area.
-   [ ] **Impromptu Speaking UI:**
    -   [ ] **Visible 55-second timer with auto-stop** for the core MVP feature.
-   [ ] **Impromptu Results Dashboard:**
    -   [ ] Display all personalized feedback from the AI Coach.
    -   [ ] **Implement a "Show More" button/dropdown for grammar errors**, displaying the top 3 by default.
    -   [ ] Add a "Listen to Sample" button.
-   [ ] **Student Progress Page ("My Progress"):**
    -   [ ] A new page to display a student's past session results and charts.

---

## 4. R&D and Experimental Tracks

These features will be developed on separate `git` branches to ensure the stability of the core MVP.

* **Experiment A: Dynamic Reference Text Generation**
    * **Goal:** To test the feasibility of using an AI-generated transcript as the reference text for pronunciation assessment.
    * **Git Branch:** `feature/experimental-dynamic-reference`
    * **Tasks:**
        1.  Create a new analysis mode, `mode=experimental`.
        2.  In the backend, implement the workflow: Audio -> Azure STT -> Raw Transcript -> OpenAI LLM (to correct/normalize) -> Corrected Transcript.
        3.  Use the "Corrected Transcript" as the `ReferenceText` in a final call to the Azure Pronunciation Assessment API.
        4.  Display the results on the frontend to allow for direct comparison and quality evaluation.

* **Experiment B: Long-Form Audio via Batch Transcription API**
    * **Goal:** To implement the scalable solution for analyzing impromptu speeches longer than 60 seconds.
    * **Git Branch:** `feature/batch-transcription-api`
    * **Tasks:**
        1.  Set up an Azure Blob Storage account.
        2.  Create new backend endpoints to start the batch job (`/start-batch-analysis`) and check its status (`/get-batch-results`).
        3.  Modify the frontend to upload the file, start the job, and then "poll" the status endpoint until the results are ready.

---

## 5. Your Action Items (Founder's To-Do List)
* [ ] **Interview Teachers (Crucial for Product Success):**
    * **Goal:** Gather real-world rubrics to create the "secret sauce" for our AI Tutor's prompts.
    * **Key Questions:**
        -   *"How do you grade a 3rd grader's speech vs. a 6th grader's?"*
        -   *"What are the top 5 most common grammar mistakes for each grade?"*

---

## 6. MVP Development Roadmap

**Phase 1: Foundational Backend**
-   Implement the database, user authentication, and the basic teacher portal for saving curriculum goals.

**Phase 2: The "Intelligent Tutor" Backend**
-   Implement the final, advanced "Senior English Tutor" prompt and the logic to inject teacher goals.

**Phase 3: The Complete Student Experience**
-   Build the frontend login pages, the "My Progress" dashboard, and the refined results dashboards (with TTS and "Show More" functionality).

**Phase 4: The Teacher's View & Contextual AI**
-   Build the Teacher Dashboard for viewing student progress.
-   Implement the "AI Memory" (RAG) feature for context-aware feedback.



------

Add Computer Vision for facial tracking, expressions, body language, gestures, etc. 
Check with rubric given by cbse



The Cost of Computer Vision AI
Now for the critical financial question. Adding video analysis is a powerful upgrade, but it comes with a significant increase in operational costs. Video processing is much more resource-intensive than audio processing.

Let's use our same usage assumption: 10 minutes per week per student, which is 360 minutes per academic year.

1. AI API Calls (Computer Vision):
Service: A top-tier service like Amazon Rekognition or Google Vision AI.

Pricing: These services are priced per minute of video analyzed. A realistic, blended rate is ~$0.12 USD per minute.

Calculation: 360 minutes/year × ~$0.12/minute = $43.20

2. Increased Cloud Costs (Storage & Bandwidth):
Data Storage: Video files are much larger than audio. Storing ~4GB of compressed video per student per year will cost more.

Bandwidth & Compute: Sending and processing these larger files requires more server resources.

Blended Cost: A conservative estimate for these additional cloud costs is ~$4.00 per student/year.

Total Estimated Cost for the Video Feature:
~$43.20 (AI) + ~$4.00 (Cloud) = ~$47.20 USD per student per year.

In Indian Rupees (at ~₹84/USD), this is approximately ₹3,950 per student per year.

The New Total Operational Cost (Audio + Video)
To offer a fully comprehensive tool that assesses both speech and body language, your costs would be:

Audio Analysis Cost (Intensive Plan): ~₹1,500

Video Analysis Cost: ~₹3,950

Total Combined Operational Cost: ~₹5,450 per student per year.

Strategic Advice: This significant cost increase confirms that video analysis is a premium, "Pro Tier" feature. You would need to charge a school a substantially higher price (e.g., ₹8,000 - ₹10,000 per student/year) for this comprehensive package to maintain a healthy business margin. This is an excellent upsell opportunity for your most advanced and well-funded client schools after you have successfully launched your audio-only MVP.