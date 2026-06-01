import streamlit as st
import requests
import plotly.graph_objects as go
import time
import os

FASTAPI_BACKEND_URL = "https://communication-backend-9c2l.onrender.com"

st.set_page_config(
    page_title="Communication Assessment Tool",
    layout="wide"
)

# ---------------------------------------------------------------------
# INITIALIZE TRAINEE PROFILE WORKSPACE & TIMING STATE STREAMS
# ---------------------------------------------------------------------
if "profile_locked" not in st.session_state: st.session_state.profile_locked = True
if "trainee_name" not in st.session_state: st.session_state.trainee_name = ""
if "trainee_emp_id" not in st.session_state: st.session_state.trainee_emp_id = ""

# Exam Phase Status Variables
if "exam_active" not in st.session_state: st.session_state.exam_active = False
if "current_section" not in st.session_state: st.session_state.current_section = "Audio"  # "Audio" or "Writing"
if "phase" not in st.session_state: st.session_state.phase = "Preparation"              # "Preparation" or "Active"
if "phase_start_epoch" not in st.session_state: st.session_state.phase_start_epoch = None

# Metrics State Caches
if "saved_wpm" not in st.session_state: st.session_state.saved_wpm = 0.0
if "saved_fillers" not in st.session_state: st.session_state.saved_fillers = 0
if "saved_pauses" not in st.session_state: st.session_state.saved_pauses = 0
if "saved_transcript" not in st.session_state: st.session_state.saved_transcript = ""
if "saved_results" not in st.session_state: st.session_state.saved_results = {}
if "cheat_detected" not in st.session_state: st.session_state.cheat_detected = False

if "session_history" not in st.session_state:
    st.session_state.session_history = {
        "labels": ["Baseline Eval", "Practice Run 1", "Practice Run 2"],
        "spoken": [55.0, 68.0, 72.0],
        "written": [60.0, 62.0, 71.0]
    }

# ---------------------------------------------------------------------
# LAYER 1: INITIAL REGISTRATION GATEWAY
# ---------------------------------------------------------------------
if st.session_state.profile_locked:
    st.title("Trainee Authentication Gateway")
    st.write("Please initialize your examination environment profile parameters to unlock the proctored assessment assets.")
    st.markdown("---")
    
    col_reg1, col_reg2 = st.columns(2)
    with col_reg1: input_name = st.text_input("Enter Full Name:")
    with col_reg2: input_id = st.text_input("Enter Employee ID:")
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Initialize Environment", type="primary"):
        if input_name.strip() == "" or input_id.strip() == "":
            st.error("Profile initialization aborted: Both fields are mandatory parameters.")
        else:
            st.session_state.trainee_name = input_name.strip()
            st.session_state.trainee_emp_id = input_id.strip()
            st.session_state.profile_locked = False
            st.rerun()
    st.stop()

user_name = st.session_state.trainee_name
user_id = st.session_state.trainee_emp_id

# ---------------------------------------------------------------------
# UNIFIED PHASE TIMER SEQUENCER (PREPARATION VS. ACTIVE)
# ---------------------------------------------------------------------
time_remaining = 0
is_exam_locked = False

if st.session_state.exam_active and st.session_state.phase_start_epoch is not None:
    elapsed = int(time.time() - st.session_state.phase_start_epoch)
    
    # Preparation phase gets 2 minutes (120s), Active phase gets 5 minutes (300s)
    target_limit = 60 if st.session_state.phase == "Preparation" else 180
    time_remaining = max(target_limit - elapsed, 0)
    
    # Auto-advance phase when time expires
    if time_remaining <= 0:
        if st.session_state.phase == "Preparation":
            st.session_state.phase = "Active"
            st.session_state.phase_start_epoch = time.time()
            st.rerun()
        else:
            is_exam_locked = True

# ---------------------------------------------------------------------
# SIDEBAR STATUS SYSTEM CONTROL TILES (ADVANCED FULLSCREEN LOCKDOWN)
# ---------------------------------------------------------------------
st.sidebar.header("Proctor Management")
st.sidebar.markdown(f"**Candidate:** `{user_name}`\n\n**Emp ID:** `{user_id}`")
st.sidebar.markdown("---")

