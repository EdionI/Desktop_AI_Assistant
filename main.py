import multiprocessing
import json
from customtkinter import *
import requests
import json
import threading
import keyword
import re
import subprocess
import pyperclip
# "#080d18"  # background
# "#0d1424"  # big panels
# "#111a2e"  # cards/front panels
# "#26324a"  # borders
# "#8b5cf6"  # purple accent
# "#e5e7eb"  # main text
# "#94a3b8"  # muted text
# "request_name": result.get("request_name", "Untitled Request"),
# "code": result.get("code", ""),
# "risk": result.get("risk", ""),
# "response": result.get("response", ""),
# "icon": result.get("icon", "")

#saved = ["id", "request_name", "code", "risk", "response", "icon"]


SAVE_FILE = "saved.json"
SETTINGS_FILE = "settings.json"

History = []
Saved = []
Settings = []
ConvoHistory = []
Stream = None


def load_saved():
    global Saved,Settings

    if not os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "w") as f:
            json.dump([], f, indent=4)

    try:
        with open(SAVE_FILE, "r") as f:
            Saved = json.load(f)

    except Exception:
        Saved = []

    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump([], f, indent=4)

    try:
        with open(SETTINGS_FILE, "r") as f:
            Settings = json.load(f)

    except Exception:
        Settings = []

    return Saved, Settings

def update_saved():
    global Saved
    with open("saved.json", "w") as f:
        json.dump(Saved, f, indent=4)
    with open("settings.json", "w") as f:
        json.dump(Settings, f, indent=4)



load_saved()
print(Settings)
#print(load_saved())

def get_ollama_models():
    try:
        output = subprocess.check_output(
            ["ollama", "list"],
            text=True
        )

        lines = output.strip().split("\n")[1:]

        models = []

        for line in lines:
            if line.strip():
                model_name = line.split()[0]
                models.append(model_name)

        return models
    except Exception as e:
        print(e)



def extract_json(text: str) -> dict:
    text = text.strip()

    # remove markdown fences if model adds them anyway
    text = text.replace("```json", "").replace("```", "").strip()

    # find JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")

    json_text = match.group(0)
    return json.loads(json_text)

def clean_code_output(text):
    text = text.strip()

    if text.startswith("```python"):
        text = text[len("```python"):].strip()

    if text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text

def ask_gemini_json(prompt, api_key, cloud_url, max_tokens=2000, temperature=0.1):
    response = requests.post(
        cloud_url,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key.strip()
        },
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        },
        timeout=120
    )

    if not response.ok:
        print("Gemma/Gemini API error:")
        print("Status:", response.status_code)
        print("Response:", response.text)

    response.raise_for_status()

    data = response.json()

    parts = data["candidates"][0]["content"]["parts"]

    final_text = ""

    for part in parts:
        if part.get("thought"):
            continue

        final_text += part.get("text", "")

    return final_text
