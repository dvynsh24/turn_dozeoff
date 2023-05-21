import os
import streamlit as st
import av
import threading
from streamlit_webrtc import (
    VideoHTMLAttributes,
    webrtc_streamer,
    WebRtcMode,
)
from audio_handle import AudioFrameHandler
from video_handle import VideoFrameHandler
from dotenv import load_dotenv
from twilio.rest import Client


# Load the .env file
load_dotenv()

alarm_file_path = os.path.join("assets", "audio_files", "wake_up.wav")

st.set_page_config(
    page_title="Dozing Off While Driving - Demo",
    page_icon="💤",
    # layout="wide",
)

st.title("Detecting Dozing Off")

# with st.container():
#     c1, c2 = st.columns(spec=[1, 1])
#     with c1:
#         WAIT_TIME = st.slider(
#             "**Seconds to wait before sounding alarm:**", 0.0, 5.0, 1.0, 0.25
#         )
#         st.write(f"Current value is **{WAIT_TIME}** seconds")

#     with c2:
#         EAR_THRESH = st.slider(
#             "**Eye Aspect Ratio threshold:**", 0.0, 0.4, 0.18, 0.01)

#         st.write(f" Current value, EAR = **{EAR_THRESH}**")

WAIT_TIME = 1
EAR_THRESH = 0.18

thresholds = {
    "EAR_THRESH": EAR_THRESH,
    "WAIT_TIME": WAIT_TIME,
}

video_handler = VideoFrameHandler()
audio_handler = AudioFrameHandler(sound_file_path=alarm_file_path)

lock = (
    threading.Lock()
)  # For thread-safe access & to prevent race-condition.
shared_state = {"play_alarm": False}


def video_frame_callback(frame: av.VideoFrame):
    frame = frame.to_ndarray(format="bgr24")

    frame, play_alarm = video_handler.process(frame, thresholds)
    with lock:
        shared_state["play_alarm"] = play_alarm

    return av.VideoFrame.from_ndarray(frame, format="bgr24")


def audio_frame_callback(frame: av.AudioFrame):
    with lock:
        play_alarm = shared_state["play_alarm"]

    new_frame: av.AudioFrame = audio_handler.process(
        frame, play_sound=play_alarm
    )
    return new_frame


def get_ice_servers():
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    token = client.tokens.create()

    return token.ice_servers


ctx = webrtc_streamer(
    key="drowsiness-detection",
    mode=WebRtcMode.SENDRECV,
    video_frame_callback=video_frame_callback,
    audio_frame_callback=audio_frame_callback,
    rtc_configuration={"iceServers": get_ice_servers()},
    media_stream_constraints={
        "video": {"height": {"ideal": 480}},
        "audio": True,
    },
    video_html_attrs=VideoHTMLAttributes(
        autoPlay=True, controls=False, muted=False
    ),
    async_processing=True
)


# webrtc_streamer(key="key", video_processor_factory=VideoProcessor,
# 				rtc_configuration=RTCConfiguration(
# 					{"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
# 					)
# 	)
