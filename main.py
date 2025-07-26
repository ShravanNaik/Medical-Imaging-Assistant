

import sys
import importlib
importlib.import_module('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import tempfile
import uuid
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from PIL import Image as PILImage, ImageEnhance, ImageFilter
import streamlit as st
import numpy as np
from dotenv import load_dotenv
import openai
import io

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🏥 RadiAI - Medical Imaging Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


hide_footer_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* This targets GitHub icon in the footer */
    .st-emotion-cache-1y4p8pa.ea3mdgi1 {
        display: none !important;
    }

    /* This targets the entire footer area */
    .st-emotion-cache-164nlkn {
        display: none !important;
    }
    </style>
"""

st.markdown(hide_footer_style, unsafe_allow_html=True)
# Get API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found in .env file")
    st.markdown("""
    **Please add the following to your .env file:**
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ```
    """)
    st.stop()

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Professional Medical CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    :root {
        --medical-blue: #1e3a8a;
        --medical-light-blue: #3b82f6;
        --medical-green: #059669;
        --medical-orange: #ea580c;
        --medical-red: #dc2626;
        --medical-gray: #6b7280;
        --medical-light-gray: #f8fafc;
        --medical-border: #e5e7eb;
        --shadow-light: 0 2px 8px rgba(0,0,0,0.08);
        --shadow-medium: 0 4px 16px rgba(0,0,0,0.12);
        --shadow-heavy: 0 8px 32px rgba(0,0,0,0.16);
    }
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    /* Professional header */
    .medical-header {
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-light-blue) 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-medium);
    }
    
    .medical-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .medical-header p {
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Professional cards */
    .medical-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: var(--shadow-light);
        border: 1px solid var(--medical-border);
        transition: all 0.2s ease;
    }
    
    .medical-card:hover {
        box-shadow: var(--shadow-medium);
    }
    
    .analysis-card {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: var(--shadow-medium);
        border-left: 4px solid var(--medical-blue);
    }
    
    /* Medical disclaimer styling */
    .medical-disclaimer {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 2px solid #f59e0b;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: var(--shadow-light);
    }
    
    .medical-disclaimer h4 {
        color: #92400e;
        margin: 0 0 0.5rem 0;
        font-weight: 600;
    }
    
    .medical-disclaimer p {
        color: #92400e;
        margin: 0;
        font-weight: 500;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.25rem;
        box-shadow: var(--shadow-light);
    }
    
    .status-success {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: var(--medical-green);
        border: 1px solid #059669;
    }
    
    .status-warning {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
        color: var(--medical-red);
        border: 1px solid #dc2626;
    }
    
    .status-info {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: var(--medical-blue);
        border: 1px solid var(--medical-light-blue);
    }
    
    /* Image display area */
    .image-display {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: var(--shadow-light);
        border: 2px dashed var(--medical-border);
        text-align: center;
        margin: 1.5rem 0;
    }
    
    .image-uploaded {
        border: 2px solid var(--medical-green);
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    }
    
    /* Enhancement controls */
    .enhancement-panel {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 1px solid var(--medical-light-blue);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: var(--shadow-light);
    }
    
    /* Professional buttons */
    .stButton > button {
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-light-blue) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: var(--shadow-light) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-medium) !important;
    }
    
    /* Sidebar styling */
    .sidebar-section {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: var(--shadow-light);
        border: 1px solid var(--medical-border);
    }
    
    /* Medical metrics grid */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: var(--shadow-light);
        border: 1px solid var(--medical-border);
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-medium);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--medical-blue);
        display: block;
        margin-bottom: 0.25rem;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: var(--medical-gray);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    /* Welcome screen */
    .welcome-card {
        background: linear-gradient(135deg, white 0%, #f8fafc 100%);
        border-radius: 16px;
        padding: 3rem;
        margin: 2rem 0;
        box-shadow: var(--shadow-medium);
        border: 1px solid var(--medical-border);
        text-align: center;
    }
    
    .welcome-card h3 {
        color: var(--medical-blue);
        font-size: 1.8rem;
        margin-bottom: 1rem;
    }
    
    .processing-status {
        background: linear-gradient(90deg, #56ab2f 0%, #a8e6cf 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        animation: pulse 2s infinite;
        margin: 1rem 0;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    if "image_enhancements" not in st.session_state:
        st.session_state.image_enhancements = {
            'brightness': 1.0,
            'contrast': 1.0,
            'sharpness': 1.0
        }
    if "current_analysis" not in st.session_state:
        st.session_state.current_analysis = None

def enhance_medical_image(image: PILImage.Image, enhancements: Dict[str, float]) -> PILImage.Image:
    """Apply medical imaging enhancements with professional algorithms"""
    try:
        # Convert to grayscale for X-ray-like images
        if image.mode == 'L' or np.array(image).mean() < 100:
            if image.mode != 'L':
                image = image.convert('L')
        
        # Apply professional image enhancements
        if enhancements['brightness'] != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(enhancements['brightness'])
        
        if enhancements['contrast'] != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(enhancements['contrast'])
        
        if enhancements['sharpness'] != 1.0:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(enhancements['sharpness'])
        
        return image
    except Exception as e:
        st.warning(f"Image enhancement failed: {e}")
        return image

def create_professional_analysis_prompt() -> str:
    """Create a comprehensive educational image analysis prompt"""
    return """
You are an AI assistant demonstrating image analysis capabilities for educational and development purposes only. This is a development/demonstration application, not for clinical use.

Please analyze this image from an educational perspective, showing how AI might approach visual analysis:

## 🔍 **Educational Image Analysis Demo**

### **Visual Elements Assessment**
- Describe what you observe in the image
- Note any patterns, shapes, or structures visible
- Comment on image quality and clarity

### **Technical Image Properties**
- Image contrast and brightness levels
- Any artifacts or technical issues visible
- Overall image quality assessment

### **Educational Structure Analysis**
If this appears to be a medical image for educational purposes:
- Describe anatomical structures visible (educational context only)
- Note any variations or interesting features
- Explain what a medical professional might look for

### **AI Analysis Demonstration**
- Show how AI processes visual information
- Demonstrate pattern recognition capabilities
- Explain the analytical approach used

### **Educational Learning Points**
- What features are most prominent in the image
- How different visual elements relate to each other
- What this demonstrates about AI image analysis

## 🎓 **Educational Context**
This analysis demonstrates:
- AI image processing capabilities
- Visual pattern recognition
- Educational image interpretation
- Technology demonstration for learning

## ⚠️ **Important Development Disclaimer**
This is a development demonstration only:
- Not for medical diagnosis or clinical use
- Educational and development purposes only
- Shows AI capabilities in image analysis
- Requires professional medical interpretation for any real medical images

Please provide an educational analysis that demonstrates AI capabilities while emphasizing this is for development/educational purposes only.
"""

# Initialize session state
initialize_session_state()

# Professional Header
st.markdown("""
<div class="medical-header">
    <h1>🏥 RadiAI - Medical Imaging Assistant</h1>
    <p>Professional AI-Enhanced Radiological Analysis • Advanced AI Vision • For Healthcare Professionals</p>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 1rem; border-radius: 8px; margin-top: 1rem;">
        <p style="margin: 0; font-weight: 600; font-size: 1rem;">
            ⚠️ DEVELOPMENT VERSION - NOT FOR CLINICAL USE
        </p>
        <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; opacity: 0.9;">
            This is a demonstration/development application only
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# API Status
if OPENAI_API_KEY:
    st.markdown("""
    <div class="status-badge status-success">
        ✅ AI Vision API Connected & Ready
    </div>
    """, unsafe_allow_html=True)

# Development Warning Banner
st.markdown("""
<div style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); 
           color: white; padding: 1.5rem; border-radius: 12px; margin: 1rem 0; 
           box-shadow: 0 4px 16px rgba(220, 38, 38, 0.3); text-align: center;">
    <h3 style="margin: 0 0 0.5rem 0; color: white;">🚨 DEVELOPMENT APPLICATION - DO NOT USE FOR REAL MEDICAL DIAGNOSIS</h3>
    <p style="margin: 0; font-weight: 500;">
        This is a demonstration/development version only. Not approved for clinical use, patient diagnosis, or medical decision making.
        Always consult qualified medical professionals for actual medical imaging interpretation.
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("""
    <div class="sidebar-section">
        <h3>🔧 System Configuration</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Reload Environment", use_container_width=True):
        load_dotenv(override=True)
        st.success("Environment reloaded!")
        st.rerun()
    
    st.markdown("""
    <div class="sidebar-section">
        <h3>🖼️ Image Enhancement</h3>
    </div>
    """, unsafe_allow_html=True)
    
    enhance_enabled = st.checkbox("Enable Image Enhancement", help="Apply professional image processing algorithms")
    
    if enhance_enabled:
        st.markdown('<div class="enhancement-panel">', unsafe_allow_html=True)
        
        st.session_state.image_enhancements['brightness'] = st.slider(
            "Brightness Adjustment", 0.5, 2.0, 1.0, 0.1,
            help="Adjust image brightness for optimal visualization"
        )
        st.session_state.image_enhancements['contrast'] = st.slider(
            "Contrast Enhancement", 0.5, 2.0, 1.0, 0.1,
            help="Enhance image contrast for better tissue differentiation"
        )
        st.session_state.image_enhancements['sharpness'] = st.slider(
            "Edge Sharpening", 0.5, 2.0, 1.0, 0.1,
            help="Sharpen edges for improved detail visualization"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Analysis History
    if st.session_state.analysis_history:
        st.markdown("""
        <div class="sidebar-section">
            <h3>📋 Analysis History</h3>
        </div>
        """, unsafe_allow_html=True)
        
        for i, analysis in enumerate(reversed(st.session_state.analysis_history[-5:])):
            with st.expander(f"Case {len(st.session_state.analysis_history) - i}"):
                st.write(f"**Date:** {analysis['timestamp']}")
                st.write(f"**File:** {analysis['filename']}")
                st.write(f"**Modality:** {analysis.get('modality', 'Not specified')}")
                if st.button(f"📄 View Report", key=f"view_{i}"):
                    st.session_state.current_analysis = analysis['analysis']
    
    # Professional Information
    st.markdown("""
    <div class="sidebar-section">
        <h3>🤖 AI Model Information</h3>
        <div class="status-badge status-info">
            Advanced AI Vision
        </div>
        <p style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">
            • Advanced visual reasoning<br>
            • Enhanced pattern recognition<br>
            • Medical image analysis<br>
            • Professional medical terminology
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Medical Disclaimer
    st.markdown("""
    <div class="medical-disclaimer">
        <h4>⚠️ DEVELOPMENT DISCLAIMER</h4>
        <p><strong>THIS IS A DEVELOPMENT/DEMO APPLICATION ONLY</strong><br><br>
        🚨 <strong>NOT FOR CLINICAL USE:</strong> This application is for development, testing, and demonstration purposes only.<br><br>
        🚫 <strong>DO NOT USE FOR:</strong><br>
        • Real patient diagnosis<br>
        • Clinical decision making<br>
        • Medical treatment planning<br>
        • Emergency medical situations<br><br>
        ✅ <strong>APPROPRIATE USE:</strong> Educational demonstrations, software testing, and development purposes only.</p>
    </div>
    """, unsafe_allow_html=True)

# Main Content Area
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📁 Medical Image Upload")
    
    uploaded_file = st.file_uploader(
        "Select Medical Imaging Study",
        type=["jpg", "jpeg", "png", "dcm", "dicom", "tiff", "bmp"],
        help="Supported: JPEG, PNG, DICOM, TIFF, BMP formats",
        accept_multiple_files=False
    )
    
    if uploaded_file:
        # File information
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.markdown(f"""
        <div class="medical-card">
            <h4>📊 File Information</h4>
            <p><strong>Filename:</strong> {uploaded_file.name}</p>
            <p><strong>Size:</strong> {file_size_mb:.2f} MB</p>
            <p><strong>Type:</strong> {uploaded_file.type}</p>
            <div class="status-badge status-success">
                ✅ File Successfully Uploaded
            </div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    if uploaded_file:
        st.markdown("### 🖼️ Image Preview")
        
        try:
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Load and process image
            image = PILImage.open(uploaded_file)
            
            # Apply enhancements if enabled
            if enhance_enabled and any(v != 1.0 for v in st.session_state.image_enhancements.values()):
                image = enhance_medical_image(image, st.session_state.image_enhancements)
                enhancement_applied = True
            else:
                enhancement_applied = False
            
            # Display image with professional styling
            st.markdown('<div class="image-display image-uploaded">', unsafe_allow_html=True)
            
            # Resize for optimal display
            width, height = image.size
            max_display_width = 500
            if width > max_display_width:
                aspect_ratio = width / height
                new_width = max_display_width
                new_height = int(new_width / aspect_ratio)
                display_image = image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            else:
                display_image = image
            
            st.image(
                display_image,
                caption=f"Medical Image: {uploaded_file.name}",
                use_container_width=True
            )
            
            if enhancement_applied:
                st.markdown("""
                <div class="status-badge status-info">
                    🔧 Image Enhancement Applied
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Error loading image: {str(e)}")
    else:
        st.markdown("### 📤 Upload Medical Image")
        st.markdown("""
        <div class="image-display">
            <h4>🏥 Professional Medical Image Analysis</h4>
            <p>Upload your medical imaging study for comprehensive AI-enhanced analysis</p>
            <p style="color: #6b7280; font-size: 0.9rem;">Drag and drop or click to browse files</p>
        </div>
        """, unsafe_allow_html=True)

# Analysis Section
if uploaded_file:
    st.markdown("---")
    st.markdown("### 🔍 AI-Enhanced Radiological Analysis")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button(
            "🚀 Perform Professional Analysis",
            type="primary",
            use_container_width=True,
            help="Start comprehensive AI-enhanced medical image analysis"
        ):
            
            with st.status("🔄 RadiAI is analyzing your medical image...", expanded=True) as status:
                try:
                    st.write("📸 Converting image for OpenAI Vision API...")
                    
                    # Reset file pointer and convert image to base64
                    uploaded_file.seek(0)
                    
                    # Process the image (apply enhancements if enabled)
                    if enhance_enabled and any(v != 1.0 for v in st.session_state.image_enhancements.values()):
                        enhanced_image = enhance_medical_image(image, st.session_state.image_enhancements)
                    else:
                        enhanced_image = image
                    
                    # Convert to RGB if necessary
                    if enhanced_image.mode in ('RGBA', 'LA'):
                        enhanced_image = enhanced_image.convert('RGB')
                    
                    # Convert to base64
                    buffer = io.BytesIO()
                    enhanced_image.save(buffer, format='PNG')
                    base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    st.write("✅ Image processed successfully!")
                    st.write("🧠 Sending to AI Vision for educational analysis...")
                    
                    # Get educational analysis prompt
                    analysis_prompt = create_professional_analysis_prompt()
                    
                    # Prepare messages for AI Vision API
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": analysis_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ]
                    
                    # Call AI Vision API
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        max_tokens=4000,
                        temperature=0.7
                    )
                    
                    # Extract the analysis result
                    analysis_result = response.choices[0].message.content
                    
                    st.write("✅ Educational analysis completed successfully!")
                    status.update(label="🧠 AI Educational Analysis Complete!", state="complete")
                    
                    # Display results with educational formatting
                    st.markdown("### 📋 Educational AI Image Analysis Demo")
                    
                    # Educational disclaimer banner
                    st.markdown("""
                    <div class="medical-disclaimer">
                        <h4>🎓 EDUCATIONAL DEMONSTRATION</h4>
                        <p><strong>📚 This is an educational demonstration of AI image analysis capabilities.</strong><br><br>
                        <strong>PURPOSE:</strong> To show how AI can process and analyze visual information for educational and development purposes.<br><br>
                        <strong>NOT FOR DIAGNOSIS:</strong> This analysis is purely educational and demonstrates AI technology capabilities only.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Analysis content
                    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                    st.markdown(analysis_result)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Analysis metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("""
                        <div class="metric-card">
                            <span class="metric-value">AI</span>
                            <div class="metric-label">Analysis Engine</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("""
                        <div class="metric-card">
                            <span class="metric-value">✓</span>
                            <div class="metric-label">Analysis Complete</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        analysis_time = datetime.now().strftime("%H:%M")
                        st.markdown(f"""
                        <div class="metric-card">
                            <span class="metric-value">{analysis_time}</span>
                            <div class="metric-label">Analysis Time</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Add to analysis history
                    analysis_record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'filename': uploaded_file.name,
                        'modality': 'Professional Analysis',
                        'analysis': analysis_result
                    }
                    st.session_state.analysis_history.append(analysis_record)
                    
                    # Professional actions
                    st.markdown("### 🎯 Professional Actions")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        # Create professional report
                        report_header = f"""
# RadiAI Professional Analysis Report

**Patient Study:** {uploaded_file.name}  
**Analysis Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**AI Analysis Engine:** Advanced AI Vision  
**File Size:** {file_size_mb:.2f} MB  

---

"""
                        full_report = report_header + analysis_result + """

---

**DEVELOPMENT APPLICATION DISCLAIMER:**

🚨 **THIS IS A DEVELOPMENT/DEMONSTRATION VERSION ONLY** 🚨

**NOT FOR CLINICAL USE:** This AI analysis is generated by a development application for demonstration and testing purposes only.

**DO NOT USE FOR:**
- Real patient diagnosis or medical treatment decisions
- Clinical care or patient management
- Emergency medical situations
- Professional medical reporting

**APPROPRIATE USE:** Software development, educational demonstrations, and testing purposes only.

**IMPORTANT:** Always consult qualified medical professionals for actual medical imaging interpretation and patient care.

**Generated by RadiAI - Medical Imaging Assistant (Development Version)**  
**Powered by Advanced AI Vision Technology - For Development/Demo Use Only**
"""
                        
                        st.download_button(
                            label="📥 Download Report",
                            data=full_report,
                            file_name=f"RadiAI_Analysis_{uploaded_file.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    
                    with col2:
                        if st.button("🔄 Re-analyze", use_container_width=True):
                            st.rerun()
                    
                    with col3:
                        if st.button("📋 Save History", use_container_width=True):
                            st.success("✅ Analysis saved to history!")
                    
                    with col4:
                        if st.button("🖨️ Print Report", use_container_width=True):
                            st.info("📋 Use browser print function (Ctrl+P)")
                    
                    # Success highlight
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%); 
                               color: white; padding: 2rem; border-radius: 15px; text-align: center; margin: 1rem 0;">
                        <h3>🎉 AI Vision Analysis Complete! (Development Demo)</h3>
                        <p>🔍 <strong>Development Application:</strong> For demonstration and testing purposes only</p>
                        <p>🧠 <strong>AI Analysis Demo:</strong> Shows potential AI analysis capabilities</p>
                        <p>🎯 <strong>Educational Format:</strong> Demonstrates structured reporting format</p>
                        <p>⚠️ <strong>Not for Clinical Use:</strong> Development/demonstration version only</p>
                    </div>
                    """, unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    st.markdown("""
                    <div class="medical-disclaimer">
                        <h4>Analysis Error</h4>
                        <p><strong>Troubleshooting Steps:</strong></p>
                        <ul>
                            <li>Verify the image is a valid medical imaging study</li>
                            <li>Check your internet connection</li>
                            <li>Try uploading in a different supported format</li>
                            <li>Ensure your AI API access has sufficient resources</li>
                            <li>Contact your IT administrator if issues persist</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

else:
    # Professional welcome screen
    st.markdown("### 👋 Welcome to RadiAI Professional")
    
    # Welcome header
    st.markdown("""
    <div class="welcome-card">
        <h3>🏥 Advanced Medical Imaging Analysis (Development Demo)</h3>
        <p style="font-size: 1.1rem; color: #6b7280; margin-bottom: 1rem;">
            Development demonstration of AI-enhanced radiological analysis capabilities using advanced AI vision technology. 
            This application showcases potential AI features for healthcare software development.
        </p>
        <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 1rem; margin-top: 1rem;">
            <p style="margin: 0; color: #92400e; font-weight: 600;">
                ⚠️ DEVELOPMENT VERSION - This is a demonstration application for software development and educational purposes only. 
                Not for clinical use or real medical diagnosis.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features in Streamlit columns
    st.markdown("#### 🔬 Supported Imaging Modalities")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Radiography:**
        - Chest X-rays, bone radiographs, dental imaging
        
        **Computed Tomography:**
        - CT scans with contrast and without
        
        **Magnetic Resonance:**
        - MRI sequences across all body systems
        """)
    
    with col2:
        st.markdown("""
        **Ultrasound:**
        - Sonographic studies and Doppler imaging
        
        **Nuclear Medicine:**
        - Scintigraphy and PET imaging
        
        **Mammography:**
        - Breast imaging and tomosynthesis
        """)
    
    st.markdown("---")
    
    st.markdown("#### 🎯 Professional Features")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Structured Reporting:**
        - Professional radiological format
        
        **Evidence-Based Analysis:**
        - Medical terminology and standards
        
        **Differential Diagnosis:**
        - Ranked diagnostic considerations
        """)
    
    with col2:
        st.markdown("""
        **Clinical Correlation:**
        - Actionable recommendations
        
        **Quality Assessment:**
        - Technical adequacy evaluation
        
        **Urgency Indicators:**
        - Red flag identification
        """)
    
    st.markdown("---")
    
    st.markdown("#### 🤖 Advanced AI Vision Capabilities")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Advanced Pattern Recognition:**
        - Subtle finding detection
        
        **Medical Image Understanding:**
        - Comprehensive visual analysis
        
        **Direct API Integration:**
        - Simple, reliable processing
        """)
    
    with col2:
        st.markdown("""
        **Professional Communication:**
        - Clear, actionable reporting
        
        **Confidence Assessment:**
        - Reliability indicators
        
        **Immediate Results:**
        - Real-time analysis
        """)
    
    st.markdown("---")
    
    st.markdown("#### 🔒 Professional Standards")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Privacy Considerations:**
        - Secure API processing
        
        **Quality Assurance:**
        - Professional validation required
        
        **Educational Purpose:**
        - Learning and support tool
        """)
    
    with col2:
        st.markdown("""
        **Clinical Integration:**
        - Workflow-compatible reporting
        
        **Analysis History:**
        - Complete case tracking
        
        **Professional Oversight:**
        - Human expert review recommended
        """)
    
    # Professional disclaimer
    st.markdown("---")
    st.markdown("""
    <div class="medical-disclaimer">
        <h4>🚨 DEVELOPMENT APPLICATION - IMPORTANT LIMITATIONS</h4>
        <p><strong>THIS IS A DEVELOPMENT/DEMONSTRATION APPLICATION ONLY</strong><br><br>
        
        <strong>🚫 DO NOT USE FOR:</strong><br>
        • Real patient diagnosis or medical decision making<br>
        • Clinical care, treatment planning, or patient management<br>
        • Emergency medical situations or urgent care<br>
        • Professional medical reporting or documentation<br><br>
        
        <strong>✅ APPROPRIATE USE:</strong><br>
        • Software development and testing<br>
        • Educational demonstrations of AI capabilities<br>
        • Technology showcases and proof of concepts<br>
        • Learning about AI in healthcare applications<br><br>
        
        <strong>DISCLAIMER:</strong> This development application demonstrates potential AI capabilities in medical imaging analysis. 
        All outputs are for demonstration purposes only. Real medical imaging must always be interpreted by qualified 
        medical professionals using approved medical devices and software.</p>
    </div>
    """, unsafe_allow_html=True)

# Professional Footer
st.markdown("---")
st.markdown("""
<div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 12px; padding: 2rem; text-align: center; margin-top: 2rem;'>
    <h3 style='margin: 0 0 1rem 0; color: white;'>🏥 RadiAI Professional Medical Imaging</h3>
    <div style='display: flex; justify-content: center; gap: 3rem; margin: 1.5rem 0; flex-wrap: wrap;'>
        <div style='text-align: center;'>
            <h4 style='margin: 0; color: #bfdbfe;'>🚨 Emergency Care</h4>
            <p style='margin: 0.25rem 0 0 0; font-size: 0.9rem;'>Call emergency services immediately</p>
        </div>
        <div style='text-align: center;'>
            <h4 style='margin: 0; color: #bfdbfe;'>🏥 Professional Consultation</h4>
            <p style='margin: 0.25rem 0 0 0; font-size: 0.9rem;'>Validate with qualified radiologists</p>
        </div>
        <div style='text-align: center;'>
            <h4 style='margin: 0; color: #bfdbfe;'>📋 Clinical Correlation</h4>
            <p style='margin: 0.25rem 0 0 0; font-size: 0.9rem;'>Integrate with patient history</p>
        </div>
        <div style='text-align: center;'>
            <h4 style='margin: 0; color: #bfdbfe;'>🔬 Multidisciplinary Care</h4>
            <p style='margin: 0.25rem 0 0 0; font-size: 0.9rem;'>Team-based approach recommended</p>
        </div>
    </div>
    <p style='color: #bfdbfe; font-size: 0.9rem; margin: 1rem 0 0 0;'>
        <em>RadiAI Development Version • Powered by Advanced AI Vision • For Development/Demo Use Only</em>
    </p>
    <p style='color: #93c5fd; font-size: 0.8rem; margin: 0.5rem 0 0 0;'>
        © 2024 RadiAI Development Application • AI Healthcare Technology Demonstration • Not for Clinical Use
    </p>
</div>
""", unsafe_allow_html=True)
