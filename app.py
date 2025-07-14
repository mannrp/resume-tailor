import streamlit as st
import google.generativeai as genai

# Page configuration
st.set_page_config(page_title="Resume Tailor", layout="wide")

# Main title
st.title("📄✨ Resume Tailor")
st.info("Upload your LaTeX resume and job description to get a tailored version using Google Gemini AI")

# API key configuration
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Create two columns for layout
col1, col2 = st.columns(2)

with col1:
    st.header("Your Information")
    
    # LaTeX resume input
    resume_latex_input = st.text_area(
        "Paste your full LaTeX resume code here",
        height=400,
        placeholder="\\documentclass{article}\n\\begin{document}\n...\n\\end{document}"
    )
    
    # Additional information input
    extra_info_input = st.text_area(
        "Add any extra skills or experiences not in your resume",
        height=150,
        placeholder="Any additional skills, certifications, or experiences you'd like to highlight..."
    )

with col2:
    st.header("Job Description")
    
    # Job description input
    job_description_input = st.text_area(
        "Paste the target job description here",
        height=600,
        placeholder="Paste the complete job description including requirements, responsibilities, and qualifications..."
    )

# Tailor resume button
if st.button("Tailor My Resume!", type="primary"):
    # Validation
    if not resume_latex_input.strip() or not job_description_input.strip():
        st.warning("Please provide both your LaTeX resume code and the job description.")
    else:
        # Show spinner while processing
        with st.spinner("✨ Gemini is tailoring your resume..."):
            try:
                # Initialize the model
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Create the prompt
                prompt_template = f"""
You are an expert career coach and a specialist in LaTeX resume editing, specifically working with "Jake's Resume" template. Your task is to meticulously edit a user's LaTeX resume to align it with a specific job description.

**Primary Goal:** Modify the provided LaTeX resume code to better match the skills and keywords found in the job description.

**Key Instructions:**
1.  **Analyze and Integrate:** Analyze the Job Description to identify key skills, technologies, and action verbs. Weave these naturally into the user's existing 'Experience', 'Projects', or 'Skills' sections. Use the 'Additional Information' from the user to add new facts where relevant.
2.  **Edit, Don't Recreate:** Your main task is to *edit* the text content within the existing LaTeX structure. Do NOT change the resume's core structure, sections, or LaTeX commands (e.g., `\\documentclass`, `\\section`, `\\resumeSubheading`). Focus your edits on the descriptive text and bullet points.
3.  **Preserve Structure:** The "Jake's Resume" template has a clear structure. Maintain it perfectly. Rephrase bullet points to be more results-oriented and to reflect the language of the job description, but do not change the formatting commands.
4.  **Strict Output Format:** The final output MUST be only the complete, modified LaTeX code. It must be clean, well-formatted, and ready to be compiled. Do not include any explanations, comments, apologies, or ```latex ``` markers in your response. Return only the raw, modified LaTeX source code.

---
**[User's Current LaTeX Resume]**
```latex
{resume_latex_input}
```

**[Job Description]**
{job_description_input}

**[Additional Information from User]**
{extra_info_input}

**[Your Modified LaTeX Resume Output]**
"""
                
                # Generate response
                response = model.generate_content(prompt_template)
                
                # Display the result
                st.subheader("✅ Your Tailored LaTeX Code:")
                st.code(response.text, language="latex")
                
            except Exception as e:
                st.error(f"An error occurred while tailoring your resume: {str(e)}")