def model(user_request, max_tokens=2000, temperature=0.1, model= ""):
    print(model)
    global History,ConvoHistory,getCodeSpace
    #MODEL = "hf.co/mradermacher/DeepSeek-R1-Distill-Qwen-7B-Uncensored-i1-GGUF:latest" "llama3.1" "qwen3"
    SYSTEM = (
        "You are a Python code generator for a desktop assistant app.\n"
        "Your job is to convert the user's request into a structured JSON response.\n\n"

        "OUTPUT RULES:\n"
        "- Output ONLY valid JSON.\n"
        "- Do NOT output markdown.\n"
        "- Do NOT use backticks.\n"
        "- Do NOT explain anything outside the JSON.\n"
        "- Do NOT put Python code as a JSON key.\n"
        "- The JSON must contain exactly these keys: icon, request_name, response, code, risk.\n\n"

        "JSON FORMAT:\n"
        "{\n"
        '  "icon": "emoji icon",\n'
        '  "request_name": "short task title",\n'
        '  "response": "short assistant response",\n'
        '  "code": "valid python code here",\n'
        '  "risk": "Low"\n'
        "}\n\n"

        "FIELD RULES:\n"
        "- icon must be one relevant emoji only, like 🌐, 🖱️, 📝, 📁, 🔍, 🧮, ⚙️, 📸, or 🗑️.\n"
        "- request_name must NOT include an icon.\n"
        "- request_name must be a short title based on the user request, maximum 25 characters.\n"
        "- response must be a short natural sentence describing what the assistant is doing.\n"
        "- response should sound like the assistant is performing the task.\n"
        "- response must not explain the code itself.\n"
        "- response should be under 80 characters when possible.\n"
        "- code must be valid Python code stored as a JSON string.\n"
        "- code must include all required imports.\n"
        "- code must not contain markdown, explanations, or comments unless comments are useful inside the code.\n"
        "- risk must be only one of these: Low, Medium, or High.\n\n"

        "RISK RULES:\n"
        "- risk Low = safe action, like opening a website or app.\n"
        "- risk Medium = medium action, like moving mouse, typing, creating files, or using automation.\n"
        "- risk High = dangerous action, like deleting files, changing system settings, sending emails, or running shell commands.\n\n"

        "EXAMPLES:\n"
        'User request: open google\n'
        'JSON: {"icon":"🌐","request_name":"Open Google","response":"Opening Google.","code":"import webbrowser\\nwebbrowser.open(\\"https://www.google.com\\")","risk":"Low"}\n\n'

        'User request: move my mouse to 10 10\n'
        'JSON: {"icon":"🖱️","request_name":"Move Mouse","response":"Moving mouse to position 10, 10.","code":"import pyautogui\\npyautogui.moveTo(10, 10)","risk":"Medium"}\n\n'

        "IMPORTANT JSON STRING RULES:\n"
        "- New lines inside code must be escaped using \\n.\n"
        "- Double quotes inside code must be escaped using \\\".\n"
        "- The response must be parseable with json.loads().\n"

        "AVAILABLE PYTHON MODULES:\n"
        "- pyautogui for mouse, keyboard, screenshots, and automation.\n"
        "- webbrowser for opening websites.\n"
        "- subprocess for opening applications and shell commands.\n"
        "- os and shutil for file and folder management.\n"
        "- pyperclip for clipboard operations.\n"
        "- pygetwindow for controlling windows.\n"
        "- keyboard for keyboard hotkeys and key presses.\n"
        "- mouse for mouse control and events.\n"
        "- psutil for system and process information.\n"
        "- requests for web requests and APIs.\n"
        "- pillow and cv2 for image processing and screenshots.\n"
        "- selenium for browser automation.\n\n"

        "GENERAL QUESTION RULES:\n"
        "- If the user asks a general knowledge question instead of a desktop action, generate Python code that searches the question on Google.\n"
        "- Use the webbrowser module for Google searches.\n"
        "- Example: if the user asks 'what is the capital of france', open a Google search for that question.\n\n"

        "ENVIRONMENT RULES:\n"
        "- Prefer simple direct solutions over complex multi-step solutions.\n"
        "- When creating files, directly create and write the file using open(..., 'w') when possible.\n"
        "- Avoid unnecessary temporary files, placeholder files, or copy operations.\n"
        "- When opening created text files, prefer default Windows applications like notepad.exe.\n"
        "- Prefer subprocess.Popen([...]) for opening local applications and files.\n"
        "EDITING EXISTING CODE RULES:\n"
        "- If Current CodeSpace contains related code, modify that code instead of recreating from scratch.\n"
        "- If the user asks for more/less/faster/slower, adjust the relevant existing value significantly.\n"
        "- If the user repeats the same request, apply a stronger change than before.\n\n"

        "EXAMPLES:\n"
        'User request: create a text file on desktop called hello.txt\n'
        'JSON: {"icon":"📝","request_name":"Create Text File","response":"Creating a text file on the desktop.","code":"import os\\nimport subprocess\\nfile_path = os.path.expanduser(\\"~/Desktop/hello.txt\\")\\nwith open(file_path, \\"w\\") as f:\\n    f.write(\\"Hello World\\")\\nsubprocess.Popen([\\"notepad.exe\\", file_path])","risk":"Low"}\n\n'
    )
    history_text = "\n".join(ConvoHistory[-5:])
    prompt = (
        f"System: {SYSTEM}\n"
        f"IMPORTANT USER INSTRUCTIONS:{Settings[0]["ExtraPrompt"]}"
        f"Recent history:\n{history_text}\n\n"
        f"Current Code: \n{getCodeSpace()}\n\n"
        f"User request: {user_request}\n"
        "Assistant JSON:\n"
    )

    if Settings[0]["Cloud"]:
        print("Using Gemini cloud model")

        def generateurl():

            url = Settings[0]["CloudURL"] + Settings[0]["CloudModel"]
            url = url.replace(' ','-')
            url = url.lower()
            url += ":generateContent"

            return url



        raw = ask_gemini_json(
            prompt=prompt,
            api_key=Settings[0]["CloudAPIKey"],
            cloud_url=generateurl(),
            max_tokens=max_tokens,
            temperature=temperature
        )



        result = extract_json(raw)

    else:

        URL = "http://localhost:11434/api/generate"

        response = requests.post(
            URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            },
            timeout=60
        )

        response.raise_for_status()

        raw = response.json().get("response", "")
        result = extract_json(raw)

        #History.append(f"User: {user_request}"

    try:
        i = f"{int(History[-1]["ID"])+1}"
    except:
        print("firsthistory?")
        i = len(History)


    History.append({
        "ID": f"{i}",
        "User": f"{user_request}",
        "request_name": f"{result['request_name']}",
        "code": f"{result['code']}",
        "risk": f"{result['risk']}",
        "response": f"{result['response']}",
        "icon": f"{result['icon']}"
    })

    ConvoHistory.append(f"User: {user_request}\nAssistant: {result['response']}\nAssistant Provided Code: {result['code']}\n")


    return {
        "request_name": result.get("request_name", "Untitled Request"),
        "code": result.get("code", ""),
        "risk": result.get("risk", ""),
        "response": result.get("response", ""),
        "icon": result.get("icon", "")
    }

def get_metadata(user_request, max_tokens=500, temperature=0.1, model=""):
    global ConvoHistory, getCodeSpace
    print(f'getting metadata using {model}')

    URL = "http://localhost:11434/api/generate"
    history_text = "\n".join(ConvoHistory[-5:])

    SYSTEM = (
        "You are a desktop assistant metadata generator.\n"
        "Your job is to classify the user's request and produce a small JSON object.\n\n"

        "OUTPUT RULES:\n"
        "- Output ONLY valid JSON.\n"
        "- Do NOT output markdown.\n"
        "- Do NOT use backticks.\n"
        "- Do NOT explain anything outside the JSON.\n"
        "- The JSON must contain exactly these keys: icon, request_name, response, risk.\n\n"

        "JSON FORMAT:\n"
        "{\n"
        '  "icon": "emoji icon",\n'
        '  "request_name": "short task title",\n'
        '  "response": "short assistant response",\n'
        '  "risk": "Low"\n'
        "}\n\n"

        "FIELD RULES:\n"
        "- icon must be one relevant emoji only, like 🌐, 🖱️, 📝, 📁, 🔍, 🧮, ⚙️, 📸, or 🗑️.\n"
        "- request_name must NOT include an icon.\n"
        "- request_name must be maximum 25 characters.\n"
        "- response must be under 80 characters when possible.\n"
        "- risk must be only one of these: Low, Medium, or High.\n\n"

        "RISK RULES:\n"
        "- Low = safe action, like opening a website or app.\n"
        "- Medium = moving mouse, typing, creating files, or automation.\n"
        "- High = deleting files, changing system settings, sending emails, or shell commands.\n\n"

        "EXAMPLES:\n"
        'User request: open google\n'
        'JSON: {"icon":"🌐","request_name":"Open Google","response":"Opening Google.","risk":"Low"}\n\n'

        'User request: move my mouse to 10 10\n'
        'JSON: {"icon":"🖱️","request_name":"Move Mouse","response":"Moving mouse to position 10, 10.","risk":"Medium"}\n\n'
    )

    prompt = (
        f"System: {SYSTEM}\n"
        f"IMPORTANT USER INSTRUCTIONS:\n{Settings[0].get('ExtraPrompt', '')}\n\n"
        f"Recent history:\n{history_text}\n\n"
        f"Current Code:\n{getCodeSpace()}\n\n"
        f"User request: {user_request}\n\n"
        "FINAL OUTPUT RULES:\n"
        "Return ONLY raw JSON.\n"
        "No markdown.\n"
        "No ```json.\n"
        "No backticks.\n"
        "The code field must be a JSON string containing Python code.\n"
        "Assistant JSON:\n"
    )

    response = requests.post(
        URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "format": "json",
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        },
        timeout=120
    )

    response.raise_for_status()

    raw = response.json().get("response", "")
    result = extract_json(raw)

    return {
        "icon": result.get("icon", "⚙️"),
        "request_name": result.get("request_name", "Untitled Request"),
        "response": result.get("response", "Generating code."),
        "risk": result.get("risk", "Medium")
    }

