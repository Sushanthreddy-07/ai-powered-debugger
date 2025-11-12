import streamlit as st
from helper_functions import fix_code, determine_execution_success, execute_code

st.set_page_config(page_title="Python AI Code Fixer", layout="centered")

st.title("🐍 Python AI Code Fixer")
st.markdown("Paste your Python code below and click **Check Code** to find and fix bugs.")

user_code = st.text_area("Your Python Code", height=300)

if st.button("Check Code"):
    if user_code.strip() == "":
        st.warning("Please paste some code first.")
    else:
        st.spinner("Checking for errors...")
        success, output = execute_code(user_code, timeout=5)

        status, msg = determine_execution_success(output, {})
        
        if status == "Success":
            st.success("✅ Good job! There aren't any mistakes.")
        else:
            st.error("❌ Error detected. Here's the corrected version:")
            fixed = fix_code(user_code, msg)
            st.code(fixed, language='python')
            st.info("⚠️ AI has attempted to fix the issue based on analysis.")
