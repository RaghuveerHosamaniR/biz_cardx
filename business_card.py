# =====================================================
# BizCardX: Extracting Business Card Data with OCR
# =====================================================
import streamlit as st
import easyocr
import pandas as pd
import mysql.connector as sql
from PIL import Image
import os
import re

# ----------------------------
# MySQL Connection
# ----------------------------
mydb = sql.connect(
    host="localhost",
    user="root",
    password="Raghuveer9964@",   
    database="bizcardx_bd",
    port=3306
)
mycursor = mydb.cursor()

# Create table if not exists
mycursor.execute('''
CREATE TABLE IF NOT EXISTS card_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name TEXT,
    card_holder TEXT,
    designation TEXT,
    mobile_number VARCHAR(50),
    email TEXT,
    website TEXT,
    area TEXT,
    city TEXT,
    state TEXT,
    pin_code VARCHAR(10),
    image LONGBLOB
)
''')

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(
    page_title="BizCardX OCR | By Raghuveer R",
    page_icon="🃏",
    layout="wide"
)

st.title("BizCardX: Extracting Business Card Data with OCR")

# ----------------------------
# Initialize EasyOCR
# ----------------------------
reader = easyocr.Reader(['en'])

# ----------------------------
# Upload & Extract Section
# ----------------------------
st.header("Upload a Business Card")
uploaded_file = st.file_uploader("Choose an image", type=['jpg','jpeg','png'])

if uploaded_file is not None:
    # Read image bytes
    image_bytes = uploaded_file.read()

    # Display uploaded image
    st.image(image_bytes, caption="Uploaded Card", use_column_width=True)

    # Save temporarily for OCR
    temp_path = os.path.join(os.getcwd(), "temp_card.jpg")
    with open(temp_path, "wb") as f:
        f.write(image_bytes)

    # OCR extraction
    extracted_text = reader.readtext(temp_path, detail=0, paragraph=False)

    st.subheader("Extracted Text")
    st.write(extracted_text)

    # ----------------------------
    # Process extracted text
    # ----------------------------
    data = {
        "company_name": "",
        "card_holder": "",
        "designation": "",
        "mobile_number": "",
        "email": "",
        "website": "",
        "area": "",
        "city": "",
        "state": "",
        "pin_code": "",
        "image": image_bytes
    }

    for idx, line in enumerate(extracted_text):
        line_clean = line.strip()
        line_lower = line_clean.lower()

        # Email
        if "@" in line_clean:
            data["email"] = line_clean

        # Website
        elif "www" in line_lower or "http" in line_lower:
            data["website"] = line_clean

        # Mobile Number
        mobile_match = re.search(
            r'(\+?\d{1,3}[-.\s]?)?(\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4})',
            line_clean
            )
        if mobile_match:
         data["mobile_number"] = mobile_match.group()

        # State and Pincode together e.g., "TamilNadu 600113"
        state_pincode_match = re.match(r'([A-Za-z\s]+)\s+(\d{5,6})', line_clean)
        if state_pincode_match:
            data["state"] = state_pincode_match.group(1).strip()
            data["pin_code"] = state_pincode_match.group(2).strip()

        # Pin Code only
        elif re.search(r'\b\d{5,6}\b', line_clean):
            data["pin_code"] = re.search(r'\b\d{5,6}\b', line_clean).group()

        # City / Area
        elif "," in line_clean:
            parts = [p.strip() for p in line_clean.split(",")]
            if len(parts) >= 2:
                data["area"] = parts[0]
                data["city"] = parts[1]

        # Card Holder and Designation
        if idx == 0:
            data["card_holder"] = line_clean
        elif idx == 1:
            data["designation"] = line_clean

    # Last line assumed as company name
    if extracted_text:
        data["company_name"] = extracted_text[-1]

    # Display extracted data in dataframe
    df = pd.DataFrame([data])
    st.subheader("Processed Data")
    st.dataframe(df)

    # ----------------------------
    # Insert automatically into MySQL
    # ----------------------------
    try:
        sql_insert = """
        INSERT INTO card_data
        (company_name, card_holder, designation, mobile_number, email, website, area, city, state, pin_code, image)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        mycursor.execute(sql_insert, (
            data["company_name"],
            data["card_holder"],
            data["designation"],
            data["mobile_number"],
            data["email"],
            data["website"],
            data["area"],
            data["city"],
            data["state"],
            data["pin_code"],
            data["image"]
        ))
        mydb.commit()
        st.success("Data saved to MySQL successfully!")
    except Exception as e:
        st.error(f"Error: {e}")

# ----------------------------
# View / Modify / Delete Data
# ----------------------------
st.header("Manage Database Records")

# Fetch data
mycursor.execute("SELECT id, company_name, card_holder, designation, mobile_number, email, website, area, city, state, pin_code FROM card_data")
records = mycursor.fetchall()
columns = ["ID","company_name","card_holder","designation","mobile_number","email","website","area","city","state","pin_code"]

df_records = pd.DataFrame(records, columns=columns)
st.dataframe(df_records)

# Delete Record
delete_id = st.number_input("Enter ID to delete record", min_value=1, step=1)
if st.button("Delete Record"):
    mycursor.execute("DELETE FROM card_data WHERE id=%s", (delete_id,))
    mydb.commit()
    st.success(f"Record with ID {delete_id} deleted!")

# Update Record
st.subheader("Update Record")
update_id = st.number_input("Enter ID to update", min_value=1, step=1, key="update_id")
update_field = st.selectbox("Select Field to Update", columns[1:])
new_value = st.text_input("New Value")
if st.button("Update Record"):
    if update_field and new_value:
        sql_update = f"UPDATE card_data SET {update_field.lower().replace(' ', '_')}=%s WHERE id=%s"
        mycursor.execute(sql_update, (new_value, update_id))
        mydb.commit()
        st.success(f"Updated {update_field} for ID {update_id}!")