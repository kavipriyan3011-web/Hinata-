import io
import json
import os
import re
import sys
import tempfile
import threading
import time
import pygame
from google import genai
from google.genai import types
from gtts import gTTS

# Initialize Pygame Audio Engine
pygame.init()
pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Hinata Hyuga AI")

# Enable Touch Screen Text Input on Android
pygame.key.start_text_input()

# UI Colors & Fonts
font_small = pygame.font.SysFont(None, 22)
font_main = pygame.font.SysFont(None, 24)

C_BG = (15, 15, 20)
C_TEXT = (255, 255, 255)
C_USER = (0, 220, 255)
C_AI = (186, 85, 211)
C_SYS = (255, 200, 50)
C_BTN = (147, 112, 219)
C_WHITE = (255, 255, 255)

CONFIG_FILE = "config.json"
PROFILE_FILE = "ai_profile.json"
HISTORY_FILE = "chat_history.json"

# File & Key Loading Strategy
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            API_KEY = data.get("api_key")
    except Exception:
        pass

client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"Client init error: {e}")

profile = {"user_name": "Naruto", "ai_name": "Hinata"}
if os.path.exists(PROFILE_FILE):
    try:
        with open(PROFILE_FILE, "r") as f:
            profile = json.load(f)
            profile["user_name"] = "Naruto"
    except Exception:
        pass

chat_messages = []
input_text = ""
is_loading = False
awaiting_api_key = False if API_KEY else True

INPUT_BOX = pygame.Rect(10, SCREEN_HEIGHT - 60, 350, 45)
SEND_BTN = pygame.Rect(370, SCREEN_HEIGHT - 60, 100, 45)


def load_chat_history():
    gemini_history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                saved_data = json.load(f)
                for item in saved_data:
                    color = C_USER if item["role"] == "user" else C_AI
                    sender = profile["user_name"] if item["role"] == "user" else profile["ai_name"]
                    add_message_ui(sender, item["text"], color)
                    gemini_history.append(
                        types.Content(
                            role=item["role"],
                            parts=[types.Part.from_text(text=item["text"])],
                        )
                    )
        except Exception as e:
            print(f"Error loading history: {e}")
    return gemini_history


def save_message_to_history(role, text):
    history_data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history_data = json.load(f)
        except Exception:
            history_data = []

    history_data.append({"role": role, "text": text})

    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_data, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")


def add_message_ui(sender, text, color):
    words = text.split(" ")
    line = f"{sender}: " if sender else ""

    for word in words:
        test_line = line + word + " "
        if font_small.size(test_line)[0] < SCREEN_WIDTH - 30:
            line = test_line
        else:
            chat_messages.append({"text": line, "color": color})
            line = "  " + word + " "
    chat_messages.append({"text": line, "color": color})

    while len(chat_messages) > 20:
        chat_messages.pop(0)


def speak_text_bg(text):
    """Soft female voice playback for Hinata."""
    def _tts():
        try:
            clean_text = re.sub(r'[*_`#]', '', text).strip()
            if not clean_text:
                return

            temp_path = os.path.join(tempfile.gettempdir(), "hinata_speech.mp3")
            tts = gTTS(text=clean_text, lang='en', tld='com.au', slow=False)
            tts.save(temp_path)

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"TTS Audio Error: {e}")

    threading.Thread(target=_tts, daemon=True).start()


SYSTEM_INSTRUCTION = (
    "You are Hinata Hyuga from Naruto talking directly to Naruto. "
    "You speak softly, politely, and gently, but get easily flustered. "
    "You MUST ALWAYS address the user simply as 'Naruto' (NEVER use 'kun' or 'Naruto-kun'). "
    "Use Hinata's humor: stuttering nervously when flustered (e.g., 'N-Naruto...'), "
    "poking index fingers together, or offering to go eat Ichiraku Ramen together. "
    "Keep responses short (1 to 2 sentences max)."
)

initial_history = load_chat_history()
chat = None

if client:
    chat = client.chats.create(
        model="gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        history=initial_history,
    )


def save_and_init_key(key):
    global API_KEY, client, chat, awaiting_api_key
    key = key.strip()
    if not key:
        return

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_key": key}, f)

        API_KEY = key
        client = genai.Client(api_key=API_KEY)
        chat = client.chats.create(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            history=initial_history,
        )
        awaiting_api_key = False
        add_message_ui("System", "API Key saved successfully!", C_SYS)
        add_message_ui("Hinata", "N-Naruto! Um... Hinata is ready to chat!", C_AI)
    except Exception as e:
        add_message_ui("System Error", f"Invalid API Key or connection failed.", C_SYS)


def send_message():
    global input_text, is_loading, awaiting_api_key
    if not input_text.strip() or is_loading:
        return

    user_msg = input_text.strip()
    input_text = ""

    if awaiting_api_key:
        save_and_init_key(user_msg)
        return

    add_message_ui(profile["user_name"], user_msg, C_USER)
    save_message_to_history("user", user_msg)
    is_loading = True

    def _async_send():
        global is_loading
        max_retries = 3
        response = None

        for attempt in range(max_retries):
            try:
                response = chat.send_message(user_msg)
                break
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
                else:
                    add_message_ui("System Error", "Server busy or invalid key. Tap SEND again!", C_SYS)
                    is_loading = False
                    return

        if response and response.text:
            add_message_ui("Hinata", response.text, C_AI)
            save_message_to_history("model", response.text)
            speak_text_bg(response.text)

        is_loading = False

    threading.Thread(target=_async_send, daemon=True).start()


def main():
    global input_text, is_loading
    if awaiting_api_key:
        add_message_ui("System", "Welcome! Please enter your Gemini API Key below:", C_SYS)
    elif not initial_history:
        add_message_ui("System", f"Logged in as {profile['user_name']}", C_SYS)
        add_message_ui("Hinata", "N-Naruto! Um... Hinata is so happy to talk with you today!", C_AI)

    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(30)
        screen.fill(C_BG)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.TEXTINPUT:
                input_text += event.text

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    send_message()
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if INPUT_BOX.collidepoint(event.pos):
                    pygame.key.start_text_input()
                elif SEND_BTN.collidepoint(event.pos):
                    send_message()

        # Render Chat
        y_offset = 20
        for msg in chat_messages:
            txt_surf = font_small.render(msg["text"], True, msg["color"])
            screen.blit(txt_surf, (15, y_offset))
            y_offset += 25

        # Input Box
        pygame.draw.rect(screen, (30, 30, 45), INPUT_BOX, border_radius=6)
        pygame.draw.rect(screen, C_AI, INPUT_BOX, width=2, border_radius=6)

        placeholder = "Paste API Key here..." if awaiting_api_key else "Tap to type..."
        display_txt = input_text if input_text else placeholder
        txt_color = C_TEXT if input_text else (120, 120, 120)
        inp_surf = font_main.render(display_txt[-24:], True, txt_color)
        screen.blit(inp_surf, (INPUT_BOX.x + 10, INPUT_BOX.y + 12))

        # Send Button
        btn_color = (100, 100, 100) if is_loading else C_BTN
        pygame.draw.rect(screen, btn_color, SEND_BTN, border_radius=6)
        btn_label = "WAIT..." if is_loading else ("SAVE" if awaiting_api_key else "SEND")
        btn_txt = font_main.render(btn_label, True, C_WHITE)
        screen.blit(
            btn_txt, (SEND_BTN.x + (100 - btn_txt.get_width()) // 2, SEND_BTN.y + 12)
        )

        pygame.display.flip()

    pygame.key.stop_text_input()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()