import streamlit as st
import google.generativeai as genai
import tempfile
import subprocess
import os
import re
import requests
import base64

# Page configuration
st.set_page_config(page_title="Resume Tailor", layout="wide")

# Main title
st.title("📄✨ Resume Tailor")
st.info("Upload your LaTeX resume and job description to get a tailored version using Google Gemini AI")

# API key configuration
api_key = None
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Enter your Gemini API Key", type="password", help="Get your API key from https://aistudio.google.com/app/apikey")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("Please provide your Gemini API key to continue.")

# Function to clean LaTeX output
def clean_latex_output(latex_code):
    """Remove markdown code blocks from LaTeX output"""
    # Remove ```latex at the beginning
    latex_code = re.sub(r'^```latex\s*', '', latex_code, flags=re.MULTILINE)
    # Remove ``` at the end
    latex_code = re.sub(r'\s*```\s*$', '', latex_code, flags=re.MULTILINE)
    return latex_code.strip()

# Function to compile LaTeX to PDF using online service
def compile_latex_to_pdf_online(latex_code):
    """Compile LaTeX code to PDF using an online LaTeX compiler"""
    try:
        # Use a more reliable LaTeX compilation approach
        # We'll use LaTeX.Online but with better error handling
        url = "https://latex.ytotech.com/builds/sync"
        
        # Prepare the request with proper headers
        files = {
            'file': ('main.tex', latex_code, 'text/plain')
        }
        
        headers = {
            'User-Agent': 'Resume-Tailor-App/1.0'
        }
        
        response = requests.post(url, files=files, headers=headers, timeout=45)
        
        # Check if we got any PDF content
        if response.status_code in [200, 201] and len(response.content) > 1000:
            # Check if it's actually a PDF by looking at the header
            if response.content.startswith(b'%PDF'):
                return response.content
            else:
                st.error("Online service returned invalid PDF content.")
                return None
        else:
            st.error(f"Online PDF compilation failed. Status: {response.status_code}, Content length: {len(response.content)}")
            if response.content:
                st.error(f"Response preview: {response.content[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Online PDF compilation timed out. The LaTeX code might be too complex or the service is busy.")
        return None
    except Exception as e:
        st.error(f"Error with online PDF compilation: {str(e)}")
        return None

# Function to compile LaTeX to PDF (with fallback options)
def compile_latex_to_pdf(latex_code):
    """Compile LaTeX code to PDF with multiple methods"""
    
    # Method 1: Try local pdflatex first
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write LaTeX to temporary file
            tex_file = os.path.join(temp_dir, "resume.tex")
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_code)
            
            # Compile with pdflatex
            result = subprocess.run([
                'pdflatex', 
                '-interaction=nonstopmode',
                '-output-directory', temp_dir,
                tex_file
            ], capture_output=True, text=True, cwd=temp_dir)
            
            pdf_file = os.path.join(temp_dir, "resume.pdf")
            
            if os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    return f.read()
            else:
                st.warning("Local pdflatex failed, trying online compilation...")
                return compile_latex_to_pdf_online(latex_code)
                
    except FileNotFoundError:
        # Method 2: Use online compilation if pdflatex not found
        st.info("Local LaTeX not found, using online compilation service...")
        return compile_latex_to_pdf_online(latex_code)
    except Exception as e:
        st.warning(f"Local compilation error: {str(e)}. Trying online compilation...")
        return compile_latex_to_pdf_online(latex_code)

# Configuration options in sidebar
st.sidebar.header("Configuration")
model_choice = st.sidebar.selectbox(
    "Select Gemini Model",
    ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-2.5-flash"],
    index=0
)

single_page_option = st.sidebar.checkbox(
    "� Optimize for single page",
    value=False,
    help="Intelligently optimizes content to fit on one page while preserving quality - uses more concise language and efficient formatting"
)

