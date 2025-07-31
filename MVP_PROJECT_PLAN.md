# AI Speech Assessment - Minimum Viable Product (MVP) Project Plan

**Document Version:** 1.0
**Date:** July 31, 2025

## 1. Project Vision

To build a scalable, AI-powered speech assessment platform for Indian schools that provides personalized, curriculum-aligned feedback to students. The MVP will serve as the foundation for this platform, focusing on two core practice modes and the infrastructure for tracking student progress over time.

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
-   [ ] **Database & User Authentication:**
    -   [ ] Set up a PostgreSQL database.
    -   [ ] Implement a simple user model (Student, Teacher).
    -   [ ] Implement signup/login functionality.
-   [ ] **Dual-Mode API Endpoint (`/api/analyze`):**
    -   [ ] Handle `mode=pronunciation` with Azure Pronunciation Assessment.
    -   [ ] Handle `mode=impromptu` with Azure STT + OpenAI AI Coach.
-   [ ] **"Intelligent Tutor" AI Coach:**
    -   [ ] Implement the advanced "Senior English Tutor" LLM prompt.
    -   [ ] Logic to fetch and inject teacher-defined curriculum goals into the prompt.
    -   [ ] The prompt will request:
        -   Personalized feedback on Fluency, Grammar, Vocabulary, Coherence.
        -   A list of all grammar errors (frontend will show top 3).
        -   A "stepping stone" rewritten sample at a grade-appropriate level.
-   [ ] **Data Persistence:**
    -   [ ] Logic to save every analysis report to the database, linked to the student's user ID.
-   [ ] **Data Retrieval Endpoints:**
    -   [ ] Create new API endpoints for the frontend to fetch a student's historical data.
-   [ ] **Text-to-Speech Endpoint (`/api/synthesize-paragraph`):**
    -   [ ] A new endpoint to convert the AI's rewritten sample into audio.

### Frontend (React)
-   [ ] **User Authentication:**
    -   [ ] Build Login and Signup pages.
-   [ ] **Mode Selection Screen:**
    -   [ ] A home screen for users to choose "Pronunciation Practice" or "Impromptu Speaking".
-   [ ] **Practice Interfaces:**
    -   [ ] Finalize the UI for both practice modes.
-   [ ] **Impromptu Results Dashboard:**
    -   [ ] Display all personalized feedback from the AI Coach.
    -   [ ] Implement the "Show More" dropdown for grammar errors.
    -   [ ] Add a "Listen to Sample" button that calls the new TTS endpoint.
-   [ ] **Student Progress Page ("My Progress"):**
    -   [ ] A new page that fetches and displays a student's past session results.
    -   [ ] Include simple charts to visualize score improvements over time.

---

## 4. Your Action Items (Founder's To-Do List)

* [ ] **Interview Teachers (Crucial for Product Success):**
    * **Goal:** To gather the real-world rubrics and teaching methods that will make our AI Tutor truly effective and unique.
    * **Who to talk to:** English teachers from different grade levels (e.g., 2nd, 4th, 6th grade).
    * **Key Questions to Ask:**
        -   *"How do you grade a student's speech? What are the most important things you listen for?"*
        -   *"What are the most common grammar mistakes you see at your grade level?"*
        -   *"What kind of vocabulary do you expect students to use for a topic like 'My Vacation'?"*
        -   *"Can you give me an example of 'good' vs. 'excellent' speech for a 4th grader?"*
    * **Outcome:** The insights from these interviews will be directly used to refine our LLM prompts for each grade level, creating our "secret sauce."

---

## 5. MVP Development Roadmap

**Phase 1: Foundational Backend**
-   Implement the database, user authentication, and the basic teacher portal for saving curriculum goals.

**Phase 2: The "Intelligent Tutor" Backend**
-   Implement the final, advanced "Senior English Tutor" prompt and the logic to inject teacher goals.

**Phase 3: The Complete Student Experience**
-   Build the frontend login pages, the "My Progress" dashboard, and integrate the TTS for the rewritten sample.

**Phase 4: The Teacher's View & Contextual AI**
-   Build the Teacher Dashboard for viewing student progress.
-   Implement the "AI Memory" (RAG) feature for context-aware feedback.

---

## 6. Future Considerations (Post-MVP)

* **Cost Optimization:** Evaluate cheaper LLMs (GPT-4o mini, Gemini Flash, Claude Haiku) once the product has traction.
* **Advanced UI/UX:** Improve error handling in the UI, add progress bars, icons, etc.
* **Teacher Tools:** Allow teachers to create and assign specific practice exercises.
* **Export/Sharing:** Allow students and teachers to export feedback reports as PDFs.

----From Gemini-----:

Proposed MVP Roadmap
Now that we are officially in the MVP stage, here is a logical roadmap to build out the complete, scalable product you've envisioned.

Phase 1: Foundational Backend (The "Scaffolding")
Goal: Build the infrastructure to support users and data.

Tasks:

Set up the PostgreSQL database.

Implement a simple User Authentication system (student/teacher signup and login).

Build a basic Teacher Portal where a teacher can input and save their monthly curriculum goals.

Phase 2: The "Intelligent Tutor" Backend (The "Brain")
Goal: Create the core AI logic that powers the personalized feedback.

Tasks:

Implement the final, advanced "Senior English Tutor" prompt in main.py.

Modify the /api/analyze endpoint to fetch teacher goals from the database and inject them into the prompt before calling the LLM.

Implement the logic to return all grammar errors but have the frontend initially show only the top 3.

Phase 3: The Complete Student Experience (The "Classroom")
Goal: Build the full, end-to-end user interface for students.

Tasks:

Build the login/signup pages.

Finalize the Impromptu Speaking Dashboard to beautifully display all the rich feedback from our new prompt.

Implement the TTS for the rewritten sample with a "Listen to Sample" button.

Build the "My Progress" page where students can see a list of their past sessions and track their scores over time.

Phase 4: The Teacher's View & Contextual AI (The "Report Card")
Goal: Empower teachers and make the AI "smarter" over time.

Tasks:

Build the Teacher Dashboard where a teacher can view the progress of all students in their class.

Implement the "AI Memory" (RAG) feature, where the AI is fed a summary of the student's past mistakes to provide even more consistent, context-aware feedback.