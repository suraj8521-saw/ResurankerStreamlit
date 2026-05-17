import streamlit as st
import spacy
import pdfplumber
import re
import os
import json

# --- 1. STREAMLIT PAGE CONFIGURATION ---
st.set_page_config(page_title="ResuRanker | AI Resume Grader", page_icon="🎯", layout="wide")

MODEL_PATH = "./skill_extractor_v6_mega/model-best"
JARGON_DB_PATH = "discovered_jargon.json"
ADV_MATRIX_PATH = "advanced_domain_matrix.json"

@st.cache_resource
def load_v6_mega_model():
    if os.path.exists(MODEL_PATH):
        try:
            return spacy.load(MODEL_PATH)
        except Exception as e:
            st.error(f"⚠️ Model load error: {e}")
            return None
    else:
        st.warning("⚠️ Model not found! Baseline used.")
        return spacy.blank("en")

nlp_v6 = load_v6_mega_model()

# --- 🤖 DYNAMIC KNOWLEDGE BASE LOADER ---
def load_dynamic_knowledge_base():
    baseline_jargon = [
        "jwt", "jwt authentication", "aes", "aes encryption", "sha-256", 
        "fastapi", "websockets", "bootstrap", "mysql", "mongodb", "rest api", "apis"
    ]
    
    if os.path.exists(JARGON_DB_PATH):
        try:
            with open(JARGON_DB_PATH, "r", encoding="utf-8") as f:
                extended_data = json.load(f)
                if isinstance(extended_data, list):
                    return list(set([str(item).lower().strip() for item in extended_data] + baseline_jargon))
        except Exception:
            return baseline_jargon
    return baseline_jargon

# --- 🔄 UNIVERSAL SYNONYM & VERSION MATCHER ---
def check_skill_match(requirement, extracted_set):
    """
    Bhai, yeh function strict versioning mismatches ko handle karta hai.
    Agar system 'html5' mangega aur user ke paas 'html' hoga, toh yeh use true return karega.
    """
    req = requirement.lower().strip()
    
    # Custom Synonym Mapping Dictionary
    SYNONYM_MAP = {
        "html5": {"html", "html5"},
        "css3": {"css", "css3"},
        "javascript": {"javascript", "js"},
        "node.js": {"node.js", "nodejs", "node"},
        "next.js": {"next.js", "nextjs"},
        "vue": {"vue", "vue.js", "vuejs"},
        "apis": {"api", "apis", "rest api", "api integration"}
    }
    
    # Gather all valid forms for the requirement
    acceptable_forms = {req}
    if req in SYNONYM_MAP:
        acceptable_forms.update(SYNONYM_MAP[req])
        
    for form in acceptable_forms:
        if form in extracted_set:
            return True
        # Substring level safe cross-checking (e.g. 'rest api' matches if user has 'api')
        if any(form in ext for ext in extracted_set):
            return True
            
    return False