# Initialize session state for storing generated LaTeX
if 'generated_latex' not in st.session_state:
    st.session_state.generated_latex = None

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
    if not api_key:
        st.warning("Please provide your Gemini API key first.")
    elif not resume_latex_input.strip() or not job_description_input.strip():
        st.warning("Please provide both your LaTeX resume code and the job description.")
    else:
        # Show spinner while processing
        with st.spinner("✨ Gemini is tailoring your resume..."):
            try:
                # Initialize the model
                model = genai.GenerativeModel(model_choice)
                
                # Create the prompt with single-page option
                single_page_instruction = """
5.  **STRICT Single Page Constraints:** This resume must fit on ONE PAGE. Follow these EXACT limits:
    - Experience section: Maximum 4 positions total
    - Bullet points: Maximum 4 per position (each bullet ≤ 1.5 lines when wrapped)
    - Skills section: Maximum 4 lines total, group technologies (e.g., "Languages: Python, Java, C++")
    - Education: Only degree, school, year - remove GPA, coursework, honors unless exceptional
    - Projects: Maximum 2-3 projects, 1-2 bullets each
    - Remove any sections like "Interests", "References", etc.
    - Use action verbs, quantify results, eliminate filler words
    - Each bullet point should be concise but impactful
""" if single_page_option else ""
                
                # Create the prompt
                prompt_template = f"""
You are an expert career coach and a specialist in LaTeX resume editing, specifically working with "Jake's Resume" template. Your task is to meticulously edit a user's LaTeX resume to align it with a specific job description.

**Primary Goal:** Modify the provided LaTeX resume code to better match the skills and keywords found in the job description.{" CRITICAL: Apply strict space constraints to ensure single-page output." if single_page_option else ""}

**Key Instructions:**
1.  **Analyze and Integrate:** Analyze the Job Description to identify key skills, technologies, and action verbs. Weave these naturally into the user's existing 'Experience', 'Projects', or 'Skills' sections. Use the 'Additional Information' from the user to add new facts where relevant.
2.  **Edit, Don't Recreate:** Your main task is to *edit* the text content within the existing LaTeX structure. Do NOT change the resume's core structure, sections, or LaTeX commands (e.g., `\\documentclass`, `\\section`, `\\resumeSubheading`). Focus your edits on the descriptive text and bullet points.
3.  **Preserve Structure:** The "Jake's Resume" template has a clear structure. Maintain it perfectly. Rephrase bullet points to be more results-oriented and to reflect the language of the job description, but do not change the formatting commands.
4.  **Strict Output Format:** The final output MUST be only the complete, modified LaTeX code. It must be clean, well-formatted, and ready to be compiled. Do not include any explanations, comments, apologies, or ```latex ``` markers in your response. Return only the raw, modified LaTeX source code.{single_page_instruction}

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
                
                # Clean the LaTeX output
                cleaned_latex = clean_latex_output(response.text)
                
                # Store in session state
                st.session_state.generated_latex = cleaned_latex
                
                # Display the result
                st.subheader("✅ Your Tailored LaTeX Code:")
                st.code(cleaned_latex, language="latex")
                
                # Download LaTeX button
                st.download_button(
                    label="📄 Download LaTeX Code",
                    data=cleaned_latex,
                    file_name="tailored_resume.tex",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"An error occurred while tailoring your resume: {str(e)}")

# PDF Compilation section (outside the main button to prevent page rerun)
if st.session_state.generated_latex:
    st.subheader("📋 PDF Compilation")
    st.info("💡 PDF compilation will try local LaTeX first, then fall back to online compilation if needed.")
    
    # Add helpful information about LaTeX installation
    with st.expander("ℹ️ Having trouble with PDF compilation?"):
        st.markdown("""
        **If online compilation fails:**
        1. Download the LaTeX code using the button above
        2. Use an online LaTeX editor like [Overleaf](https://www.overleaf.com/)
        3. Or install LaTeX locally:
           - **Windows**: [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/)
           - **Mac**: [MacTeX](https://www.tug.org/mactex/)
           - **Linux**: `sudo apt-get install texlive-full` (Ubuntu/Debian)
        """)
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        if st.button("🔄 Compile to PDF", key="compile_pdf"):
            with st.spinner("Compiling PDF..."):
                pdf_bytes = compile_latex_to_pdf(st.session_state.generated_latex)
                if pdf_bytes:
                    st.session_state.pdf_bytes = pdf_bytes
                    st.success("PDF compiled successfully!")
    
    with col_pdf2:
        if 'pdf_bytes' in st.session_state and st.session_state.pdf_bytes:
            st.download_button(
                label="📋 Download PDF",
                data=st.session_state.pdf_bytes,
                file_name="tailored_resume.pdf",
                mime="application/pdf",
                key="download_pdf"
            )
