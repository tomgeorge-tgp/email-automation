
import streamlit as st
import requests
import json

st.set_page_config(page_title="Bulk Email Sender", layout="centered")

st.title("📧 Bulk Email Sender (ACS)")

template_file = st.file_uploader("Upload HTML Template", type=["html"])
excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if st.button("Send Emails"):
    if not template_file or not excel_file:
        st.error("All files are required")
    else:
        # Prepare files for upload
        # Streamlit's UploadedFile object behaves like a file, so we can pass it directly
        # However, requests.post expects a tuple or file-like object with a name
        
        files = {
            "template_file": (template_file.name, template_file, "text/html"),
            "excel_file": (excel_file.name, excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }

        data = {}

        with st.spinner("Sending emails in parallel..."):
            try:
                # Assuming backend is running on localhost:8000
                res = requests.post(
                    "http://localhost:9000/send-bulk-emails",
                    files=files,
                    data=data,
                    timeout=300
                )
                
                if res.status_code == 200:
                    st.success("Emails processed!")
                    st.json(res.json())
                else:
                    st.error(f"Error: {res.status_code} - {res.text}")
            except requests.exceptions.ConnectionError:
                 st.error("Could not connect to backend. Is it running? (Make sure to run 'make dev')")
            except Exception as e:
                st.error(f"An error occurred: {e}")