def inject_proctor_lockdown(is_active, violations_allowed=3):
    status_flag = "true" if is_active else "false"
    st.components.v1.html(
        f"""
        <script>
            const targetDoc = window.parent.document;
            const targetWin = window.parent;
            const bodyEl = targetDoc.documentElement;

            function launchFullscreen() {{
                if ({status_flag}) {{
                    if (!targetDoc.fullscreenElement) {{
                        bodyEl.requestFullscreen().catch(err => {{
                            console.log("Fullscreen activation deferred.");
                        }});
                    }}
                }}
            }}

            let escapeCount = 0;
            targetDoc.addEventListener('fullscreenchange', () => {{
                if (!targetDoc.fullscreenElement && {status_flag}) {{
                    escapeCount++;
                    if (escapeCount >= {violations_allowed}) {{
                        alert('TERMINAL BREACH: Fullscreen broken. Exam invalidated.');
                        window.parent.location.reload();
                    }} else {{
                        alert(`PROCTOR ALERT [Violation ${{escapeCount}}/{violations_allowed}]: Return to fullscreen immediately or your session will be locked.`);
                        setTimeout(launchFullscreen, 500);
                    }}
                }}
            }});

            let tabNavCount = 0;
            function logTabViolation() {{
                if ({status_flag}) {{
                    tabNavCount++;
                    if (tabNavCount >= {violations_allowed}) {{
                        alert('EXAM VOIDED: Tab switching violation limit hit.');
                        window.parent.location.reload();
                    }} else {{
                        alert(`ILLEGAL ACTION CAUGHT [Violation ${{tabNavCount}}/{violations_allowed}]: Do not switch tabs or windows!`);
                    }}
                }}
            }}

            targetDoc.addEventListener('visibilitychange', () => {{
                if (targetDoc.visibilityState === 'hidden') logTabViolation();
            }});
            
            targetWin.addEventListener('blur', () => {{
                setTimeout(() => {{ if (!targetDoc.hasFocus()) logTabViolation(); }}, 200);
            }});

            targetDoc.addEventListener('copy', (e) => e.preventDefault());
            targetDoc.addEventListener('paste', (e) => e.preventDefault());
            targetDoc.addEventListener('contextmenu', (e) => e.preventDefault());

            if ({status_flag}) {{
                setInterval(launchFullscreen, 1000);
            }}
        </script>
        """, height=0,
    )

if not st.session_state.exam_active:
    st.sidebar.subheader("Exam Activation")
    st.sidebar.warning("Clicking below locks the terminal environment into Fullscreen mode and starts your 2-min preparation window.")
    
    if st.sidebar.button("Start Assessment", type="primary", use_container_width=True):
        st.session_state.phase_start_epoch = time.time()
        st.session_state.phase = "Preparation"
        st.session_state.current_section = "Audio"
        st.session_state.exam_active = True
        st.rerun()
    inject_proctor_lockdown(is_active=False)
else:
    inject_proctor_lockdown(is_active=True)
    
    st.sidebar.markdown(f"**Section:** `{st.session_state.current_section} Assessment`")
    st.sidebar.markdown(f"**Status:** `{st.session_state.phase} Phase`")
    
    st.sidebar.markdown("### Live Phase Countdown")
    with st.sidebar:
        st.components.v1.html(
            f"""
            <div style="font-family: monospace; background-color: #1e1e24; color: #ff4b4b; padding: 12px; border-radius: 6px; text-align: center; font-size: 24px; font-weight: bold; border: 2px solid #ff4b4b;" id="countdown-box">00:00</div>
            <script>
                var total_seconds = {time_remaining};
                var display_box = document.getElementById('countdown-box');
                function updateClock() {{
                    if (total_seconds <= 0) {{
                        display_box.innerHTML = "NEXT PHASE";
                        setTimeout(function() {{ window.parent.location.reload(); }}, 500);
                        return;
                    }}
                    var minutes = Math.floor(total_seconds / 60); var seconds = total_seconds % 60;
                    var clean_m = minutes < 10 ? "0" + minutes : minutes; var clean_s = seconds < 10 ? "0" + seconds : seconds;
                    display_box.innerHTML = clean_m + ":" + clean_s;
                    total_seconds--; setTimeout(updateClock, 1000);
                }}
                updateClock();
            </script>
            """, height=75
        )

    if st.session_state.phase == "Preparation":
        if st.sidebar.button("Skip Prep and Start", use_container_width=True):
            st.session_state.phase = "Active"
            st.session_state.phase_start_epoch = time.time()
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Exam Termination")
    if st.sidebar.button("End Test and Generate Report", type="secondary", use_container_width=True):
        st.session_state.exam_active = False
        st.components.v1.html("<script>if(window.parent.document.fullscreenElement){window.parent.document.exitFullscreen();}</script>", height=0)
        st.rerun()