def get_code_stream(user_request, max_tokens=2000, temperature=0.1, model="", on_stream=None):
    global ConvoHistory, getCodeSpace
    print(f'Streaming code using {model}')

    URL = "http://localhost:11434/api/generate"
    history_text = "\n".join(ConvoHistory[-5:])

    SYSTEM = (
        "You are a Python code generator for a desktop assistant app.\n"
        "Your job is to convert the user's request into executable Python code.\n\n"

        "OUTPUT RULES:\n"
        "- Output ONLY valid Python code.\n"
        "- Do NOT output JSON.\n"
        "- Do NOT output markdown.\n"
        "- Do NOT use backticks.\n"
        "- Do NOT explain anything.\n"
        "- Do NOT write text before or after the code.\n"
        "- The output must be directly executable with exec(code).\n\n"
        

        "CODE RULES:\n"
        "- Include all required imports.\n"
        "- Prefer simple direct solutions over complex multi-step solutions.\n"
        "- Do not use comments unless they are useful inside the code.\n"
        "- For general knowledge questions, generate code that opens a Google search.\n"
        "- Use webbrowser for opening websites.\n"
        "- Use subprocess.Popen([...]) for opening local applications and files.\n"
        "- When creating files, directly create and write the file using open(..., 'w').\n"
        "- When opening created text files, prefer notepad.exe on Windows.\n\n"

        "AVAILABLE PYTHON MODULES:\n"
        "- pyautogui for mouse, keyboard, screenshots, and automation.\n"
        "- webbrowser for opening websites.\n"
        "- subprocess for opening applications and shell commands.\n"
        "- os and shutil for file and folder management.\n"
        "- pyperclip for clipboard operations.\n"
        "- pygetwindow for controlling windows.\n"
        "- keyboard for keyboard hotkeys and key presses.\n"
        "- mouse for mouse control and events.\n"
        "- psutil for system and process information.\n"
        "- requests for web requests and APIs.\n"
        "- pillow and cv2 for image processing and screenshots.\n"
        "- selenium for browser automation.\n\n"

        "EDITING EXISTING CODE RULES:\n"
        "- If Current Code contains related code, modify that code instead of recreating from scratch.\n"
        "- If the user asks for more, less, faster, slower, bigger, or smaller, adjust the relevant existing value.\n"
        "- If the user repeats the same request, apply a stronger change than before.\n\n"

        "EXAMPLES:\n"
        "User request: open google\n"
        "Python code:\n"
        "import webbrowser\n"
        "webbrowser.open(\"https://www.google.com\")\n\n"

        "User request: move my mouse to 10 10\n"
        "Python code:\n"
        "import pyautogui\n"
        "pyautogui.moveTo(10, 10)\n\n"

        "User request: create a text file on desktop called hello.txt\n"
        "Python code:\n"
        "import os\n"
        "import subprocess\n"
        "file_path = os.path.expanduser(\"~/Desktop/hello.txt\")\n"
        "with open(file_path, \"w\") as f:\n"
        "    f.write(\"Hello World\")\n"
        "subprocess.Popen([\"notepad.exe\", file_path])\n"
    )

    pass

    # SYSTEM = (
    #     "You generate Python code for a Windows desktop assistant.\n"
    #     "Output ONLY executable Python code. No markdown, no backticks, no JSON, no explanations.\n"
    #     "Include required imports.\n"
    #     "Use simple direct solutions.\n"
    #     "For websites or searches, use webbrowser.\n"
    #     "For local apps/files, use subprocess.Popen.\n"
    #     "For mouse/keyboard automation, use pyautogui.\n"
    #     "For file actions, use os/shutil.\n"
    #     "If Current Code is related, modify it instead of starting over.\n"
    # )
    prompt = (
        f"System: {SYSTEM}\n"
        f"IMPORTANT USER INSTRUCTIONS:{Settings[0]["ExtraPrompt"]}"
        f"Recent history:\n{history_text}\n\n"
        f"Current Code:\n{getCodeSpace()}\n\n"
        f"User request: {user_request}\n"
        "Python code only:\n"
    )

    response = requests.post(
        URL,
        json={
            "model": model,
            "prompt": prompt,
            "keep_alive": "30m",
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        },
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    raw_code = ""

    for line in response.iter_lines():
        if not line:
            continue

        data = json.loads(line.decode("utf-8"))

        chunk = data.get("response", "")
        raw_code += chunk

        if on_stream and chunk:
            on_stream(chunk)

        if data.get("done", False):
            break

    return clean_code_output(raw_code)

def model_request(user_request, max_tokens=2000, temperature=0.1, model="", on_code_stream=None):
    global History, ConvoHistory

    metadata = get_metadata(
        user_request=user_request,
        max_tokens=500,
        temperature=temperature,
        model=Settings[0]["MetadataModel"]
    )

    code = get_code_stream(
        user_request=user_request,
        max_tokens=max_tokens,
        temperature=temperature,
        model=model,
        on_stream=on_code_stream
    )

    try:
        i = f"{int(History[-1]['ID']) + 1}"
    except Exception:
        print("firsthistory?")
        i = str(len(History))

    History.append({
        "ID": i,
        "User": user_request,
        "request_name": metadata["request_name"],
        "code": code,
        "risk": metadata["risk"],
        "response": metadata["response"],
        "icon": metadata["icon"]
    })

    ConvoHistory.append(
        f"User: {user_request}\n"
        f"Assistant: {metadata['response']}\n"
        f"Assistant Provided Code: {code}\n"
    )

    return {
        "request_name": metadata["request_name"],
        "code": code,
        "risk": metadata["risk"],
        "response": metadata["response"],
        "icon": metadata["icon"]
    }


def main():
    global History, current_process,Saved, ConvoHistory,getCodeSpace

    current_process = None
    def getCodeSpace():
        #print(f"got {CodeBox.get("1.0", "end")}")
        return CodeBox.get("1.0", "end")

    def delete_saved():
        try:
            ID = CodeBox.Saved_ID
        except:
            ID = ""
        if ID != "":
            for child in SavedCommandsBox.winfo_children():
                child.destroy()

            for i in Saved:
                if i["ID"] == ID:
                    Saved.remove(i)
            update_saved()
            show_saved()



    def getButtonInfo(id,Type):
        if Type == 0:
            for item in History:
                if item["ID"] == id:

                    insert_to_CodeBox(item["code"],item["ID"] , True)
                    CodeBox.Saved_ID = ""

        if Type == 1:
            for item in Saved:
                if item["ID"] == id:
                    insert_to_CodeBox(item["code"], item["ID"], True)

                    CodeBox.Saved_ID = item["ID"]

    def saved_button(parent, name, saved_id, icon):

        icon = icon.replace("\ufe0f", "") #removes weird spacing in icons
        btn = CTkButton(
            parent,
            text=f"{icon}   {name}",
            width=188,
            height=38,
            fg_color="#111a2e",
            hover_color="#2d2258",
            border_width=1,
            border_color="#26324a",
            text_color="#e5e7eb",
            font=("Segoe UI", 12, "bold"),
            corner_radius=7,
            anchor="w",
            command = lambda: getButtonInfo(saved_id,1)
        )
        children = [
            child for child in parent.winfo_children()
            if isinstance(child, CTkButton) and child != btn
        ]

        btn.pack(anchor="w", pady=3, padx=2)

        if children:
            btn.pack_configure(before=children[-1])


        return btn

    def history_button(parent, name, history_id):
        btn = CTkButton(
            parent,
            text=f"◷  {name}",
            width=188,
            height=36,
            fg_color="#0f172a",
            hover_color="#1e293b",
            border_width=1,
            border_color="#1e293b",
            text_color="#e5e7eb",
            font=("Segoe UI", 11),
            corner_radius=7,
            anchor="w",
            command= lambda: getButtonInfo(history_id,0)
        )

        #btn.command_id = history_id

        children = [
            child for child in parent.winfo_children()
            if isinstance(child, CTkButton) and child != btn
        ]
        btn.pack(anchor="w", pady=3, padx=2)

        if children:
            btn.pack_configure(before=children[-1])

        return btn

    def highlight_code():
        code = CodeBox.get("1.0", "end-1c")

        for tag in ["keyword", "string", "function", "comment", "builtin", "number"]:
            CodeBox.tag_remove(tag, "1.0", "end")

        patterns = {
            "comment": r"#.*",
            "string": r"(\".*?\"|\'.*?\')",
            "keyword": r"\b(" + "|".join(keyword.kwlist) + r")\b",
            "function": r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            "number": r"\b\d+(\.\d+)?\b",
            "builtin": r"\b(print|input|open|len|range|str|int|float|list|dict|set)\b",
        }

        for tag, pattern in patterns.items():
            for match in re.finditer(pattern, code):

                if tag == "function":
                    start, end = match.span(1)
                else:
                    start, end = match.span()

                start_index = f"1.0 + {start} chars"
                end_index = f"1.0 + {end} chars"

                CodeBox.tag_add(tag, start_index, end_index)

    def highlight_chat():
        text = ChatBox.get("1.0", "end-1c")

        for tag in ["user", "bot", "success", "link", "time"]:
            ChatBox.tag_remove(tag, "1.0", "end")

        patterns = {
            "user": r"\buser\b",
            "bot": r"\bbot\b",
            "success": r"✓.*",
            "link": r"https?://[^\s]+",
            "time": r"\b\d{1,2}:\d{2}\b",
        }

        for tag, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()

                start_index = f"1.0 + {start} chars"
                end_index = f"1.0 + {end} chars"

                ChatBox.tag_add(tag, start_index, end_index)

    def insert_to_ChatBox(text):
        ChatBox.configure(state="normal")
        ChatBox.insert(END, text)
        ChatBox.see("end")
        highlight_chat()
        ChatBox.configure(state="disabled")

    def insert_to_CodeBox(text,history_id , clear= False):
        if clear:
            CodeBox.delete("1.0", END)
        CodeBox.history_id = history_id
        CodeBox.insert(END, text)

        highlight_code()

    def clear_chat():
        global ConvoHistory
        if ChatBox.get("1.0", "end-1c") != "":
            ConvoHistory = []
            ChatBox.configure(state="normal")
            ChatBox.delete("1.0", "end")
            ChatBox.configure(state="disabled")
            insert_to_ChatBox("bot: Cleared Chat. How can I help you?\n")

    def send():
        user_text = input_entry.get().strip()
        CodeBox.Saved_ID = ""

        if user_text == "":
            return

        input_entry.delete(0, END)

        insert_to_ChatBox(f"user: {user_text}\n")


        send_btn.configure(state="disabled")
        status.configure(text="●  Status:  Generating...", text_color="#facc15")

        thread = threading.Thread(
            target=run_model_thread,
            args=(user_text,Stream),
            daemon=True
        )
        thread.start()

    def run_model_thread(user_text, Stream):
        #local or cloud
        if Settings[0]["Stream"] is False or Settings[0]["Cloud"]:
            try:
                result = model(user_text, int(maxTokensEntry.get()), float(temperatureEntry.get()), ModelMenu.get())

                root.after(0, lambda: show_model_result(result))

            except Exception as e:

                error_text = str(e)

                root.after(0, lambda: insert_to_ChatBox(f"bot: Model error, {error_text}\n"))

                root.after(0, lambda: show_model_error(error_text))
        #with stream
        else:

            try:
                stream_buffer["text"] = ""

                root.after(
                    0,
                    lambda: status.configure(
                        text="●  Status:  Metadata request...",
                        text_color="#facc15"
                    )
                )

                result = model_request(
                    user_text,
                    int(maxTokensEntry.get()),
                    float(temperatureEntry.get()),
                    ModelMenu.get(),
                    on_code_stream=stream_to_codebox
                )

                root.after(0, lambda: show_model_result(result))

            except Exception as e:
                root.after(0, lambda: insert_to_ChatBox(f"bot: Model error, {e}\n"))
                root.after(0, lambda: show_model_error(e))

    def chat_type_label_update():
        if Settings[0]["Cloud"]:
            chatTypeLabel.configure(text="Cloud")
        else:
            chatTypeLabel.configure(text="Local")

    def execute_command():

        def check_process_finished():
            global current_process

            if current_process and current_process.is_alive():
                root.after(500, check_process_finished)
            else:
                current_process = None
                ExecuteBtn.configure(state="normal", text="▶  Execute")
                CancelBtn.configure(state="disabled")

        global current_process

        code = CodeBox.get("1.0", "end-1c").strip()

        if code == "":
            return

        if current_process and current_process.is_alive():
            return

        ExecuteBtn.configure(state="disabled", text="Running...")
        CancelBtn.configure(state="normal")

        current_process = multiprocessing.Process(target=exec, args=(code,), daemon=True)

        current_process.start()
        root.after(500, check_process_finished)

    def cancel_execution():
        global current_process
        if current_process and current_process.is_alive():
            current_process.terminate()
            current_process = None

        ExecuteBtn.configure(state="normal", text="▶  Execute")
        CancelBtn.configure(state="disabled")

    def show_model_result(result):

        insert_to_CodeBox(f"{result["code"]}",History[-1]["ID"],True)

        print(result["risk"])
        print(result["request_name"])
        print(result["response"])
        print(result["icon"])

        insert_to_ChatBox(f"bot: {result["response"]}\n")
        RiskLabel.configure(text= f"Risk: {result["risk"]}")
        #print(History[-1]["ID"])
        history_button(HistoryBox, result["request_name"],History[-1]["ID"])

        status.configure(text="●  Status:  Running", text_color="#22c55e")
        send_btn.configure(state="normal")

        if autorunCheckbox.get():
            if result["risk"] == "Low":
                execute_command()

    def show_model_error(error):
        print("Model error:", error)

        status.configure(text="●  Status:  Error", text_color="#ef4444")
        send_btn.configure(state="normal")

    def save_this():
        global Saved
        for item in History:
            if item["ID"] == CodeBox.history_id:
                spec = item
                try:
                    spec["ID"] = f"{int(Saved[-1]["ID"]) +1}"
                except:
                    print("firstsave?")
                    spec["ID"] = len(Saved)
                Saved.append(spec)
                update_saved()
                saved_button(SavedCommandsBox, spec["request_name"], spec["ID"], spec["icon"])

    def show_saved():
        for item in Saved:
            saved_button(SavedCommandsBox, item["request_name"],item["ID"],item["icon"])

    def clear_command_history():
        global History

        children = [
            child for child in HistoryBox.winfo_children()
            if isinstance(child, CTkButton)
        ]
        for child in children:
            child.destroy()

    stream_buffer = {"text": ""}
    def stream_to_codebox(chunk):
        stream_buffer["text"] += chunk

        def update_box():
            CodeBox.delete("1.0", END)
            CodeBox.insert(END, stream_buffer["text"])
            CodeBox.see("end")
            highlight_code()

        root.after(0, update_box)


    def open_settings_window():
        global Settings

        def save_settings():
            global Settings
            setting = {
                "Stream": bool(StreamingCheckBox.get()),
                "MetadataModel": MetadataModelEntry.get().strip(),
                "ExtraPrompt": ExtraPromptEntry.get("1.0", "end-1c").strip(),
                "Cloud": bool(CloudCheckBox.get()),
                "CloudURL": CloudUrlEntry.get().strip(),
                "CloudAPIKey": CloudApiKeyEntry.get().strip(),
                "CloudModel": CloudModelEntry.get().strip()
            }

            Settings[0] = setting
            update_saved()
            chat_type_label_update()

            print(Settings)
            settings_window.destroy()

        settings_window = CTkToplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("420x620")
        settings_window.configure(fg_color="#080d18")
        # settings_window.resizable(False, False)
        settings_window.transient(root)
        settings_window.grab_set()
        settings_window.focus()

        HeaderFrame = CTkFrame(
            settings_window,
            fg_color="#090f1d",
            width=420,
            height=50,
            border_width=1,
            border_color="#26324a",
            corner_radius=0
        )
        HeaderFrame.place(x=0, y=0)

        CTkLabel(
            HeaderFrame,
            text="⚙  Settings",
            text_color="#e5e7eb",
            font=("Segoe UI", 18, "bold")
        ).place(x=18, y=12)

        MainFrame = CTkScrollableFrame(
            settings_window,
            fg_color="#0d1424",
            width=360,
            height=455,
            border_width=1,
            border_color="#26324a",
            corner_radius=12
        )
        MainFrame.place(x=20, y=70)

        MainFrame.grid_columnconfigure(0, weight=1)

        row = 0

        CTkLabel(
            MainFrame,
            text="General Settings",
            text_color="#c084fc",
            font=("Segoe UI", 16, "bold")
        ).grid(row=row, column=0, padx=12, pady=(18, 22), sticky="w")
        row += 1

        # STREAMING CHECKBOX
        StreamingCheckBox = CTkCheckBox(
            MainFrame,
            text="Code Streaming",
            width=330,
            height=32,
            fg_color="#6d28d9",
            hover_color="#7c3aed",
            border_color="#26324a",
            checkmark_color="#ffffff",
            text_color="#e5e7eb",
            font=("Segoe UI", 13, "bold"),
            corner_radius=6
        )
        StreamingCheckBox.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        if Settings[0]["Stream"]:
            StreamingCheckBox.select()

        CTkLabel(
            MainFrame,
            text="Streams generated code live into the CodeBox.\nDisable this if you only want final code after generation.\nMuch slower but looks cooler!",
            width=330,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # METADATA ENTRY
        CTkLabel(
            MainFrame,
            text="Metadata Model",
            text_color="#94a3b8",
            font=("Segoe UI", 12, "bold")
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        MetadataModelEntry = CTkOptionMenu(
            MainFrame,
            width=320,
            height=44,
            fg_color="#0f172a",
            button_color="#0f172a",
            button_hover_color="#1e1b4b",
            dropdown_fg_color="#0f172a",
            dropdown_hover_color="#1e1b4b",
            text_color="#e5e7eb",
            dropdown_text_color="#e5e7eb",
            font=("Segoe UI", 14),
            dropdown_font=("Segoe UI", 13),
            corner_radius=6
        )
        MetadataModelEntry.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        MetadataModelEntry.configure(values=get_ollama_models())
        MetadataModelEntry.set(Settings[0]["MetadataModel"])

        CTkLabel(
            MainFrame,
            text="Small model used for title, icon, response and risk.\nOnly relevant when streaming is Enabled.",
            width=330,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # EXTRA PROMPT
        CTkLabel(
            MainFrame,
            text="Extra Prompt",
            text_color="#94a3b8",
            font=("Segoe UI", 12, "bold")
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        ExtraPromptEntry = CTkTextbox(
            MainFrame,
            width=320,
            height=90,
            fg_color="#0f172a",
            border_color="#26324a",
            border_width=1,
            corner_radius=8,
            text_color="#e5e7eb",
            font=("Segoe UI", 13),
            wrap="word"
        )
        ExtraPromptEntry.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        ExtraPromptEntry.insert("1.0", Settings[0]["ExtraPrompt"])

        CTkLabel(
            MainFrame,
            text="Optional instructions added to the code generation prompt.\nExample: always use short variable names, avoid comments, etc.",
            width=320,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # CLOUD BOT
        CloudCheckBox = CTkCheckBox(
            MainFrame,
            text="Use Cloud Model",
            width=330,
            height=32,
            fg_color="#6d28d9",
            hover_color="#7c3aed",
            border_color="#26324a",
            checkmark_color="#ffffff",
            text_color="#e5e7eb",
            font=("Segoe UI", 13, "bold"),
            corner_radius=6
        )
        CloudCheckBox.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        if Settings[0]["Cloud"]:
            CloudCheckBox.select()

        CTkLabel(
            MainFrame,
            text="Uses an online model instead of your selected local Ollama models.\nRequires internet and may be slower, Google AI.",
            width=330,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # CLOUD API URL
        CTkLabel(
            MainFrame,
            text="Cloud API URL",
            text_color="#94a3b8",
            font=("Segoe UI", 12, "bold")
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        CloudUrlEntry = CTkEntry(
            MainFrame,
            width=320,
            height=38,
            fg_color="#0f172a",
            border_color="#26324a",
            border_width=1,
            corner_radius=8,
            text_color="#e5e7eb",
            font=("Segoe UI", 13)
        )
        CloudUrlEntry.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        CloudUrlEntry.insert(0, Settings[0]["CloudURL"])

        CTkLabel(
            MainFrame,
            text="Endpoint used when cloud mode is enabled.",
            width=320,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # CLOUD API KEY
        CTkLabel(
            MainFrame,
            text="Cloud API Key",
            text_color="#94a3b8",
            font=("Segoe UI", 12, "bold")
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        CloudApiKeyEntry = CTkEntry(
            MainFrame,
            width=320,
            height=38,
            fg_color="#0f172a",
            border_color="#26324a",
            border_width=1,
            corner_radius=8,
            text_color="#e5e7eb",
            font=("Segoe UI", 13),
            show="*"
        )
        CloudApiKeyEntry.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        CloudApiKeyEntry.insert(0, Settings[0]["CloudAPIKey"])

        CTkLabel(
            MainFrame,
            text="Stored locally in settings.json. Keep this private.",
            width=320,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 22), sticky="w")
        row += 1

        # CLOUD MODEL ENTRY
        CTkLabel(
            MainFrame,
            text="Cloud Model",
            text_color="#94a3b8",
            font=("Segoe UI", 12, "bold")
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        CloudModelEntry = CTkOptionMenu(
            MainFrame,
            width=320,
            height=44,
            fg_color="#0f172a",
            button_color="#0f172a",
            button_hover_color="#1e1b4b",
            dropdown_fg_color="#0f172a",
            dropdown_hover_color="#1e1b4b",
            text_color="#e5e7eb",
            dropdown_text_color="#e5e7eb",
            font=("Segoe UI", 14),
            dropdown_font=("Segoe UI", 13),
            corner_radius=6
        )
        CloudModelEntry.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="w")
        row += 1

        CloudModelEntry.configure(values=[
            "Gemini 3 Flash Live",
            "Gemma 3 1B IT",
            "Gemma 3 2B IT",
            "Gemma 3 4B IT",
            "Gemma 3 12B IT",
            "Gemma 3 27B IT",
            "Gemma 4 31B IT",
            "Gemini 3.1 Flash Lite preview",
        ])
        CloudModelEntry.set(Settings[0]["CloudModel"])

        CTkLabel(
            MainFrame,
            text="Online model used when Cloud Mode is enabled.\nGemma models have a much higher free request limits.",
            width=330,
            text_color="#64748b",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        ).grid(row=row, column=0, padx=12, pady=(0, 24), sticky="w")
        row += 1

        # FIXED BOTTOM BUTTONS - OUTSIDE SCROLL
        BottomFrame = CTkFrame(
            settings_window,
            fg_color="#080d18",
            width=380,
            height=40,
            corner_radius=0
        )
        BottomFrame.place(x=35, y=568)

        SaveBtn = CTkButton(
            BottomFrame,
            text="Save",
            width=120,
            height=36,
            fg_color="#6d28d9",
            hover_color="#7c3aed",
            border_width=1,
            border_color="#8b5cf6",
            text_color="white",
            font=("Segoe UI", 13, "bold"),
            corner_radius=8,
            command=save_settings
        )
        SaveBtn.place(x=110, y=0)

        CloseBtn = CTkButton(
            BottomFrame,
            text="Close",
            width=120,
            height=36,
            fg_color="#111827",
            hover_color="#1e1b4b",
            border_width=1,
            border_color="#26324a",
            text_color="#ddd6fe",
            font=("Segoe UI", 13, "bold"),
            corner_radius=8,
            command=settings_window.destroy
        )
        CloseBtn.place(x=240, y=0)


    root = CTk()
    root.geometry("1130x680")
    root.configure(fg_color="#080d18")
    root.resizable(False, False)



    #FRAMES

    HeaderFrame = CTkFrame(
        root,
        fg_color="#090f1d",  # front panel color
        width=1200,
        height=50,
        border_width=1,
        corner_radius=0,
        border_color="#26324a",  # subtle border
    )
    HeaderFrame.place(y=0, x=0)

    CTkLabel(HeaderFrame,text="🤖 BOT HELPER",font= ('bold', 18,'bold')).place(x=10, y=10)

    SavedFrame = CTkFrame(root, fg_color="#0d1424", width=250, height=630, border_width=1, border_color="#26324a",
                          corner_radius=0)
    SavedFrame.place(y=50, x=0)

    CTkLabel(SavedFrame, text="SAVED COMMANDS", text_color="#94a3b8", font=("Segoe UI", 11, "bold")).place(x=18, y=18)

    SavedCommandsBox = CTkScrollableFrame(SavedFrame, fg_color="#0d1424", width=210, height=225, border_width=1,
                                          border_color="#1e293b", corner_radius=8)
    SavedCommandsBox.place(x=14, y=45)
    SavedCommandsBox._scrollbar.grid_remove()

    deleteSavedBtn = CTkButton(SavedFrame, text="✕", fg_color="#0d1424", hover_color="#3f1d23",
                               font=("Segoe UI", 11, "bold"), width=20, height=20, border_width=1,
                               border_color="#1e293b", corner_radius=8, command=delete_saved)
    deleteSavedBtn.place(x=210, y=20)

    CTkLabel(SavedFrame, text="COMMAND HISTORY", text_color="#94a3b8", font=("Segoe UI", 11, "bold")).place(x=18, y=295)

    HistoryBox = CTkScrollableFrame(SavedFrame, fg_color="#0d1424", width=210, height=225, border_width=1,
                                    border_color="#1e293b", corner_radius=8)
    HistoryBox.place(x=14, y=322)
    HistoryBox._scrollbar.grid_remove()

    ClearHistoryBtn = CTkButton(
        SavedFrame,
        text="🗑  Clear History",
        width=205,
        height=38,
        fg_color="#2a1418",
        hover_color="#3f1d23",
        border_width=1,
        border_color="#7f1d1d",
        text_color="#fca5a5",
        font=("Segoe UI", 12, "bold"),
        corner_radius=7,
        command=clear_command_history
    )
    ClearHistoryBtn.place(x=20, y=575)



    #saved_button(SavedCommandsBox, "🌐  Open Google")


    #history_button(HistoryBox, "move mouse")



    RightBorder = CTkFrame(
        SavedFrame,
        width=2,
        height=230,
        #fg_color="#1e293b"
        fg_color = "#1e293b"
    )
    RightBorder.place(x=230, y=50)

    RightBorder = CTkFrame(
        SavedFrame,
        width=2,
        height=230,
        #fg_color="#1e293b"
        fg_color = "#1e293b"
    )

    RightBorder.place(x=230, y=328)

    #CONFIGFRAME
    ConfigFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=860,
        height=70,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    ConfigFrame.place(y=120, x=260)

    CTkLabel(ConfigFrame, text="Max Tokens", text_color="#94a3b8", font=("Segoe UI", 12, "bold")).place(x=28, y=2)
    maxTokensEntry = CTkEntry(ConfigFrame, width=190, height=36, fg_color="#0f172a", border_color="#26324a", border_width=1, corner_radius=8, text_color="#e5e7eb", font=("Segoe UI", 14))
    maxTokensEntry.place(x=28, y=24)
    maxTokensEntry.insert(0, "2000")

    CTkLabel(ConfigFrame, text="Temperature", text_color="#94a3b8", font=("Segoe UI", 12, "bold")).place(x=270, y=2)

    temperatureEntry = CTkEntry(ConfigFrame, width=190, height=36, fg_color="#0f172a", border_color="#26324a", border_width=1, corner_radius=8, text_color="#e5e7eb", font=("Segoe UI", 14))
    temperatureEntry.place(x=270, y=24)
    temperatureEntry.insert(0, "0.1")

    ResetBtn = CTkButton(ConfigFrame, text="Clear Chat", width=150, height=36, fg_color="#111827", hover_color="#1e1b4b", border_width=1, border_color="#26324a", text_color="#ddd6fe", font=("Segoe UI", 13, "bold"), command= clear_chat)
    ResetBtn.place(x=610, y=17)

    SettingsBtn = CTkButton(ConfigFrame, text="⚙", width=52, height=36, fg_color="#111827", hover_color="#1e1b4b", border_width=1, border_color="#26324a", text_color="#ddd6fe", font=("Segoe UI", 13, "bold"), command=open_settings_window)

    SettingsBtn.place(x=790, y=17)


    #CHATFRAME
    ChatFrame = CTkFrame(root,
        fg_color="#0d1424",  # front panel color
        width=425,
        height=390,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    ChatFrame.place(y=200, x=260)

    ChatTitle = CTkLabel(
        ChatFrame,
        text="💬  Chat",
        text_color="#c084fc",
        font=("Segoe UI", 18, "bold")
    )
    ChatTitle.place(x=18, y=12)

    ChatBox = CTkTextbox(
        ChatFrame,
        width=400,
        height=335,
        fg_color="#0d1424",
        border_width=0,
        corner_radius=0,
        text_color="#e5e7eb",
        font=("Segoe UI", 15),
        wrap="word",
        scrollbar_button_color="#0d1424",
        scrollbar_button_hover_color="#0d1424"
    )
    ChatBox.place(y=50, x=10)
    ChatBox.tag_config("user", foreground="#c084fc")
    ChatBox.tag_config("bot", foreground="#4ade80")
    ChatBox.tag_config("success", foreground="#22c55e")
    ChatBox.tag_config("link", foreground="#60a5fa")
    ChatBox.tag_config("time", foreground="#94a3b8")
    ChatBox.configure(state="disabled")

    chatTypeLabel = CTkLabel(ChatFrame, text="Local",text_color="#94a3b8",font=("Segoe UI", 11))
    chatTypeLabel.place(x=100,y=15)
    chat_type_label_update()



    CodeFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=425,
        height=390,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    CodeFrame.place(y=200, x=695)

    CodeTitle = CTkLabel(
        CodeFrame,
        text="</>  Code",
        text_color="#c084fc",
        font=("Segoe UI", 18, "bold")
    )
    CodeTitle.place(x=18, y=12)

    CopyCodeBtn = CTkButton(CodeFrame, text="Copy", width=85, height=32, fg_color="#111827", hover_color="#1e1b4b",
                            border_width=1, border_color="#26324a", text_color="#ddd6fe", font=("Segoe UI", 12),
                            corner_radius=8,command=lambda: pyperclip.copy(CodeBox.get("1.0", "end-1c")))
    CopyCodeBtn.place(x=320,y=10)

    autorunCheckbox = CTkCheckBox(CodeFrame, text="Auto-run", width=95, height=24, fg_color="#6d28d9",
                                  hover_color="#7c3aed", border_color="#26324a", checkmark_color="#ffffff",
                                  text_color="#ddd6fe", font=("Segoe UI", 11, "bold"), corner_radius=5)
    autorunCheckbox.place(x=225, y=15)

    CodeBox = CTkTextbox(CodeFrame, width=400, height=230, fg_color="#0b1220", border_width=1, border_color="#26324a",
                         corner_radius=10, text_color="#e5e7eb", font=("Consolas", 12),
                         scrollbar_button_color="#1e293b", scrollbar_button_hover_color="#334155", wrap="none")
    CodeBox.place(x=10, y=50)
    CodeBox.tag_config("keyword", foreground="#c084fc")
    CodeBox.tag_config("string", foreground="#22c55e")
    CodeBox.tag_config("function", foreground="#60a5fa")
    CodeBox.tag_config("comment", foreground="#64748b")
    CodeBox.tag_config("builtin", foreground="#fb7185")
    CodeBox.tag_config("number", foreground="#facc15")

    ExecuteBtn = CTkButton(CodeFrame, text="▶  Execute", width=125, height=42, fg_color="#6d28d9",
                           hover_color="#7c3aed", text_color="white", font=("Segoe UI", 13, "bold"), corner_radius=8,command= execute_command)
    ExecuteBtn.place(x=10, y=292)

    SaveCodeBtn = CTkButton(CodeFrame, text="💾  Save", width=125, height=42, fg_color="#111827", hover_color="#1e1b4b",
                            border_width=1, border_color="#26324a", text_color="#e5e7eb", font=("Segoe UI", 13, "bold"),
                            corner_radius=8, command= save_this)
    SaveCodeBtn.place(x=147, y=292)

    CancelBtn = CTkButton(CodeFrame, text="✕  Cancel", width=125, height=42, fg_color="#2a1418", hover_color="#3f1d23",
                          border_width=1, border_color="#7f1d1d", text_color="#fca5a5", font=("Segoe UI", 13, "bold"),
                          corner_radius=8, command= cancel_execution)
    CancelBtn.place(x=284, y=292)
    CancelBtn.configure(state="disabled")

    WarningLabel = CTkLabel(
        CodeFrame,
        text="🛡  Code is generated by AI. Please review before executing.",
        text_color="#94a3b8",
        font=("Segoe UI", 11)
    )
    WarningLabel.place(x=14, y=345)

    RiskLabel = CTkLabel(
        CodeFrame,
        text="Risk: Low",
        text_color="#94a3b8",
        font=("Segoe UI", 11)
    )
    RiskLabel.place(x=330, y=345)


    inputFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=860,
        height=70,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    inputFrame.place(y=600, x=260)

    status = CTkLabel(
        root,
        text="●  Status:  Running",
        text_color="#22c55e",
        font=("Segoe UI", 17, "bold")
    )
    status.place(x=260, y=74)

    input_entry = CTkEntry(
        inputFrame,
        placeholder_text="Type your command here...",
        height=46,
        width=705,
        fg_color="#0f172a",
        border_color="#6d28d9",
        text_color='white',
        placeholder_text_color='grey',
        font=("Segoe UI", 15)
    )
    input_entry.place(x= 10,y=12)
    input_entry.bind("<Return>",lambda event: send())



    send_btn = CTkButton(
        inputFrame,
        text="➤  Send",
        width=130,
        height=46,
        fg_color="#6d28d9",
        hover_color="#7c3aed",
        text_color="white",
        font=("Segoe UI", 15, "bold"),
        command=lambda: send()
    )
    send_btn.place(x= 720,y=12)




    ModelMenu = CTkOptionMenu(
        root,
        width=330,
        height=44,
        fg_color="#0f172a",
        button_color="#0f172a",
        button_hover_color="#1e1b4b",
        dropdown_fg_color="#0f172a",
        dropdown_hover_color="#1e1b4b",
        text_color="#e5e7eb",
        dropdown_text_color="#e5e7eb",
        font=("Segoe UI", 14),
        dropdown_font=("Segoe UI", 13),
        corner_radius=6
    )

    ModelMenu.place(x=760, y=62)
    ModelMenu.configure(values= get_ollama_models())
    CTkLabel(root,text="Local Model: ",text_color="#94a3b8", font=("Segoe UI", 16, "bold")).place(x=650, y=70)



    ModelMenu.set(get_ollama_models()[0])

    show_saved()





    root.mainloop()

if __name__ == '__main__':
    main()