# --- 2. ADVANCED PDF EXTRACTION ---
def extract_and_clean_pdf(uploaded_file):
    raw_text = ""
    if uploaded_file.type == "application/pdf":
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text(x_tolerance=2, y_tolerance=3)
                    if extracted: raw_text += extracted + "\n"
        except Exception: return ""
    else:
        raw_text = str(uploaded_file.read(), "utf-8", errors="ignore")

    if raw_text:
        clean_text = re.sub(r'\S+@\S+', ' ', raw_text)
        clean_text = re.sub(r'http\S+|www.\S+', ' ', clean_text)
        clean_text = re.sub(r'\+?\d[\d -]{8,15}\d', ' ', clean_text)
        clean_text = re.sub(r'[•◦●▪\-\*|]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
    return ""

# --- 3. DOMAIN KNOWLEDGE CONFIGURATION ---
BASE_DOMAINS = {
    "Software Developer": {
        "primary": ["java", "python", "c++", "c#", "data structures", "oop", "sql"],
        "secondary": ["git", "github", "linux", "agile", "problem solving", "docker"]
    },
    "Frontend Developer": {
        "primary": ["javascript", "html5", "css3", "react", "dom"],
        "secondary": ["tailwind css", "typescript", "next.js", "vue", "figma", "git"]
    },
    "Backend Engineer": {
        "primary": ["node.js", "python", "java", "sql", "apis", "rest api"],
        "secondary": ["express.js", "django", "postgresql", "mongodb", "aws", "docker", "microservices"]
    },
    "Full-Stack Developer": {
        "primary": ["javascript", "react", "node.js", "sql", "apis", "mongodb"],
        "secondary": ["express.js", "typescript", "git", "aws", "docker", "tailwind css", "ci/cd"]
    },
    "Data Scientist": {
        "primary": ["python", "machine learning", "sql", "pandas", "numpy"],
        "secondary": ["tensorflow", "pytorch", "r", "matplotlib", "scikit-learn", "eda", "data visualization"]
    },
    "Data Engineer": {
        "primary": ["python", "sql", "etl", "data pipelines", "databases"],
        "secondary": ["apache spark", "hadoop", "airflow", "snowflake", "bigquery", "apache kafka"]
    },
    "DevOps Engineer": {
        "primary": ["docker", "kubernetes", "ci/cd", "linux", "aws", "git"],
        "secondary": ["terraform", "jenkins", "ansible", "bash", "github actions", "azure"]
    },
    "Cloud Architect": {
        "primary": ["aws", "azure", "google cloud", "cloud architecture", "microservices"],
        "secondary": ["terraform", "kubernetes", "distributed systems", "serverless", "security"]
    },
    "Machine Learning Engineer": {
        "primary": ["python", "pytorch", "tensorflow", "machine learning", "deep learning"],
        "secondary": ["computer vision", "nlp", "model optimization", "aws", "docker", "numpy"]
    },
    "Mobile Developer": {
        "primary": ["swift", "kotlin", "flutter", "react native", "mobile app development"],
        "secondary": ["dart", "android studio", "firebase", "ui design", "git"]
    },
    "Systems/Embedded Engineer": {
        "primary": ["c", "c++", "rust", "embedded systems", "linux"],
        "secondary": ["rtos", "concurrent programming", "assembly", "microcontrollers", "git"]
    },
    "QA / Automation Engineer": {
        "primary": ["automated testing", "selenium", "cypress", "jest", "tdd"],
        "secondary": ["python", "java", "git", "ci/cd", "api testing", "playwright"]
    },
    "Cybersecurity Analyst": {
        "primary": ["cybersecurity", "network security", "linux", "python", "penetration testing"],
        "secondary": ["cryptography", "wireshark", "security auditing", "bash", "aws security"]
    },
    "Scrum Master / Agile Coach": {
        "primary": ["agile methodologies", "scrum master", "sprint planning", "jira"],
        "secondary": ["stakeholder management", "team development", "kanban", "communication"]
    },
    "IT Analyst": {
        "primary": ["sql", "excel", "agile", "data analysis", "databases"],
        "secondary": ["scrum", "itil", "tableau", "power bi", "jira"]
    }
}

DOMAIN_REQUIREMENTS = BASE_DOMAINS.copy()
ADVANCED_JSON_ROLES = {}

if os.path.exists(ADV_MATRIX_PATH):
    try:
        with open(ADV_MATRIX_PATH, "r", encoding="utf-8") as f:
            ADVANCED_JSON_ROLES = json.load(f)
            if isinstance(ADVANCED_JSON_ROLES, dict):
                DOMAIN_REQUIREMENTS.update(ADVANCED_JSON_ROLES)
    except Exception:
        pass

# --- 4. UI SIDEBAR CONFIGURATION ---
st.sidebar.header("📋 Job Target Config")

role_source = st.sidebar.radio(
    "Select Role Category Group:", 
    ["Standard Core Roles", "Advanced / Custom Roles (AI Pool)"]
)

if role_source == "Standard Core Roles" or not ADVANCED_JSON_ROLES:
    selectable_roles = list(BASE_DOMAINS.keys())
else:
    selectable_roles = list(ADVANCED_JSON_ROLES.keys())

job_role = st.sidebar.selectbox("Select Target Job Field/Role:", selectable_roles)

# --- 5. MAIN UI DESIGN ---
st.title("🎯 ResuRanker: Advanced AI Resume Analyzer")
st.subheader("Enterprise ATS | Skill Gap Analysis & Weighted Grading")
st.markdown("---")

uploaded_file = st.file_uploader("Upload candidate resume (PDF or TXT format)", type=["pdf", "txt"])

if uploaded_file is not None:
    with st.spinner("🕵️‍♂️ Running Deep AI Skill Gap Analysis..."):
        
        sanitized_resume_text = extract_and_clean_pdf(uploaded_file)
        
        if not sanitized_resume_text.strip():
            st.error("⚠️ Resume empty or unreadable.")
        else:
            with st.expander("🔍 DEBUG: View Raw Extracted Text"):
                st.write(sanitized_resume_text)

            # 🧠 NLP Inference
            doc = nlp_v6(sanitized_resume_text.lower())
            raw_extracted_skills = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "SKILL"]))
            
            # --- AI EXTRACTION COMPILATION (With Length Guardrails) ---
            extracted_skills_set = set()
            for raw_skill in raw_extracted_skills:
                clean_skill = re.sub(r"[^a-zA-Z0-9\s\.\+#\-']", ' ', raw_skill)
                clean_skill = re.sub(r'\s+', ' ', clean_skill).strip().lower()
                
                if clean_skill and len(clean_skill) > 1:
                    if len(clean_skill.split()) <= 4 and len(clean_skill) <= 40:
                        extracted_skills_set.add(clean_skill)

            # --- 🤖 AUTOMATED HYBRID BREAKOUT ENGINE (With Ghost Prevention) ---
            for role, reqs in DOMAIN_REQUIREMENTS.items():
                for req in reqs["primary"] + reqs["secondary"]:
                    if len(req.split()) > 4 or len(req) > 40:
                        continue
                    pattern = r'(?<![a-zA-Z0-9])' + re.escape(req) + r'(?![a-zA-Z0-9])'
                    if re.search(pattern, sanitized_resume_text.lower()):
                        extracted_skills_set.add(req)

            CORE_JARGON_DATABASE = load_dynamic_knowledge_base()
            for jargon in CORE_JARGON_DATABASE:
                if len(jargon.split()) > 4 or len(jargon) > 40:
                    continue
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(jargon) + r'(?![a-zA-Z0-9])'
                if re.search(pattern, sanitized_resume_text.lower()):
                    extracted_skills_set.add(jargon)

            # --- GLOBAL MASTER SKILLS PROFILE SECTION ---
            st.markdown("### 🧠 AI Extracted Master Skills Portfolio")
            st.markdown("All verified technical traits and competencies detected across the entire resume structure:")
            
            if extracted_skills_set:
                skills_cloud = " &nbsp;|&nbsp; ".join([f"**`{s.title()}`**" for s in sorted(extracted_skills_set)])
                st.info(skills_cloud)
            else:
                st.warning("No technical entities detected inside text context.")
            
            st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

            # 📑 SPLIT INTERFACE VIA TABS
            tab1, tab2, tab3 = st.tabs([
                "🎯 Targeted Role Analyzer", 
                "🌍 Filter Resume for Job Roles", 
                "🔍 Explore Other Roles Detailed Breakdown"
            ])

            # ==================== TAB 1: TARGETED ENGINE ====================
            with tab1:
                req_primary = [p.lower() for p in DOMAIN_REQUIREMENTS[job_role]["primary"]]
                req_secondary = [s.lower() for s in DOMAIN_REQUIREMENTS[job_role]["secondary"]]
                
                # --- STRICT WEIGHTED SCORING & GAP ANALYSIS USING SYNONYM MATCHING ---
                user_has_primary = []
                user_missing_primary = []
                for req in req_primary:
                    if check_skill_match(req, extracted_skills_set):
                        user_has_primary.append(req)
                    else:
                        user_missing_primary.append(req)

                user_has_secondary = []
                user_missing_secondary = []
                for req in req_secondary:
                    if check_skill_match(req, extracted_skills_set):
                        user_has_secondary.append(req)
                    else:
                        user_missing_secondary.append(req)

                other_skills_found = set()
                for ext_skill in extracted_skills_set:
                    is_primary = any(req in ext_skill for req in req_primary)
                    is_secondary = any(req in ext_skill for req in req_secondary)
                    if not is_primary and not is_secondary:
                        other_skills_found.add(ext_skill)

                primary_score = (len(user_has_primary) / len(req_primary)) * 70 if req_primary else 0
                secondary_score = (len(user_has_secondary) / len(req_secondary)) * 30 if req_secondary else 0
                total_match_score = primary_score + secondary_score

                if total_match_score >= 80:
                    grade, color = "Top-Tier Fit 🌟", "green"
                elif total_match_score >= 50:
                    grade, color = "Good Fit 👍", "blue"
                elif total_match_score >= 30:
                    grade, color = "Average / Needs Upskilling 📈", "orange"
                else:
                    grade, color = "Skill Gap Too High ⚠️", "red"

                col1, col2 = st.columns([1, 1.2]) 
                with col1:
                    st.markdown("#### 🔥 Target Verified Skills")
                    if user_has_primary:
                        for skill in sorted(user_has_primary):
                            st.markdown(f"✅ **{skill.title()}**")
                    else:
                        st.info("No matching primary skills found in this resume.")
                        
                    st.markdown("#### 🌟 Extra/Bonus Skills (Relevant)")
                    st.caption("Matches Job Secondary Requirements")
                    if user_has_secondary:
                        for skill in sorted(user_has_secondary):
                            st.markdown(f"➕ *{skill.title()}*")
                    else:
                        st.info("No additional relevant skills found.")
                    
                    st.markdown("#### 🌍 Cross-Functional / Other Tech")
                    st.caption("Candidate's skills in other domains & custom dynamic jargon")
                    if other_skills_found:
                        for skill in sorted(other_skills_found):
                            st.markdown(f"🔹 *{skill.title()}*")
                    else:
                        st.info("No cross-functional skills detected.")
                        
                with col2:
                    st.markdown("#### 📊 Skill Gap Analysis Report")
                    st.markdown(f"**Target Role:** {job_role} | **Final Grade:** :{color}[{grade}]")
                    st.progress(int(total_match_score))
                    st.subheader(f"Match Score: {total_match_score:.1f}%")
                    st.markdown("---")
                    
                    st.markdown("#### 🚨 Strictly Missing (Must Haves)")
                    if user_missing_primary:
                        for missing in user_missing_primary:
                            st.markdown(f"❌ <span style='color:red;'>**{missing.title()}**</span> (Critical for role)", unsafe_allow_html=True)
                    else:
                        st.success("✅ Candidate meets ALL Primary Requirements!")

                    st.markdown("#### 💡 Highly Recommended (Good to Have)")
                    if user_missing_secondary:
                        for missing in user_missing_secondary:
                            st.markdown(f"⚠️ *{missing.title()}* (Boosts hiring chance)")
                    else:
                        st.success("✅ Candidate has ALL recommended skills!")

            # ==================== TAB 2: MULTI-ROLE REVERSE FILTER ====================
            with tab2:
                st.markdown("### 🌍 Universal Job Role Fitment Matrix")
                st.markdown("This engine cross-checks candidate traits across all configured systems simultaneously.")
                st.markdown("---")
                st.markdown("#### 📊 Ranked Market Competency Evaluation (Scores >= 15%)")
                
                role_rankings = []
                for current_eval_role, specs in DOMAIN_REQUIREMENTS.items():
                    p_reqs = [p.lower() for p in specs["primary"]]
                    s_reqs = [s.lower() for s in specs["secondary"]]
                    
                    # Synonym matching engine for dynamic alignment
                    matches_p = [r for r in p_reqs if check_skill_match(r, extracted_skills_set)]
                    matches_s = [r for r in s_reqs if check_skill_match(r, extracted_skills_set)]
                    
                    calc_p = (len(matches_p) / len(p_reqs)) * 70 if p_reqs else 0
                    calc_s = (len(matches_s) / len(s_reqs)) * 30 if s_reqs else 0
                    final_score = calc_p + calc_s
                    
                    if final_score >= 15.0:
                        role_rankings.append({
                            "role": current_eval_role,
                            "score": final_score,
                            "matched_p": matches_p,
                            "matched_s": matches_s,
                            "total_p_count": len(p_reqs)
                        })
                
                role_rankings = sorted(role_rankings, key=lambda x: x["score"], reverse=True)
                
                if not role_rankings:
                    st.info("No corporate domain matches detected above the baseline 15% mark.")
                else:
                    for ranking in role_rankings:
                        r_score = ranking["score"]
                        
                        m_col1, m_col2 = st.columns([1.5, 2])
                        with m_col1:
                            st.markdown(f"🔹 **{ranking['role']}**")
                            st.markdown(f"**Score: {r_score:.1f}%**")
                        with m_col2:
                            st.progress(int(r_score))
                            with st.expander("👁️ View Matching Trait Details"):
                                p_txt = ", ".join(ranking['matched_p']).title() if ranking['matched_p'] else "None"
                                s_txt = ", ".join(ranking['matched_s']).title() if ranking['matched_s'] else "None"
                                st.markdown(f"📌 **Primary Met:** {p_txt} *(Total Required: {ranking['total_p_count']})*")
                                # 🔥 FIXED STRING BUG: Variable is now dynamically injected safely
                                st.markdown(f"📌 **Secondary Met:** {s_txt}")

            # ==================== TAB 3: OPTIONAL DROPDOWN INSPECTOR ====================
            with tab3:
                st.markdown("### 🔍 Deep-Dive Into Any Registered Job Role")
                st.markdown("Select any specific career matrix directly from your custom dataset below to instantly generate a custom gap report.")
                
                full_master_roles = list(DOMAIN_REQUIREMENTS.keys())
                selected_other_role = st.selectbox(
                    "Choose an Alternate Job Role to Inspect:", 
                    options=full_master_roles, 
                    key="alternate_role_dropdown"
                )
                
                st.markdown(f"### 📊 Detailed Gap Analysis for: **{selected_other_role}**")
                st.markdown("---")
                
                alt_primary = [p.lower() for p in DOMAIN_REQUIREMENTS[selected_other_role]["primary"]]
                alt_secondary = [s.lower() for s in DOMAIN_REQUIREMENTS[selected_other_role]["secondary"]]
                
                alt_has_primary = []
                alt_missing_primary = []
                for req in alt_primary:
                    if check_skill_match(req, extracted_skills_set):
                        alt_has_primary.append(req)
                    else:
                        alt_missing_primary.append(req)

                alt_has_secondary = []
                alt_missing_secondary = []
                for req in alt_secondary:
                    if check_skill_match(req, extracted_skills_set):
                        alt_has_secondary.append(req)
                    else:
                        alt_missing_secondary.append(req)

                alt_p_score = (len(alt_has_primary) / len(alt_primary)) * 70 if alt_primary else 0
                alt_s_score = (len(alt_has_secondary) / len(alt_secondary)) * 30 if alt_secondary else 0
                alt_total_score = alt_p_score + alt_s_score
                
                if alt_total_score >= 80: alt_grade, alt_color = "Top-Tier Fit 🌟", "green"
                elif alt_total_score >= 50: alt_grade, alt_color = "Good Fit 👍", "blue"
                elif alt_total_score >= 30: alt_grade, alt_color = "Average / Needs Upskilling 📈", "orange"
                else: alt_grade, alt_color = "Skill Gap Too High ⚠️", "red"
                
                alt_col1, alt_col2 = st.columns([1, 1.2])
                with alt_col1:
                    st.markdown("#### ✅ Matched Capabilities")
                    st.markdown("**Core Primary Skills Met:**")
                    if alt_has_primary:
                        st.markdown(", ".join([f"`{s.title()}`" for s in sorted(alt_has_primary)]))
                    else:
                        st.caption("No matching primary elements detected.")
                        
                    st.markdown("**Secondary/Bonus Skills Met:**")
                    if alt_has_secondary:
                        st.markdown(", ".join([f"`{s.title()}`" for s in sorted(alt_has_secondary)]))
                    else:
                        st.caption("No matching secondary elements detected.")
                        
                with alt_col2:
                    st.markdown(f"**Fitment Grade:** :{alt_color}[{alt_grade}]")
                    st.progress(int(alt_total_score))
                    st.subheader(f"Calculated Score: {alt_total_score:.1f}%")
                    
                    st.markdown("##### 🚨 Strictly Missing (Must Haves for this Role)")
                    if alt_missing_primary:
                        for missing in alt_missing_primary:
                            st.markdown(f"❌ <span style='color:red;'>**{missing.title()}**</span>", unsafe_allow_html=True)
                    else:
                        st.success("✅ Meets all primary conditions!")
                        
                    st.markdown("##### 💡 Recommended Additions")
                    if alt_missing_secondary:
                        for missing in alt_missing_secondary:
                            st.markdown(f"⚠️ *{missing.title()}*")
                    else:
                        st.success("✅ Meets all secondary conditions!")