WORD_LIMIT = 150
st.title("Secure Communication Assessment Environment")
if not st.session_state.exam_active:
    st.info("Tutorial Mode Active: Browse the tabs below to get familiar. Click 'Start Assessment' in the sidebar to lock the browser and unlock input windows.")
elif is_exam_locked:
    st.error("TIME LIMIT EXPIRED: Submissions locked.")

tab1, tab2, tab3 = st.tabs(["In-App Audio Assessment", "Supervised Writing Assessment", "Progress and Summary Matrix"])

# ==========================================
# TAB 1: IN-APP AUDIO NATIVE ASSESSMENT
# ==========================================
with tab1:
    st.header("Audio Evaluation")
    
    if st.session_state.exam_active and st.session_state.current_section == "Audio" and st.session_state.phase == "Preparation":
        st.warning("Preparation Phase Active: Organize your thoughts. Audio recording tools unlock when the countdown hits zero.")
    
    st.write("Talk on Time Management.  Click the Microphone icon below to record your response natively.")
    from audio_recorder_streamlit import audio_recorder
    audio_bytes = audio_recorder(text="Click to record speaking path", recording_color="#d32f2f", neutral_color="#333333", icon_size="2x")
    
    if audio_bytes is not None:
        st.audio(audio_bytes, format='audio/wav')
        
        audio_submit_disabled = (
            not st.session_state.exam_active or 
            st.session_state.current_section != "Audio" or 
            st.session_state.phase != "Active" or 
            is_exam_locked
        )
        
        if st.button("Analyze Speech Performance", type="primary", disabled=audio_submit_disabled):
            with st.spinner("Processing speech metrics..."):
                try:
                    files = {"file": ("live_recording.wav", audio_bytes, "audio/wav")}
                    response = requests.post(f"{FASTAPI_BACKEND_URL}/assess/speech", files=files)
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.saved_wpm = data.get("words_per_minute", 0.0)
                        st.session_state.saved_fillers = data.get("filler_word_count", 0)
                        st.session_state.saved_pauses = data.get("long_pauses_detected", 0)
                        st.session_state.saved_transcript = data.get("transcript", "")
                        
                        if not isinstance(st.session_state.saved_results, dict):
                            st.session_state.saved_results = {}
                        st.session_state.saved_results["speech_tier"] = data.get("speech_tier", "-")
                        
                        next_num = len(st.session_state.session_history["labels"]) + 1
                        st.session_state.session_history["labels"].append(f"Attempt {next_num}")
                        st.session_state.session_history["spoken"].append(float(min(int((data.get("words_per_minute", 0.0)/60)*100), 100) if data.get("words_per_minute", 0.0) > 0 else 70))
                        st.session_state.session_history["written"].append(float(st.session_state.session_history["written"][-1] if st.session_state.session_history["written"] else 60.0))
                        
                        # ADVANCE MANIFEST AUTOMATICALLY TO WRITING SECTION
                        st.session_state.current_section = "Writing"
                        st.session_state.phase = "Preparation"
                        st.session_state.phase_start_epoch = time.time()
                        st.success("Speech Metrics Logged! Moving to Writing Section Preparation...")
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e: st.error(f"Error: {str(e)}")

