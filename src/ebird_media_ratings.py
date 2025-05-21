import os
import urllib.request
import pandas as pd
import gzip
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import psycopg2
import json

# Load configuration
with open("config.json", "r") as config_file:
    config = json.load(config_file)

def fetch_and_filter_csv(user_id, output_file="new_filtered_data.csv"):
    url = f"https://search.macaulaylibrary.org/api/v2/export.csv?userId={user_id}&count=10000"
    headers = {
        "accept-encoding": "gzip, deflate, br, zstd",
        "cookie": "_gcl_au=1.1.1980076834.1743468053; hubspotutk=be576d9323cf740679ed81f2db0cf59c; i18n_redirected=en; _ga=GA1.3.1396778837.1743468053; _gid=GA1.2.1212662105.1743813037; __hssrc=1; _d0371=d329ecf100c400d2; _gid=GA1.3.1212662105.1743813037; ml-search-session=eyJ1c2VyIjp7InVzZXJJZCI6IlVTRVI2MjMxMzcxIiwidXNlcm5hbWUiOiJzZWFyY2hpbmc0Y3JpdHRlcnMiLCJmaXJzdE5hbWUiOiJldmVyZXR0IiwibGFzdE5hbWUiOiIhIiwiZnVsbE5hbWUiOiJldmVyZXR0ICEiLCJyb2xlcyI6W10sInByZWZzIjp7IlBST0ZJTEVfVklTSVRTX09QVF9JTiI6InRydWUiLCJQUklWQUNZX1BPTElDWV9BQ0NFUFRFRCI6InRydWUiLCJQUk9GSUxFX09QVF9JTiI6InRydWUiLCJTSE9XX1NVQlNQRUNJRVMiOiJmYWxzZSIsIkRJU1BMQVlfTkFNRV9QUkVGIjoibiIsIlZJU0lUU19PUFRfT1VUIjoiZmFsc2UiLCJESVNQTEFZX0NPTU1PTl9OQU1FIjoidHJ1ZSIsIkRJU1BMQVlfU0NJRU5USUZJQ19OQU1FIjoiZmFsc2UiLCJQUk9GSUxFX1JFR0lPTiI6IlVTIiwiU0hPV19DT01NRU5UUyI6ImZhbHNlIiwiUkVHSU9OX1BSRUYiOiJVUyIsIkNPTU1PTl9OQU1FX0xPQ0FMRSI6ImVuX1VTIiwiQUxFUlRTX09QVF9PVVQiOiJmYWxzZSIsIkVNQUlMX0NTIjoidHJ1ZSIsIlRPUDEwMF9PUFRfT1VUIjoiZmFsc2UiLCJTT1JUX1RBWE9OIjoidHJ1ZSIsInNwcFByZWYiOiJjb21tb24iLCJyZWdpb25QcmVmTmFtZSI6IlVuaXRlZCBTdGF0ZXMifX19; ml-search-session.sig=OsC4EsvQH1yll7jvDOhn2gfNXOU; _ga=GA1.1.1396778837.1743468053; __hstc=264660688.be576d9323cf740679ed81f2db0cf59c.1743468054054.1743813037712.1743817220890.3; __hssc=264660688.1.1743817220890; _ga_DTHTPXK4V9=GS1.1.1743817206.3.1.1743817390.0.0.0; _ga_YT7Y2S4MBX=GS1.1.1743817206.3.1.1743817390.0.0.0; _ga_QR4NVXZ8BM=GS1.1.1743817206.3.1.1743817390.58.0.0; _ga_CYH8S0R99B=GS1.1.1743817206.3.1.1743817390.58.0.0"
    }

    try:
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request)
        # compressing csv into a temp file
        with open("exported_data.csv.gz", "wb") as file:
            file.write(response.read())
        # decompressing
        with gzip.open("exported_data.csv.gz", "rb") as f_in:
            with open("exported_data.csv", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        df = pd.read_csv("exported_data.csv")
        columns_to_keep = ["ML Catalog Number", "Common Name", "Date", "Average Community Rating", "Number of Ratings"]
        filtered_df = df[columns_to_keep]
        filtered_df.to_csv(output_file, index=False)
        return filtered_df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def compare_and_notify(new_data_path, old_data_path, email_config):
    try:
        new_data = pd.read_csv(new_data_path)
        old_data = pd.read_csv(old_data_path)
        new_data["Number of Ratings"] = pd.to_numeric(new_data["Number of Ratings"], errors="coerce")
        old_data["Number of Ratings"] = pd.to_numeric(old_data["Number of Ratings"], errors="coerce")
        merged = pd.merge(new_data, old_data, on="ML Catalog Number", suffixes=("_new", "_old"))
        increased_ratings = merged[merged["Number of Ratings_new"] > merged["Number of Ratings_old"]]
        
        if not increased_ratings.empty:
            message = "<html><body>"
            for _, row in increased_ratings.iterrows():
                url = f"https://macaulaylibrary.org/asset/{row['ML Catalog Number']}"
                message += (
                    f"<li><a href='{url}'>{row['Common Name_new']}</a> observed on {row['Date_new']} "
                    f"has a new rating: now rated {row['Average Community Rating_new']} stars "
                    f"with {row['Number of Ratings_new']} rating(s).</li>"
                )
            message += "</ul></body></html>"
            send_email(email_config, "New eBird rating!", message, is_html=True)
            print("Email sent with updates.")
        else:
            print("No updates in ratings.")
    except Exception as e:
        print(f"An error occurred during comparison: {e}")

def send_email(email_config, subject, body, is_html=False):
    try:
        message = Mail(
            from_email=email_config["from_email"],
            to_emails=email_config["to_email"],
            subject=subject,
            html_content=body if is_html else None,
            plain_text_content=body if not is_html else None
        )
        sg = SendGridAPIClient(email_config["password"])  # Use API key as password
        response = sg.send(message)
        print(f"Email sent successfully: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")

def get_users():
    conn = psycopg2.connect(
        dbname=config["db_name"],
        user=config["db_user"],
        password=config["db_password"],
        host=config["db_host"]
    )
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, email FROM users;")
    users = cursor.fetchall()
    conn.close()
    return users

def import_csv_to_db(user_id, csv_path):
    conn = psycopg2.connect(
        dbname=config["db_name"],
        user=config["db_user"],
        password=config["db_password"],
        host=config["db_host"]
    )
    cursor = conn.cursor()
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO ratings (user_id, ml_catalog_number, common_name, date, average_rating, number_of_ratings)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, ml_catalog_number) DO NOTHING;
        """, (user_id, row["ML Catalog Number"], row["Common Name"], row["Date"], row["Average Community Rating"], row["Number of Ratings"]))
    conn.commit()
    conn.close()

def check_for_new_changes(user_id):
    conn = psycopg2.connect(
        dbname=config["db_name"],
        user=config["db_user"],
        password=config["db_password"],
        host=config["db_host"]
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ml_catalog_number, common_name, date, average_rating, number_of_ratings
        FROM ratings
        WHERE user_id = %s
        ORDER BY date DESC;
    """, (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    users = get_users()
    for user_id, email in users:
        email_config = {
            "from_email": "ebirdratingbot@gmail.com",
            "to_email": email,
            "smtp_server": "smtp.sendgrid.net",
            "smtp_port": 2525,
            "password": config["email_password"]
        }
        
        new_data_path = f"new_filtered_data_{user_id}.csv"
        fetch_and_filter_csv(user_id, output_file=new_data_path)
        import_csv_to_db(user_id, new_data_path)
        
        changes = check_for_new_changes(user_id)
        if changes:
            message = "<html><body><ul>"
            for change in changes:
                url = f"https://macaulaylibrary.org/asset/{change[0]}"
                message += f"<li><a href='{url}'>{change[1]}</a> observed on {change[2]} now rated {change[3]} stars with {change[4]} ratings.</li>"
            message += "</ul></body></html>"
            send_email(email_config, "New eBird rating updates!", message, is_html=True)
        else:
            print(f"No updates for user {user_id}.")