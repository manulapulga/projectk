import streamlit as st
import streamlit.components.v1 as components

def hide_streamlit_style():
    # Use components.html for more control
    hide_style = """
        <style>
        /* Remove ALL Streamlit branding */
        footer {display: none !important;}
        #MainMenu {display: none !important;}
        header {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        
        /* Hide anything with streamlit in class or text */
        *[class*="streamlit"]:not(.stApp):not(.stButton) {display: none !important;}
        
        /* Force hide the footer area */
        .stApp > div:last-child > div:last-child {display: none !important;}
        </style>
        
        <script>
        // Nuclear option - remove all streamlit branding
        setInterval(() => {
            // Remove footer
            document.querySelectorAll('footer').forEach(el => el.remove());
            
            // Remove header elements with streamlit
            document.querySelectorAll('header').forEach(el => {
                if (el.innerText.includes('Streamlit') || el.innerHTML.includes('streamlit')) {
                    el.remove();
                }
            });
            
            // Remove any element with 'streamlit' in class or text
            document.querySelectorAll('*').forEach(el => {
                const classAttr = el.getAttribute('class') || '';
                const text = el.innerText || '';
                if (classAttr.includes('streamlit') || text.includes('Streamlit')) {
                    if (!el.closest('.stApp')) {
                        el.remove();
                    }
                }
            });
        }, 1000);
        </script>
    """
    
    # Use both methods for maximum coverage
    st.markdown(hide_style, unsafe_allow_html=True)
    components.html(hide_style, height=0, width=0)