# ==========================================
# TAB 2: IN-APP WRITING ASSESSMENT (PROCTOR-READY)
# ==========================================
with tab2:
    st.header("Writing Evaluation")
    
    is_writing_active = (
        st.session_state.exam_active and 
        st.session_state.current_section == "Writing" and 
        st.session_state.phase == "Active" and 
        not is_exam_locked
    )
    
    if st.session_state.exam_active and st.session_state.current_section == "Writing" and st.session_state.phase == "Preparation":
        st.warning("Preparation Phase Active: Review your assignment prompt. The typing window unlocks automatically when prep time ends.")
    
    st.write(f"Topic : Time Management. Type your essay response below. (Max {WORD_LIMIT} words).")
    user_text = st.text_area("Enter your response:", height=200, placeholder="Inputs unlock automatically during active phase...", disabled=not is_writing_active)
    
    # Hide spelling highlights natively
    st.components.v1.html(
        """
        <script>
            function killHighlights() {
                var textareas = window.parent.document.querySelectorAll('textarea');
                textareas.forEach(function(el) {
                    el.setAttribute('spellcheck', 'false');
                    el.setAttribute('autocomplete', 'off');
                    el.setAttribute('autocorrect', 'off');
                });
            }
            killHighlights(); setTimeout(killHighlights, 500); setTimeout(killHighlights, 1500);
        </script>
        """, height=0
    )

    current_word_count = len(user_text.split())
    st.markdown(f"Word Metrics: `{current_word_count} / {WORD_LIMIT} words used`")

    writing_submit_disabled = (not is_writing_active or current_word_count > WORD_LIMIT)
    if st.button("Analyze Writing Quality", type="primary", disabled=writing_submit_disabled):
        if user_text.strip() == "": st.warning("Please enter text context first.")
        else:
            with st.spinner("Analyzing text layout metrics..."):
                try:
                    payload = {"text": user_text, "cheat_flag": st.session_state.cheat_detected}
                    response = requests.post(f"{FASTAPI_BACKEND_URL}/assess/text", data=payload)
                    if response.status_code == 200:
                        res_data = response.json()
                        if not isinstance(st.session_state.saved_results, dict):
                            st.session_state.saved_results = {}
                        st.session_state.saved_results.update(res_data)
                        
                        next_num = len(st.session_state.session_history["labels"]) + 1
                        st.session_state.session_history["labels"].append(f"Attempt {next_num}")
                        st.session_state.session_history["spoken"].append(float(st.session_state.session_history["spoken"][-1] if st.session_state.session_history["spoken"] else 70.0))
                        st.session_state.session_history["written"].append(float(res_data.get('grammar_score', 0)))
                        st.success("Writing Metrics Logged! View results in Tab 3.")
                except Exception as e: st.error(f"Error: {str(e)}")

