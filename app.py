import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import pandas as pd
from datetime import datetime
import time
import json
import os

# Lấy thông tin từ Hugging Face Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_URL = os.getenv("SHEET_URL")

# Lưu tạm thời tệp JSON credentials
with open("credentials.json", "w") as file:
    file.write(GOOGLE_SHEETS_CREDENTIALS)

# Thiết lập API Google Sheets
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Mở Google Sheets và lấy dữ liệu
sheet = client.open_by_url(SHEET_URL).sheet1

# Từ điển lưu trữ trạng thái tín hiệu đã gửi của các mã cổ phiếu
sent_signals = {}

# Hàm gửi tin nhắn Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(url, params=params)
    return response

# Hàm kiểm tra tín hiệu và gửi tin nhắn
def notify_signals(df):
    global sent_signals
    for index, row in df.iterrows():
        stock_code = row['Mã']
        signal = row['Tín hiệu']

        # Kiểm tra xem ô Tín hiệu có giá trị hay không
        if pd.notnull(signal) and signal.strip() != "":
            # Điều kiện để gửi tin nhắn
            send_message = False

            # Điều kiện 1: Kiểm tra xem mã cổ phiếu đã có trong sent_signals hay chưa
            if stock_code not in sent_signals:
                send_message = True
            else:
                # Nếu đã có trong sent_signals, lấy tín hiệu cuối cùng đã gửi
                last_signal = sent_signals[stock_code]

                # Điều kiện 2: Kiểm tra các tín hiệu cụ thể để gửi tin nhắn
                if signal != last_signal:
                    if signal == 'MUA TIÊU CHUẨN' and last_signal in ['BÁN HẾT', 'BÁN 50%']:
                        send_message = True
                    elif signal == 'BÁN HẾT' and last_signal not in ['MUA TIÊU CHUẨN', 'MUA BÙNG NỔ', 'MUA BẮT ĐÁY']:
                        send_message = True
                    elif signal == 'BÁN 50%' and last_signal not in ['MUA TIÊU CHUẨN', 'MUA BÙNG NỔ', 'BÁN HẾT', 'MUA BẮT ĐÁY']:
                        send_message = True
                    elif signal == 'MUA BÙNG NỔ' and last_signal in ['MUA TIÊU CHUẨN', 'BÁN HẾT', 'BÁN 50%']:
                        send_message = True
                    elif signal == 'MUA BẮT ĐÁY' and last_signal in ['BÁN HẾT', 'BÁN 50%']:
                        send_message = True

            if send_message:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if signal == 'MUA TIÊU CHUẨN' or signal == 'MUA BÙNG NỔ':
                    adjusted_price = row['Giá hiện tại'] * 1.01
                    action_message = f"Giá mua an toàn khi < {adjusted_price:.2f}"
                else:
                    action_message = ""

                message = f"Mã: {stock_code}\nTín hiệu: {signal}\n{action_message}\nGiá tại thông báo: {row['Giá hiện tại']}\nThời gian thông báo: {current_time}\nVNWEALTH - FLASHDEAL"
                send_telegram_message(message)

                # Cập nhật trạng thái tín hiệu đã gửi
                sent_signals[stock_code] = signal

# Streamlit UI
st.title('Stock Signal Notification System')

st.write("Fetching data from Google Sheets and monitoring stock signals...")

# Lấy dữ liệu mới nhất từ Google Sheets
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Hiển thị dữ liệu trên Streamlit
st.dataframe(df)

# Gửi thông báo khi có tín hiệu mua/bán
notify_signals(df)

st.write("Monitoring for new signals. The page will refresh every 10 seconds.")
st.experimental_rerun(timeout=10)
