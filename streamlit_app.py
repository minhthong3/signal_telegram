import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import pandas as pd
from datetime import datetime
import time
import json

# Cấu hình Google Sheets
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1kkOjUihnNpcWn8jmNM7majctXlqU18fGvwlTOVi9efg/edit#gid=0"
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
GCP_SERVICE_ACCOUNT_FILE = st.secrets["GCP_SERVICE_ACCOUNT_FILE"]  # JSON từ secrets


# Hàm để lấy dữ liệu từ Google Sheets
@st.experimental_singleton
def get_google_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GCP_SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    return client

# Hàm gửi tin nhắn Telegram
def send_telegram_message(bot_token, chat_id, message):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, params=params)
    return response

# Hàm kiểm tra tín hiệu và gửi tin nhắn
def notify_signals(df, sent_signals, bot_token, chat_id):
    new_sent_signals = sent_signals.copy()  # Tạo bản sao của từ điển tín hiệu đã gửi
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
                send_telegram_message(bot_token, chat_id, message)

                # Cập nhật trạng thái tín hiệu đã gửi
                new_sent_signals[stock_code] = signal
    return new_sent_signals

# Token và chat_id của Telegram bot
TELEGRAM_TOKEN = TELEGRAM_TOKEN
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID

# Từ điển lưu trữ trạng thái tín hiệu đã gửi của các mã cổ phiếu
if 'sent_signals' not in st.session_state:
    st.session_state['sent_signals'] = {}

st.title("Stock Trading Signals")

# Tải dữ liệu từ Google Sheets
client = get_google_sheet_client()
sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1

def main():
    while True:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Kiểm tra tín hiệu và gửi thông báo
        st.session_state['sent_signals'] = notify_signals(df, st.session_state['sent_signals'], TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

        st.dataframe(df)

        # Dừng 10 giây trước khi kiểm tra lại
        time.sleep(10)

if __name__ == "__main__":
    main()