# ==========================================
# TAB 3: COMPLETE RADAR SCORECARD & EXPORT MATRIX
# ==========================================
with tab3:
    st.header("Comprehensive Performance Dashboard")
    
    # Force type-safe localized extractions
    wpm = float(st.session_state.get("saved_wpm", 0.0))
    fillers = int(st.session_state.get("saved_fillers", 0))
    pauses = int(st.session_state.get("saved_pauses", 0))
    transcript = str(st.session_state.get("saved_transcript", "")).strip()
    
    results = st.session_state.get("saved_results", {})
    if not isinstance(results, dict) or results is None: 
        results = {}

    grammar_score = int(results.get('grammar_score', 0))
    vocabulary_score = int(results.get('vocabulary_score', 0))
    conciseness_score = int(results.get('conciseness_score', 0))
    impact_score = int(results.get('impact_score', 0))
    speech_tier = str(results.get('speech_tier', "-"))

    # Isolate array pointers from missing key crashes
    strengths_list = results.get('identified_strengths', [])
    if not strengths_list: 
        strengths_list = ["Audio data parsed and logged." if wpm > 0 else "System awaiting entry run."]
        
    errors_list = results.get('identified_errors', [])
    if not errors_list: 
        errors_list = ["No critical text anomalies found yet." if wpm > 0 else "System awaiting entry run."]
        
    suggestions_list = results.get('improvement_suggestions', [])
    if not suggestions_list: 
        suggestions_list = ["Continue baseline presentation drills." if wpm > 0 else "System awaiting entry run."]

    if wpm == 0.0 and grammar_score == 0:
        st.warning("No live exam records found for this terminal workspace. Submit responses in Tab 1 or Tab 2 first.")
    else:
        st.subheader("Individual Competency Scorecard")
        st.markdown("**Speech Analytics:**")
        aud_c1, aud_c2, aud_c3, aud_c4 = st.columns(4)
        aud_c1.metric(label="Speaking Pacing Rate", value=f"{wpm} WPM")
        aud_c2.metric(label="Filler Words Count", value=str(fillers))
        aud_c3.metric(label="Long Pauses Detected", value=str(pauses))
        aud_c4.metric(label="Assessed Competency Tier", value=speech_tier)
        
        st.markdown("**Writing Analytics:**")
        wri_c1, wri_c2, wri_c3, wri_c4 = st.columns(4)
        wri_c1.metric(label="Grammar and Clarity", value=f"{grammar_score} / 100")
        wri_c2.metric(label="Vocabulary Depth", value=f"{vocabulary_score} / 100")
        wri_c3.metric(label="Conciseness Profile", value=f"{conciseness_score} / 100")
        wri_c4.metric(label="Impact Vector", value=f"{impact_score} / 100")
        
        st.markdown("---")
        ui_col1, ui_col2 = st.columns([1, 1])
        with ui_col1:
            categories = ['Grammar/<br>Ease', 'Vocabulary<br>Sophistication', 'Conciseness<br>Score', 'Impact<br>Alignment']
            scores = [grammar_score, vocabulary_score, conciseness_score, impact_score]
            fig = go.Figure(data=go.Scatterpolar(r=scores, theta=categories, fill='toself', line_color='rgb(214, 39, 40)'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title="Linguistic Quality Blueprint")
            st.plotly_chart(fig, use_container_width=True)
            if transcript: st.text_area("Captured Speech Transcript:", value=transcript, height=100, disabled=True)
                
        with ui_col2:
            st.subheader("Evaluation Analysis Overview")
            for strength in strengths_list: st.markdown(f"Strength: {strength}")
            for error in errors_list: st.markdown(f"Advisory: {error}")
            for advice in suggestions_list: st.markdown(f"Action: {advice}")

        st.markdown("---")
        fig_progress = go.Figure()
        fig_progress.add_trace(go.Scatter(x=st.session_state.session_history["labels"], y=st.session_state.session_history["spoken"], name='Speech Track %', mode='lines+markers', line=dict(color='firebrick', width=3)))
        fig_progress.add_trace(go.Scatter(x=st.session_state.session_history["labels"], y=st.session_state.session_history["written"], name='Written Track %', mode='lines+markers', line=dict(color='royalblue', width=3)))
        fig_progress.update_layout(title='Longitudinal Trainee Progress Matrix', xaxis_title='Timeline Evaluations', template='plotly_white')
        st.plotly_chart(fig_progress, use_container_width=True)

       # =================================================================
        # EXPORT CERTIFIED EVALUATION RECORD
        # =================================================================
        st.markdown("---")
        st.subheader("Export Certified Evaluation Record")
        
        strengths_html = "".join([f"<li>{s}</li>" for s in strengths_list])
        errors_html = "".join([f"<li>{e}</li>" for e in errors_list])
        steps_html = "".join([f"<li>STEP {idx+1}: {adv}</li>" for idx, adv in enumerate(suggestions_list)])

        # Unified single configuration entry point for absolute safety
        clean_user_id = "".join([c for c in str(user_id) if c.isalnum()]).lower()
        chart_image_path = os.path.join(os.getcwd(), f"temp_radar_{clean_user_id}.png")
        
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            # Map out the 4 core scoring channels symmetrically
            labels = ['Grammar/Ease', 'Vocabulary Soph.', 'Conciseness', 'Impact Alignment']
            stats = [grammar_score, vocabulary_score, conciseness_score, impact_score]
            
            # Close the radar loop mathematically by repeating the first value
            angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
            stats = stats + [stats[0]]
            angles = angles + [angles[0]]
            
            # Initialize a pure standalone Matplotlib Polar Plot
            fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
            
            # Draw the filled polygon structure matching your dashboard colors
            ax.fill(angles, stats, color='#D62728', alpha=0.25)
            ax.plot(angles, stats, color='#D62728', linewidth=2)
            
            # Setup the clean visual boundaries (0 to 100 max rating scale)
            ax.set_yticklabels([])
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, fontsize=8, color='#1A365D', weight='bold')
            ax.set_ylim(0, 100)
            
            # Export chart image asset natively to the server disk cache
            plt.savefig(chart_image_path, bbox_inches='tight', dpi=150)
            plt.close()
            
            # Link it via file schema directly to the PDF compiler context
            image_url = f"file://{os.path.abspath(chart_image_path)}"
            image_html = f'<img src="{image_url}" width="230" height="230" />'
            
        except Exception as e:
            # Fallback to visual table matrix representation if disk output fails
            image_html = f'<p style="color:red; font-size:10pt;">Graphic engine paused: {str(e)}</p>'

        report_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 15mm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; color: #333333; }}
                .header {{ background-color: #1A365D; color: white; padding: 18px; text-align: center; }}
                .section-title {{ font-size: 13pt; color: #1A365D; font-weight: bold; border-bottom: 2px solid #D69E2E; margin-top: 18px; padding-bottom: 4px; }}
                .metric-table {{ width: 100%; margin-top: 8px; border-collapse: collapse; }}
                .metric-table th {{ background-color: #2B6CB0; color: white; padding: 6px; text-align: left; font-size: 10pt; }}
                .metric-table td {{ padding: 10px; background-color: #F7FAFC; border: 1px solid #E2E8F0; text-align: center; font-size: 11pt; }}
                .val {{ font-size: 15pt; font-weight: bold; color: #2B6CB0; }}
                .transcript-box {{ background-color: #FAFAFA; border: 1px solid #E2E8F0; padding: 10px; font-style: italic; font-size: 9pt; margin-top: 8px; }}
                .split-container {{ width: 100%; margin-top: 12px; }}
                .left-col {{ width: 45%; text-align: center; vertical-align: top; }}
                .right-col {{ width: 55%; vertical-align: top; padding-left: 15px; }}
                ul {{ padding-left: 15px; margin-top: 4px; }} li {{ margin-bottom: 4px; font-size: 10pt; }}
                h4 {{ margin-bottom: 2px; margin-top: 8px; font-size: 11pt; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>OFFICIAL ASSESSMENT PERFORMANCE SCORECARD</h1>
                <h3>TRAINEE NAME: {user_name} &nbsp;|&nbsp; EMP ID: {user_id}</h3>
            </div>
            <div class="section-title">Spoken Audio Assessment Metrics</div>
            <table class="metric-table">
                <tr><th>Speaking Pacing Rate</th><th>Filler Words Count</th><th>Assessed Competency Tier</th></tr>
                <tr><td><span class="val">{wpm} WPM</span></td><td><span class="val">{fillers}</span></td><td><span class="val">{speech_tier}</span></td></tr>
            </table>
            {"<div class='transcript-box'><strong>Speech Transcript:</strong> <br>" + transcript + "</div>" if transcript != "" else ""}
            
            <div class="section-title">Written Competency Ratings</div>
            <table class="metric-table">
                <tr><th>Grammar and Clarity</th><th>Vocabulary Depth</th><th>Conciseness Profile</th><th>Impact</th></tr>
                <tr><td><span class="val">{grammar_score}%</span></td><td><span class="val">{vocabulary_score}%</span></td><td><span class="val">{conciseness_score}%</span></td><td><span class="val">{impact_score}%</span></td></tr>
            </table>
            
            <table class="split-container">
                <tr>
                    <td class="left-col">
                        <div style="font-weight:bold; font-size:9pt; color:#1A365D; margin-bottom:4px;">Linguistic Quality Map</div>
                        {image_html}
                    </td>
                    <td class="right-col" style="text-align: left;">
                        <div style="font-size:11pt; color:#1A365D; font-weight:bold; border-left:3px solid #D69E2E; padding-left:5px;">Evaluation Insights Summary</div>
                        <h4>Identified Core Strengths:</h4><ul>{strengths_html}</ul>
                        <h4>Flagged Weakness Metrics:</h4><ul>{errors_html}</ul>
                    </td>
                </tr>
            </table>
            <div class="section-title">Actionable Tactical Plan</div><ul>{steps_html}</ul>
        </body>
        </html>
        """

        # Initialize explicit state containers out of loop scopes
        pdf_data = None
        clean_filename = f"Performance_Report_{clean_user_id}_{user_name.replace(' ', '_')}.pdf"

        try:
            from io import BytesIO
            from xhtml2pdf import pisa
            
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(report_html, dest=pdf_buffer)
            
            if not pisa_status.err:
                pdf_data = pdf_buffer.getvalue()
            else:
                st.error("PDF Engine Error parsing layout configurations.")
        except Exception as e: 
            st.error(f"PDF Compiler Error: {str(e)}")
        finally:
            # Safely handle cache wiping loops
            if os.path.exists(chart_image_path):
                try: os.remove(chart_image_path)
                except Exception: pass

        # RENDER DOWNLOAD BUTTON NATIVELY OUTSIDE SCOPE LIFECYCLES
        if pdf_data is not None:
            st.download_button(
                label="Download Certified Scorecard PDF",
                data=pdf_data,
                file_name=clean_filename,
                mime="application/pdf",
                type="primary"
            )
