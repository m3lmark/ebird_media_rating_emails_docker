import os
import json
import urllib.request
import pandas as pd
import gzip
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def load_config(config_path="config.json"):
    with open(config_path, "r") as file:
        return json.load(file)

def fetch_and_filter_csv(user_id, cookie, output_file="new_filtered_data.csv"):
    url = f"https://search.macaulaylibrary.org/api/v2/export.csv?userId={user_id}&count=10000"
    headers = {
        "accept-encoding": "gzip, deflate, br, zstd",
        "cookie": cookie
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
        msg = MIMEMultipart()
        msg["From"] = email_config["from_email"]
        msg["To"] = email_config["to_email"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html" if is_html else "plain"))
        with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
            server.starttls()
            server.login(email_config["from_email"], email_config["password"])
            server.send_message(msg)
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")

if __name__ == "__main__":
    config = load_config("config.json")
    user_id = config["user_id"]
    cookie = config["cookie"]
    email_config = {
        "from_email": config["from_email"],
        "to_email": config["to_email"],
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "password": config["email_password"]
    }
    
    data_dir = "data"  # directory for storing data files
    os.makedirs(data_dir, exist_ok=True)  # ensure the directory exists

    new_data_path = os.path.join(data_dir, "new_filtered_data.csv")
    old_data_path = os.path.join(data_dir, "filtered_data.csv")
    
    if not os.path.exists(old_data_path):
        print(f"No old data found at {old_data_path}. Fetching initial dataset.")
        fetch_and_filter_csv(user_id, cookie, output_file=old_data_path)
    else:
        fetch_and_filter_csv(user_id, cookie, output_file=new_data_path)
        compare_and_notify(new_data_path, old_data_path, email_config)
        shutil.move(new_data_path, old_data_path)